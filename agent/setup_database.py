#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Creates the database and tables for the AI Call Service
"""

import os
import sys
import asyncpg
import asyncio
from dotenv import load_dotenv
from database import create_tables, get_database_url

load_dotenv()

async def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    
    # Parse database URL to get connection info
    db_url = get_database_url()
    
    if not db_url.startswith('postgresql://'):
        print("❌ DATABASE_URL must be a PostgreSQL URL")
        return False
    
    # Extract database info from URL
    import urllib.parse as urlparse
    parsed = urlparse.urlparse(db_url)
    
    db_host = parsed.hostname
    db_port = parsed.port or 5432
    db_name = parsed.path[1:]  # Remove leading slash
    db_user = parsed.username
    db_password = parsed.password
    
    print(f"🔍 Checking PostgreSQL connection to {db_host}:{db_port}")
    
    try:
        # Connect to postgres default database to create our database
        default_conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database='postgres'
        )
        
        # Check if our database exists
        db_exists = await default_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        
        if not db_exists:
            print(f"📝 Creating database '{db_name}'...")
            await default_conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ Database '{db_name}' created successfully")
        else:
            print(f"✅ Database '{db_name}' already exists")
        
        await default_conn.close()
        
        # Now connect to our database and create tables
        print("📋 Creating tables...")
        create_tables()
        print("✅ All tables created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 AI Call Service - PostgreSQL Database Setup")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  No .env file found. Please create one based on .env.example")
        print("   Copy .env.example to .env and fill in your database credentials")
        return 1
    
    # Run async setup
    success = asyncio.run(create_database_if_not_exists())
    
    if success:
        print("\n🎉 Database setup completed successfully!")
        print("🚀 You can now start the API service with: python main.py")
        return 0
    else:
        print("\n❌ Database setup failed!")
        print("💡 Make sure PostgreSQL is running and credentials are correct")
        return 1

if __name__ == "__main__":
    sys.exit(main())