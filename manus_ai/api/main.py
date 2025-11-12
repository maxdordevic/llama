"""
FastAPI Backend for Manus AI Clone
Main API server handling all requests
"""

import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime

from ..core.orchestrator import AgentOrchestrator
from ..core.task_planner import TaskPlanner
from ..core.session_manager import SessionManager, SessionStatus
from ..core.llm_providers import LLMManager, LLMProvider
from ..memory.memory_system import MemoryManager
from ..sandbox.code_executor import CodeExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Manus AI Clone API",
    description="Autonomous AI Agent Platform with Multi-Agent Architecture",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
llm_manager = LLMManager()
task_planner = TaskPlanner(llm_manager)
orchestrator = AgentOrchestrator(llm_manager, task_planner)
session_manager = SessionManager()
memory_manager = MemoryManager()
code_executor = CodeExecutor()

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}


# Pydantic models
class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    status: str
    metadata: Optional[Dict[str, Any]] = None


class ExecuteCodeRequest(BaseModel):
    code: str
    context: Optional[Dict[str, Any]] = None
    timeout: int = 30


class SessionCreate(BaseModel):
    user_id: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryAddRequest(BaseModel):
    user_id: str
    content: str
    memory_type: str = "fact"
    importance: float = 0.5
    long_term: bool = False


# Routes

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Manus AI Clone API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "orchestrator": "operational",
            "task_planner": "operational",
            "session_manager": "operational",
            "llm_manager": "operational"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Main chat endpoint for user interactions
    Handles complete task execution end-to-end
    """
    try:
        logger.info(f"Chat request from user {request.user_id}")

        # Get or create session
        if request.session_id:
            session = await session_manager.get_session(request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = await session_manager.create_session(
                user_id=request.user_id,
                metadata=request.metadata
            )

        # Add user message to session
        await session_manager.add_message(
            session_id=session.id,
            role="user",
            content=request.message
        )

        # Get user memory for context
        memory = memory_manager.get_memory(request.user_id)
        context_summary = memory.get_context_summary()

        # Execute request through orchestrator
        async def progress_callback(update: Dict[str, Any]):
            # Send progress updates via WebSocket if connected
            if session.id in active_connections:
                try:
                    await active_connections[session.id].send_json(update)
                except:
                    pass

        result = await orchestrator.execute_request(
            user_request=request.message,
            session_id=session.id,
            progress_callback=progress_callback
        )

        # Add result to session
        await session_manager.add_result(session.id, result)

        # Generate response message
        if result["status"] == "success":
            response_message = result["result"].get("summary", "Task completed successfully")

            # Add assistant message to session
            await session_manager.add_message(
                session_id=session.id,
                role="assistant",
                content=response_message
            )

            # Learn from successful execution
            if result.get("plan"):
                memory.record_successful_approach(
                    task_type="general",
                    approach=result["plan"],
                    success_score=1.0
                )

        else:
            response_message = f"Task failed: {result.get('error', 'Unknown error')}"

            await session_manager.add_message(
                session_id=session.id,
                role="assistant",
                content=response_message
            )

        return ChatResponse(
            session_id=session.id,
            message=response_message,
            status=result["status"],
            metadata={
                "execution_time": result.get("execution_time", 0),
                "plan": result.get("plan", {})
            }
        )

    except Exception as e:
        logger.error(f"Chat request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint
    Returns Server-Sent Events for real-time progress
    """
    try:
        async def event_generator():
            # Create or get session
            if request.session_id:
                session = await session_manager.get_session(request.session_id)
            else:
                session = await session_manager.create_session(
                    user_id=request.user_id,
                    metadata=request.metadata
                )

            yield f"data: {json.dumps({'type': 'session', 'session_id': session.id})}\n\n"

            # Add user message
            await session_manager.add_message(
                session_id=session.id,
                role="user",
                content=request.message
            )

            # Progress callback for streaming
            async def progress_callback(update: Dict[str, Any]):
                yield f"data: {json.dumps(update)}\n\n"

            # Execute request
            result = await orchestrator.execute_request(
                user_request=request.message,
                session_id=session.id,
                progress_callback=progress_callback
            )

            # Send final result
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
            yield f"data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time progress updates
    """
    await websocket.accept()
    active_connections[session_id] = websocket

    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()

            # Handle incoming messages if needed
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        if session_id in active_connections:
            del active_connections[session_id]


@app.post("/sessions", response_model=Dict[str, Any])
async def create_session(request: SessionCreate):
    """Create new session"""
    try:
        session = await session_manager.create_session(
            user_id=request.user_id,
            title=request.title,
            metadata=request.metadata
        )
        return session.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str):
    """Get session by ID"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.get("/users/{user_id}/sessions", response_model=List[Dict[str, Any]])
async def list_user_sessions(user_id: str, limit: int = 50, offset: int = 0):
    """List sessions for user"""
    sessions = await session_manager.list_user_sessions(user_id, limit, offset)
    return [s.to_dict() for s in sessions]


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete session"""
    await session_manager.delete_session(session_id)
    return {"status": "deleted"}


@app.post("/execute/code")
async def execute_code(request: ExecuteCodeRequest):
    """
    Execute Python code in sandboxed environment
    """
    try:
        result = await code_executor.execute_code(
            code=request.code,
            context=request.context,
        )
        return result
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/add")
async def add_memory(request: MemoryAddRequest):
    """Add memory for user"""
    try:
        memory = memory_manager.get_memory(request.user_id)
        entry = memory.add_memory(
            content=request.content,
            memory_type=request.memory_type,
            importance=request.importance,
            long_term=request.long_term
        )
        return entry.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{user_id}")
async def get_user_memory(user_id: str):
    """Get user memory"""
    try:
        memory = memory_manager.get_memory(user_id)
        return memory.export_memory()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """Get user preferences"""
    try:
        memory = memory_manager.get_memory(user_id)
        return memory.preferences
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan/create")
async def create_execution_plan(request: Dict[str, Any]):
    """Create execution plan for request"""
    try:
        user_request = request.get("user_request")
        if not user_request:
            raise HTTPException(status_code=400, detail="user_request required")

        plan = await task_planner.create_plan(user_request)
        return plan.to_dict()
    except Exception as e:
        logger.error(f"Plan creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers")
async def list_providers():
    """List available LLM providers"""
    return {
        "providers": [
            {
                "id": provider.value,
                "name": provider.name,
                "available": True  # Could check API keys
            }
            for provider in LLMProvider
        ]
    }


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("Manus AI Clone API starting up...")
    logger.info(f"Available LLM providers: {[p.value for p in LLMProvider]}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("Manus AI Clone API shutting down...")
    # Close WebSocket connections
    for ws in active_connections.values():
        await ws.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
