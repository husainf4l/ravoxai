"""
Database models for call tracking and conversation storage - PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class CallRecord(Base):
    __tablename__ = "call_records"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, nullable=False)
    caller_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    main_prompt = Column(Text)
    caller_id = Column(String)
    
    # Call status and timing
    status = Column(String, default="initiated")  # initiated, connected, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Recording information
    recording_url = Column(String)  # S3 URL for audio recording
    recording_s3_key = Column(String)  # S3 key for direct access
    recording_sid = Column(String)  # LiveKit recording SID
    transcript_url = Column(String)  # S3 URL for transcript file
    transcript_s3_key = Column(String)  # S3 key for transcript
    
    # Media metadata
    recording_file_size = Column(Integer)  # File size in bytes
    recording_duration_ms = Column(Integer)  # Recording duration in milliseconds
    recording_format = Column(String)  # Audio format (mp3, wav, etc.)
    
    # Conversation data
    conversation_transcript = Column(Text)
    conversation_summary = Column(Text)
    
    # Success indicators
    call_connected = Column(Boolean, default=False)
    recording_available = Column(Boolean, default=False)


# Database setup - PostgreSQL
def get_database_url():
    """Get database URL from environment or use default"""
    # Try to get from environment variables
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Build from individual components
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "ai_calls")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "password")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

DATABASE_URL = get_database_url()

# Convert async URL to sync URL for SQLAlchemy operations
SYNC_DATABASE_URL = DATABASE_URL
if "postgresql+asyncpg://" in DATABASE_URL:
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        raise

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False