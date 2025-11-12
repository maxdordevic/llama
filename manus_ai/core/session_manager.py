"""
Session Management System
Handles user sessions, persistence, and state management
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Message:
    """Chat message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Session:
    """User session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = "New Session"
    status: SessionStatus = SessionStatus.ACTIVE
    messages: List[Message] = field(default_factory=list)
    execution_plan: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to session"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history in LLM format"""
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
        if limit:
            messages = messages[-limit:]
        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status.value,
            "messages": [msg.to_dict() for msg in self.messages],
            "execution_plan": self.execution_plan,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages user sessions and state
    Features:
    - Session lifecycle management
    - Message history
    - State persistence
    - Session replay
    - Concurrent session handling
    """

    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage = storage_backend or InMemoryStorage()
        self.active_sessions: Dict[str, Session] = {}

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create new session"""
        session = Session(
            user_id=user_id,
            title=title or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            metadata=metadata or {}
        )

        self.active_sessions[session.id] = session
        await self.storage.save_session(session)

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Load from storage
        session = await self.storage.load_session(session_id)
        if session:
            self.active_sessions[session_id] = session

        return session

    async def update_session(self, session: Session):
        """Update session"""
        session.updated_at = datetime.utcnow()
        self.active_sessions[session.id] = session
        await self.storage.save_session(session)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Message:
        """Add message to session"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = session.add_message(role, content, metadata)
        await self.update_session(session)

        return message

    async def set_execution_plan(
        self,
        session_id: str,
        plan: Dict[str, Any]
    ):
        """Set execution plan for session"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.execution_plan = plan
        await self.update_session(session)

    async def add_result(
        self,
        session_id: str,
        result: Dict[str, Any]
    ):
        """Add execution result to session"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.results.append(result)
        await self.update_session(session)

    async def complete_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED
    ):
        """Mark session as completed"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = status
        session.completed_at = datetime.utcnow()
        await self.update_session(session)

        logger.info(f"Session {session_id} marked as {status.value}")

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """List sessions for user"""
        return await self.storage.list_user_sessions(user_id, limit, offset)

    async def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        await self.storage.delete_session(session_id)
        logger.info(f"Deleted session {session_id}")

    async def cleanup_old_sessions(self, days: int = 30):
        """Cleanup sessions older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        await self.storage.cleanup_sessions(cutoff)


class InMemoryStorage:
    """In-memory storage backend"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    async def save_session(self, session: Session):
        """Save session"""
        self.sessions[session.id] = session

    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load session"""
        return self.sessions.get(session_id)

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """List user sessions"""
        user_sessions = [
            s for s in self.sessions.values()
            if s.user_id == user_id
        ]
        # Sort by created_at descending
        user_sessions.sort(key=lambda s: s.created_at, reverse=True)
        return user_sessions[offset:offset + limit]

    async def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def cleanup_sessions(self, cutoff: datetime):
        """Cleanup old sessions"""
        to_delete = [
            sid for sid, session in self.sessions.items()
            if session.created_at < cutoff
        ]
        for sid in to_delete:
            del self.sessions[sid]


class MongoDBStorage:
    """MongoDB storage backend"""

    def __init__(self, connection_string: str, database: str = "manus_ai"):
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self.client = AsyncIOMotorClient(connection_string)
            self.db = self.client[database]
            self.sessions_collection = self.db["sessions"]
        except ImportError:
            raise ImportError("motor package required for MongoDB storage")

    async def save_session(self, session: Session):
        """Save session to MongoDB"""
        doc = session.to_dict()
        await self.sessions_collection.update_one(
            {"id": session.id},
            {"$set": doc},
            upsert=True
        )

    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from MongoDB"""
        doc = await self.sessions_collection.find_one({"id": session_id})
        if not doc:
            return None

        # Reconstruct session from document
        return self._doc_to_session(doc)

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """List user sessions"""
        cursor = self.sessions_collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(offset).limit(limit)

        sessions = []
        async for doc in cursor:
            sessions.append(self._doc_to_session(doc))

        return sessions

    async def delete_session(self, session_id: str):
        """Delete session"""
        await self.sessions_collection.delete_one({"id": session_id})

    async def cleanup_sessions(self, cutoff: datetime):
        """Cleanup old sessions"""
        await self.sessions_collection.delete_many({
            "created_at": {"$lt": cutoff.isoformat()}
        })

    def _doc_to_session(self, doc: Dict[str, Any]) -> Session:
        """Convert MongoDB document to Session object"""
        # Parse dates
        created_at = datetime.fromisoformat(doc["created_at"])
        updated_at = datetime.fromisoformat(doc["updated_at"])
        completed_at = datetime.fromisoformat(doc["completed_at"]) if doc.get("completed_at") else None

        # Parse messages
        messages = [
            Message(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                metadata=msg.get("metadata", {})
            )
            for msg in doc.get("messages", [])
        ]

        return Session(
            id=doc["id"],
            user_id=doc["user_id"],
            title=doc["title"],
            status=SessionStatus(doc["status"]),
            messages=messages,
            execution_plan=doc.get("execution_plan"),
            results=doc.get("results", []),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            metadata=doc.get("metadata", {})
        )
