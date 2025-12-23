# Quick Deploy to DigitalOcean - 5 Minutes ⚡

## The Fast Way

### 1. Create Droplet
- Go to [DigitalOcean Dashboard](https://cloud.digitalocean.com)
- Click **Create** → **Droplets**
- Choose: **Ubuntu 22.04**, **$5/month plan**
- Copy the IP address when created

### 2. Connect & Deploy
```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Run deployment script
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/deploy_digitalocean.sh
chmod +x deploy_digitalocean.sh
./deploy_digitalocean.sh
```

### 3. Configure Bot
```bash
# Edit .env file and add your Telegram token
nano /home/essay-bot/.env

# Add your token:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456

# Restart bot
supervisorctl restart essay-bot
```

### 4. Done! ✅
Your bot is now live and running 24/7!

## Verify It's Working
```bash
# Check status
supervisorctl status essay-bot

# View logs
tail -f /var/log/essay-bot.log
```

## Common Commands

```bash
# Restart bot after code changes
supervisorctl restart essay-bot

# Stop bot
supervisorctl stop essay-bot

# Start bot
supervisorctl start essay-bot

# View live logs
tail -f /var/log/essay-bot.log

# Update code from GitHub
cd /home/essay-bot
git pull
supervisorctl restart essay-bot
```

## Backup Your Data
```bash
# Backup database to local machine
scp root@YOUR_DROPLET_IP:/var/lib/postgresql/backup.sql ./

# Or manually backup via PostgreSQL
ssh root@YOUR_DROPLET_IP
pg_dump -U essay_bot_user essay_bot > /home/backup.sql
```

## Costs
- **$5/month** for basic droplet (sufficient for most use cases)
- Database included
- Pay only for bandwidth usage

## Need Help?

### Bot not responding?
```bash
supervisorctl restart essay-bot
tail -f /var/log/essay-bot.log
```

### Database issues?
```bash
sudo -u postgres psql -d essay_bot -U essay_bot_user
```

### Want to use webhooks instead of polling?
See the full deployment guide: `DEPLOYMENT_DIGITALOCEAN.md`

---

**That's it! Your essay bot is now deployed to DigitalOcean** 🚀
