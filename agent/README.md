# AI Call Agent - Clean Version

A minimal, production-ready AI call agent with subject context support.

## Features

- **Subject-Aware Calls**: AI agent incorporates call purpose into conversation
- **Professional Greetings**: Context-aware introductions  
- **REST API**: HTTP endpoint for programmatic call initiation
- **Google Real-time Model**: Natural conversation processing
- **LiveKit Integration**: SIP calling via LiveKit cloud

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your LiveKit credentials
```

### 2. Run the Agent

```bash
# Start the AI agent
python agent_main.py dev
```

### 3. Run the API (separate terminal)

```bash
# Activate venv and start API server
source venv/bin/activate
python main.py
```

## Usage

### API Endpoint

```bash
curl -X POST "http://localhost:8000/make-call" \
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