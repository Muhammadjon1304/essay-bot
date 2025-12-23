# Essay Writing Telegram Bot

A collaborative essay writing bot for Telegram that allows two users to write essays together.

## Features

- ✍️ **Create Essays**: Start a new essay with a topic
- 👤 **Partner Writing**: One person writes the opening (< 50 words), partner develops it (150+ words)
- 📥 **PDF Export**: Download the complete essay as a PDF file
- 📚 **Essay History**: View all your essays
- 🔄 **Easy Sharing**: Share essay codes with partners to collaborate

## Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather on Telegram)

## Installation

1. Clone or download this project
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your Telegram Bot Token:
   - Open `.env` file
   - Replace `your_telegram_bot_token_here` with your actual token from @BotFather

## Running the Bot

```bash
python bot.py
```

The bot will start polling for updates.

## How to Use

### For the First Writer:
1. Send `/start` to the bot
2. Click "📝 Create New Essay"
3. Enter the essay topic
4. Write your opening paragraph (less than 50 words)
5. Share the essay code with your partner

### For the Partner:
1. Use `/join <essay_id>` to join the essay
2. Read the opening paragraph
3. Develop and expand the essay to at least 150 words
4. Submit your contribution

### Download Essay:
1. Once both parts are complete, click "📥 Download PDF"
2. The complete essay will be sent as a PDF file

## Project Structure

```
.
├── bot.py                 # Main bot logic
├── pdf_generator.py       # PDF generation module
├── requirements.txt       # Python dependencies
├── .env                   # Configuration file (add your token here)
├── essays.json           # Stores essay data (auto-created)
└── essays/               # Folder for generated PDFs (auto-created)
```

## Commands

- `/start` - Start the bot and see main menu
- `/join <essay_id>` - Join an existing essay as a partner
- `/help` - Show help message

## Technologies Used

- **python-telegram-bot**: Telegram Bot API wrapper
- **reportlab**: PDF generation
- **python-dotenv**: Environment variable management

## Essay Workflow

1. Writer 1: Creates essay topic + writes opening (< 50 words)
2. Writer 2: Uses code to join essay + develops it (150+ words)
3. Both: Can download final essay as PDF with author credits

## Notes

- Essays are saved in `essays.json`
- PDFs are generated on-demand and saved in the `essays/` folder
- Each essay has a unique ID for easy partner sharing
- Author names are stored for PDF credits

## Support

For issues or questions about Telegram Bot API, visit: https://core.telegram.org/bots
# essay-bot
