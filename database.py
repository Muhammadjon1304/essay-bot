import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
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

def get_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Create essays table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS essays (
                id VARCHAR(255) PRIMARY KEY,
                creator_id BIGINT NOT NULL,
                creator_name VARCHAR(255) NOT NULL,
                topic TEXT NOT NULL,
                first_content TEXT,
                second_content TEXT,
                status VARCHAR(50) DEFAULT 'waiting_first',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_writer_id BIGINT,
                finish_requests JSONB DEFAULT '{}'::jsonb,
                is_anonymous BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Create partners table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id SERIAL PRIMARY KEY,
                essay_id VARCHAR(255) NOT NULL REFERENCES essays(id) ON DELETE CASCADE,
                partner_id BIGINT NOT NULL,
                partner_name VARCHAR(255) NOT NULL,
                is_anonymous BOOLEAN DEFAULT FALSE,
                UNIQUE(essay_id, partner_id)
            )
        """)
        
        # Create user_session table to track which essay a user is currently working on
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_session (
                user_id BIGINT PRIMARY KEY,
                current_essay_id VARCHAR(255) NOT NULL REFERENCES essays(id) ON DELETE CASCADE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_essays_creator ON essays(creator_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_essays_status ON essays(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_partners_partner ON partners(partner_id)")
        
        conn.commit()
        logger.info("✅ Database initialized successfully")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def create_essay(essay_id, creator_id, creator_name, topic):
    """Create a new essay"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO essays (id, creator_id, creator_name, topic, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (essay_id, creator_id, creator_name, topic, 'waiting_first'))
        
        conn.commit()
        logger.info(f"✅ Essay created: {essay_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error creating essay: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_essay(essay_id):
    """Get essay by ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT * FROM essays WHERE id = %s", (essay_id,))
        essay = cur.fetchone()
        
        if essay:
            # Get partners
            cur.execute("""
                SELECT partner_id as id, partner_name as name FROM partners 
                WHERE essay_id = %s
            """, (essay_id,))
            partners = cur.fetchall()
            essay['partners'] = [dict(p) for p in partners]
            
            return dict(essay)
        return None
    except psycopg2.Error as e:
        logger.error(f"Error getting essay: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def update_essay(essay_id, **kwargs):
    """Update essay fields"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        allowed_fields = ['first_content', 'second_content', 'status', 'last_writer_id', 'finish_requests', 'is_anonymous']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = %s")
                values.append(value)
        
        if not updates:
            return
        
        values.append(essay_id)
        query = f"UPDATE essays SET {', '.join(updates)} WHERE id = %s"
        cur.execute(query, values)
        conn.commit()
        logger.info(f"✅ Essay updated: {essay_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error updating essay: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def add_partner(essay_id, partner_id, partner_name, is_anonymous=False):
    """Add a partner to an essay"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO partners (essay_id, partner_id, partner_name, is_anonymous)
            VALUES (%s, %s, %s, %s)
        """, (essay_id, partner_id, partner_name, is_anonymous))
        
        conn.commit()
        logger.info(f"✅ Partner added to essay: {essay_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error adding partner: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_user_essays(creator_id):
    """Get all essays created by a user"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM essays WHERE creator_id = %s ORDER BY created_at DESC
        """, (creator_id,))
        essays = cur.fetchall()
        
        result = []
        for essay in essays:
            essay_dict = dict(essay)
            # Get partners
            cur.execute("""
                SELECT partner_id as id, partner_name as name FROM partners 
                WHERE essay_id = %s
            """, (essay_dict['id'],))
            partners = cur.fetchall()
            essay_dict['partners'] = [dict(p) for p in partners]
            result.append(essay_dict)
        
        return result
    except psycopg2.Error as e:
        logger.error(f"Error getting user essays: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_user_joined_essays(partner_id):
    """Get all essays a user joined as a partner"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT e.* FROM essays e
            JOIN partners p ON e.id = p.essay_id
            WHERE p.partner_id = %s
            ORDER BY e.created_at DESC
        """, (partner_id,))
        essays = cur.fetchall()
        
        result = []
        for essay in essays:
            essay_dict = dict(essay)
            # Get all partners
            cur.execute("""
                SELECT partner_id as id, partner_name as name FROM partners 
                WHERE essay_id = %s
            """, (essay_dict['id'],))
            partners = cur.fetchall()
            essay_dict['partners'] = [dict(p) for p in partners]
            result.append(essay_dict)
        
        return result
    except psycopg2.Error as e:
        logger.error(f"Error getting joined essays: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def check_partner_exists(essay_id, partner_id):
    """Check if a partner already exists for an essay"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT COUNT(*) FROM partners 
            WHERE essay_id = %s AND partner_id = %s
        """, (essay_id, partner_id))
        count = cur.fetchone()[0]
        return count > 0
    except psycopg2.Error as e:
        logger.error(f"Error checking partner: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_all_essays():
    """Get all essays (for admin purposes)"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT * FROM essays ORDER BY created_at DESC")
        essays = cur.fetchall()
        
        result = []
        for essay in essays:
            essay_dict = dict(essay)
            # Get partners
            cur.execute("""
                SELECT partner_id as id, partner_name as name FROM partners 
                WHERE essay_id = %s
            """, (essay_dict['id'],))
            partners = cur.fetchall()
            essay_dict['partners'] = [dict(p) for p in partners]
            result.append(essay_dict)
        
        return result
    except psycopg2.Error as e:
        logger.error(f"Error getting all essays: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def set_user_session(user_id, essay_id):
    """Set user's current essay session"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO user_session (user_id, current_essay_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET current_essay_id = EXCLUDED.current_essay_id, updated_at = CURRENT_TIMESTAMP
        """, (user_id, essay_id))
        
        conn.commit()
        logger.info(f"✅ User session set: user_id={user_id}, essay_id={essay_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error setting user session: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_user_session(user_id):
    """Get user's current essay session"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT current_essay_id FROM user_session WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        return result['current_essay_id'] if result else None
    except psycopg2.Error as e:
        logger.error(f"Error getting user session: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def clear_user_session(user_id):
    """Clear user's session"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM user_session WHERE user_id = %s", (user_id,))
        conn.commit()
        logger.info(f"✅ User session cleared: user_id={user_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error clearing user session: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_available_essays():
    """Get all essays waiting for partners (status: waiting_partner)"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT * FROM essays 
            WHERE status = 'waiting_partner'
            ORDER BY created_at DESC
        """)
        essays = cur.fetchall()
        
        result = []
        for essay in essays:
            essay_dict = dict(essay)
            # Get partners
            cur.execute("""
                SELECT partner_id as id, partner_name as name FROM partners 
                WHERE essay_id = %s
            """, (essay_dict['id'],))
            partners = cur.fetchall()
            essay_dict['partners'] = [dict(p) for p in partners]
            result.append(essay_dict)
        
        return result
    except psycopg2.Error as e:
        logger.error(f"Error getting available essays: {e}")
        raise
    finally:
        cur.close()
        conn.close()

