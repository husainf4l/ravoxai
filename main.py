from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from auth_sip_client import AuthenticatedSIPClient
from voice_sip_client import VoiceSIPClient
from rtp_voice_client import VoiceRTPSIPClient
from sip_caller import AsteriskCaller
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

@app.post("/inbound")
async def inbound_call(request: Request):
    data = await request.json()
    # Log or process the inbound call data
    print("Inbound call received:", data)
    return JSONResponse(content={"status": "received"})

@app.post("/make_call")
async def make_call(request: Request):
    """Make an outbound call using Asterisk AMI"""
    data = await request.json()
    to_number = data.get("to_number", "0796026659")
    from_channel = data.get("from_channel", "SIP/1001")
    
    caller = AsteriskCaller()
    
    if caller.connect():
        success = caller.make_call(from_channel, to_number)
        caller.disconnect()
        
        if success:
            return JSONResponse(content={"status": "success", "message": f"Call initiated to {to_number}"})
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to initiate call"})
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to connect to Asterisk"})

@app.post("/voice_call")
async def make_voice_call(request: Request):
    """Make a voice call with generated speech"""
    data = await request.json()
    to_number = data.get("to_number", "0796026659")
    message_text = data.get("message", "Hello! This is a test call from your VoIP agent. Can you hear me clearly?")
    
    # Check if ElevenLabs API key is configured
    if not os.getenv('ELEVENLABS_API_KEY'):
        return JSONResponse(content={
            "status": "error", 
            "message": "ElevenLabs API key not configured"
        })
    
    try:
        print(f"Creating VoiceRTPSIPClient...")
        voice_client = VoiceRTPSIPClient()  # Use RTP voice client for better quality
        print(f"Making voice call to {to_number} with message: {message_text}")
        success = voice_client.make_voice_call_with_rtp(to_number, message_text)
        print(f"Voice call result: {success}")
        
        if success:
            return JSONResponse(content={
                "status": "success", 
                "message": f"Voice call completed to {to_number}",
                "spoke_message": message_text
            })
        else:
            return JSONResponse(content={
                "status": "error", 
                "message": "Voice call failed"
            })
            
    except Exception as e:
        print(f"Exception in voice call: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={
            "status": "error", 
            "message": f"Error making voice call: {str(e)}"
        })

@app.post("/sip_call")
async def make_sip_call(request: Request):
    """Make a simple SIP call without voice"""
    data = await request.json()
    to_number = data.get("to_number", "0796026659")
    
    try:
        sip_client = AuthenticatedSIPClient()
        success = sip_client.make_authenticated_call(to_number)
        
        if success:
            return JSONResponse(content={
                "status": "success", 
                "message": f"SIP call completed to {to_number}"
            })
        else:
            return JSONResponse(content={
                "status": "error", 
                "message": "SIP call failed"
            })
            
    except Exception as e:
        return JSONResponse(content={
            "status": "error", 
            "message": f"Error making SIP call: {str(e)}"
        })

@app.get("/")
def root():
    return {
        "message": "VoIP Agent FastAPI is running", 
        "endpoints": {
            "POST /voice_call": "Make a call with generated speech",
            "POST /sip_call": "Make a simple SIP call",
            "POST /inbound": "Handle inbound calls",
            "POST /make_call": "Make call via AMI"
        }
    }
