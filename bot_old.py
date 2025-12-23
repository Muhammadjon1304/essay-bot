import os
import json
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
import logging

# Load environment variables from .env file
load_dotenv(override=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN or TOKEN == "your_telegram_bot_token_here":
    logger.error("❌ No valid Telegram token found. Please set TELEGRAM_BOT_TOKEN in .env file")
    exit(1)
DATA_FILE = "essays.json"

WAITING_FOR_PARTNER = 1
WRITING_FIRST = 2
WAITING_FOR_PARTNER_TURN = 3
WRITING_DEVELOPMENT = 4

def load_essays():
    """Load essays from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_essays(essays):
    """Save essays to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(essays, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    keyboard = [
        [InlineKeyboardButton("📝 Create New Essay", callback_data="create_essay")],
        [InlineKeyboardButton("📂 My Created Essays", callback_data="my_essays")],
        [InlineKeyboardButton("👥 My Joined Essays", callback_data="my_joined_essays")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 Essay Writing Bot\n\n"
        "Collaborate with a partner to write essays together!\n"
        "1. One person writes opening (< 50 words)\n"
        "2. Partner adds their part (< 50 words)\n"
        "3. Alternate turns, then download as PDF",
        reply_markup=reply_markup
    )
    return WAITING_FOR_PARTNER

async def create_essay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle create essay callback"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📌 What is the essay topic?\n\n"
        "Enter a topic or title for your essay:",
        reply_markup=reply_markup,
        parse_mode=None
    )
    
    context.user_data['action'] = 'waiting_for_topic'
    return WRITING_FIRST

async def my_essays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's created essays"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    essays = load_essays()
    
    user_essays = []
    for essay_id, essay in essays.items():
        if str(essay['creator_id']) == user_id:
            user_essays.append(essay)
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not user_essays:
        await query.edit_message_text("📭 You don't have any created essays yet.", reply_markup=reply_markup)
        return
    
    essay_list = ""
    for i, essay in enumerate(user_essays, 1):
        status = "✅ Complete" if essay.get('status') == 'complete' else "⏳ Pending"
        essay_list += f"{i}. {essay['topic']} - {status}\n"
    
    await query.edit_message_text(f"📚 Your Created Essays\n\n{essay_list}", reply_markup=reply_markup, parse_mode=None)

async def my_joined_essays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show essays user joined as partner"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    essays = load_essays()
    
    # Find essays where user is a partner
    joined_essays = []
    for essay_id, essay in essays.items():
        partners = essay.get('partners', [])
        for partner in partners:
            if str(partner['id']) == user_id:
                essay['id'] = essay_id  # Store ID for later use
                joined_essays.append(essay)
                break
    
    if not joined_essays:
        await query.edit_message_text("👥 You haven't joined any essays yet.\n\nUse /join <essay_id> to join!")
        return
    
    # Build keyboard with continue buttons for essays where it's user's turn
    keyboard = []
    essay_list = ""
    
    for i, essay in enumerate(joined_essays, 1):
        creator_name = essay.get('creator_name', 'Unknown')
        status = "✅ Complete" if essay.get('status') == 'complete' else "⏳ Pending"
        
        # Determine whose turn it is
        last_writer = essay.get('last_writer_id')
        creator_id = str(essay.get('creator_id'))
        partner_id = user_id
        essay_id = essay.get('id')
        
        if essay.get('status') == 'complete':
            turn_info = "✅ Complete"
            is_your_turn = False
        elif not last_writer or last_writer == creator_id:
            # Either not started or creator just wrote - it's partner's turn
            turn_info = "Your Turn!"
            is_your_turn = True
        else:
            # Partner (you) wrote last - it's creator's turn to write
            turn_info = "Waiting for creator..."
            is_your_turn = False
        
        essay_list += f"{i}. {essay['topic']}\n   by {creator_name} - {status}\n   Turn: {turn_info}\n"
        
        # Add continue button for essays where it's user's turn
        if is_your_turn:
            keyboard.append([InlineKeyboardButton(f"✍️ Continue: {essay['topic'][:20]}...", callback_data=f"continue_{essay_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"👥 Essays You Joined\n\n{essay_list}", reply_markup=reply_markup, parse_mode=None)

async def handle_first_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle first writer's content"""
    text = update.message.text
    essays = load_essays()
    
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or f"User{user_id[-4:]}"
    
    action = context.user_data.get('action')
    
    # Step 1: User provided the topic
    if action == 'waiting_for_topic':
        essay_id = f"essay_{user_id}_{datetime.now().timestamp()}"
        essays[essay_id] = {
            'id': essay_id,
            'creator_id': user_id,
            'creator_name': username,
            'topic': text,
            'first_content': '',
            'second_content': '',
            'status': 'waiting_first',
            'created_at': datetime.now().isoformat(),
            'finish_requests': {},
        }
        save_essays(essays)
        context.user_data['current_essay_id'] = essay_id
        context.user_data['action'] = 'waiting_for_opening'
        
        await update.message.reply_text(
            f"✍️ Now write your opening paragraph (less than 50 words):\n\n"
            f"*Topic:* {text}",
            parse_mode="Markdown"
        )
        return WRITING_FIRST
    
    # Step 2: User provided the opening paragraph
    elif action == 'waiting_for_opening':
        word_count = len(text.split())
        
        if word_count >= 50:
            await update.message.reply_text(
                f"⚠️ Too long! Please write less than 50 words (you wrote {word_count} words)"
            )
            return WRITING_FIRST
        
        essay_id = context.user_data.get('current_essay_id')
        essays[essay_id]['first_content'] = text
        essays[essay_id]['status'] = 'waiting_partner'
        save_essays(essays)
        
        await update.message.reply_text(
            f"✅ Perfect! ({word_count} words)\n\n"
            f"📤 *Share this code with your partner:*\n"
            f"`{essay_id}`\n\n"
            f"They can join with:\n"
            f"`/join {essay_id}`",
            parse_mode="Markdown"
        )
        
        context.user_data['current_essay_id'] = None
        context.user_data['action'] = None
        return ConversationHandler.END

async def join_essay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join an existing essay"""
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /join <essay_id>")
        return
    
    essay_id = context.args[0]
    essays = load_essays()
    
    if essay_id not in essays:
        await update.message.reply_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    current_user_id = str(update.message.from_user.id)
    current_username = update.message.from_user.username or f"User{current_user_id[-4:]}"
    creator_id = str(essay['creator_id'])
    
    if essay['status'] not in ['waiting_partner', 'in_progress']:
        await update.message.reply_text("❌ This essay is not open for contributions!")
        return
    
    # Initialize partners list if not exists
    if 'partners' not in essay:
        essay['partners'] = []
    
    # Check if partner is already registered
    partner_ids = [p['id'] for p in essay['partners']]
    
    # If already a partner, don't allow /join again
    if current_user_id in partner_ids:
        await update.message.reply_text(
            "❌ You are already part of this essay!\n\n"
            "Just wait for the notification when it's your turn to write."
        )
        return
    
    # Creator cannot join their own essay
    if current_user_id == creator_id:
        await update.message.reply_text("❌ You created this essay! Wait for your partner to write.")
        return
    
    # Register the partner (first and only join allowed)
    if len(essay['partners']) == 0:
        essay['partners'].append({
            'id': current_user_id,
            'name': current_username
        })
        save_essays(essays)
    else:
        # More than one partner not allowed
        await update.message.reply_text("❌ This essay already has a partner! Only 2 people can write.")
        return
    
    context.user_data['current_essay_id'] = essay_id
    context.user_data['action'] = 'writing_development'
    
    current_content = essay['first_content']
    if essay.get('second_content'):
        current_content += "\n\n" + essay['second_content']
    
    message = (
        f"Essay Topic: {essay['topic']}\n\n"
        f"Current Content ({len(current_content.split())} words):\n"
        f"{current_content[:200]}...\n\n"
        f"Add your contribution (less than 50 words):"
    )
    
    await update.message.reply_text(message)
    return WRITING_DEVELOPMENT

async def handle_development(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle partner's essay development"""
    text = update.message.text
    essay_id = context.user_data.get('current_essay_id')
    essays = load_essays()
    
    if essay_id not in essays:
        await update.message.reply_text("❌ Essay not found!")
        return ConversationHandler.END
    
    current_user_id = str(update.message.from_user.id)
    current_username = update.message.from_user.username or f"User{current_user_id[-4:]}"
    
    essay = essays[essay_id]
    creator_id = str(essay['creator_id'])
    
    # Initialize finish_requests if not exists
    if 'finish_requests' not in essay:
        essay['finish_requests'] = {}
    
    # Initialize partners list if not exists
    if 'partners' not in essay:
        essay['partners'] = []
    
    # First contribution - set the partner
    if len(essay['partners']) == 0:
        if current_user_id == creator_id:
            await update.message.reply_text("❌ You are the creator! You need a partner to contribute.")
            return WRITING_DEVELOPMENT
        
        essay['partners'].append({
            'id': current_user_id,
            'name': current_username
        })
    else:
        # Check if user is authorized (must be creator or the partner)
        partner_ids = [p['id'] for p in essay['partners']]
        if current_user_id != creator_id and current_user_id not in partner_ids:
            await update.message.reply_text("❌ You are not part of this essay! Only the creator and one partner can write.")
            return WRITING_DEVELOPMENT
    
    word_count = len(text.split())
    
    if word_count >= 50:
        await update.message.reply_text(
            f"⚠️ Too long! Please write less than 50 words (you wrote {word_count} words)"
        )
        return WRITING_DEVELOPMENT
    
    # Clear finish requests when someone writes (new turn)
    essay['finish_requests'] = {}
    
    # Determine whose turn it is and add content
    if essay.get('second_content'):
        # Already has content, so this is a turn after the partner
        essay['second_content'] += f"\n\n{text}"
    else:
        # First contribution by partner
        essay['second_content'] = text
    
    essay['status'] = 'in_progress'
    essay['last_writer_id'] = current_user_id
    save_essays(essays)
    
    full_essay = essay['first_content'] + "\n\n" + essay['second_content']
    total_words = len(full_essay.split())
    
    # Determine whose turn is next
    partner_id = str(essay['partners'][0]['id']) if essay['partners'] else None
    next_turn = "creator" if current_user_id == partner_id else "partner"
    next_turn_id = creator_id if next_turn == "creator" else partner_id
    next_turn_name = essay['creator_name'] if next_turn == "creator" else essay['partners'][0]['name']
    
    keyboard = [
        [InlineKeyboardButton("🏁 Request to Finish", callback_data=f"finish_request_{essay_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Great contribution! ({word_count} words)\n\n"
        f"Essay Status:\n"
        f"Total words: {total_words}\n\n"
        f"Next turn: {next_turn_name}",
        reply_markup=reply_markup
    )
    
    # Send notification to the partner
    if next_turn_id:
        try:
            # Escape special characters for plain text
            essay_topic = essay['topic']
            essay_content_preview = full_essay[:200] + "..." if len(full_essay) > 200 else full_essay
            
            notification_message = (
                f"🔔 YOUR TURN!\n\n"
                f"Essay: {essay_topic}\n\n"
                f"Current content ({total_words} words):\n"
                f"{essay_content_preview}\n\n"
                f"Ready to add your part (less than 50 words)?\n\n"
                f"⏰ Update at {datetime.now().strftime('%H:%M:%S')}"
            )
            
            # Create keyboard with Continue Writing button
            keyboard = [
                [InlineKeyboardButton("✍️ Continue Writing", callback_data=f"continue_{essay_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=next_turn_id,
                text=notification_message,
                reply_markup=reply_markup,
                parse_mode=None
            )
            logger.info(f"✅ Notification sent to {next_turn_id} for essay {essay_id} at {datetime.now()}")
            
            # Send confirmation to current user
            await update.message.reply_text(
                f"📤 Notification sent to {next_turn_name}!\n\n"
                f"They will receive a message with the essay to continue."
            )
        except Exception as e:
            logger.error(f"❌ Could not send notification to {next_turn_id}: {e}")
            await update.message.reply_text(
                f"⚠️ Error sending notification. Partner ID: {next_turn_id}"
            )
    else:
        logger.warning(f"⚠️ No next_turn_id found for essay {essay_id}")
    
    context.user_data['current_essay_id'] = None
    context.user_data['action'] = None
    return WAITING_FOR_PARTNER

async def continue_writing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow partner to continue writing in alternating turns"""
    query = update.callback_query
    await query.answer()
    
    essay_id = query.data.replace("continue_", "")
    essays = load_essays()
    
    if essay_id not in essays:
        await query.edit_message_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    current_user_id = str(query.from_user.id)
    creator_id = str(essay['creator_id'])
    partner_ids = [str(p['id']) for p in essay.get('partners', [])]
    
    # Check if user is authorized (must be creator or the partner)
    if current_user_id != creator_id and current_user_id not in partner_ids:
        await query.edit_message_text("❌ You are not part of this essay!")
        return
    
    last_writer = essay.get('last_writer_id')
    
    # Enforce alternating turns
    if last_writer and last_writer == current_user_id:
        await query.edit_message_text(
            "❌ It's not your turn! Please wait for your partner to write.",
            parse_mode="Markdown"
        )
        return
    
    context.user_data['current_essay_id'] = essay_id
    context.user_data['action'] = 'writing_development'
    
    current_content = essay['first_content'] + "\n\n" + essay['second_content']
    current_words = len(current_content.split())
    
    message = (
        f"📝 Current Essay ({current_words} words):\n\n"
        f"{current_content}\n\n"
        f"---\n\n"
        f"Now write your contribution (less than 50 words):"
    )
    
    await query.edit_message_text(message, parse_mode=None)
    
    return WRITING_DEVELOPMENT

async def finish_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send finish request to partner"""
    query = update.callback_query
    await query.answer()
    
    essay_id = query.data.replace("finish_request_", "")
    essays = load_essays()
    
    if essay_id not in essays:
        await query.edit_message_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    current_user_id = str(query.from_user.id)
    creator_id = str(essay['creator_id'])
    partner_ids = [p['id'] for p in essay.get('partners', [])]
    
    # Initialize finish_requests if not exists
    if 'finish_requests' not in essay:
        essay['finish_requests'] = {}
    
    # Add current user's finish request
    essay['finish_requests'][current_user_id] = True
    save_essays(essays)
    
    # Determine the other user
    if current_user_id == creator_id:
        other_user_id = partner_ids[0] if partner_ids else None
        current_username = essay['creator_name']
    else:
        other_user_id = creator_id
        current_username = [p['name'] for p in essay['partners'] if str(p['id']) == current_user_id][0]
    
    # Check if both have requested finish
    both_accepted = (
        len(essay['finish_requests']) == 2 and
        all(essay['finish_requests'].values())
    )
    
    if both_accepted:
        # Both accepted - mark as complete
        essay['status'] = 'complete'
        save_essays(essays)
        
        full_essay = essay['first_content'] + "\n\n" + essay['second_content']
        total_words = len(full_essay.split())
        
        keyboard = [
            [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{essay_id}")],
            [InlineKeyboardButton("🔄 Start New Essay", callback_data="create_essay")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎉 Essay Complete!\n\n"
            f"Total words: {total_words}\n\n"
            f"Ready to download as PDF",
            reply_markup=reply_markup,
            parse_mode=None
        )
        
        # Notify partner
        if other_user_id:
            try:
                keyboard_partner = [
                    [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{essay_id}")],
                    [InlineKeyboardButton("🔄 Start New Essay", callback_data="create_essay")],
                ]
                reply_markup_partner = InlineKeyboardMarkup(keyboard_partner)
                
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=f"🎉 Essay Complete!\n\n{current_username} accepted the finish request.\n\nTotal words: {total_words}\n\nReady to download as PDF",
                    reply_markup=reply_markup_partner,
                    parse_mode=None
                )
            except Exception as e:
                logger.error(f"❌ Could not notify partner: {e}")
    else:
        # Only one user accepted - send request to other user
        if other_user_id:
            try:
                keyboard = [
                    [InlineKeyboardButton("✅ Accept & Finish", callback_data=f"finish_request_{essay_id}")],
                    [InlineKeyboardButton("❌ Decline", callback_data=f"decline_finish_{essay_id}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=other_user_id,
                    text=f"🏁 Finish Request\n\n{current_username} wants to finish this essay.\n\nEssay: {essay['topic']}\n\nDo you want to finish and download?",
                    reply_markup=reply_markup,
                    parse_mode=None
                )
                logger.info(f"✅ Finish request sent to {other_user_id}")
            except Exception as e:
                logger.error(f"❌ Could not send finish request: {e}")
        
        await query.edit_message_text(
            f"🏁 Finish Request Sent!\n\n"
            f"Waiting for {essay['creator_name'] if current_user_id != creator_id else essay['partners'][0]['name']} to accept.",
            parse_mode=None
        )

async def decline_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Decline finish request"""
    query = update.callback_query
    await query.answer()
    
    essay_id = query.data.replace("decline_finish_", "")
    essays = load_essays()
    
    if essay_id not in essays:
        await query.edit_message_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    
    # Clear finish requests
    essay['finish_requests'] = {}
    save_essays(essays)
    
    await query.edit_message_text(
        "❌ Finish request declined.\n\n"
        "Use 'Continue Writing' when you're ready to add more.",
        parse_mode=None
    )

async def finish_essay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish the essay and prepare for download (legacy - now handled by finish_request)"""
    query = update.callback_query
    await query.answer()
    
    essay_id = query.data.replace("finish_", "")
    essays = load_essays()
    
    if essay_id not in essays:
        await query.edit_message_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    essay['status'] = 'complete'
    save_essays(essays)
    
    full_essay = essay['first_content'] + "\n\n" + essay['second_content']
    total_words = len(full_essay.split())
    
    keyboard = [
        [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{essay_id}")],
        [InlineKeyboardButton("🔄 Start New Essay", callback_data="create_essay")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎉 Essay Complete!\n\n"
        f"Total words: {total_words}\n\n"
        f"Ready to download as PDF",
        reply_markup=reply_markup,
        parse_mode=None
    )

async def download_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send PDF"""
    query = update.callback_query
    await query.answer()
    
    essay_id = query.data.replace("download_", "")
    essays = load_essays()
    
    if essay_id not in essays:
        await query.edit_message_text("❌ Essay not found!")
        return
    
    essay = essays[essay_id]
    
    try:
        pdf_file = generate_essay_pdf(essay)
        
        with open(pdf_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"{essay['topic']}.pdf"
            )
        
        os.remove(pdf_file)
        await query.edit_message_text("✅ PDF sent successfully!")
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        await query.edit_message_text("❌ Error generating PDF")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "📖 *How to Use Essay Writing Bot*\n\n"
        "1️⃣ *Create Essay*: Start a new essay with a topic\n"
        "2️⃣ *Write Opening*: Write less than 50 words\n"
        "3️⃣ *Share Code*: Give your essay code to a partner\n"
        "4️⃣ *Partner Develops*: Use /join <code> to develop it\n"
        "5️⃣ *Download*: Download the complete essay as PDF\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/join <essay_id> - Join a partner's essay\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 Create New Essay", callback_data="create_essay")],
        [InlineKeyboardButton("📂 My Created Essays", callback_data="my_essays")],
        [InlineKeyboardButton("👥 My Joined Essays", callback_data="my_joined_essays")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎯 Essay Writing Bot\n\n"
        "Collaborate with a partner to write essays together!\n"
        "1. One person writes opening (< 50 words)\n"
        "2. Partner adds their part (< 50 words)\n"
        "3. Alternate turns, then download as PDF",
        reply_markup=reply_markup
    )
    return WAITING_FOR_PARTNER

def main():
    """Start the bot"""
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("join", join_essay),
        ],
        states={
            WAITING_FOR_PARTNER: [
                CallbackQueryHandler(create_essay, pattern="^create_essay$"),
                CallbackQueryHandler(my_essays, pattern="^my_essays$"),
                CallbackQueryHandler(my_joined_essays, pattern="^my_joined_essays$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(continue_writing, pattern="^continue_"),
                CallbackQueryHandler(finish_request, pattern="^finish_request_"),
                CallbackQueryHandler(decline_finish, pattern="^decline_finish_"),
                CallbackQueryHandler(finish_essay, pattern="^finish_"),
            ],
            WRITING_FIRST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_first_write),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(create_essay, pattern="^create_essay$"),
            ],
            WRITING_DEVELOPMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_development),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("join", join_essay),
            CommandHandler("help", help_command),
        ],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("join", join_essay))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(download_pdf, pattern="^download_"))
    app.add_handler(CallbackQueryHandler(continue_writing, pattern="^continue_"))
    app.add_handler(CallbackQueryHandler(finish_request, pattern="^finish_request_"))
    app.add_handler(CallbackQueryHandler(decline_finish, pattern="^decline_finish_"))
    app.add_handler(CallbackQueryHandler(finish_essay, pattern="^finish_"))
    
    logger.info("✅ Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
