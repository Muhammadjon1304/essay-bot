# PostgreSQL Migration Guide

## ✅ Complete Migration Done!

Your Telegram essay bot is now using **PostgreSQL** instead of JSON files!

## 🚀 Quick Setup

### 1. Install PostgreSQL

**macOS (using Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Or download from:** https://www.postgresql.org/download/

### 2. Create Database

Open Terminal and run:
```bash
# Connect to PostgreSQL
psql postgres

# In the PostgreSQL prompt, run:
CREATE DATABASE essay_bot;
\q
```

### 3. Update .env File

Your `.env` file already has PostgreSQL configuration:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=essay_bot
DB_USER=postgres
DB_PASSWORD=password
```

**Update the password if your PostgreSQL has a different password:**
```bash
# Change password in PostgreSQL:
psql postgres
ALTER USER postgres WITH PASSWORD 'your_new_password';
\q

# Update .env:
DB_PASSWORD=your_new_password
```

### 4. Install Python Package

```bash
pip install psycopg2-binary
```

### 5. Run the Bot

```bash
python bot.py
```

The bot will:
- ✅ Connect to PostgreSQL
- ✅ Create all necessary tables automatically
- ✅ Initialize indexes for performance
- ✅ Start polling for Telegram updates

## 📊 Database Schema

### Tables Created:

**essays** table:
- `id` (TEXT PRIMARY KEY) - Unique essay ID
- `creator_id` (BIGINT) - Telegram user ID of creator
- `creator_name` (VARCHAR) - Username of creator
- `topic` (TEXT) - Essay topic
- `first_content` (TEXT) - Opening paragraph
- `second_content` (TEXT) - Partner contributions
- `status` (VARCHAR) - waiting_first, waiting_partner, in_progress, complete
- `created_at` (TIMESTAMP) - Creation time
- `last_writer_id` (BIGINT) - ID of last person who wrote
- `finish_requests` (JSONB) - Finish request status from both partners

**partners** table:
- `id` (SERIAL PRIMARY KEY) - Auto-incrementing ID
- `essay_id` (VARCHAR) - References essays.id
- `partner_id` (BIGINT) - Telegram user ID of partner
- `partner_name` (VARCHAR) - Username of partner

**Indexes:**
- `idx_essays_creator` - For fast lookup by creator
- `idx_essays_status` - For filtering by status
- `idx_partners_partner` - For finding essays by partner

## 🔄 Migration from JSON

The new PostgreSQL version:
- ✅ Supports all existing features
- ✅ Handles concurrent users better
- ✅ More scalable for large datasets
- ✅ Better data integrity
- ✅ Automatic backups possible

## 🔧 Troubleshooting

### "Connection refused" Error
```bash
# Check if PostgreSQL is running:
brew services list

# Start PostgreSQL:
brew services start postgresql@15
```

### "Database does not exist" Error
```bash
# Create the database:
createdb essay_bot
```

### "ROLE 'postgres' does not exist" Error
```bash
# Create the role:
createuser postgres
```

## 📁 New Files

- `database.py` - Database operations module
- `bot.py` - Updated bot with PostgreSQL support
- `.env` - Updated with PostgreSQL configuration

## 🎯 Benefits of PostgreSQL

| Feature | JSON | PostgreSQL |
|---------|------|-----------|
| Concurrent Users | Limited | ✅ Excellent |
| Data Integrity | Basic | ✅ Strong (ACID) |
| Query Performance | Slow | ✅ Fast |
| Scalability | Limited | ✅ Excellent |
| Backups | Manual | ✅ Automated |
| Recovery | Difficult | ✅ Easy |
| Data Relationships | Flat | ✅ Relations |

## ✨ Features Still Working

✅ Essay creation with topics
✅ Turn-based writing (< 50 words)
✅ Partner joining (one-time)
✅ Notifications with timestamps
✅ Dual-acceptance finish system
✅ PDF generation
✅ My Created Essays view
✅ My Joined Essays view with turn tracking
✅ Back buttons and navigation

## 🚦 Status Check

To verify everything is working:

```bash
# Connect to database
psql -U postgres -d essay_bot

# Check tables
\dt

# See essay data
SELECT * FROM essays;

# See partners
SELECT * FROM partners;

# Exit
\q
```

## 📞 Support

If you encounter any issues:

1. Check PostgreSQL is running: `brew services list`
2. Verify database exists: `psql -l | grep essay_bot`
3. Check logs in terminal for detailed error messages
4. Make sure all Python packages are installed: `pip install -r requirements.txt`

---

**Your bot is now production-ready with PostgreSQL!** 🎉
