import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from dotenv import load_dotenv
from pdf_generator import generate_essay_pdf
from database import (
    init_db,
    create_essay as db_create_essay,
    get_essay,
    update_essay,
    add_partner,
    get_user_essays,
    get_user_joined_essays,
    get_all_essays,
    set_user_session,
    get_user_session,
    clear_user_session,
    check_partner_exists,
    get_available_essays,
)
import logging
import json

# Load environment variables from .env file
load_dotenv(override=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Support both TELEGRAM_BOT_TOKEN and TELEGRAM_TOKEN
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TOKEN or TOKEN == "your_telegram_bot_token_here":
    logger.error("❌ No valid Telegram token found. Please set TELEGRAM_TOKEN or TELEGRAM_BOT_TOKEN in environment")
    exit(1)

WAITING_FOR_PARTNER = 1
WRITING_FIRST = 2
WAITING_FOR_PARTNER_TURN = 3
WRITING_DEVELOPMENT = 4
CHOOSE_ANONYMITY = 5
CHOOSE_JOIN_ANONYMITY = 6

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - shows main menu"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    keyboard = [
        [InlineKeyboardButton("📝 Create New Essay", callback_data="create_essay")],
        [InlineKeyboardButton("🔍 Browse Topics", callback_data="browse_essays")],
        [InlineKeyboardButton("📂 My Created Essays", callback_data="my_essays")],
        [InlineKeyboardButton("👥 My Joined Essays", callback_data="my_joined_essays")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Welcome, {username}!\n\n"
        "🎯 Collaborative Essay Writing Bot\n\n"
        "Write essays together with friends!\n"
        "Take turns writing (< 50 words per turn)\n\n"
        "What would you like to do?",
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_PARTNER

async def browse_essays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available essays looking for partners"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    available = get_available_essays()
    
    # Filter out essays created by the user
    available = [e for e in available if e['creator_id'] != user_id]
    
    if not available:
        await query.edit_message_text(
            "🔍 No essays available right now!\n\n"
            "Create your own essay or wait for others to post topics.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
            ])
        )
        return WAITING_FOR_PARTNER
    
    text = "🔍 **Available Essays Looking for Partners:**\n\n"
    buttons = []
    
    for i, essay in enumerate(available, 1):
        creator_info = "🔐 Anonymous" if essay.get('is_anonymous') else f"by {essay['creator_name']}"
        text += f"{i}. 📝 {essay['topic']}\n   {creator_info}\n   {len(essay.get('first_content', '').split())} words\n\n"
        buttons.append([InlineKeyboardButton(f"Join: {essay['topic'][:30]}", callback_data=f"join_essay_{essay['id']}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return WAITING_FOR_PARTNER

async def join_essay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask if user wants to join anonymously"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essay_id = query.data.split('_', 2)[2]
    
    essay = get_essay(essay_id)
    
    if not essay:
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    if essay['status'] not in ['waiting_partner', 'in_progress']:
        await query.edit_message_text("❌ This essay is no longer accepting partners!")
        return WAITING_FOR_PARTNER
    
    # Check if already joined
    if check_partner_exists(essay_id, user_id):
        await query.edit_message_text("❌ You already joined this essay!")
        return WAITING_FOR_PARTNER
    
    # Check if essay has reached max partners
    if len(essay.get('partners', [])) > 0:
        await query.edit_message_text("❌ This essay already has a partner!")
        return WAITING_FOR_PARTNER
    
    # Store essay_id in context for the next step
    context.user_data['joining_essay_id'] = essay_id
    
    # Ask about anonymity
    keyboard = [
        [InlineKeyboardButton("👤 Public (Show my name)", callback_data="join_anon_no")],
        [InlineKeyboardButton("🔐 Anonymous (Hide my name)", callback_data="join_anon_yes")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 Topic: {essay['topic']}\n"
        f"Opening: {essay['first_content']}\n\n"
        "Would you like to join this essay anonymously?",
        reply_markup=reply_markup
    )
    
    return CHOOSE_JOIN_ANONYMITY

async def choose_join_anonymity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle join anonymity choice and complete the join"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    is_anonymous = query.data == "join_anon_yes"
    essay_id = context.user_data.get('joining_essay_id')
    
    essay = get_essay(essay_id)
    if not essay:
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    # Add partner with anonymity setting
    add_partner(essay_id, user_id, username, is_anonymous=is_anonymous)
    update_essay(essay_id, status='in_progress')
    
    creator_info = "🔐 Anonymous" if essay.get('is_anonymous') else f"by {essay['creator_name']}"
    partner_mode = "🔐 Anonymously" if is_anonymous else "👤 Publicly"
    
    await query.edit_message_text(
        f"✅ Successfully joined {partner_mode}!\n\n"
        f"📝 Topic: {essay['topic']}\n"
        f"   {creator_info}\n"
        f"Opening: {essay['first_content']}\n\n"
        "👉 Wait for your partner to continue writing or check your joined essays to start!"
    )
    
    # Notify creator
    partner_display = "Someone" if is_anonymous else username
    await context.bot.send_message(
        chat_id=essay['creator_id'],
        text=f"🔔 PARTNER JOINED!\n\n"
        f"📝 {partner_display} joined your essay: {essay['topic']}\n\n"
        f"Now write your next part (less than 50 words)!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Continue Writing", callback_data=f"continue_{essay_id}")],
        ])
    )
    
    context.user_data.pop('joining_essay_id', None)
    return WAITING_FOR_PARTNER

async def create_essay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start essay creation process - ask about anonymity"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👤 Public (Show my name)", callback_data="anon_no")],
        [InlineKeyboardButton("🔐 Anonymous (Hide my name)", callback_data="anon_yes")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 Would you like to post this essay anonymously?\n\n"
        "Public: Others will see your name in the Browse section\n"
        "Anonymous: Only the topic will be visible",
        reply_markup=reply_markup
    )
    
    return CHOOSE_ANONYMITY

async def choose_anonymity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle anonymity choice and ask for topic"""
    query = update.callback_query
    await query.answer()
    
    is_anonymous = query.data == "anon_yes"
    context.user_data['is_anonymous'] = is_anonymous
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mode = "🔐 Anonymous" if is_anonymous else "👤 Public"
    await query.edit_message_text(
        f"{mode} Mode\n\n📝 What's the topic of your essay?",
        reply_markup=reply_markup
    )
    
    return WRITING_FIRST

async def handle_first_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle topic and first paragraph"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    text = update.message.text
    
    if text.startswith('/'):
        return WRITING_FIRST
    
    # Check if this is topic or first paragraph
    if 'topic' not in context.user_data:
        # This is the topic
        context.user_data['topic'] = text
        await update.message.reply_text(
            f"📚 Topic: {text}\n\n"
            "Now write your opening paragraph (less than 50 words):"
        )
        return WRITING_FIRST
    else:
        # This is the first paragraph
        topic = context.user_data['topic']
        word_count = len(text.split())
        
        if word_count > 50:
            await update.message.reply_text(
                f"❌ Too long! Your paragraph has {word_count} words (max 50).\n"
                "Please write a shorter version:"
            )
            return WRITING_FIRST
        
        # Create essay in database
        essay_id = f"essay_{user_id}_{datetime.now().timestamp()}"
        is_anonymous = context.user_data.get('is_anonymous', False)
        db_create_essay(essay_id, user_id, username, topic)
        update_essay(essay_id, first_content=text, status='waiting_partner', is_anonymous=is_anonymous)
        
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("📋 Share Essay Link", callback_data=f"share_{essay_id}")],
            [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Great opening paragraph! ({word_count} words)\n\n"
            f"📝 Topic: {topic}\n"
            f"Opening: {text}\n\n"
            f"🔐 Join Code: `{essay_id}`\n"
            f"📝 Tell your partner to message: `/join {essay_id}`\n\n"
            "Or share the essay link with your partner so they can join!",
            reply_markup=reply_markup
        )
        
        return WAITING_FOR_PARTNER

async def join_essay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join an essay as a partner"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    essay_id = update.message.text.split()[-1] if ' ' in update.message.text else update.message.text
    
    essay = get_essay(essay_id)
    
    if not essay:
        await update.message.reply_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    if essay['status'] not in ['waiting_partner', 'in_progress']:
        await update.message.reply_text("❌ This essay is no longer accepting partners!")
        return WAITING_FOR_PARTNER
    
    # Check if already joined
    if check_partner_exists(essay_id, user_id):
        await update.message.reply_text("❌ You already joined this essay!")
        return WAITING_FOR_PARTNER
    
    # Check if essay has reached max partners
    if len(essay.get('partners', [])) > 0:
        await update.message.reply_text("❌ This essay already has a partner!")
        return WAITING_FOR_PARTNER
    
    # Add partner
    add_partner(essay_id, user_id, username)
    update_essay(essay_id, status='in_progress')
    
    await update.message.reply_text(
        f"✅ Successfully joined!\n\n"
        f"📝 Topic: {essay['topic']}\n"
        f"Opening: {essay['first_content']}\n\n"
        "👉 Wait for your partner to continue writing!"
    )
    
    # Notify creator
    await context.bot.send_message(
        chat_id=essay['creator_id'],
        text=f"🔔 PARTNER JOINED!\n\n"
        f"📝 {username} joined your essay: {essay['topic']}\n\n"
        f"Now write your next part (less than 50 words)!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Continue Writing", callback_data=f"continue_{essay_id}")],
        ])
    )
    
    return WAITING_FOR_PARTNER

async def my_essays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's created essays"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essays = get_user_essays(user_id)
    
    if not essays:
        await query.edit_message_text(
            "📂 No essays created yet!\n\n"
            "Create your first essay to get started.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
            ])
        )
        return WAITING_FOR_PARTNER
    
    text = "📂 **My Created Essays:**\n\n"
    for i, essay in enumerate(essays, 1):
        status_emoji = "✅" if essay['status'] == 'complete' else "⏳"
        text += f"{i}. {essay['topic']}\n   Status: {status_emoji} {essay['status'].replace('_', ' ').title()}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return WAITING_FOR_PARTNER

async def my_joined_essays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show essays where user is a partner"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essays = get_user_joined_essays(user_id)
    
    if not essays:
        await query.edit_message_text(
            "👥 You haven't joined any essays yet!\n\n"
            "Ask a friend to share an essay link or use /join command.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
            ])
        )
        return WAITING_FOR_PARTNER
    
    text = "👥 **My Joined Essays:**\n\n"
    buttons = []
    
    for i, essay in enumerate(essays, 1):
        # Determine turn
        last_writer = essay.get('last_writer_id')
        if essay['status'] == 'complete':
            turn_text = "✅ Complete"
        elif last_writer == user_id:
            turn_text = "⏳ Waiting for creator..."
        elif last_writer == essay['creator_id'] or last_writer is None:
            turn_text = "🎯 Your Turn!"
        else:
            turn_text = "⏳ Waiting..."
        
        status_emoji = "✅" if essay['status'] == 'complete' else "⏳"
        text += f"{i}. {essay['topic']}\n   by {essay['creator_name']} - {status_emoji} {essay['status'].replace('_', ' ').title()}\n   Turn: {turn_text}\n\n"
        
        # Add continue button only if it's user's turn and essay is not complete
        if turn_text == "🎯 Your Turn!" and essay['status'] != 'complete':
            buttons.append([InlineKeyboardButton(f"✍️ Continue: {essay['topic']}", callback_data=f"continue_{essay['id']}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return WAITING_FOR_PARTNER

async def continue_writing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display essay for partner to continue writing"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essay_id = query.data.split('_', 1)[1]
    
    logger.info(f"✍️ Continue writing: user_id={user_id}, essay_id={essay_id}")
    
    essay = get_essay(essay_id)
    if not essay:
        logger.error(f"❌ Essay not found: {essay_id}")
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    logger.info(f"✍️ Essay found: {essay['topic']}, last_writer={essay.get('last_writer_id')}")
    
    # Check authorization
    partner_ids = [str(p['id']) for p in essay.get('partners', [])]
    if str(user_id) not in partner_ids and essay['creator_id'] != user_id:
        logger.error(f"❌ Authorization failed for user {user_id}")
        await query.edit_message_text("❌ You don't have permission to write this essay!")
        return WAITING_FOR_PARTNER
    
    # Check if it's user's turn
    last_writer = essay.get('last_writer_id')
    if str(last_writer) == str(user_id):
        logger.warning(f"⚠️ Not user's turn: last_writer={last_writer}, current_user={user_id}")
        await query.edit_message_text("❌ It's not your turn yet! Wait for your partner.")
        return WAITING_FOR_PARTNER
    
    set_user_session(user_id, essay_id)
    context.user_data['current_essay_id'] = essay_id
    
    content = essay.get('first_content', '')
    if essay.get('second_content'):
        content += f"\n\n{essay['second_content']}"
    
    word_count = len(content.split())
    
    logger.info(f"✍️ Showing essay for writing: {word_count} words")
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 Current Essay ({word_count} words):\n\n"
        f"{content}\n\n"
        "---\n\n"
        "Ready to write your contribution (less than 50 words)?",
        reply_markup=reply_markup
    )
    
    return WRITING_DEVELOPMENT

async def handle_development(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle essay continuation"""
    user_id = update.effective_user.id
    text = update.message.text
    # Try to get essay_id from context first, then from database session
    essay_id = context.user_data.get('current_essay_id') or get_user_session(user_id)
    
    essay = get_essay(essay_id)
    if not essay:
        logger.error(f"❌ Essay not found: {essay_id}")
        await update.message.reply_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    # Validate authorization
    partner_ids = [str(p['id']) for p in essay.get('partners', [])]
    if str(user_id) not in partner_ids and essay['creator_id'] != user_id:
        await update.message.reply_text("❌ You don't have permission!")
        return WAITING_FOR_PARTNER
    
    # Enforce turn-based alternation - check if it's this user's turn
    last_writer_id = essay.get('last_writer_id')
    if last_writer_id and str(last_writer_id) == str(user_id):
        await update.message.reply_text(
            "❌ It's not your turn yet! Wait for your partner to write first."
        )
        return WRITING_DEVELOPMENT
    
    word_count = len(text.split())
    if word_count > 50:
        await update.message.reply_text(
            f"❌ Too long! You have {word_count} words (max 50).\n"
            "Please write a shorter version:"
        )
        return WRITING_DEVELOPMENT
    
    # Store text temporarily in context for confirmation
    context.user_data['pending_text'] = text
    context.user_data['pending_word_count'] = word_count
    
    # Show preview and confirm
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Submit", callback_data=f"confirm_write_{essay_id}")],
        [InlineKeyboardButton("✏️ Edit", callback_data=f"continue_{essay_id}")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📝 Your contribution ({word_count} words):\n\n"
        f"{text}\n\n"
        "Confirm to submit your writing?",
        reply_markup=reply_markup
    )
    
    return WRITING_DEVELOPMENT

async def confirm_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and save the written text"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    essay_id = query.data.split('_', 2)[2]
    
    logger.info(f"📝 Confirm write started: user_id={user_id}, essay_id={essay_id}")
    
    # Get pending text from context
    pending_text = context.user_data.get('pending_text')
    pending_word_count = context.user_data.get('pending_word_count', 0)
    
    if not pending_text:
        await query.edit_message_text("❌ No text to submit!")
        return WAITING_FOR_PARTNER
    
    essay = get_essay(essay_id)
    if not essay:
        logger.error(f"❌ Essay not found: {essay_id}")
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    logger.info(f"📝 Essay found: {essay['topic']}, creator_id={essay['creator_id']}")
    
    # Update essay - append the text
    if essay['creator_id'] == user_id and not essay.get('second_content'):
        logger.info(f"📝 Updating first_content for essay {essay_id}")
        update_essay(essay_id, first_content=essay['first_content'] + ' ' + pending_text)
    else:
        logger.info(f"📝 Updating second_content for essay {essay_id}")
        second_content = essay.get('second_content', '')
        if second_content:
            second_content += ' ' + pending_text
        else:
            second_content = pending_text
        update_essay(essay_id, second_content=second_content)
    
    update_essay(essay_id, last_writer_id=user_id, finish_requests='{}')
    
    # Refresh essay from database
    essay = get_essay(essay_id)
    logger.info(f"📝 Essay refreshed, partners count: {len(essay.get('partners', []))}")
    
    # Determine next writer
    if essay['creator_id'] == user_id:
        # Current user is creator, next writer is partner
        if essay.get('partners') and len(essay['partners']) > 0:
            next_writer_id = essay['partners'][0]['id']
            next_writer_name = essay['partners'][0]['name']
        else:
            logger.error(f"❌ No partners found for essay {essay_id}")
            next_writer_id = None
            next_writer_name = "Unknown"
    else:
        # Current user is partner, next writer is creator
        next_writer_id = essay['creator_id']
        next_writer_name = essay['creator_name']
    
    logger.info(f"🔔 Next writer: {next_writer_name} (ID: {next_writer_id})")
    
    keyboard = [
        [InlineKeyboardButton("🏁 Request to Finish", callback_data=f"finish_request_{essay_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Great contribution! ({pending_word_count} words)\n\n"
        f"📝 Essay: {essay['topic']}\n"
        f"Next turn: {next_writer_name}",
        reply_markup=reply_markup
    )
    
    # Build full content for notification
    full_content = essay.get('first_content', '')
    if essay.get('second_content'):
        full_content += f"\n\n{essay['second_content']}"
    
    total_words = len(full_content.split())
    content_preview = full_content[:200] + "..." if len(full_content) > 200 else full_content
    
    # Send notification to partner EVERY TIME - THIS IS MANDATORY
    if next_writer_id:
        try:
            logger.info(f"🔔 Sending notification to {next_writer_id}...")
            message = await context.bot.send_message(
                chat_id=next_writer_id,
                text=f"🔔 YOUR TURN!\n\n"
                f"Essay: {essay['topic']}\n\n"
                f"Current content ({total_words} words):\n{content_preview}\n\n"
                f"Ready to add your part?\n\n"
                f"⏰ Update at {datetime.now().strftime('%H:%M:%S')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ Continue Writing", callback_data=f"continue_{essay_id}")],
                ])
            )
            logger.info(f"✅ Turn notification successfully sent to {next_writer_name} (ID: {next_writer_id})")
        except Exception as e:
            logger.error(f"❌ Error sending notification to {next_writer_id}: {type(e).__name__}: {e}")
    else:
        logger.warning(f"⚠️  No valid next_writer_id to send notification")
    
    clear_user_session(user_id)
    context.user_data.clear()
    return WAITING_FOR_PARTNER

async def finish_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request to finish essay"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    essay_id = query.data.split('_', 2)[2]
    
    essay = get_essay(essay_id)
    if not essay:
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    # Get current finish requests
    finish_requests = essay.get('finish_requests', {})
    if not isinstance(finish_requests, dict):
        finish_requests = json.loads(finish_requests) if isinstance(finish_requests, str) else {}
    
    finish_requests[str(user_id)] = True
    finish_requests_json = json.dumps(finish_requests)
    update_essay(essay_id, finish_requests=finish_requests_json)
    
    # Check if both accepted
    if len(finish_requests) == 2 and all(finish_requests.values()):
        update_essay(essay_id, status='complete')
        
        # Generate PDF
        try:
            pdf_file = generate_essay_pdf(essay)
            logger.info(f"✅ PDF generated: {pdf_file}")
        except Exception as e:
            logger.error(f"❌ Error generating PDF: {e}")
            pdf_file = None
        
        await query.edit_message_text(
            f"🎉 Essay Complete!\n\n"
            f"📝 Topic: {essay['topic']}\n\n"
            "✅ Both partners accepted. Generating PDF..."
        )
        
        # Send PDF to current user
        if pdf_file and os.path.exists(pdf_file):
            try:
                with open(pdf_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=f,
                        filename=f"{essay['topic'].replace(' ', '_')}.pdf",
                        caption="📄 Your essay PDF"
                    )
                    logger.info(f"✅ PDF sent to user {user_id}")
            except Exception as e:
                logger.error(f"❌ Error sending PDF to {user_id}: {e}")
        
        # Send to other partner
        other_user_id = essay['creator_id'] if user_id != essay['creator_id'] else essay['partners'][0]['id']
        await context.bot.send_message(
            chat_id=other_user_id,
            text=f"🎉 Essay Complete!\n\n"
            f"📝 Topic: {essay['topic']}\n\n"
            "✅ Both partners accepted. Generating PDF..."
        )
        
        # Send PDF to other partner
        if pdf_file and os.path.exists(pdf_file):
            try:
                with open(pdf_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=other_user_id,
                        document=f,
                        filename=f"{essay['topic'].replace(' ', '_')}.pdf",
                        caption="📄 Your essay PDF"
                    )
                    logger.info(f"✅ PDF sent to user {other_user_id}")
            except Exception as e:
                logger.error(f"❌ Error sending PDF to {other_user_id}: {e}")
    else:
        # Get other partner
        if user_id == essay['creator_id']:
            other_user_id = essay['partners'][0]['id']
            other_username = essay['partners'][0]['name']
        else:
            other_user_id = essay['creator_id']
            other_username = essay['creator_name']
        
        await query.edit_message_text(
            f"🏁 Finish Request Sent!\n\n"
            f"Waiting for {other_username} to accept...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
            ])
        )
        
        # Send request to other partner
        keyboard = [
            [InlineKeyboardButton("✅ Accept & Finish", callback_data=f"accept_finish_{essay_id}")],
            [InlineKeyboardButton("❌ Decline", callback_data=f"decline_finish_{essay_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=other_user_id,
            text=f"❓ {username} wants to finish the essay!\n\n"
            f"📝 Topic: {essay['topic']}\n\n"
            "Do you accept?",
            reply_markup=reply_markup
        )
    
    return WAITING_FOR_PARTNER

async def accept_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept finish request"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essay_id = query.data.split('_', 2)[2]
    
    essay = get_essay(essay_id)
    if not essay:
        await query.edit_message_text("❌ Essay not found!")
        return WAITING_FOR_PARTNER
    
    # Update finish requests
    finish_requests = essay.get('finish_requests', {})
    if not isinstance(finish_requests, dict):
        finish_requests = json.loads(finish_requests) if isinstance(finish_requests, str) else {}
    
    finish_requests[str(user_id)] = True
    finish_requests_json = json.dumps(finish_requests)
    update_essay(essay_id, finish_requests=finish_requests_json)
    
    # Check if both accepted
    if len(finish_requests) == 2 and all(finish_requests.values()):
        update_essay(essay_id, status='complete')
        
        # Generate PDF
        try:
            pdf_file = generate_essay_pdf(essay)
            logger.info(f"✅ PDF generated: {pdf_file}")
        except Exception as e:
            logger.error(f"❌ Error generating PDF: {e}")
            pdf_file = None
        
        await query.edit_message_text(
            f"🎉 Essay Complete!\n\n"
            f"📝 Topic: {essay['topic']}\n\n"
            "✅ Both partners accepted. Generating PDF..."
        )
        
        # Send PDF to current user (who accepted)
        if pdf_file and os.path.exists(pdf_file):
            try:
                with open(pdf_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=f,
                        filename=f"{essay['topic'].replace(' ', '_')}.pdf",
                        caption="📄 Your essay PDF"
                    )
                    logger.info(f"✅ PDF sent to user {user_id}")
            except Exception as e:
                logger.error(f"❌ Error sending PDF to {user_id}: {e}")
        
        # Send to other partner (who requested finish)
        other_user_id = essay['creator_id'] if user_id != essay['creator_id'] else essay['partners'][0]['id']
        await context.bot.send_message(
            chat_id=other_user_id,
            text=f"🎉 Essay Complete!\n\n"
            f"📝 Topic: {essay['topic']}\n\n"
            "✅ Both partners accepted. Generating PDF..."
        )
        
        # Send PDF to other partner
        if pdf_file and os.path.exists(pdf_file):
            try:
                with open(pdf_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=other_user_id,
                        document=f,
                        filename=f"{essay['topic'].replace(' ', '_')}.pdf",
                        caption="📄 Your essay PDF"
                    )
                    logger.info(f"✅ PDF sent to user {other_user_id}")
            except Exception as e:
                logger.error(f"❌ Error sending PDF to {other_user_id}: {e}")
    else:
        await query.edit_message_text(
            "✅ You accepted the finish request!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
            ])
        )
    
    return WAITING_FOR_PARTNER

async def decline_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Decline finish request"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    essay_id = query.data.split('_', 2)[2]
    
    # Clear finish requests
    update_essay(essay_id, finish_requests='{}')
    
    await query.edit_message_text(
        "❌ Finish request declined.\n\n"
        "Continue writing when ready!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")],
        ])
    )
    
    return WAITING_FOR_PARTNER

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 Create New Essay", callback_data="create_essay")],
        [InlineKeyboardButton("🔍 Browse Topics", callback_data="browse_essays")],
        [InlineKeyboardButton("📂 My Created Essays", callback_data="my_essays")],
        [InlineKeyboardButton("👥 My Joined Essays", callback_data="my_joined_essays")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎯 Main Menu\n\n"
        "What would you like to do?",
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_PARTNER

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = (
        "📖 Help\n\n"
        "Commands:\n"
        "/start - Main menu\n"
        "/help - Show this help\n\n"
        "How to use:\n"
        "1. Create a new essay with a topic\n"
        "2. Write opening paragraph (< 50 words)\n"
        "3. Share essay link with partner\n"
        "4. Partner joins the essay\n"
        "5. Take turns writing (< 50 words each turn)\n"
        "6. Request to finish when done\n"
        "7. Download as PDF\n\n"
        "Rules:\n"
        "• Max 50 words per contribution\n"
        "• Alternating turns only\n"
        "• Both partners must accept to finish"
    )
    await update.message.reply_text(help_text)

def main():
    """Main function to start the bot"""
    # Initialize database
    try:
        init_db()
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.error("Make sure PostgreSQL is running and configured correctly in .env")
        exit(1)
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_PARTNER: [
                CallbackQueryHandler(create_essay, pattern="^create_essay$"),
                CallbackQueryHandler(browse_essays, pattern="^browse_essays$"),
                CallbackQueryHandler(my_essays, pattern="^my_essays$"),
                CallbackQueryHandler(my_joined_essays, pattern="^my_joined_essays$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(join_essay_callback, pattern="^join_essay_"),
                CallbackQueryHandler(continue_writing, pattern="^continue_"),
                CallbackQueryHandler(confirm_write, pattern="^confirm_write_"),
                CallbackQueryHandler(finish_request, pattern="^finish_request_"),
                CallbackQueryHandler(accept_finish, pattern="^accept_finish_"),
                CallbackQueryHandler(decline_finish, pattern="^decline_finish_"),
            ],
            CHOOSE_ANONYMITY: [
                CallbackQueryHandler(choose_anonymity, pattern="^anon_"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            CHOOSE_JOIN_ANONYMITY: [
                CallbackQueryHandler(choose_join_anonymity, pattern="^join_anon_"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            WRITING_FIRST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_first_write),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(create_essay, pattern="^create_essay$"),
            ],
            WRITING_DEVELOPMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_development),
                CallbackQueryHandler(confirm_write, pattern="^confirm_write_"),
                CallbackQueryHandler(continue_writing, pattern="^continue_"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
        },
        fallbacks=[CommandHandler("help", help_command)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join_essay))
    
    # External handlers for notification flow - these work outside conversation state
    # These are added AFTER the ConversationHandler, so they only fire if ConversationHandler doesn't handle the update
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(browse_essays, pattern="^browse_essays$"))
    app.add_handler(CallbackQueryHandler(join_essay_callback, pattern="^join_essay_"))
    app.add_handler(CallbackQueryHandler(choose_join_anonymity, pattern="^join_anon_"))
    app.add_handler(CallbackQueryHandler(continue_writing, pattern="^continue_"))
    app.add_handler(CallbackQueryHandler(confirm_write, pattern="^confirm_write_"))
    app.add_handler(CallbackQueryHandler(finish_request, pattern="^finish_request_"))
    app.add_handler(CallbackQueryHandler(accept_finish, pattern="^accept_finish_"))
    app.add_handler(CallbackQueryHandler(decline_finish, pattern="^decline_finish_"))
    
    # External message handler for development text - catches messages from users with active sessions
    async def handle_development_external(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle development messages from external flow"""
        user_id = update.effective_user.id
        essay_id = get_user_session(user_id)
        
        if essay_id:
            logger.info(f"📝 External message handler: user_id={user_id}, essay_id={essay_id}")
            context.user_data['current_essay_id'] = essay_id
            await handle_development(update, context)
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_development_external))
    
    logger.info("✅ Bot started successfully!")
    logger.info("🤖 Using PostgreSQL database")
    app.run_polling()

if __name__ == "__main__":
    main()
