"""
Memory and Learning System
Maintains context, learns from interactions, and adapts to user preferences
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryEntry:
    """Single memory entry"""

    def __init__(
        self,
        content: str,
        memory_type: str = "fact",  # fact, preference, approach, feedback
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ):
        self.id = str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0

    def access(self):
        """Mark memory as accessed"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }


class MemorySystem:
    """
    Memory and learning system for the AI agent
    Features:
    - Short-term and long-term memory
    - User preference learning
    - Successful approach tracking
    - Context-aware retrieval
    - Memory consolidation
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.short_term_memory: List[MemoryEntry] = []
        self.long_term_memory: Dict[str, List[MemoryEntry]] = defaultdict(list)
        self.preferences: Dict[str, Any] = {}
        self.successful_approaches: Dict[str, List[Dict]] = defaultdict(list)

    def add_memory(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
        long_term: bool = False
    ) -> MemoryEntry:
        """Add new memory"""
        entry = MemoryEntry(content, memory_type, importance, metadata)

        if long_term or importance >= 0.7:
            # Add to long-term memory
            self.long_term_memory[memory_type].append(entry)
            logger.info(f"Added long-term memory: {content[:50]}...")
        else:
            # Add to short-term memory
            self.short_term_memory.append(entry)

            # Limit short-term memory size
            if len(self.short_term_memory) > 100:
                # Consolidate or remove old memories
                self._consolidate_short_term()

        return entry

    def get_relevant_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Retrieve relevant memories for a query"""
        # Simple keyword-based retrieval
        # In production, would use vector embeddings and similarity search

        all_memories = []

        # Search short-term memory
        all_memories.extend(self.short_term_memory)

        # Search long-term memory
        if memory_type:
            all_memories.extend(self.long_term_memory.get(memory_type, []))
        else:
            for memories in self.long_term_memory.values():
                all_memories.extend(memories)

        # Filter by keyword match
        query_lower = query.lower()
        relevant = [
            mem for mem in all_memories
            if any(word in mem.content.lower() for word in query_lower.split())
        ]

        # Sort by importance and recency
        relevant.sort(
            key=lambda m: (m.importance, m.last_accessed),
            reverse=True
        )

        # Mark as accessed
        for mem in relevant[:limit]:
            mem.access()

        return relevant[:limit]

    def learn_preference(self, key: str, value: Any, confidence: float = 0.5):
        """Learn user preference"""
        if key in self.preferences:
            # Update existing preference
            existing = self.preferences[key]
            # Weighted average
            new_confidence = (existing["confidence"] + confidence) / 2
            self.preferences[key] = {
                "value": value,
                "confidence": new_confidence,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            self.preferences[key] = {
                "value": value,
                "confidence": confidence,
                "updated_at": datetime.utcnow().isoformat()
            }

        logger.info(f"Learned preference: {key} = {value}")

        # Also add to long-term memory
        self.add_memory(
            content=f"User preference: {key} = {value}",
            memory_type="preference",
            importance=0.8,
            long_term=True
        )

    def record_successful_approach(
        self,
        task_type: str,
        approach: Dict[str, Any],
        success_score: float = 1.0
    ):
        """Record a successful approach for future reference"""
        approach_record = {
            "approach": approach,
            "success_score": success_score,
            "timestamp": datetime.utcnow().isoformat(),
            "usage_count": 0
        }

        self.successful_approaches[task_type].append(approach_record)

        # Add to long-term memory
        self.add_memory(
            content=f"Successful approach for {task_type}: {json.dumps(approach)}",
            memory_type="approach",
            importance=0.9,
            metadata={"task_type": task_type, "success_score": success_score},
            long_term=True
        )

        logger.info(f"Recorded successful approach for {task_type}")

    def get_successful_approaches(
        self,
        task_type: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get successful approaches for a task type"""
        approaches = self.successful_approaches.get(task_type, [])

        # Sort by success score and usage
        approaches.sort(
            key=lambda a: (a["success_score"], -a["usage_count"]),
            reverse=True
        )

        return approaches[:limit]

    def get_context_summary(self, recent_messages: Optional[List[Dict]] = None) -> str:
        """Generate context summary from memory"""
        summary_parts = []

        # User preferences
        if self.preferences:
            prefs = [
                f"- {key}: {value['value']}"
                for key, value in self.preferences.items()
                if value["confidence"] > 0.5
            ]
            if prefs:
                summary_parts.append("User Preferences:")
                summary_parts.extend(prefs)

        # Recent important memories
        important_memories = [
            mem for mem in self.short_term_memory
            if mem.importance >= 0.7
        ][-5:]

        if important_memories:
            summary_parts.append("\nRecent Important Context:")
            for mem in important_memories:
                summary_parts.append(f"- {mem.content}")

        return "\n".join(summary_parts) if summary_parts else "No additional context"

    def _consolidate_short_term(self):
        """Consolidate short-term memory"""
        # Move important memories to long-term
        for mem in self.short_term_memory[:]:
            if mem.importance >= 0.6 or mem.access_count >= 3:
                self.long_term_memory[mem.memory_type].append(mem)
                self.short_term_memory.remove(mem)

        # Remove oldest low-importance memories
        self.short_term_memory.sort(
            key=lambda m: (m.importance, m.last_accessed)
        )
        self.short_term_memory = self.short_term_memory[-50:]

    def forget_memory(self, memory_id: str):
        """Remove a specific memory"""
        # Remove from short-term
        self.short_term_memory = [
            m for m in self.short_term_memory if m.id != memory_id
        ]

        # Remove from long-term
        for memory_type in self.long_term_memory:
            self.long_term_memory[memory_type] = [
                m for m in self.long_term_memory[memory_type]
                if m.id != memory_id
            ]

    def export_memory(self) -> Dict[str, Any]:
        """Export memory for persistence"""
        return {
            "user_id": self.user_id,
            "short_term_memory": [m.to_dict() for m in self.short_term_memory],
            "long_term_memory": {
                memory_type: [m.to_dict() for m in memories]
                for memory_type, memories in self.long_term_memory.items()
            },
            "preferences": self.preferences,
            "successful_approaches": self.successful_approaches
        }

    @classmethod
    def load_memory(cls, data: Dict[str, Any]) -> "MemorySystem":
        """Load memory from exported data"""
        memory_system = cls(data["user_id"])

        # Load short-term memory
        for mem_dict in data.get("short_term_memory", []):
            entry = MemoryEntry(
                content=mem_dict["content"],
                memory_type=mem_dict["memory_type"],
                importance=mem_dict["importance"],
                metadata=mem_dict.get("metadata", {})
            )
            entry.id = mem_dict["id"]
            entry.created_at = datetime.fromisoformat(mem_dict["created_at"])
            entry.last_accessed = datetime.fromisoformat(mem_dict["last_accessed"])
            entry.access_count = mem_dict["access_count"]
            memory_system.short_term_memory.append(entry)

        # Load long-term memory
        for memory_type, memories in data.get("long_term_memory", {}).items():
            for mem_dict in memories:
                entry = MemoryEntry(
                    content=mem_dict["content"],
                    memory_type=mem_dict["memory_type"],
                    importance=mem_dict["importance"],
                    metadata=mem_dict.get("metadata", {})
                )
                entry.id = mem_dict["id"]
                entry.created_at = datetime.fromisoformat(mem_dict["created_at"])
                entry.last_accessed = datetime.fromisoformat(mem_dict["last_accessed"])
                entry.access_count = mem_dict["access_count"]
                memory_system.long_term_memory[memory_type].append(entry)

        memory_system.preferences = data.get("preferences", {})
        memory_system.successful_approaches = defaultdict(
            list,
            data.get("successful_approaches", {})
        )

        return memory_system


class MemoryManager:
    """Manages memory systems for multiple users"""

    def __init__(self):
        self.user_memories: Dict[str, MemorySystem] = {}

    def get_memory(self, user_id: str) -> MemorySystem:
        """Get or create memory system for user"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = MemorySystem(user_id)
        return self.user_memories[user_id]

    async def save_memories(self, storage_path: str):
        """Save all memories to storage"""
        for user_id, memory in self.user_memories.items():
            data = memory.export_memory()
            # Save to file or database
            # Implementation depends on storage backend

    async def load_memories(self, storage_path: str):
        """Load memories from storage"""
        # Load from file or database
        # Implementation depends on storage backend
        pass
