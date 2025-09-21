import logging
import json
import asyncio
from datetime import datetime
from livekit.agents import JobContext
from livekit.agents.voice import Agent
from livekit.plugins import google, silero
from database import CallRecord, SessionLocal
from s3_service import get_s3_service

logger = logging.getLogger(__name__)


class CallAgent:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)
        self.call_record = None
        self.s3_service = get_s3_service()
        self.db_session = None
        self.label = "AI Call Agent"  # Add required label attribute
    
    async def start(self):
        try:
            self.db_session = SessionLocal()
            await self._create_call_record()
            
            # Set up event handlers (only if we have a call record)
            if self.call_record:
                self.ctx.room.on("participant_connected", self._on_participant_connected)
                self.ctx.room.on("participant_disconnected", self._on_participant_disconnected)
                self.logger.info(f"CallAgent started for room {self.ctx.room.name} - Call ID: {self.call_record.id}")
            else:
                self.logger.info(f"CallAgent started for room {self.ctx.room.name} - No database record")
            
        except Exception as e:
            self.logger.error(f"Failed to start CallAgent: {e}")
            if self.db_session:
                self.db_session.rollback()
            # Don't raise - continue without database functionality
    
    async def _create_call_record(self):
        """Create database record for this call (optional - only if call context is available)"""
        try:
            # Extract metadata from JobContext (more reliable than room metadata)
            metadata = getattr(self.ctx._info.accept_arguments, 'metadata', '{}') or "{}"
            self.logger.info(f"Database - Raw metadata from JobContext: '{metadata}' (length: {len(metadata)})")
            
            # Also try room metadata as fallback
            if metadata == "{}":
                room_metadata = self.ctx.room.metadata or "{}"
                if room_metadata != "{}":
                    metadata = room_metadata
                    self.logger.info(f"Database - Using room metadata as fallback: '{metadata}' (length: {len(metadata)})")            # Try to extract call information from metadata
            call_info = {}
            if metadata and metadata != "{}":
                try:
                    import json
                    import base64
                    
                    # First try JSON parsing
                    try:
                        parsed_metadata = json.loads(metadata)
                        self.logger.info(f"Database - Successfully parsed JSON metadata: {parsed_metadata}")
                    except json.JSONDecodeError:
                        # If JSON fails, try pipe-separated format
                        self.logger.info("Database - JSON parsing failed, trying pipe-separated format")
                        parsed_metadata = {}
                        pairs = metadata.split('|')
                        for pair in pairs:
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                parsed_metadata[key.strip()] = value.strip()
                        
                        # Decode base64 main_prompt if present
                        if 'main_prompt' in parsed_metadata:
                            try:
                                parsed_metadata['main_prompt'] = base64.b64decode(parsed_metadata['main_prompt']).decode('utf-8')
                            except Exception as decode_error:
                                self.logger.warning(f"Failed to decode main_prompt: {decode_error}")
                        
                        self.logger.info(f"Database - Successfully parsed pipe-separated metadata: {parsed_metadata}")
                    
                    call_info = {
                        'phone_number': parsed_metadata.get('phone_number', parsed_metadata.get('db_call_id', 'unknown')),
                        'caller_name': parsed_metadata.get('caller_name', 'LiveKit Caller'),
                        'agent_name': parsed_metadata.get('agent_name', 'AI Assistant'),
                        'company_name': parsed_metadata.get('company_name', 'AI Call Service'),
                        'subject': parsed_metadata.get('subject', parsed_metadata.get('call_subject', 'General Call')),
                        'main_prompt': parsed_metadata.get('main_prompt', ''),
                        'caller_id': parsed_metadata.get('caller_id', parsed_metadata.get('db_call_id', 'system'))
                    }
                    self.logger.info(f"Database - Extracted call info: {call_info}")
                except Exception as e:
                    self.logger.error(f"Failed to parse call metadata: {e}")
                    self.logger.error(f"Metadata content: '{metadata}'")            # If no call information available, use defaults for LiveKit-direct calls
            if not call_info:
                call_info = {
                    'phone_number': f'livekit-{self.ctx.room.name}',
                    'caller_name': 'LiveKit Caller',
                    'agent_name': 'AI Assistant',
                    'company_name': 'AI Call Service',
                    'subject': 'Direct LiveKit Call',
                    'main_prompt': 'Direct LiveKit connection - no specific prompt',
                    'caller_id': 'livekit-system'
                }

            # Create call record
            self.call_record = CallRecord(
                status="initiated",
                metadata=metadata,
                started_at=datetime.utcnow(),
                **call_info
            )
            
            self.db_session.add(self.call_record)
            self.db_session.commit()
            self.logger.info(f"Created call record with ID: {self.call_record.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create call record: {e}")
            # Don't raise - continue without database record
            self.call_record = None
    
    def _on_participant_connected(self, participant):
        """Handle participant joining the call"""
        try:
            if self.call_record:
                self.call_record.status = "connected"
                self.call_record.connected_at = datetime.utcnow()
                self.db_session.commit()
                self.logger.info(f"Participant connected - Updated call {self.call_record.id}")
        except Exception as e:
            self.logger.error(f"Error updating call record: {e}")
    
    def _on_participant_disconnected(self, participant):
        """Handle participant leaving the call"""
        try:
            if self.call_record:
                self.call_record.status = "completed"
                self.call_record.ended_at = datetime.utcnow()
                
                if self.call_record.started_at and self.call_record.ended_at:
                    duration = (self.call_record.ended_at - self.call_record.started_at).total_seconds()
                    self.call_record.duration_seconds = int(duration)
                
                self.db_session.commit()
                self.logger.info(f"Participant disconnected - Updated call {self.call_record.id}")
        except Exception as e:
            self.logger.error(f"Error updating call record: {e}")
    
    async def on_enter(self):
        await self.start()
        
        # Get metadata from JobContext (more reliable than room metadata)
        metadata = getattr(self.ctx._info.accept_arguments, 'metadata', '{}') or "{}"
        self.logger.info(f"Agent - Raw metadata from JobContext: '{metadata}' (length: {len(metadata)})")
        
        # Also try room metadata as fallback
        if metadata == "{}":
            room_metadata = self.ctx.room.metadata or "{}"
            if room_metadata != "{}":
                metadata = room_metadata
                self.logger.info(f"Agent - Using room metadata as fallback: '{metadata}' (length: {len(metadata)})")

        # Parse metadata and extract all fields
        call_metadata = {}
        if metadata and metadata.strip() and metadata != "{}":
            try:
                import base64
                
                # First try JSON parsing
                try:
                    # Clean the metadata string to handle potential formatting issues
                    cleaned_metadata = metadata.strip()
                    if cleaned_metadata.startswith("'") and cleaned_metadata.endswith("'"):
                        cleaned_metadata = cleaned_metadata[1:-1]
                    
                    call_metadata = json.loads(cleaned_metadata)
                    self.logger.info(f"Agent - Successfully parsed JSON metadata: {call_metadata}")
                except json.JSONDecodeError:
                    # If JSON fails, try pipe-separated format
                    self.logger.info("Agent - JSON parsing failed, trying pipe-separated format")
                    pairs = metadata.split('|')
                    for pair in pairs:
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            call_metadata[key.strip()] = value.strip()
                    
                    # Decode base64 main_prompt if present
                    if 'main_prompt' in call_metadata:
                        try:
                            call_metadata['main_prompt'] = base64.b64decode(call_metadata['main_prompt']).decode('utf-8')
                        except Exception as decode_error:
                            self.logger.warning(f"Failed to decode main_prompt: {decode_error}")
                    
                    self.logger.info(f"Agent - Successfully parsed pipe-separated metadata: {call_metadata}")
            except Exception as e:
                self.logger.error(f"Failed to parse metadata: {e}")
                self.logger.error(f"Metadata content: '{metadata}'")
        else:
            self.logger.info("No metadata provided or metadata is empty")        # Extract individual fields with defaults
        caller_name = call_metadata.get("caller_name", "")
        agent_name = call_metadata.get("agent_name", "Ash")  # Default to "Ash" as requested
        company_name = call_metadata.get("company_name", "Rolevate")  # Default to "Rolevate"
        subject = call_metadata.get("subject", "")
        main_prompt = call_metadata.get("main_prompt", "")
        caller_id = call_metadata.get("caller_id", "")
        
        # Log the extracted values for debugging
        self.logger.info(f"Extracted agent_name: '{agent_name}'")
        self.logger.info(f"Extracted caller_name: '{caller_name}'")
        self.logger.info(f"Extracted company_name: '{company_name}'")

        # Create personalized greeting
        if caller_name:
            initial_greeting = f"Hello {caller_name}! I'm {agent_name} from {company_name}. I'm calling to confirm our meeting tomorrow at 2 PM."
        else:
            initial_greeting = f"Hello! I'm {agent_name} from {company_name}. I'm calling to confirm our meeting tomorrow at 2 PM."

        self.logger.info(f"Generated greeting: {initial_greeting}")
        self.logger.info(f"Main prompt: {main_prompt}")
        self.logger.info(f"Subject: {subject}")
        
        # Set up AI agent with Google's Gemini Realtime Model
        try:
            from livekit.plugins.google.beta import realtime
            from livekit.agents.voice import Agent, AgentSession

            # Create ultra-fast realtime model for immediate response
            self.logger.info(f"Setting up ultra-fast agent with greeting: {initial_greeting}")

            # FAST INITIAL GREETING: Skip TTS for now, focus on realtime model
            self.logger.info(f"Skipping TTS for now - focusing on realtime model setup")
            self.logger.info(f"Will use greeting in realtime model instructions: {initial_greeting}")

            # Set up the realtime agent for conversation
            try:
                from livekit.plugins.google.beta import realtime
                from livekit.agents.voice import Agent, AgentSession

                # Create realtime model with simple, direct instructions
                realtime_model = realtime.RealtimeModel(
                    model="gemini-2.0-flash-exp",
                    voice="Puck",
                    instructions=f"""You are Ash from Rolevate calling to confirm a meeting.

START: Say "{initial_greeting}" then immediately ask: "Does our 2 PM meeting tomorrow still work for you?"

CONTINUE: Ask about project timeline, deliverables, team availability, and additional resources needed.

DRIVE the conversation - don't wait for responses.""",
                    temperature=0.1
                )

                # Create agent with simple instructions
                agent = Agent(
                    instructions=f"""You are Ash from Rolevate.

Say: "{initial_greeting}"

Then immediately ask: "Does 2 PM tomorrow work for our meeting?"

Continue asking about: project timeline, deliverables, team availability, resources.

Be proactive - drive the conversation yourself.""",
                    llm=realtime_model,
                    allow_interruptions=True
                )

                # Start the agent session
                session = AgentSession()
                await session.start(agent, room=self.ctx.room)

                self.logger.info("Realtime agent started successfully")

            except Exception as realtime_error:
                self.logger.error(f"Realtime model failed: {realtime_error}")
                # Fallback to just logging the greeting
                self.logger.info(f"Fallback greeting: {initial_greeting}")
                raise realtime_error
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
            # Fallback to simple text-based interaction
            self.logger.info("Using fallback text-based interaction")
            self.logger.info(f"Fallback greeting: {initial_greeting}")
    
    async def cleanup(self):
        try:
            if self.call_record and self.call_record.status not in ["completed", "failed"]:
                self.call_record.status = "completed"
                self.call_record.ended_at = datetime.utcnow()
                
                if self.call_record.started_at and self.call_record.ended_at:
                    duration = (self.call_record.ended_at - self.call_record.started_at).total_seconds()
                    self.call_record.duration_seconds = int(duration)
                
                self.db_session.commit()
                self.logger.info(f"Cleaned up call record {self.call_record.id}")
            
            if self.db_session:
                self.db_session.close()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


async def agent_entry_point(ctx: JobContext):
    """Entry point for the agent with proper cleanup"""
    agent_instance = None
    try:
        # Create and start the agent
        agent_instance = CallAgent(ctx)
        await agent_instance.on_enter()
        
        # Keep the agent running - don't try to use AgentSession
        # The agent handles everything internally through the realtime model
        
    except Exception as e:
        logger.error(f"Agent error: {e}")
        if agent_instance and agent_instance.call_record and agent_instance.db_session:
            try:
                agent_instance.call_record.status = "failed"
                agent_instance.db_session.commit()
            except Exception:
                pass
    
    finally:
        if agent_instance:
            await agent_instance.cleanup()


if __name__ == "__main__":
    from livekit.agents import cli
    
    cli.run_app(agent_entry_point)
