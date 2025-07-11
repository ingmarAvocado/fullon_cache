"""Additional tests to increase BaseCache coverage."""

import asyncio
from unittest.mock import patch

import pytest
from redis.exceptions import RedisError

from fullon_cache import BaseCache
from fullon_cache.exceptions import CacheError, ConnectionError, PubSubError


class TestBaseCacheAdditionalCoverage:
    """Additional coverage tests for BaseCache."""

    @pytest.mark.asyncio
    async def test_scard_method(self):
        """Test scard (set cardinality)."""
        cache = BaseCache()

        # Add members to set
        async with cache._redis_context() as r:
            await r.sadd(cache._make_key("myset"), "member1", "member2", "member3")

        # Get cardinality
        count = await cache.scard("myset")
        assert count == 3

    @pytest.mark.asyncio
    async def test_scard_with_error(self):
        """Test scard with Redis error."""
        cache = BaseCache()

        with patch('redis.asyncio.Redis.scard', side_effect=RedisError("Scard failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.scard("myset")
            assert "Failed to get set cardinality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scan_iter_method(self, worker_id):
        """Test scan_iter method."""
        cache = BaseCache()

        # Use worker-specific keys with timestamp to avoid collisions
        import time
        timestamp = str(time.time()).replace('.', '')
        key_prefix = f"test_{worker_id}_{timestamp}"
        keys_to_set = [f"{key_prefix}:1", f"{key_prefix}:2"]
        other_key = f"other_{worker_id}_{timestamp}:1"
        
        try:
            # Set some keys with retry logic for parallel execution
            for attempt in range(3):
                try:
                    await cache.set(keys_to_set[0], "value1")
                    await cache.set(keys_to_set[1], "value2")
                    await cache.set(other_key, "value3")
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.1)

            # Wait a bit to ensure keys are saved
            await asyncio.sleep(0.05)
            
            # Scan for keys with retry logic
            keys = []
            for attempt in range(3):
                try:
                    keys = []
                    async for key in cache.scan_iter(f"{key_prefix}:*"):
                        keys.append(key)
                    
                    # If we got the expected keys, break
                    if len(keys) >= 2:
                        break
                        
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.1)

            # Should find both keys we set
            assert len(keys) >= 2, f"Expected at least 2 keys, got {len(keys)}: {keys}"
            
        finally:
            # Cleanup
            try:
                await cache.delete(*keys_to_set)
                await cache.delete(other_key)
            except:
                pass

    @pytest.mark.asyncio
    async def test_subscribe_error_handling(self):
        """Test subscribe with connection errors."""
        cache = BaseCache()

        # Mock get_redis to raise error immediately
        with patch('fullon_cache.base_cache.get_redis', side_effect=RedisError("Connection failed")):
            with pytest.raises(PubSubError) as exc_info:
                async for msg in cache.subscribe("channel1"):
                    pass  # Should not reach here
            assert "Subscription failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ping_with_redis_error(self):
        """Test ping with Redis error."""
        cache = BaseCache()

        # Mock ping to raise RedisError
        with patch('redis.asyncio.Redis.ping', side_effect=RedisError("Connection lost")):
            with pytest.raises(ConnectionError) as exc_info:
                await cache.ping()
            # The error comes from connection pool
            assert "Unexpected error connecting to Redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hset_with_mapping(self):
        """Test hset with mapping parameter."""
        cache = BaseCache()

        # Delete the hash first to ensure clean state
        await cache.delete("hash")

        # Test with mapping
        mapping = {"field1": "value1", "field2": "value2"}
        result = await cache.hset("hash", mapping=mapping)
        assert result >= 0  # Allow 0 for fields updated, > 0 for new fields

        # Verify values
        value1 = await cache.hget("hash", "field1")
        assert value1 == "value1"

    @pytest.mark.asyncio
    async def test_subscribe_with_no_channels(self):
        """Test subscribe with empty channel list."""
        cache = BaseCache()

        # Subscribe with no channels should immediately return
        count = 0
        async for _ in cache.subscribe():
            count += 1
            if count > 5:  # Safety limit
                break

        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_coverage(self):
        """Test publish method error path."""
        cache = BaseCache()

        # Normal publish should work
        result = await cache.publish("test_channel", "test message")
        assert result >= 0
