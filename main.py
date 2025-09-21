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

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio
import os
from contextlib import asynccontextmanager
from src.agent.call_service import make_sip_call, validate_phone_number
from src.database.database import CallRecord, get_db, create_tables, test_connection
from src.services.s3_service import get_s3_service, test_s3_connection

# Load environment variables from config/.env
env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(env_path)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background task management
background_tasks_running = False

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🔍 Testing PostgreSQL database connection...")
    db_available = test_connection()

    if not db_available:
        logger.warning("⚠️ Database connection failed - running in limited mode")
        logger.warning("💡 Some features will be disabled. Run 'python setup_database.py' to set up the database")
        logger.warning("💡 The API will still work for basic operations")
    else:
        logger.info("✅ PostgreSQL connection successful")
        create_tables()
        logger.info("✅ Database tables created/verified")

    # Test S3 connection
    logger.info("🔍 Testing AWS S3 connection...")
    if test_s3_connection():
        logger.info("✅ AWS S3 connection successful")
    else:
        logger.warning("⚠️ AWS S3 connection failed - media upload will be disabled")
        logger.warning("💡 Check your AWS credentials in .env file")

    # Start background tasks
    global background_tasks_running
    background_tasks_running = True
    asyncio.create_task(run_background_tasks())
    logger.info("✅ Background tasks started")

    yield

    # Shutdown
    logger.info("🛑 Shutting down AI Call Service...")
    background_tasks_running = False
    logger.info("✅ Background tasks stopped")

app = FastAPI(
    title="AI Call Service",
    description="API to initiate AI-powered phone calls with subject context and database tracking",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Background Task Functions
async def run_background_tasks():
    """Main background task runner"""
    logger.info("🔄 Starting background task scheduler...")
    
    while background_tasks_running:
        try:
            # Run cleanup tasks every 5 minutes
            await cleanup_old_records()
            
            # Run health check every 2 minutes
            await health_check()
            
            # Run status update task every 1 minute
            await update_call_statuses()
            
            # Wait 1 minute before next cycle
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"❌ Background task error: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error

async def cleanup_old_records():
    """Clean up old call records and failed calls"""
    try:
        db = next(get_db())
        
        # Clean up failed calls older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        failed_calls = db.query(CallRecord).filter(
            CallRecord.status == "failed",
            CallRecord.created_at < cutoff_time
        ).all()
        
        for call in failed_calls:
            logger.info(f"🧹 Cleaning up failed call: {call.call_id}")
            db.delete(call)
        
        # Clean up old completed calls (older than 30 days)
        old_cutoff = datetime.utcnow() - timedelta(days=30)
        old_calls = db.query(CallRecord).filter(
            CallRecord.status == "completed",
            CallRecord.created_at < old_cutoff
        ).all()
        
        for call in old_calls:
            logger.info(f"🧹 Cleaning up old completed call: {call.call_id}")
            db.delete(call)
        
        db.commit()
        logger.info(f"✅ Cleaned up {len(failed_calls)} failed calls and {len(old_calls)} old calls")
        
    except Exception as e:
        logger.error(f"❌ Database cleanup error: {e}")
        db.rollback()
    finally:
        db.close()

async def health_check():
    """Perform health checks on external services"""
    try:
        # Check database connection
        db_healthy = test_connection()
        
        # Check S3 connection
        s3_healthy = test_s3_connection()
        
        if not db_healthy:
            logger.warning("⚠️ Database health check failed")
        if not s3_healthy:
            logger.warning("⚠️ S3 health check failed")
        
        if db_healthy and s3_healthy:
            logger.debug("✅ All health checks passed")
            
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")

async def update_call_statuses():
    """Update call statuses for calls that may have timed out"""
    try:
        db = next(get_db())
        
        # Find calls that have been "connecting" for more than 5 minutes
        timeout_cutoff = datetime.utcnow() - timedelta(minutes=5)
        stale_calls = db.query(CallRecord).filter(
            CallRecord.status == "connecting",
            CallRecord.started_at < timeout_cutoff
        ).all()
        
        for call in stale_calls:
            logger.warning(f"⏰ Call timeout detected: {call.call_id}")
            call.status = "timeout"
            call.ended_at = datetime.utcnow()
        
        # Find calls that have been "initiated" for more than 2 minutes
        initiated_timeout = datetime.utcnow() - timedelta(minutes=2)
        old_initiated = db.query(CallRecord).filter(
            CallRecord.status == "initiated",
            CallRecord.created_at < initiated_timeout
        ).all()
        
        for call in old_initiated:
            logger.warning(f"⏰ Call initiation timeout: {call.call_id}")
            call.status = "failed"
        
        db.commit()
        logger.info(f"✅ Updated {len(stale_calls)} stale calls and {len(old_initiated)} old initiated calls")
        
    except Exception as e:
        logger.error(f"❌ Status update error: {e}")
        db.rollback()
    finally:
        db.close()


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

    model_config = {"from_attributes": True}


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


@app.get("/calls")
async def get_all_calls(db: Session = Depends(get_db)):
    """Get all call records"""
    try:
        logger.info("📞 Fetching all call records...")
        calls = db.query(CallRecord).order_by(CallRecord.created_at.desc()).all()
        logger.info(f"✅ Found {len(calls)} call records")
        
        # Convert to dict format to avoid Pydantic issues
        result = []
        for call in calls:
            result.append({
                "id": call.id,
                "call_id": call.call_id,
                "phone_number": call.phone_number,
                "caller_name": call.caller_name,
                "agent_name": call.agent_name,
                "company_name": call.company_name,
                "subject": call.subject,
                "status": call.status,
                "created_at": call.created_at.isoformat() if call.created_at else None,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "duration_seconds": call.duration_seconds,
                "recording_url": call.recording_url,
                "recording_available": call.recording_available,
                "conversation_transcript": call.conversation_transcript,
                "conversation_summary": call.conversation_summary
            })
        
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching call records: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/calls/{call_id}")
async def get_call(call_id: str, db: Session = Depends(get_db)):
    """Get specific call record by call_id"""
    try:
        logger.info(f"📞 Fetching call record: {call_id}")
        call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
        if not call:
            logger.warning(f"⚠️ Call record not found: {call_id}")
            raise HTTPException(status_code=404, detail="Call record not found")
        
        logger.info(f"✅ Found call record: {call_id}")
        # Return as dict format
        return {
            "id": call.id,
            "call_id": call.call_id,
            "phone_number": call.phone_number,
            "caller_name": call.caller_name,
            "agent_name": call.agent_name,
            "company_name": call.company_name,
            "subject": call.subject,
            "status": call.status,
            "created_at": call.created_at.isoformat() if call.created_at else None,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": call.duration_seconds,
            "recording_url": call.recording_url,
            "recording_available": call.recording_available,
            "conversation_transcript": call.conversation_transcript,
            "conversation_summary": call.conversation_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching call record {call_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/test-calls")
async def test_calls_endpoint(db: Session = Depends(get_db)):
    """Test endpoint to debug call records"""
    try:
        calls = db.query(CallRecord).order_by(CallRecord.created_at.desc()).limit(1).all()
        if not calls:
            return {"message": "No calls found"}
        
        call = calls[0]
        # Return raw data without Pydantic model
        return {
            "id": call.id,
            "call_id": call.call_id,
            "phone_number": call.phone_number,
            "status": call.status,
            "created_at": str(call.created_at)
        }
    except Exception as e:
        return {"error": str(e), "type": str(type(e))}


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
    """Get comprehensive media information for a specific call"""
    try:
        logger.info(f"📞 Fetching media for call: {call_id}")
        call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
        if not call:
            raise HTTPException(status_code=404, detail="Call record not found")

        s3_service = get_s3_service()
        media_files = []

        if s3_service:
            # Get all recordings from S3
            s3_recordings = s3_service.list_call_recordings(call_id)
            media_files.extend(s3_recordings)

        # Build comprehensive media response
        media_info = {
            "call_id": call.call_id,
            "recording_available": call.recording_url is not None,
            "recording_url": call.recording_url,
            "recording_s3_key": call.recording_s3_key,
            "transcript_available": call.transcript_url is not None,
            "transcript_url": call.transcript_url,
            "transcript_s3_key": call.transcript_s3_key,
            "duration_seconds": call.duration_seconds,
            "recording_format": call.recording_format,
            "call_status": call.status,
            "call_created_at": call.created_at.isoformat() if call.created_at else None,
            "call_started_at": call.started_at.isoformat() if call.started_at else None,
            "call_ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "s3_media_files": media_files,
            "media_summary": {
                "total_files": len(media_files),
                "has_audio": any(f.get('type') == 'audio' for f in media_files),
                "has_transcript": any(f.get('type') == 'transcript' for f in media_files),
                "recording_formats": list(set(f.get('format', 'unknown') for f in media_files if f.get('type') == 'audio'))
            }
        }

        logger.info(f"✅ Found media for call: {call_id} - {len(media_files)} files")
        return media_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching media for call {call_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


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
        },
        "background_tasks": {
            "running": background_tasks_running,
            "tasks": ["cleanup_old_records", "health_check", "update_call_statuses"]
        }
    }


@app.post("/tasks/cleanup")
async def trigger_cleanup():
    """Manually trigger database cleanup task"""
    try:
        await cleanup_old_records()
        return {"message": "Cleanup task completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@app.post("/tasks/health-check")
async def trigger_health_check():
    """Manually trigger health check"""
    try:
        await health_check()
        return {"message": "Health check completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/tasks/update-statuses")
async def trigger_status_update():
    """Manually trigger call status update task"""
    try:
        await update_call_statuses()
        return {"message": "Status update task completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status update failed: {str(e)}")


@app.get("/tasks/status")
async def get_task_status():
    """Get background task status"""
    return {
        "background_tasks_running": background_tasks_running,
        "available_tasks": [
            "cleanup_old_records",
            "health_check", 
            "update_call_statuses"
        ]
    }


@app.post("/calls/{call_id}/upload-media")
async def upload_call_media(
    call_id: str,
    file_type: str = "recording",  # "recording" or "transcript"
    file_path: str = None,
    s3_key: str = None,
    db: Session = Depends(get_db)
):
    """Upload media file for an existing call (recording or transcript)"""
    try:
        logger.info(f"📤 Uploading {file_type} for call: {call_id}")

        # Find the call record
        call = db.query(CallRecord).filter(CallRecord.call_id == call_id).first()
        if not call:
            raise HTTPException(status_code=404, detail="Call record not found")

        s3_service = get_s3_service()
        if not s3_service:
            raise HTTPException(status_code=503, detail="S3 service not available")

        upload_result = None

        if file_type == "recording":
            if file_path and os.path.exists(file_path):
                # Upload from local file
                upload_result = s3_service.upload_recording(file_path, call_id)
            elif s3_key:
                # Just update the S3 key reference
                upload_result = {"s3_key": s3_key, "url": s3_service.get_recording_url(s3_key)}
            else:
                raise HTTPException(status_code=400, detail="Either file_path or s3_key must be provided")

            # Update call record
            call.recording_available = True
            call.recording_url = upload_result["s3_url"]
            call.recording_s3_key = upload_result["s3_key"]
            call.recording_format = upload_result.get("format", "mp3")

        elif file_type == "transcript":
            if file_path and os.path.exists(file_path):
                # Read file content and upload
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                upload_result = s3_service.upload_transcript(transcript_content, call_id)
            elif s3_key:
                # Just update the S3 key reference
                upload_result = {"s3_key": s3_key, "url": s3_service.get_transcript_url(s3_key)}
            else:
                raise HTTPException(status_code=400, detail="Either file_path or s3_key must be provided")

            # Update call record
            call.transcript_available = True
            call.transcript_url = upload_result["s3_url"]
            call.transcript_s3_key = upload_result["s3_key"]

        else:
            raise HTTPException(status_code=400, detail="file_type must be 'recording' or 'transcript'")

        # Commit changes
        db.commit()

        logger.info(f"✅ Successfully uploaded {file_type} for call: {call_id}")
        return {
            "message": f"{file_type.title()} uploaded successfully",
            "call_id": call_id,
            "file_type": file_type,
            "s3_key": upload_result["s3_key"],
            "url": upload_result["url"],
            "updated_fields": {
                "recording_available": call.recording_available,
                "transcript_available": call.transcript_available,
                "recording_url": call.recording_url,
                "transcript_url": call.transcript_url
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading media for call {call_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


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