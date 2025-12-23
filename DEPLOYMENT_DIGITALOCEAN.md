# Deployment Guide: Essay Bot on DigitalOcean

## Prerequisites
- DigitalOcean account
- Telegram Bot Token (from @BotFather)
- PostgreSQL credentials or setup access

## Step 1: Create a Droplet on DigitalOcean

1. Go to [DigitalOcean Console](https://cloud.digitalocean.com)
2. Click "Create" → "Droplets"
3. Choose:
   - **Region**: Choose closest to your users
   - **OS**: Ubuntu 22.04 x64
   - **Plan**: Basic ($5/month is sufficient)
   - **Authentication**: SSH Key (recommended) or Password
4. Create droplet and note the IP address

## Step 2: Connect to Your Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

Or use password authentication if SSH key not configured.

## Step 3: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and pip
apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL
apt install -y postgresql postgresql-contrib

# Install Git
apt install -y git

# Install supervisor (for process management)
apt install -y supervisor
```

## Step 4: Set Up PostgreSQL

```bash
# Start PostgreSQL service
systemctl start postgresql
systemctl enable postgresql

# Connect to PostgreSQL
sudo -u postgres psql

# Inside PostgreSQL shell:
CREATE DATABASE essay_bot;
CREATE USER essay_bot_user WITH PASSWORD 'strong_password_here';
ALTER ROLE essay_bot_user SET client_encoding TO 'utf8';
ALTER ROLE essay_bot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE essay_bot_user SET default_transaction_deferrable TO on;
ALTER ROLE essay_bot_user SET default_transaction_read_committed TO on;
GRANT ALL PRIVILEGES ON DATABASE essay_bot TO essay_bot_user;
\q
```

## Step 5: Clone and Set Up Your Bot

```bash
# Navigate to home directory
cd /home

# Clone your repository (or create directory)
git clone YOUR_REPO_URL essay-bot
cd essay-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## Step 6: Configure Environment Variables

```bash
# Create .env file
nano .env

# Add these variables:
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
DB_HOST=localhost
DB_PORT=5432
DB_NAME=essay_bot
DB_USER=essay_bot_user
DB_PASSWORD=strong_password_here
```

Save with Ctrl+X, then Y, then Enter.

## Step 7: Run Database Migrations

```bash
source venv/bin/activate
python migrate_db.py
python migrate_partners_db.py
```

## Step 8: Set Up Supervisor for Process Management

Supervisor will keep your bot running and restart it if it crashes.

```bash
# Create supervisor config file
nano /etc/supervisor/conf.d/essay-bot.conf
```

Add this configuration:

```ini
[program:essay-bot]
directory=/home/essay-bot
command=/home/essay-bot/venv/bin/python bot.py
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/essay-bot.log
environment=PATH="/home/essay-bot/venv/bin",HOME="/home/essay-bot"
```

Save and exit (Ctrl+X, Y, Enter).

## Step 9: Start the Bot with Supervisor

```bash
# Update supervisor
supervisorctl reread
supervisorctl update

# Start the bot
supervisorctl start essay-bot

# Check status
supervisorctl status essay-bot

# View logs
tail -f /var/log/essay-bot.log
```

## Step 10: Set Up Firewall (Optional but Recommended)

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTP (if needed)
ufw allow 80/tcp

# Enable firewall
ufw enable
```

## Step 11: Set Up SSL Certificate (Optional)

If you want to use webhooks instead of polling:

```bash
# Install Certbot
apt install -y certbot

# Get certificate
certbot certonly --standalone -d YOUR_DOMAIN_HERE
```

## Monitoring and Maintenance

### View Bot Logs
```bash
tail -f /var/log/essay-bot.log
```

### Restart the Bot
```bash
supervisorctl restart essay-bot
```

### Stop the Bot
```bash
supervisorctl stop essay-bot
```

### Update Bot Code
```bash
cd /home/essay-bot
git pull
supervisorctl restart essay-bot
```

## Backup Your Database

```bash
# Backup PostgreSQL database
pg_dump -U essay_bot_user essay_bot > essay_bot_backup.sql

# Download backup to your local machine
# Use scp or your DigitalOcean file manager
```

## Troubleshooting

### Bot not starting?
```bash
supervisorctl status essay-bot
tail -f /var/log/essay-bot.log
```

### Database connection issues?
```bash
sudo -u postgres psql -d essay_bot -U essay_bot_user
```

### Check if port is available
```bash
netstat -tuln | grep 5432
```

## Cost Estimation (as of December 2025)

- **Droplet**: $5-15/month (depending on specs)
- **Database**: Included in droplet
- **Bandwidth**: Usually sufficient for free tier
- **Total**: ~$5-15/month

## Scaling Up

As your bot grows:
- Upgrade droplet CPU/RAM
- Use DigitalOcean Managed PostgreSQL for better performance
- Add load balancing with multiple bot instances

---

**Your bot will now be running 24/7 on DigitalOcean!** 🚀
