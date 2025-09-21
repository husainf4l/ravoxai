"""
Call Service - SIP Call Initiation
Handles making phone calls via LiveKit API
"""

import os
import uuid
from dotenv import load_dotenv
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest
from livekit.protocol import room as room_proto
import logging

load_dotenv()
logger = logging.getLogger(__name__)


async def make_sip_call(to_number: str, agent_name: str = "AI Assistant", subject: str = "General conversation", 
                      caller_name: str = "the caller", company_name: str = "Our Company", main_prompt: str = "",
                      db_call_id: str = None):
    """
    Make a SIP call to the specified phone number
    
    Args:
        to_number: Phone number to call
        agent_name: Name for the AI agent
        subject: Subject/purpose of the call
        caller_name: Name of the person being called
        company_name: Name of the calling company
        main_prompt: Main conversation prompt with detailed context
        db_call_id: Database call ID for tracking
        
    Returns:
        dict: Call result with success status and details
    """
    logger.info(f"🤖 Initiating call to {to_number}")
    logger.info(f"📝 Subject: {subject}")
    logger.info(f"👤 Caller: {caller_name} | Agent: {agent_name} | Company: {company_name}")
    logger.info(f"📋 Main prompt length: {len(main_prompt)} characters")
    logger.info(f"🆔 Database call ID: {db_call_id}")

    # LiveKit credentials
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([api_key, api_secret]):
        return {
            "success": False,
            "error": "Missing LiveKit credentials",
            "call_id": None
        }

    try:
        # Initialize LiveKit API
        livekit_api = api.LiveKitAPI()
        
        # Create unique room
        call_id = str(uuid.uuid4())[:8]
        room_name = f"agent-call-{call_id}"
        
        # Create room with call context metadata
        # Encode main_prompt to handle special characters
        import base64
        encoded_prompt = base64.b64encode(main_prompt.encode('utf-8')).decode('ascii')
        
        # Build metadata string with database call ID
        metadata_parts = [
            f"call_subject:{subject}",
            f"caller_name:{caller_name}",
            f"company_name:{company_name}",
            f"main_prompt:{encoded_prompt}"
        ]
        
        if db_call_id:
            metadata_parts.append(f"db_call_id:{db_call_id}")
        
        room_request = room_proto.CreateRoomRequest(
            name=room_name,
            metadata="|".join(metadata_parts)
        )
        room = await livekit_api.room.create_room(room_request)
        logger.info(f"✅ Room created: {room.name}")

        # Place SIP call
        trunk_id = "ST_uPk4gPzCd9jz"  # Your SIP trunk
        
        sip_request = CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=to_number,
            room_name=room_name,
            participant_identity="phone-caller",
            participant_name=f"{agent_name} Call",
            wait_until_answered=False
        )
        
        sip_participant = await livekit_api.sip.create_sip_participant(sip_request)
        
        logger.info("✅ Call initiated successfully!")
        await livekit_api.aclose()
        
        return {
            "success": True,
            "call_id": call_id,
            "room_name": room_name,
            "participant_id": sip_participant.participant_identity,
            "phone_number": to_number,
            "message": f"Call initiated successfully to {to_number}"
        }

    except Exception as e:
        error_msg = f"Failed to initiate call: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "call_id": call_id if 'call_id' in locals() else None,
            "phone_number": to_number
        }


def validate_phone_number(phone_number: str) -> bool:
    """Basic phone number validation"""
    if not phone_number:
        return False
    
    # Remove spaces and common characters
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Basic checks
    return len(cleaned) >= 7 and cleaned.replace("+", "").isdigit()