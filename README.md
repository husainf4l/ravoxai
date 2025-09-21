# RavoX AI - AI Calling Agent

A clean, well-structured AI calling agent with LiveKit integration and subject-aware conversations.

## 🏗️ Project Structure

```
ravoxai/
├── main.py                 # Main FastAPI application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── src/                   # Source code
│   ├── __init__.py
│   ├── agent/             # AI agent components
│   │   ├── __init__.py
│   │   ├── call_agent.py      # Main agent logic
│   │   ├── agent_main.py      # Agent entry point
│   │   └── call_service.py    # SIP call service
│   ├── database/          # Database models
│   │   ├── __init__.py
│   │   └── database.py        # SQLAlchemy models
│   ├── services/          # External services
│   │   ├── __init__.py
│   │   └── s3_service.py      # AWS S3 integration
│   ├── nodes/             # Node types (future)
│   │   └── __init__.py
│   ├── tools/             # Utility tools (future)
│   │   └── __init__.py
│   └── utils/             # Helper functions (future)
│       └── __init__.py
├── config/                # Configuration files
├── tests/                 # Test files (future)
└── docs/                  # Documentation
    ├── dashboard.html
    └── POSTGRESQL_SETUP.md
```

## ✨ Features

- **Subject-Aware Calls**: AI agent incorporates call purpose into conversation
- **Professional Greetings**: Context-aware introductions with agent name
- **REST API**: HTTP endpoint for programmatic call initiation
- **Google Gemini Realtime**: Natural conversation processing
- **LiveKit Integration**: SIP calling via LiveKit cloud
- **PostgreSQL Database**: Call record storage and tracking
- **AWS S3 Integration**: Media file storage and sharing
- **Clean Architecture**: Well-organized, maintainable codebase

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL database
- LiveKit account and API keys
- AWS S3 bucket (optional, for media storage)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd ravoxai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp config/.env.example config/.env
# Edit config/.env with your API keys
```

### Using VS Code Tasks

This project includes **one main VS Code task** that runs everything in **separate terminals**:

#### **Main Task**
- **Start RavoX AI** - One-click start for the entire system (`Ctrl+Shift+B`)
  - ✅ Starts FastAPI server in **Terminal 1**
  - ✅ Starts LiveKit agent in **Terminal 2**
  - ✅ Both services run simultaneously
  - ✅ Separate terminals for better debugging

#### **What You'll See When Running**

**Terminal 1 (FastAPI Server):**
```
📡 Starting FastAPI Server...
INFO:__main__:🚀 Starting AI Call Service API...
INFO:__main__:📖 API Documentation available at: http://localhost:8000/docs
INFO:__main__:🔗 Health check at: http://localhost:8000/
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Terminal 2 (LiveKit Agent):**
```
🤖 Starting LiveKit Agent...
INFO:call-agent:🚀 Starting AI Call Agent...
INFO:     Watching for file changes...
```

#### **Expected Warnings (Normal)**
- ⚠️ Database connection warnings (PostgreSQL not required for basic operation)
- ⚠️ S3 connection warnings (AWS not required for basic operation)
- These don't prevent the system from working!

#### **Individual Tasks**
- **Start FastAPI Server** - Run only the API server
- **Start LiveKit Agent** - Run only the AI agent
- **Quick Setup & Start** - Install dependencies and start everything
- **Stop All Services** - Stop all running services

#### **How It Works**
```bash
# Press Ctrl+Shift+B or use Command Palette
Tasks: Run Task → Start RavoX AI
```

This will open **two separate terminals**:
- **Terminal 1**: FastAPI server with API endpoints
- **Terminal 2**: LiveKit agent for AI conversations

#### **Benefits of Separate Terminals**
- 🔍 **Better Debugging**: See logs from each service separately
- 🔄 **Individual Restart**: Restart one service without affecting the other
- 📊 **Clear Monitoring**: Monitor each service's performance independently
- 🛑 **Selective Stopping**: Stop individual services as needed

### Manual Alternative
```bash
# Terminal 1 - Start FastAPI server
source venv/bin/activate
set -a && source config/.env && set +a
python main.py

# Terminal 2 - Start LiveKit agent
source venv/bin/activate
set -a && source config/.env && set +a
python -m src.agent.agent_main dev
```

## 📖 API Documentation

Once the server is running, visit:
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/dashboard
- **Health Check**: http://localhost:8000/

## 🔧 Configuration

Environment variables in `config/.env`:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# LiveKit
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name
```

## 🧪 Testing

```bash
# Test compilation
python -m py_compile main.py src/agent/*.py src/database/*.py src/services/*.py

# Test imports
python -c "from main import app; print('✅ Imports successful')"
```

## 📊 Monitoring

The application includes built-in monitoring:
- **Background Tasks**: Automatic cleanup and health checks
- **Database Monitoring**: Connection status and performance
- **Service Health**: Real-time status endpoints
- **Logging**: Comprehensive logging with different levels

## 🏗️ Architecture

### Core Components
- **FastAPI Server** (`main.py`): REST API and web interface
- **LiveKit Agent** (`src/agent/`): AI conversation handling
- **Database Layer** (`src/database/`): Data persistence
- **Service Layer** (`src/services/`): External integrations

### Background Tasks
- **Database Cleanup**: Removes old failed/completed calls
- **Health Monitoring**: Checks service connectivity
- **Status Updates**: Manages call state transitions
- **Error Recovery**: Automatic retry mechanisms

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Use VS Code tasks to test
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 📡 Usage

### API Endpoint

```bash
curl -X POST "http://localhost:8000/make-call" \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "0796026659",
    "agent_name": "Ash",
    "caller_name": "Husain",
    "company_name": "Rolevate",
    "subject": "Meeting confirmation",
    "main_prompt": "Confirm our 2 PM meeting tomorrow and discuss project timeline"
  }'
```

### Response

```json
{
  "success": true,
  "call_id": "call-12345",
  "message": "Call initiated successfully"
}
```

## 🔧 Configuration

### Environment Variables

Create `config/.env` with:

```env
# LiveKit Configuration
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ravoxai

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=me-central-1
S3_BUCKET_NAME=your-bucket-name
```

## 🏛️ Architecture

### Core Components

- **`main.py`**: FastAPI application with REST endpoints
- **`src/agent/`**: LiveKit agent implementation
- **`src/database/`**: PostgreSQL models and connections
- **`src/services/`**: External service integrations (S3, etc.)

### Agent Flow

1. **API Request** → `main.py` receives call request
2. **Validation** → Phone number and parameters validated
3. **Database** → Call record created
4. **LiveKit** → SIP call initiated via LiveKit
5. **Agent** → AI agent handles conversation
6. **Recording** → Call data stored and media uploaded

## 📚 Documentation

- [PostgreSQL Setup](docs/POSTGRESQL_SETUP.md)
- [API Dashboard](docs/dashboard.html)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "0796026659",
       "subject": "Follow up on your recent inquiry about our services",
       "agent_name": "Sarah from Sales",
       "caller_id": "Your Company"
     }'
```

### Parameters

- `phone_number`: Target phone number (required)
- `subject`: Purpose/context of the call (required)
- `agent_name`: Name for the AI agent (optional)
- `caller_id`: Display name for caller ID (optional)

## Files

- `main.py`: FastAPI REST service (primary entry point)
- `agent_main.py`: Agent entry point
- `call_agent.py`: Core AI agent logic
- `call_service.py`: SIP calling functionality  
- `requirements.txt`: Dependencies

## Configuration

Set these environment variables in `.env`:

```
LIVEKIT_URL=wss://your-livekit-url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

## API Documentation

When running, visit: http://localhost:8000/docs for interactive API documentation.