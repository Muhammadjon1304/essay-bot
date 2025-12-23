# Setup Guide for Essay Writing Bot

## Getting Your Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Start the chat and send: `/start`
3. Send: `/newbot`
4. Follow the prompts:
   - Name your bot (e.g., "Essay Writing Bot")
   - Give it a username (e.g., "essay_writing_bot")
5. BotFather will give you a token that looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456`

## Configure the Bot

1. Open `.env` file in the project
2. Replace `your_telegram_bot_token_here` with your actual token:
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456
   ```
3. Save the file

## Run the Bot

```bash
python bot.py
```

You should see:
```
2025-12-22 13:26:01,014 - __main__ - INFO - ✅ Bot started polling...
```

## Test the Bot

1. Open Telegram
2. Find your bot (search for its username)
3. Send `/start`
4. The bot should respond with the main menu

## Troubleshooting

**"No valid Telegram token found"**
- Make sure you've saved the `.env` file after adding the token
- Check that there are no extra spaces in the token

**Bot not responding**
- Verify the token is correct by checking @BotFather
- Make sure the bot is running (check terminal output)
- Try sending `/start` again
