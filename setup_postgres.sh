#!/bin/bash

# PostgreSQL Setup Script for Essay Bot
# This script helps set up PostgreSQL for the essay bot

set -e

echo "🚀 PostgreSQL Setup for Essay Bot"
echo "=================================="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed"
    echo ""
    echo "Install PostgreSQL using Homebrew:"
    echo "  brew install postgresql@15"
    echo "  brew services start postgresql@15"
    echo ""
    exit 1
fi

echo "✅ PostgreSQL found"
echo ""

# Check if PostgreSQL service is running
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL service is not running"
    echo "Starting PostgreSQL..."
    brew services start postgresql@15
    sleep 2
fi

echo "✅ PostgreSQL is running"
echo ""

# Create database
echo "📁 Creating database 'essay_bot'..."
createdb essay_bot 2>/dev/null || echo "   (Database already exists)"

echo "✅ Database ready"
echo ""

# Test connection
echo "🔌 Testing database connection..."
psql -U postgres -d essay_bot -c "SELECT 1" > /dev/null
echo "✅ Connection successful"
echo ""

# Check if python bot can connect
echo "🤖 Testing bot database initialization..."
python3 -c "
from database import init_db
init_db()
print('✅ Database tables created successfully')
" 2>/dev/null || echo "⚠️  Could not initialize tables (will be done on first bot run)"

echo ""
echo "=================================="
echo "✅ PostgreSQL Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env file with your PostgreSQL password (if not 'password')"
echo "  2. Run: python bot.py"
echo ""
