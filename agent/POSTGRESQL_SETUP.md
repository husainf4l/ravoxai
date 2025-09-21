# AI Call Service - PostgreSQL Setup Guide

## 🗄️ Database Configuration

The AI Call Service now uses PostgreSQL for robust conversation tracking and recording management.

## 📋 Prerequisites

1. **PostgreSQL Server** installed and running
2. **Python dependencies** installed

## ⚡ Quick Setup

### 1. Install PostgreSQL

**macOS (using Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from https://www.postgresql.org/download/

### 2. Create Database User (Optional)
```bash
# Connect to PostgreSQL as superuser
psql postgres

# Create user and database
CREATE USER ai_calls_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE ai_calls OWNER ai_calls_user;
GRANT ALL PRIVILEGES ON DATABASE ai_calls TO ai_calls_user;
\q
```

### 3. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials:
```env
# Option 1: Full DATABASE_URL (recommended)
DATABASE_URL=postgresql://ai_calls_user:your_secure_password@localhost:5432/ai_calls

# Option 2: Individual components
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_calls
POSTGRES_USER=ai_calls_user
POSTGRES_PASSWORD=your_secure_password
```

### 4. Install Python Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Setup Database
```bash
python setup_database.py
```

### 6. Start the Service
```bash
python main.py
```

## 🛠️ Database Schema

The system automatically creates these tables:

### `call_records`
- `id` - Primary key
- `call_id` - Unique call identifier (UUID)
- `phone_number` - Target phone number
- `caller_name` - Name of person being called
- `agent_name` - AI agent name
- `company_name` - Calling company
- `subject` - Call subject/purpose
- `main_prompt` - Detailed conversation context
- `status` - Call status (initiated, connecting, completed, failed)
- `created_at`, `started_at`, `ended_at` - Timestamps
- `duration_seconds` - Call duration
- `recording_url` - Link to call recording
- `conversation_transcript` - Full conversation text
- `conversation_summary` - AI-generated summary

## 📊 Dashboard Access

View all calls and recordings at:
http://localhost:8000/dashboard

## 🔧 Troubleshooting

### Connection Issues
```bash
# Test connection manually
python -c "from database import test_connection; print('✅ Connected' if test_connection() else '❌ Failed')"
```

### Reset Database
```bash
# Drop and recreate all tables
python -c "from database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

### Check PostgreSQL Status
```bash
# macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql
```

## 🌐 Production Deployment

For production, consider:
- Using managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- Setting up connection pooling
- Configuring SSL connections
- Setting up database backups

## 📚 API Endpoints

- `POST /make-call` - Initiate call (saves to DB)
- `GET /calls` - List all call records
- `GET /calls/{call_id}` - Get specific call
- `PUT /calls/{call_id}/update` - Update call with recording/transcript
- `GET /dashboard` - Web dashboard

The system now provides complete conversation tracking with PostgreSQL reliability! 🚀