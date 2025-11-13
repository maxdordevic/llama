"""
Advanced Caching Layer with Redis
Intelligent caching for LLM responses, embeddings, and query results
"""

import asyncio
import hashlib
import json
import logging
import pickle
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time

try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache invalidation strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live only


class CacheNamespace(str, Enum):
    """Cache namespaces for different data types"""
    LLM_RESPONSES = "llm_responses"
    EMBEDDINGS = "embeddings"
    VECTOR_SEARCH = "vector_search"
    API_RESPONSES = "api_responses"
    USER_SESSIONS = "user_sessions"
    QUERY_RESULTS = "query_results"
    FILE_METADATA = "file_metadata"
    ANALYTICS = "analytics"


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    default_ttl: int = 3600  # 1 hour
    max_size_mb: int = 1000  # 1GB
    strategy: CacheStrategy = CacheStrategy.LRU
    compression: bool = True
    serialization: str = "json"  # json or pickle


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    namespace: CacheNamespace
    created_at: datetime
    expires_at: Optional[datetime] = None
    hits: int = 0
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    total_keys: int = 0
    memory_used_mb: float = 0.0
    evictions: int = 0


class CacheManager:
    """Advanced cache manager with Redis backend"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: Optional[CacheConfig] = None
    ):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL
            config: Cache configuration
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis not installed. Run: pip install redis")

        self.redis_url = redis_url
        self.config = config or CacheConfig()
        self.redis: Optional[Redis] = None
        self.logger = logging.getLogger(__name__)

        # Statistics
        self.stats = CacheStats()

    async def connect(self):
        """Connect to Redis"""
        if self.redis is None:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # Handle binary data
            )
            self.logger.info(f"Connected to Redis: {self.redis_url}")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None

    def _generate_key(
        self,
        namespace: CacheNamespace,
        identifier: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key

        Args:
            namespace: Cache namespace
            identifier: Base identifier
            params: Additional parameters for key uniqueness

        Returns:
            Cache key
        """
        # Create deterministic key from params
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"{namespace.value}:{identifier}:{params_hash}"
        else:
            return f"{namespace.value}:{identifier}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if self.config.serialization == "pickle":
            return pickle.dumps(value)
        else:
            # JSON serialization
            return json.dumps(value).encode('utf-8')

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if self.config.serialization == "pickle":
            return pickle.loads(data)
        else:
            return json.loads(data.decode('utf-8'))

    async def get(
        self,
        namespace: CacheNamespace,
        identifier: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get value from cache

        Args:
            namespace: Cache namespace
            identifier: Cache identifier
            params: Additional parameters

        Returns:
            Cached value or None
        """
        if not self.config.enabled:
            return None

        await self.connect()

        key = self._generate_key(namespace, identifier, params)

        try:
            data = await self.redis.get(key)

            if data:
                # Cache hit
                self.stats.hits += 1

                # Update access time (for LRU)
                await self.redis.expire(key, self.config.default_ttl)

                value = self._deserialize(data)
                self.logger.debug(f"Cache HIT: {key}")
                return value
            else:
                # Cache miss
                self.stats.misses += 1
                self.logger.debug(f"Cache MISS: {key}")
                return None

        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            self.stats.misses += 1
            return None

    async def set(
        self,
        namespace: CacheNamespace,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            namespace: Cache namespace
            identifier: Cache identifier
            value: Value to cache
            ttl: Time to live in seconds
            params: Additional parameters

        Returns:
            True if successful
        """
        if not self.config.enabled:
            return False

        await self.connect()

        key = self._generate_key(namespace, identifier, params)
        ttl = ttl or self.config.default_ttl

        try:
            data = self._serialize(value)

            await self.redis.setex(key, ttl, data)

            self.logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            self.logger.error(f"Cache set error: {e}")
            return False

    async def delete(
        self,
        namespace: CacheNamespace,
        identifier: str,
        params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete value from cache"""
        await self.connect()

        key = self._generate_key(namespace, identifier, params)

        try:
            result = await self.redis.delete(key)
            self.logger.debug(f"Cache DELETE: {key}")
            return result > 0

        except Exception as e:
            self.logger.error(f"Cache delete error: {e}")
            return False

    async def clear_namespace(self, namespace: CacheNamespace) -> int:
        """Clear all keys in namespace"""
        await self.connect()

        pattern = f"{namespace.value}:*"

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                count = await self.redis.delete(*keys)
                self.logger.info(f"Cleared {count} keys from {namespace.value}")
                return count
            return 0

        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        await self.connect()

        try:
            info = await self.redis.info("memory")

            total_keys = await self.redis.dbsize()
            memory_used = info.get("used_memory", 0) / (1024 * 1024)  # MB

            self.stats.total_keys = total_keys
            self.stats.memory_used_mb = memory_used

            # Calculate hit rate
            total_requests = self.stats.hits + self.stats.misses
            if total_requests > 0:
                self.stats.hit_rate = (self.stats.hits / total_requests) * 100

            return self.stats

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return self.stats

    async def cached(
        self,
        namespace: CacheNamespace,
        identifier: str,
        ttl: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator for caching function results

        Usage:
            @cache.cached(CacheNamespace.LLM_RESPONSES, "completion")
            async def get_completion(prompt):
                return await llm.complete(prompt)
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Try to get from cache
                cached_value = await self.get(namespace, identifier, params)

                if cached_value is not None:
                    return cached_value

                # Call function
                result = await func(*args, **kwargs)

                # Store in cache
                await self.set(namespace, identifier, result, ttl, params)

                return result

            return wrapper
        return decorator


# ==================== Specialized Cache Managers ====================

class LLMResponseCache:
    """Specialized cache for LLM responses"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = CacheNamespace.LLM_RESPONSES
        self.logger = logging.getLogger(__name__)

    async def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Get cached LLM response"""
        params = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Generate unique identifier from prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

        return await self.cache.get(self.namespace, prompt_hash, params)

    async def cache_response(
        self,
        prompt: str,
        response: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Cache LLM response"""
        params = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

        return await self.cache.set(self.namespace, prompt_hash, response, ttl, params)

    async def get_cost_savings(self) -> Dict[str, Any]:
        """Calculate cost savings from cache hits"""
        stats = await self.cache.get_stats()

        # Estimate cost savings (assuming average cost per request)
        avg_cost_per_request = 0.01  # $0.01 per LLM call
        saved_requests = stats.hits
        estimated_savings = saved_requests * avg_cost_per_request

        return {
            "cache_hits": stats.hits,
            "cache_misses": stats.misses,
            "hit_rate_percent": stats.hit_rate,
            "estimated_cost_saved_usd": estimated_savings,
            "avg_cost_per_request_usd": avg_cost_per_request
        }


class EmbeddingCache:
    """Specialized cache for text embeddings"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = CacheNamespace.EMBEDDINGS
        self.logger = logging.getLogger(__name__)

    async def get_embedding(
        self,
        text: str,
        model: str = "all-MiniLM-L6-v2"
    ) -> Optional[List[float]]:
        """Get cached embedding"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        params = {"model": model}

        return await self.cache.get(self.namespace, text_hash, params)

    async def cache_embedding(
        self,
        text: str,
        embedding: List[float],
        model: str = "all-MiniLM-L6-v2",
        ttl: int = 604800  # 7 days
    ) -> bool:
        """Cache embedding"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        params = {"model": model}

        return await self.cache.set(self.namespace, text_hash, embedding, ttl, params)

    async def get_batch(
        self,
        texts: List[str],
        model: str = "all-MiniLM-L6-v2"
    ) -> Dict[str, Optional[List[float]]]:
        """Get embeddings for multiple texts"""
        results = {}

        for text in texts:
            embedding = await self.get_embedding(text, model)
            results[text] = embedding

        return results

    async def cache_batch(
        self,
        embeddings: Dict[str, List[float]],
        model: str = "all-MiniLM-L6-v2",
        ttl: int = 604800
    ) -> int:
        """Cache multiple embeddings"""
        count = 0

        for text, embedding in embeddings.items():
            if await self.cache_embedding(text, embedding, model, ttl):
                count += 1

        return count


class QueryResultCache:
    """Cache for database and API query results"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.namespace = CacheNamespace.QUERY_RESULTS
        self.logger = logging.getLogger(__name__)

    async def get_query_result(
        self,
        query_key: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get cached query result"""
        return await self.cache.get(self.namespace, query_key, params)

    async def cache_query_result(
        self,
        query_key: str,
        result: Any,
        ttl: int = 300,  # 5 minutes
        params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cache query result"""
        return await self.cache.set(self.namespace, query_key, result, ttl, params)


# ==================== Cache Warming ====================

class CacheWarmer:
    """Proactively warm cache with frequently accessed data"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.logger = logging.getLogger(__name__)

    async def warm_llm_responses(self, common_prompts: List[Dict[str, Any]]):
        """Warm cache with common LLM prompts"""
        llm_cache = LLMResponseCache(self.cache)

        for prompt_config in common_prompts:
            prompt = prompt_config["prompt"]
            response = prompt_config["response"]
            model = prompt_config.get("model", "default")

            await llm_cache.cache_response(prompt, response, model)

        self.logger.info(f"Warmed cache with {len(common_prompts)} LLM responses")

    async def warm_embeddings(self, common_texts: List[str], model: str):
        """Warm cache with common text embeddings"""
        from ..core.vector_store import EmbeddingModel

        embedding_cache = EmbeddingCache(self.cache)
        embedder = EmbeddingModel(model)

        for text in common_texts:
            embedding = embedder.encode_single(text)
            await embedding_cache.cache_embedding(text, embedding, model)

        self.logger.info(f"Warmed cache with {len(common_texts)} embeddings")


# ==================== Global Cache Instance ====================

_cache_manager: Optional[CacheManager] = None


def get_cache_manager(redis_url: Optional[str] = None) -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager

    if _cache_manager is None:
        import os
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        _cache_manager = CacheManager(redis_url=url)

    return _cache_manager


def get_llm_cache() -> LLMResponseCache:
    """Get LLM response cache"""
    return LLMResponseCache(get_cache_manager())


def get_embedding_cache() -> EmbeddingCache:
    """Get embedding cache"""
    return EmbeddingCache(get_cache_manager())


def get_query_cache() -> QueryResultCache:
    """Get query result cache"""
    return QueryResultCache(get_cache_manager())
