"""Base cache module providing core Redis operations.

This module provides the foundation for all cache operations including
connection management, key operations, and common utilities.
"""

import json
from fullon_log import get_component_logger
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from .connection import ConnectionPool, get_redis
from .exceptions import (
    CacheError,
    ConnectionError,
    PubSubError,
    SerializationError,
)

logger = get_component_logger("fullon.cache.base")


class BaseCache:
    """Base class for all cache operations.
    
    This class provides core Redis functionality including connection management,
    key operations, serialization, pub/sub, and error handling. All other cache
    classes use this as their foundation.
    
    Features:
        - Async Redis operations with connection pooling
        - Automatic serialization/deserialization of complex types
        - Pub/Sub support for real-time updates
        - Key pattern operations (scan, delete by pattern)
        - Error handling with automatic retries
        - Transaction support with pipelines
        
    Example:
        cache = BaseCache()
        
        # Basic operations
        await cache.set("key", "value")
        value = await cache.get("key")
        
        # Complex data
        await cache.set_json("user:123", {"name": "John", "age": 30})
        user = await cache.get_json("user:123")
        
        # Pub/Sub
        await cache.publish("channel", "message")
        async for message in cache.subscribe("channel"):
            print(message)
    """

    def __init__(self, key_prefix: str = "", decode_responses: bool = True):
        """Initialize the base cache.
        
        Args:
            key_prefix: Optional prefix for all keys (useful for namespacing)
            decode_responses: Whether to decode Redis responses (default: True)
        """
        self.key_prefix = key_prefix
        self.decode_responses = decode_responses
        self._pool = ConnectionPool()
        self._pubsub_clients: dict[str, redis.client.PubSub] = {}
        self._closed = False

    async def close(self) -> None:
        """Close all connections and cleanup resources.
        
        This should be called when the cache is no longer needed.
        """
        if self._closed:
            return

        # Close all pubsub clients
        for client in self._pubsub_clients.values():
            try:
                await client.aclose()
            except Exception:
                pass
        self._pubsub_clients.clear()

        # Mark as closed
        self._closed = True

    def _make_key(self, key: str) -> str:
        """Add prefix to key if configured.
        
        Args:
            key: The base key
            
        Returns:
            The key with prefix applied
        """
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    async def _get_redis(self) -> redis.Redis:
        """Get a Redis connection from the pool.
        
        Returns:
            Redis client instance
            
        Raises:
            ConnectionError: If unable to connect to Redis
        """
        if self._closed:
            raise ConnectionError("Cache is closed")
        return await self._pool.get_connection(decode_responses=self.decode_responses)

    class _RedisContext:
        """Context manager for Redis operations."""

        def __init__(self, cache):
            self.cache = cache
            self.redis_client = None

        async def __aenter__(self):
            """Enter the context - get Redis connection."""
            self.redis_client = await self.cache._get_redis()
            return self.redis_client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Exit the context - close Redis connection."""
            if self.redis_client:
                try:
                    await self.redis_client.aclose()
                except Exception:
                    pass  # Ignore errors during cleanup
            return False

    def _redis_context(self):
        """Get a Redis context manager.
        
        Returns:
            Context manager for Redis operations
            
        Example:
            async with self._redis_context() as r:
                await r.set("key", "value")
        """
        return self._RedisContext(self)

    # Basic Operations

    async def get(self, key: str) -> str | None:
        """Get a value from cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.get(self._make_key(key))
        except RedisError as e:
            logger.error(f"Failed to get key {key}: {e}")
            raise CacheError(f"Failed to get key: {str(e)}")

    async def set(self, key: str, value: str | bytes,
                  ttl: int | None = None) -> bool:
        """Set a value in cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                if ttl:
                    return await r.setex(self._make_key(key), ttl, value)
                else:
                    return await r.set(self._make_key(key), value)
        except RedisError as e:
            logger.error(f"Failed to set key {key}: {e}")
            raise CacheError(f"Failed to set key: {str(e)}")

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.
        
        Args:
            *keys: Keys to delete
            
        Returns:
            Number of keys deleted
            
        Raises:
            CacheError: If Redis operation fails
        """
        if not keys:
            return 0

        try:
            async with self._redis_context() as r:
                full_keys = [self._make_key(k) for k in keys]
                return await r.delete(*full_keys)
        except RedisError as e:
            logger.error(f"Failed to delete keys: {e}")
            raise CacheError(f"Failed to delete keys: {str(e)}")

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.
        
        Args:
            *keys: Keys to check
            
        Returns:
            Number of keys that exist
            
        Raises:
            CacheError: If Redis operation fails
        """
        if not keys:
            return 0

        try:
            async with self._redis_context() as r:
                full_keys = [self._make_key(k) for k in keys]
                return await r.exists(*full_keys)
        except RedisError as e:
            logger.error(f"Failed to check key existence: {e}")
            raise CacheError(f"Failed to check key existence: {str(e)}")

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key.
        
        Args:
            key: The cache key
            ttl: Time to live in seconds
            
        Returns:
            True if expiration was set
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.expire(self._make_key(key), ttl)
        except RedisError as e:
            logger.error(f"Failed to set expiration on key {key}: {e}")
            raise CacheError(f"Failed to set expiration: {str(e)}")

    # JSON Operations

    async def get_json(self, key: str) -> Any | None:
        """Get and deserialize JSON data.
        
        Args:
            key: The cache key
            
        Returns:
            Deserialized data or None if not found
            
        Raises:
            SerializationError: If deserialization fails
            CacheError: If Redis operation fails
        """
        value = await self.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise SerializationError(
                f"Failed to decode JSON for key {key}",
                data_type="json",
                operation="deserialize"
            )

    async def set_json(self, key: str, value: Any,
                       ttl: int | None = None) -> bool:
        """Serialize and set JSON data.
        
        Args:
            key: The cache key
            value: Data to serialize and cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful
            
        Raises:
            SerializationError: If serialization fails
            CacheError: If Redis operation fails
        """
        try:
            # Check if value has any unserializable types
            def json_default(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                # Raise TypeError for other non-serializable objects
                raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

            json_str = json.dumps(value, default=json_default)
            return await self.set(key, json_str, ttl)
        except (TypeError, ValueError):
            raise SerializationError(
                f"Failed to encode JSON for key {key}",
                data_type=str(type(value)),
                operation="serialize"
            )

    # Hash Operations

    async def hget(self, key: str, field: str) -> str | None:
        """Get a field from a hash.
        
        Args:
            key: The hash key
            field: The field name
            
        Returns:
            The field value or None
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.hget(self._make_key(key), field)
        except RedisError as e:
            logger.error(f"Failed to get hash field {key}:{field}: {e}")
            raise CacheError(f"Failed to get hash field: {str(e)}")

    async def hset(self, key: str, field: str | None = None, value: str | None = None,
                   mapping: dict[str, Any] | None = None) -> int:
        """Set field(s) in a hash.
        
        Args:
            key: The hash key
            field: The field name (if setting single field)
            value: The field value (if setting single field)
            mapping: Dict of field:value pairs (if setting multiple)
            
        Returns:
            Number of fields created
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                if mapping:
                    return await r.hset(self._make_key(key), mapping=mapping)
                else:
                    return await r.hset(self._make_key(key), field, value)
        except RedisError as e:
            logger.error(f"Failed to set hash field(s) for {key}: {e}")
            raise CacheError(f"Failed to set hash field: {str(e)}")

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields from a hash.
        
        Args:
            key: The hash key
            
        Returns:
            Dict of field:value pairs
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.hgetall(self._make_key(key))
        except RedisError as e:
            logger.error(f"Failed to get hash {key}: {e}")
            raise CacheError(f"Failed to get hash: {str(e)}")

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete fields from a hash.
        
        Args:
            key: The hash key
            *fields: Fields to delete
            
        Returns:
            Number of fields deleted
            
        Raises:
            CacheError: If Redis operation fails
        """
        if not fields:
            return 0

        try:
            async with self._redis_context() as r:
                return await r.hdel(self._make_key(key), *fields)
        except RedisError as e:
            logger.error(f"Failed to delete hash fields: {e}")
            raise CacheError(f"Failed to delete hash fields: {str(e)}")

    # List Operations

    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list.
        
        Args:
            key: The list key
            *values: Values to push
            
        Returns:
            Length of list after push
            
        Raises:
            CacheError: If Redis operation fails
        """
        if not values:
            return 0

        try:
            async with self._redis_context() as r:
                return await r.lpush(self._make_key(key), *values)
        except RedisError as e:
            logger.error(f"Failed to push to list {key}: {e}")
            raise CacheError(f"Failed to push to list: {str(e)}")

    async def rpush(self, key: str, *values: str) -> int:
        """Push values to the right of a list.
        
        Args:
            key: The list key
            *values: Values to push
            
        Returns:
            Length of list after push
            
        Raises:
            CacheError: If Redis operation fails
        """
        if not values:
            return 0

        try:
            async with self._redis_context() as r:
                return await r.rpush(self._make_key(key), *values)
        except RedisError as e:
            logger.error(f"Failed to push to list {key}: {e}")
            raise CacheError(f"Failed to push to list: {str(e)}")

    async def lpop(self, key: str) -> str | None:
        """Pop value from the left of a list.
        
        Args:
            key: The list key
            
        Returns:
            The popped value or None
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.lpop(self._make_key(key))
        except RedisError as e:
            logger.error(f"Failed to pop from list {key}: {e}")
            raise CacheError(f"Failed to pop from list: {str(e)}")

    async def blpop(self, keys: list[str], timeout: int = 0) -> tuple | None:
        """Blocking pop from the left of lists.
        
        Args:
            keys: List keys to pop from
            timeout: Timeout in seconds (0 = block forever)
            
        Returns:
            Tuple of (key, value) or None if timeout
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                full_keys = [self._make_key(k) for k in keys]
                result = await r.blpop(full_keys, timeout)
                if result:
                    # Remove prefix from returned key
                    key = result[0]
                    if self.key_prefix and key.startswith(self.key_prefix + ":"):
                        key = key[len(self.key_prefix) + 1:]
                    return (key, result[1])
                return None
        except RedisError as e:
            logger.error(f"Failed to blocking pop: {e}")
            raise CacheError(f"Failed to blocking pop: {str(e)}")

    # Pattern Operations

    async def scan_keys(self, pattern: str = "*", count: int = 100) -> AsyncIterator[str]:
        """Scan for keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            count: Hint for number of keys per iteration
            
        Yields:
            Keys matching the pattern
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            async with self._redis_context() as r:
                full_pattern = self._make_key(pattern)
                cursor = 0

                while True:
                    cursor, keys = await r.scan(cursor, match=full_pattern, count=count)

                    for key in keys:
                        # Remove prefix from returned keys
                        if self.key_prefix and key.startswith(self.key_prefix + ":"):
                            yield key[len(self.key_prefix) + 1:]
                        else:
                            yield key

                    if cursor == 0:
                        break

        except RedisError as e:
            logger.error(f"Failed to scan keys: {e}")
            raise CacheError(f"Failed to scan keys: {str(e)}")

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "temp:*")
            
        Returns:
            Number of keys deleted
            
        Raises:
            CacheError: If Redis operation fails
        """
        deleted = 0
        keys_to_delete = []

        async for key in self.scan_keys(pattern):
            keys_to_delete.append(key)

            # Delete in batches of 1000
            if len(keys_to_delete) >= 1000:
                deleted += await self.delete(*keys_to_delete)
                keys_to_delete = []

        # Delete remaining keys
        if keys_to_delete:
            deleted += await self.delete(*keys_to_delete)

        return deleted

    # Pub/Sub Operations

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel.
        
        Args:
            channel: The channel name
            message: The message to publish
            
        Returns:
            Number of subscribers that received the message
            
        Raises:
            PubSubError: If publish fails
        """
        try:
            async with self._redis_context() as r:
                return await r.publish(channel, message)
        except RedisError as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            raise PubSubError(f"Failed to publish: {str(e)}", channel=channel)

    async def subscribe(self, *channels: str) -> AsyncIterator[dict]:
        """Subscribe to channels and yield messages.
        
        Args:
            *channels: Channel names to subscribe to
            
        Yields:
            Messages received on subscribed channels
            
        Raises:
            PubSubError: If subscription fails
        """
        if not channels:
            # Return empty async generator for no channels
            return

        redis_client = None
        pubsub = None

        try:
            redis_client = await get_redis(decode_responses=True)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(*channels)

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    yield message

        except RedisError as e:
            logger.error(f"Subscription error: {e}")
            raise PubSubError(f"Subscription failed: {str(e)}", channel=str(channels))
        finally:
            if pubsub:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            if redis_client:
                await redis_client.aclose()

    # Utility Operations

    async def ping(self) -> bool:
        """Test Redis connection.
        
        Returns:
            True if connected
            
        Raises:
            ConnectionError: If not connected
        """
        try:
            async with self._redis_context() as r:
                return await r.ping()
        except RedisError as e:
            raise ConnectionError(f"Redis ping failed: {str(e)}")

    async def scan_iter(self, pattern: str = "*", count: int = 100) -> AsyncIterator[str]:
        """Scan keys matching pattern.
        
        Args:
            pattern: Redis pattern to match
            count: Hint for number of keys to return per iteration
            
        Yields:
            Matching keys
        """
        # Add prefix to pattern
        full_pattern = self._make_key(pattern)

        async with self._redis_context() as r:
            async for key in r.scan_iter(match=full_pattern, count=count):
                yield key

    async def xadd(self, stream: str, fields: dict[str, Any], maxlen: int | None = None,
                   approximate: bool = True) -> str:
        """Add entry to Redis stream.
        
        Args:
            stream: Stream key
            fields: Fields to add
            maxlen: Maximum stream length
            approximate: Use approximate trimming
            
        Returns:
            Message ID
        """
        try:
            async with self._redis_context() as r:
                return await r.xadd(
                    self._make_key(stream),
                    fields,
                    maxlen=maxlen,
                    approximate=approximate
                )
        except RedisError as e:
            logger.error(f"Failed to add to stream {stream}: {e}")
            raise CacheError(f"Failed to add to stream: {str(e)}")

    async def xread(self, streams: dict[str, str], count: int | None = None,
                    block: int | None = None) -> list:
        """Read from Redis streams.
        
        Args:
            streams: Dict of stream:id pairs
            count: Max entries to return
            block: Block timeout in ms
            
        Returns:
            Stream entries
        """
        try:
            async with self._redis_context() as r:
                # Add prefix to stream keys
                prefixed_streams = {
                    self._make_key(stream): id_
                    for stream, id_ in streams.items()
                }
                return await r.xread(prefixed_streams, count=count, block=block)
        except RedisError as e:
            logger.error(f"Failed to read from streams: {e}")
            raise CacheError(f"Failed to read from streams: {str(e)}")

    async def xdel(self, stream: str, *ids: str) -> int:
        """Delete entries from stream.
        
        Args:
            stream: Stream key
            ids: Message IDs to delete
            
        Returns:
            Number deleted
        """
        try:
            async with self._redis_context() as r:
                return await r.xdel(self._make_key(stream), *ids)
        except RedisError as e:
            logger.error(f"Failed to delete from stream {stream}: {e}")
            raise CacheError(f"Failed to delete from stream: {str(e)}")

    async def xlen(self, stream: str) -> int:
        """Get stream length.
        
        Args:
            stream: Stream key
            
        Returns:
            Stream length
        """
        try:
            async with self._redis_context() as r:
                return await r.xlen(self._make_key(stream))
        except RedisError as e:
            logger.error(f"Failed to get stream length {stream}: {e}")
            raise CacheError(f"Failed to get stream length: {str(e)}")

    async def xtrim(self, stream: str, maxlen: int, approximate: bool = True) -> int:
        """Trim stream to maxlen.
        
        Args:
            stream: Stream key
            maxlen: Maximum length
            approximate: Use approximate trimming
            
        Returns:
            Number trimmed
        """
        try:
            async with self._redis_context() as r:
                return await r.xtrim(self._make_key(stream), maxlen=maxlen, approximate=approximate)
        except RedisError as e:
            logger.error(f"Failed to trim stream {stream}: {e}")
            raise CacheError(f"Failed to trim stream: {str(e)}")

    # Timestamp utilities for consistent datetime handling

    def _to_redis_timestamp(self, dt: datetime | None) -> str | None:
        """Convert datetime to ISO format string for Redis storage.
        
        This ensures all timestamps are stored consistently as ISO format
        strings with timezone information.
        
        Args:
            dt: Datetime object (should be timezone-aware UTC)
            
        Returns:
            ISO format string or None if dt is None
            
        Example:
            >>> dt = datetime.now(timezone.utc)
            >>> cache._to_redis_timestamp(dt)
            '2025-06-05T12:00:00.123456+00:00'
        """
        if dt is None:
            return None

        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = dt.replace(tzinfo=UTC)

        # Convert to UTC if different timezone
        if dt.tzinfo != UTC:
            dt = dt.astimezone(UTC)

        return dt.isoformat()

    def _from_redis_timestamp(self, value: str | None) -> datetime | None:
        """Parse ISO format string from Redis to datetime object.
        
        This ensures all timestamps retrieved from Redis are proper
        timezone-aware datetime objects.
        
        Args:
            value: ISO format string from Redis
            
        Returns:
            Timezone-aware datetime object or None
            
        Example:
            >>> cache._from_redis_timestamp('2025-06-05T12:00:00.123456+00:00')
            datetime.datetime(2025, 6, 5, 12, 0, 0, 123456, tzinfo=timezone.utc)
        """
        if value is None or value == '':
            return None

        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(value)

            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)

            return dt
        except (ValueError, AttributeError) as e:
            # Log warning but don't fail
            logger.warning(f"Failed to parse timestamp '{value}': {e}")
            return None

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        """Trim list to specified range.
        
        Args:
            key: List key
            start: Start index
            stop: Stop index
            
        Returns:
            True if successful
        """
        try:
            async with self._redis_context() as r:
                return await r.ltrim(self._make_key(key), start, stop)
        except RedisError as e:
            logger.error(f"Failed to trim list {key}: {e}")
            raise CacheError(f"Failed to trim list: {str(e)}")

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        """Get range of elements from list.
        
        Args:
            key: List key
            start: Start index
            stop: Stop index
            
        Returns:
            List elements
        """
        try:
            async with self._redis_context() as r:
                return await r.lrange(self._make_key(key), start, stop)
        except RedisError as e:
            logger.error(f"Failed to get list range {key}: {e}")
            raise CacheError(f"Failed to get list range: {str(e)}")

    async def llen(self, key: str) -> int:
        """Get list length.
        
        Args:
            key: List key
            
        Returns:
            List length
        """
        try:
            async with self._redis_context() as r:
                return await r.llen(self._make_key(key))
        except RedisError as e:
            logger.error(f"Failed to get list length {key}: {e}")
            raise CacheError(f"Failed to get list length: {str(e)}")

    async def info(self) -> dict:
        """Get Redis server information.
        
        Returns:
            Dict with server information
            
        Raises:
            CacheError: If operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.info()
        except RedisError as e:
            raise CacheError(f"Failed to get server info: {str(e)}")

    async def flushdb(self) -> bool:
        """Flush the current database.
        
        WARNING: This deletes all data in the current database!
        
        Returns:
            True if successful
            
        Raises:
            CacheError: If operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.flushdb()
        except RedisError as e:
            raise CacheError(f"Failed to flush database: {str(e)}")

    async def scard(self, key: str) -> int:
        """Get the cardinality (number of members) of a set.
        
        Args:
            key: The set key
            
        Returns:
            Number of members in the set
            
        Raises:
            CacheError: If operation fails
        """
        try:
            async with self._redis_context() as r:
                return await r.scard(self._make_key(key))
        except RedisError as e:
            raise CacheError(f"Failed to get set cardinality: {str(e)}")

    # Pipeline Operations

    @asynccontextmanager
    async def pipeline(self, transaction: bool = True):
        """Create a pipeline for batch operations.
        
        Args:
            transaction: Whether to use MULTI/EXEC transaction
            
        Yields:
            Pipeline instance
            
        Example:
            async with cache.pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.set("key2", "value2")
                results = await pipe.execute()
        """
        async with self._redis_context() as r:
            async with r.pipeline(transaction=transaction) as pipe:
                yield pipe
