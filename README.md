# VoIP Agent FastAPI

This is a minimal FastAPI application to receive inbound call webhooks from FreePBX or similar systems. Point your inbound route to http://<your-server>:8000/inbound.

## Usage

1. Install dependencies:
   pip install -r requirements.txt

2. Run the server:
   uvicorn main:app --host 0.0.0.0 --port 8000

3. Set your FreePBX inbound route to POST to http://<your-server>:8000/inbound

You can extend the `/inbound` endpoint to add agent logic later.
# ravoxai
