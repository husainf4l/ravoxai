"""
FastAPI Call API - Clean Minimal Version
REST     # Test S3 connection
    logger.info("🔍 Testing AWS S3 connection...")
    if test_s3_connection():
        logger.info("✅ AWS S3 connection successful")
    else:
        logger.warning("⚠️  AWS S3 connection failed - media upload will be disabled")
        logger.info("💡 Note: Core system works without S3. Media files will be stored locally.")
        logger.info("💡 S3 is only needed for cloud media storage and sharing.")point to initiate AI phone calls with subject context
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from dotenv import load_dotenv
from call_service import make_sip_call, validate_phone_number
from database import CallRecord, get_db, create_tables, test_connection
from s3_service import get_s3_service, test_s3_connection

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Call Service",
    description="API to initiate AI-powered phone calls with subject context and conversation tracking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    logger.info("🔍 Testing PostgreSQL database connection...")
    if not test_connection():
        logger.error("❌ Database connection failed! Please check your PostgreSQL configuration.")
        logger.error("💡 Run 'python setup_database.py' to set up the database")
        raise Exception("Database connection failed")
    
    logger.info("✅ PostgreSQL connection successful")
    create_tables()
    logger.info("✅ Database tables created/verified")
    
    # Test S3 connection
    logger.info("🔍 Testing AWS S3 connection...")
    if test_s3_connection():
        logger.info("✅ AWS S3 connection successful")
    else:
        logger.warning("⚠️  AWS S3 connection failed - media upload will be disabled")
        logger.warning("💡 Check your AWS credentials in .env file")


class CallRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to call", example="0796026659")
    subject: str = Field(..., description="Subject/purpose of the call", example="Follow up on your recent inquiry")
    caller_name: str = Field(..., description="Name of the person being called", example="Husain")
    agent_name: str = Field(default="AI Assistant", description="Name for the AI agent", example="Sarah from Sales")
    company_name: str = Field(default="Our Company", description="Company name", example="TechCorp Solutions")
    main_prompt: str = Field(..., description="Main conversation prompt with detailed context and instructions", 
                            example="I am calling to confirm our meeting tomorrow at 2 PM. Please discuss the project timeline and budget requirements.")
    caller_id: str = Field(default="AI Call Service", description="Caller ID to display")


class CallResponse(BaseModel):
    success: bool
    call_id: str
    message: str
    phone_number: str
    database_id: int
    recording_url: Optional[str] = None


class CallRecordResponse(BaseModel):
    id: int
    call_id: str
    phone_number: str
    caller_name: str
    agent_name: str
    company_name: str
    subject: str
    status: str
    created_at: datetime
    started_at: datetime = None
    ended_at: datetime = None
    duration_seconds: int = None
    recording_url: str = None
    recording_available: bool
    conversation_transcript: str = None
    conversation_summary: str = None

    class Config:
        from_attributes = True


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "AI Call Service",
        "message": "Ready to make calls with subject context and database tracking!",
        "dashboard": "/dashboard"
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the call records dashboard"""
    return FileResponse("dashboard.html")


@app.post("/make-call", response_model=CallResponse)
async def make_call(request: CallRequest, db: Session = Depends(get_db)):
    """
    Initiate a call to the specified phone number with subject context
    """
    try:
        logger.info(f"📞 Call request: {request.phone_number} - Subject: {request.subject}")
        logger.info(f"👤 Caller: {request.caller_name} | Agent: {request.agent_name} | Company: {request.company_name}")
        logger.info(f"📝 Main prompt: {request.main_prompt[:100]}...")  # Log first 100 chars
        
        # Validate phone number
        if not validate_phone_number(request.phone_number):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        
        # Create database record
        db_record = CallRecord(
            phone_number=request.phone_number.strip(),
            caller_name=request.caller_name,
            agent_name=request.agent_name,
            company_name=request.company_name,
            subject=request.subject,
            main_prompt=request.main_prompt,
            caller_id=request.caller_id,
            status="initiated"
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        logger.info(f"💾 Created database record ID: {db_record.id} with call_id: {db_record.call_id}")
            
        # Initiate call
        call_result = await make_sip_call(
            to_number=request.phone_number.strip(),
            agent_name=request.agent_name,
            subject=request.subject,
            caller_name=request.caller_name,
            company_name=request.company_name,
            main_prompt=request.main_prompt,
            db_call_id=db_record.call_id  # Pass database call ID to service
        )
        
        if call_result["success"]:
            # Update database with call success
            db_record.status = "connecting"
            db_record.started_at = datetime.utcnow()
            db.commit()
            
            return CallResponse(
                success=True,
                call_id=db_record.call_id,
                message=call_result["message"],
                phone_number=request.phone_number,
                database_id=db_record.id,
                recording_url=None  # Will be updated when call completes
            )
        else:
            # Update database with call failure
            db_record.status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Call failed: {call_result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/calls", response_model=list[CallRecordResponse])
async def get_all_calls(db: Session = Depends(get_db)):
    """Get all call records"""
    calls = db.query(CallRecord).order_by(CallRecord.created_at.desc()).all()
    return calls


@app.get("/calls/{call_id}", response_model=CallRecordResponse)
async def get_call(call_id: str, db: Session = Depends(get_db)):
    """Get specific call record by call_id"""
    call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    return call


@app.put("/calls/{call_id}/update")
async def update_call_status(
    call_id: str, 
    status: str = None,
    recording_url: str = None,
    transcript: str = None,
    summary: str = None,
    duration: int = None,
    db: Session = Depends(get_db)
):
    """Update call record with status, recording, transcript, etc."""
    call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    if status:
        call.status = status
        if status == "completed":
            call.ended_at = datetime.utcnow()
            call.call_connected = True
    
    if recording_url:
        call.recording_url = recording_url
        call.recording_available = True
    
    if transcript:
        call.conversation_transcript = transcript
        
        # Upload transcript to S3
        s3_service = get_s3_service()
        if s3_service:
            transcript_result = s3_service.upload_transcript(transcript, call_id)
            if transcript_result["success"]:
                call.transcript_url = transcript_result["s3_url"]
                call.transcript_s3_key = transcript_result["s3_key"]
                logger.info(f"📝 Transcript uploaded to S3: {transcript_result['s3_url']}")
    
    if summary:
        call.conversation_summary = summary
        
    if duration:
        call.duration_seconds = duration
    
    db.commit()
    return {"message": "Call record updated successfully"}


@app.post("/calls/{call_id}/upload-recording")
async def upload_recording(
    call_id: str,
    file_path: str,
    db: Session = Depends(get_db)
):
    """Upload call recording to S3 and update database"""
    call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    s3_service = get_s3_service()
    if not s3_service:
        raise HTTPException(status_code=503, detail="S3 service not available")
    
    # Upload recording to S3
    upload_result = s3_service.upload_recording(file_path, call_id, "audio")
    
    if upload_result["success"]:
        # Update database with S3 information
        call.recording_url = upload_result["s3_url"]
        call.recording_s3_key = upload_result["s3_key"]
        call.recording_file_size = upload_result["file_size"]
        call.recording_available = True
        db.commit()
        
        logger.info(f"🎧 Recording uploaded and database updated for call {call_id}")
        return {
            "success": True,
            "message": "Recording uploaded successfully",
            "s3_url": upload_result["s3_url"]
        }
    else:
        raise HTTPException(status_code=500, detail=f"Recording upload failed: {upload_result['error']}")


@app.get("/calls/{call_id}/recording-url")
async def get_secure_recording_url(call_id: str, db: Session = Depends(get_db)):
    """Generate secure presigned URL for call recording"""
    call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    if not call.recording_s3_key:
        raise HTTPException(status_code=404, detail="No recording available for this call")
    
    s3_service = get_s3_service()
    if not s3_service:
        raise HTTPException(status_code=503, detail="S3 service not available")
    
    # Generate presigned URL (valid for 1 hour)
    presigned_url = s3_service.generate_presigned_url(call.recording_s3_key, expiration=3600)
    
    if presigned_url:
        return {
            "recording_url": presigned_url,
            "expires_in": 3600,
            "call_id": call_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to generate secure recording URL")


@app.get("/calls/{call_id}/media")
async def get_call_media(call_id: str, db: Session = Depends(get_db)):
    """Get all media files associated with a call"""
    call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    s3_service = get_s3_service()
    media_files = []
    
    if s3_service:
        # Get all recordings from S3
        s3_recordings = s3_service.list_call_recordings(call_id)
        media_files.extend(s3_recordings)
    
    return {
        "call_id": call_id,
        "media_files": media_files,
        "recording_url": call.recording_url,
        "transcript_url": call.transcript_url,
        "database_recording_available": call.recording_available
    }


@app.get("/status")
async def get_status():
    """Service status"""
    s3_available = test_s3_connection()
    return {
        "service": "AI Call Service",
        "status": "running",
        "features": ["subject_context", "ai_agent", "sip_calling", "database_tracking", "recording_links"],
        "integrations": {
            "postgresql": "connected",
            "aws_s3": "connected" if s3_available else "disconnected",
            "livekit": "configured"
        },
        "storage": {
            "recordings": "AWS S3" if s3_available else "local/disabled",
            "transcripts": "AWS S3" if s3_available else "database_only"
        }
    }


def main():
    """Main entry point for the FastAPI application"""
    import uvicorn
    
    logger.info("🚀 Starting AI Call Service API...")
    logger.info("📖 API Documentation available at: http://localhost:8000/docs")
    logger.info("🔗 Health check at: http://localhost:8000/")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()