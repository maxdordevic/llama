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

# Infrastructure components
from ..core.jobs import get_job_manager, get_scheduled_jobs_manager
from ..core.cache import get_cache_manager, get_llm_cache
from ..core.events import get_event_bus, get_webhook_manager, get_event_emitter, EventType

# Infrastructure routers
from .infrastructure_endpoints import jobs_router, cache_router, webhooks_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Manus AI Clone API",
    description="Autonomous AI Agent Platform with Multi-Agent Architecture and Enterprise Infrastructure",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include infrastructure routers
app.include_router(jobs_router, prefix="/api/v2/jobs", tags=["Job Queue"])
app.include_router(cache_router, prefix="/api/v2/cache", tags=["Caching"])
app.include_router(webhooks_router, prefix="/api/v2/webhooks", tags=["Webhooks & Events"])

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
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check for all system components"""
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }

    # Core components
    health_status["components"]["orchestrator"] = {"status": "operational", "details": "Multi-agent orchestration system"}
    health_status["components"]["task_planner"] = {"status": "operational", "details": "Task planning and decomposition"}
    health_status["components"]["session_manager"] = {"status": "operational", "details": "Session management"}
    health_status["components"]["llm_manager"] = {"status": "operational", "details": "LLM provider management"}

    # Infrastructure components
    try:
        # Check Redis (cache)
        cache_manager = get_cache_manager()
        try:
            stats = await cache_manager.get_stats()
            health_status["components"]["cache"] = {
                "status": "operational",
                "details": f"{stats.total_keys} keys, {stats.hit_rate:.1f}% hit rate"
            }
        except Exception as e:
            health_status["components"]["cache"] = {"status": "degraded", "error": str(e)}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["cache"] = {"status": "unavailable", "error": str(e)}
        health_status["status"] = "degraded"

    try:
        # Check Celery workers
        job_manager = get_job_manager()
        try:
            stats = job_manager.get_queue_stats()
            health_status["components"]["job_queue"] = {
                "status": "operational",
                "details": f"{stats.get('workers', 0)} workers, {stats.get('active_jobs', 0)} active jobs"
            }
        except Exception as e:
            health_status["components"]["job_queue"] = {"status": "degraded", "error": str(e)}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["job_queue"] = {"status": "unavailable", "error": str(e)}
        health_status["status"] = "degraded"

    try:
        # Check Event Bus
        event_bus = get_event_bus()
        event_count = len(event_bus.event_history)
        health_status["components"]["event_bus"] = {
            "status": "operational",
            "details": f"{event_count} events in history"
        }
    except Exception as e:
        health_status["components"]["event_bus"] = {"status": "degraded", "error": str(e)}

    try:
        # Check Webhook Manager
        webhook_manager = get_webhook_manager()
        webhooks = webhook_manager.list_webhooks(active_only=True)
        health_status["components"]["webhooks"] = {
            "status": "operational",
            "details": f"{len(webhooks)} active webhooks"
        }
    except Exception as e:
        health_status["components"]["webhooks"] = {"status": "degraded", "error": str(e)}

    return health_status


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


# Event streaming WebSocket connections
event_stream_connections: Dict[str, WebSocket] = {}


@app.websocket("/ws/events/{client_id}")
async def event_stream_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time event streaming
    Clients can subscribe to specific event types and receive updates in real-time
    """
    await websocket.accept()
    event_stream_connections[client_id] = websocket

    logger.info(f"Event stream client connected: {client_id}")

    # Track subscribed events
    subscribed_events = set()

    # Event handler for broadcasting to this client
    async def event_handler(event):
        """Handle events and send to this WebSocket client"""
        if event.type in subscribed_events or not subscribed_events:  # Empty set = subscribe to all
            try:
                await websocket.send_json({
                    "type": "event",
                    "event_id": event.id,
                    "event_type": event.type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "metadata": event.metadata
                })
            except Exception as e:
                logger.error(f"Failed to send event to client {client_id}: {e}")

    # Subscribe to event bus
    event_bus = get_event_bus()

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to event stream",
            "available_events": [e.value for e in EventType]
        })

        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

                elif msg_type == "subscribe":
                    # Subscribe to specific events
                    events = message.get("events", [])
                    for event_str in events:
                        try:
                            event_type = EventType(event_str)
                            subscribed_events.add(event_type)
                            event_bus.subscribe(event_type, event_handler)
                            logger.info(f"Client {client_id} subscribed to {event_type.value}")
                        except ValueError:
                            logger.warning(f"Unknown event type: {event_str}")

                    await websocket.send_json({
                        "type": "subscribed",
                        "events": [e.value for e in subscribed_events]
                    })

                elif msg_type == "unsubscribe":
                    # Unsubscribe from events
                    events = message.get("events", [])
                    for event_str in events:
                        try:
                            event_type = EventType(event_str)
                            if event_type in subscribed_events:
                                subscribed_events.remove(event_type)
                                event_bus.unsubscribe(event_type, event_handler)
                                logger.info(f"Client {client_id} unsubscribed from {event_type.value}")
                        except ValueError:
                            pass

                    await websocket.send_json({
                        "type": "unsubscribed",
                        "events": [e.value for e in subscribed_events]
                    })

                elif msg_type == "subscribe_all":
                    # Subscribe to all events
                    for event_type in EventType:
                        subscribed_events.add(event_type)
                        event_bus.subscribe(event_type, event_handler)

                    await websocket.send_json({
                        "type": "subscribed",
                        "events": "all"
                    })
                    logger.info(f"Client {client_id} subscribed to all events")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        logger.info(f"Event stream client disconnected: {client_id}")

        # Unsubscribe from all events
        for event_type in subscribed_events:
            event_bus.unsubscribe(event_type, event_handler)

        if client_id in event_stream_connections:
            del event_stream_connections[client_id]

    except Exception as e:
        logger.error(f"Event stream error for client {client_id}: {e}")
        if client_id in event_stream_connections:
            del event_stream_connections[client_id]


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


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    Returns metrics for monitoring infrastructure components
    """
    metrics_data = []

    # System info
    metrics_data.append(f'# HELP manus_ai_info System information')
    metrics_data.append(f'# TYPE manus_ai_info gauge')
    metrics_data.append(f'manus_ai_info{{version="2.0.0"}} 1')

    try:
        # Cache metrics
        cache_manager = get_cache_manager()
        stats = await cache_manager.get_stats()

        metrics_data.append(f'# HELP cache_hits_total Total cache hits')
        metrics_data.append(f'# TYPE cache_hits_total counter')
        metrics_data.append(f'cache_hits_total {stats.hits}')

        metrics_data.append(f'# HELP cache_misses_total Total cache misses')
        metrics_data.append(f'# TYPE cache_misses_total counter')
        metrics_data.append(f'cache_misses_total {stats.misses}')

        metrics_data.append(f'# HELP cache_hit_rate Cache hit rate percentage')
        metrics_data.append(f'# TYPE cache_hit_rate gauge')
        metrics_data.append(f'cache_hit_rate {stats.hit_rate}')

        metrics_data.append(f'# HELP cache_keys_total Total number of cache keys')
        metrics_data.append(f'# TYPE cache_keys_total gauge')
        metrics_data.append(f'cache_keys_total {stats.total_keys}')

        metrics_data.append(f'# HELP cache_memory_bytes Cache memory usage in bytes')
        metrics_data.append(f'# TYPE cache_memory_bytes gauge')
        metrics_data.append(f'cache_memory_bytes {stats.memory_used_mb * 1024 * 1024}')
    except Exception as e:
        logger.error(f"Failed to collect cache metrics: {e}")

    try:
        # Job queue metrics
        job_manager = get_job_manager()
        job_stats = job_manager.get_queue_stats()

        metrics_data.append(f'# HELP celery_workers_active Number of active Celery workers')
        metrics_data.append(f'# TYPE celery_workers_active gauge')
        metrics_data.append(f'celery_workers_active {job_stats.get("workers", 0)}')

        metrics_data.append(f'# HELP celery_tasks_active Number of active tasks')
        metrics_data.append(f'# TYPE celery_tasks_active gauge')
        metrics_data.append(f'celery_tasks_active {job_stats.get("active_jobs", 0)}')
    except Exception as e:
        logger.error(f"Failed to collect job queue metrics: {e}")

    try:
        # Event and webhook metrics
        event_bus = get_event_bus()
        metrics_data.append(f'# HELP events_emitted_total Total events emitted')
        metrics_data.append(f'# TYPE events_emitted_total counter')
        metrics_data.append(f'events_emitted_total {len(event_bus.event_history)}')

        webhook_manager = get_webhook_manager()
        webhooks = webhook_manager.list_webhooks(active_only=True)
        metrics_data.append(f'# HELP webhooks_registered_total Total registered webhooks')
        metrics_data.append(f'# TYPE webhooks_registered_total gauge')
        metrics_data.append(f'webhooks_registered_total {len(webhooks)}')
    except Exception as e:
        logger.error(f"Failed to collect event metrics: {e}")

    try:
        # WebSocket connections
        metrics_data.append(f'# HELP websocket_connections_active Active WebSocket connections')
        metrics_data.append(f'# TYPE websocket_connections_active gauge')
        metrics_data.append(f'websocket_connections_active {len(active_connections)}')
    except Exception as e:
        logger.error(f"Failed to collect WebSocket metrics: {e}")

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content="\n".join(metrics_data), media_type="text/plain")


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("="*70)
    logger.info("Manus AI Clone API v2.0.0 - Starting up...")
    logger.info("="*70)

    # Core components
    logger.info(f"✓ Available LLM providers: {[p.value for p in LLMProvider]}")
    logger.info(f"✓ Orchestrator initialized")
    logger.info(f"✓ Task Planner initialized")
    logger.info(f"✓ Session Manager initialized")

    # Infrastructure components
    try:
        cache_manager = get_cache_manager()
        logger.info(f"✓ Cache Manager initialized")

        job_manager = get_job_manager()
        logger.info(f"✓ Job Queue initialized")

        event_bus = get_event_bus()
        logger.info(f"✓ Event Bus initialized")

        webhook_manager = get_webhook_manager()
        logger.info(f"✓ Webhook Manager initialized")

        # Emit startup event
        event_emitter = get_event_emitter()
        from ..core.events import EventType
        await event_emitter.emit(
            EventType.SYSTEM_WARNING,  # Using warning as custom startup event
            data={"message": "Manus AI system started", "version": "2.0.0"}
        )
        logger.info(f"✓ Startup event emitted")

    except Exception as e:
        logger.error(f"⚠ Infrastructure initialization warning: {e}")
        logger.info("  System will continue with core features only")

    logger.info("="*70)
    logger.info("🚀 Manus AI is ready!")
    logger.info("="*70)
    logger.info(f"📡 API Documentation: http://localhost:8000/docs")
    logger.info(f"📊 Health Check: http://localhost:8000/health/detailed")
    logger.info(f"📈 Metrics: http://localhost:8000/metrics")
    logger.info(f"🔄 Job Queue Dashboard: http://localhost:5555")
    logger.info("="*70)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("="*70)
    logger.info("Manus AI Clone API shutting down...")
    logger.info("="*70)

    # Close WebSocket connections
    total_connections = len(active_connections) + len(event_stream_connections)
    logger.info(f"Closing {total_connections} WebSocket connections...")

    for ws in active_connections.values():
        await ws.close()

    for ws in event_stream_connections.values():
        await ws.close()

    # Emit shutdown event
    try:
        event_emitter = get_event_emitter()
        from ..core.events import EventType
        await event_emitter.emit(
            EventType.SYSTEM_WARNING,
            data={"message": "Manus AI system shutting down", "version": "2.0.0"}
        )
        logger.info("✓ Shutdown event emitted")
    except Exception as e:
        logger.warning(f"Failed to emit shutdown event: {e}")

    logger.info("✓ Shutdown complete")
    logger.info("="*70)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
