"""
Database migration script to add is_anonymous column to essays table
"""
import psycopg2
import os
from dotenv import load_dotenv
import logging

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "essay_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

def migrate():
    """Add is_anonymous column to essays table"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'essays' AND column_name = 'is_anonymous'
        """)
        
        if cur.fetchone():
            logger.info("✅ Column 'is_anonymous' already exists")
            cur.close()
            conn.close()
            return
        
        # Add the column
        cur.execute("""
            ALTER TABLE essays 
            ADD COLUMN is_anonymous BOOLEAN DEFAULT FALSE
        """)
        
        conn.commit()
        logger.info("✅ Migration successful: Added is_anonymous column to essays table")
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
