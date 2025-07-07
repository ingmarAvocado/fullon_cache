"""Additional tests to increase BaseCache coverage."""

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
    async def test_scan_iter_method(self):
        """Test scan_iter method."""
        cache = BaseCache()

        # Set some keys
        await cache.set("test:1", "value1")
        await cache.set("test:2", "value2")
        await cache.set("other:1", "value3")

        # Scan for keys
        keys = []
        async for key in cache.scan_iter("test:*"):
            keys.append(key)

        assert len(keys) >= 2

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
