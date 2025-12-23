#!/bin/bash

# Essay Bot - DigitalOcean Deployment Script
# Run this script on your DigitalOcean droplet as root

set -e  # Exit on error

echo "🤖 Essay Bot - DigitalOcean Deployment Script"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script must be run as root"
    exit 1
fi

# Step 1: Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Step 2: Install dependencies
echo "📦 Installing dependencies..."
apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib git supervisor

# Step 3: Start PostgreSQL
echo "🗄️ Starting PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Step 4: Create database and user
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE DATABASE IF NOT EXISTS essay_bot;
CREATE USER IF NOT EXISTS essay_bot_user WITH PASSWORD 'essay_bot_secure_password_12345';
ALTER ROLE essay_bot_user SET client_encoding TO 'utf8';
ALTER ROLE essay_bot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE essay_bot_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE essay_bot TO essay_bot_user;
\q
EOF

# Step 5: Clone repository
echo "📥 Cloning repository..."
if [ ! -d "/home/essay-bot" ]; then
    read -p "Enter your GitHub repository URL (or press Enter to skip): " REPO_URL
    if [ ! -z "$REPO_URL" ]; then
        git clone "$REPO_URL" /home/essay-bot
    else
        echo "❌ Repository URL required. Please clone manually."
        exit 1
    fi
fi

# Step 6: Set up Python environment
echo "🐍 Setting up Python virtual environment..."
cd /home/essay-bot
python3.11 -m venv venv
source venv/bin/activate

# Step 7: Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 8: Create .env file
echo "⚙️ Creating .env file..."
if [ ! -f "/home/essay-bot/.env" ]; then
    cat > /home/essay-bot/.env <<EOF
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# PostgreSQL Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=essay_bot
DB_USER=essay_bot_user
DB_PASSWORD=essay_bot_secure_password_12345
EOF
    
    echo "⚠️  Please edit /home/essay-bot/.env and add your Telegram bot token"
    read -p "Press Enter after updating .env file..."
fi

# Step 9: Run migrations
echo "🗄️ Running database migrations..."
source venv/bin/activate
python migrate_db.py
python migrate_partners_db.py

# Step 10: Set up supervisor
echo "👀 Setting up Supervisor..."
cat > /etc/supervisor/conf.d/essay-bot.conf <<EOF
[program:essay-bot]
directory=/home/essay-bot
command=/home/essay-bot/venv/bin/python bot.py
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/essay-bot.log
environment=PATH="/home/essay-bot/venv/bin",HOME="/home/essay-bot"

[group:essay-bot-group]
programs=essay-bot
EOF

# Reload supervisor
supervisorctl reread
supervisorctl update
supervisorctl start essay-bot

# Step 11: Verify bot is running
echo ""
echo "✅ Deployment complete!"
echo "=============================================="
echo ""
echo "Bot Status:"
supervisorctl status essay-bot

echo ""
echo "📋 Next steps:"
echo "1. Edit /home/essay-bot/.env with your Telegram bot token"
echo "2. Restart the bot: supervisorctl restart essay-bot"
echo "3. View logs: tail -f /var/log/essay-bot.log"
echo ""
echo "🚀 Your bot is now running on DigitalOcean!"
