"""
Cleimport logging
import os
from dotenv import load_dotenv
from livekit.agents import JobContext, AgentSession, cli, WorkerOptions
from .call_agent import CallAgent

# Load environment variables from config/.env
env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
) Entry Point
Minimal implementation for AI call agent
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.agents import JobContext, AgentSession, cli, WorkerOptions
from .call_agent import CallAgent

# Load environment variables
load_dotenv(dotenv_path="../../config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
)

# Suppress verbose websockets debug logs
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("google_genai.live").setLevel(logging.WARNING)
logging.getLogger("livekit.plugins.google").setLevel(logging.INFO)

logger = logging.getLogger("call-agent")


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the agent.
    
    Args:
        ctx: The job context provided by the agent framework
    """
    
    try:
        logger.info(f"🚀 Starting Call Agent for room: {ctx.room.name}")
        
        # Connect to LiveKit
        await ctx.connect()
        logger.info("✅ Connected to LiveKit")
        
        # Create call agent and run it directly
        agent = CallAgent(ctx)
        logger.info("✅ Call agent created")
        
        # Start the agent directly - don't use AgentSession
        await agent.on_enter()
        logger.info("✅ Agent started and ready!")
        
        # Keep alive - wait for room to close naturally
        try:
            await ctx.wait_for_participant()
            # Keep running until disconnected
            while ctx.room.connection_state == "connected":
                await asyncio.sleep(1)
        except Exception:
            pass  # Room closed or connection lost
        
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        if hasattr(agent, 'call_record') and agent.call_record and agent.db_session:
            try:
                agent.call_record.status = "failed"
                agent.db_session.commit()
            except Exception:
                pass
        raise
    
    finally:
        # Cleanup
        if 'agent' in locals():
            await agent.cleanup()
if __name__ == "__main__":
    logger.info("🚀 Starting AI Call Agent...")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))