"""Additional tests to achieve 100% coverage for BaseCache."""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from fullon_cache import BaseCache
from fullon_cache.exceptions import CacheError, ConnectionError, SerializationError


class TestBaseCacheCoverage:
    """Additional tests for complete BaseCache coverage."""

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test the close method."""
        cache = BaseCache()
        
        # Add some pubsub clients
        mock_client = AsyncMock()
        cache._pubsub_clients['test'] = mock_client
        
        # Close the cache
        await cache.close()
        
        # Verify cleanup
        assert cache._closed is True
        assert len(cache._pubsub_clients) == 0
        mock_client.aclose.assert_called_once()
        
        # Closing again should do nothing
        await cache.close()

    @pytest.mark.asyncio
    async def test_close_with_exception(self):
        """Test close method when aclose raises exception."""
        cache = BaseCache()
        
        # Add a pubsub client that raises on close
        mock_client = AsyncMock()
        mock_client.aclose.side_effect = Exception("Close failed")
        cache._pubsub_clients['test'] = mock_client
        
        # Should not raise
        await cache.close()
        assert cache._closed is True

    @pytest.mark.asyncio
    async def test_set_with_redis_error(self):
        """Test set method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.set', side_effect=RedisError("Set failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.set("key", "value")
            assert "Failed to set key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_with_redis_error(self):
        """Test delete method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.delete', side_effect=RedisError("Delete failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.delete("key1", "key2")
            assert "Failed to delete keys" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exists_with_redis_error(self):
        """Test exists method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.exists', side_effect=RedisError("Exists failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.exists("key")
            assert "Failed to check key existence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_expire_with_redis_error(self):
        """Test expire method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.expire', side_effect=RedisError("Expire failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.expire("key", 60)
            assert "Failed to set expiration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scan_keys_with_redis_error(self):
        """Test scan_keys method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.scan', side_effect=RedisError("Scan failed")):
            with pytest.raises(CacheError) as exc_info:
                async for _ in cache.scan_keys("pattern*"):
                    pass
            assert "Failed to scan keys" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hset_with_redis_error(self):
        """Test hset method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.hset', side_effect=RedisError("Hset failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.hset("hash", "field", "value")
            assert "Failed to set hash field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hget_with_redis_error(self):
        """Test hget method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.hget', side_effect=RedisError("Hget failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.hget("hash", "field")
            assert "Failed to get hash field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hgetall_with_redis_error(self):
        """Test hgetall method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.hgetall', side_effect=RedisError("Hgetall failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.hgetall("hash")
            assert "Failed to get hash" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hdel_with_redis_error(self):
        """Test hdel method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.hdel', side_effect=RedisError("Hdel failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.hdel("hash", "field1", "field2")
            assert "Failed to delete hash fields" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rpush_with_redis_error(self):
        """Test rpush method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.rpush', side_effect=RedisError("Rpush failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.rpush("list", "value1", "value2")
            assert "Failed to push to list" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lpop_with_redis_error(self):
        """Test lpop method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.lpop', side_effect=RedisError("Lpop failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.lpop("list")
            assert "Failed to pop from list" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lrange_with_redis_error(self):
        """Test lrange method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.lrange', side_effect=RedisError("Lrange failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.lrange("list", 0, -1)
            assert "Failed to get list range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_blpop_with_redis_error(self):
        """Test blpop method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.blpop', side_effect=RedisError("Blpop failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.blpop(["list"], timeout=1)
            assert "Failed to blocking pop" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ltrim_with_redis_error(self):
        """Test ltrim method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.ltrim', side_effect=RedisError("Ltrim failed")):
            with pytest.raises(CacheError) as exc_info:
                await cache.ltrim("list", 0, 10)
            assert "Failed to trim list" in str(exc_info.value)

    def test_decode_mode_based_on_host(self):
        """Test that decode mode is set based on host."""
        # This test is no longer valid as decode mode is always True
        # in the ConnectionPool configuration
        cache = BaseCache()
        # decode_responses is always True in the current implementation
        assert cache.decode_responses is True

    @pytest.mark.asyncio
    async def test_json_deserialization_with_invalid_data(self):
        """Test get_json with invalid JSON data."""
        cache = BaseCache()
        
        # Mock get to return invalid JSON
        with patch.object(cache, 'get', return_value='invalid json'):
            with pytest.raises(SerializationError) as exc_info:
                await cache.get_json("key")
            assert "Failed to decode JSON for key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_redis_context_with_closed_cache(self):
        """Test _redis_context when cache is closed."""
        cache = BaseCache()
        await cache.close()
        
        with pytest.raises(ConnectionError) as exc_info:
            async with cache._redis_context():
                pass
        assert "Cache is closed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pipeline_context(self):
        """Test the pipeline context manager."""
        cache = BaseCache()
        
        # Test successful pipeline
        async with cache.pipeline() as pipe:
            await pipe.set("key1", "value1")
            await pipe.set("key2", "value2")
            results = await pipe.execute()
        
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_from_redis_timestamp_edge_cases(self):
        """Test _from_redis_timestamp with edge cases."""
        cache = BaseCache()
        
        # Test with None
        assert cache._from_redis_timestamp(None) is None
        
        # Test with empty string
        assert cache._from_redis_timestamp("") is None
        
        # Test with invalid format
        assert cache._from_redis_timestamp("invalid-timestamp") is None

    @pytest.mark.asyncio
    async def test_set_json_with_non_serializable(self):
        """Test set_json with non-serializable object."""
        cache = BaseCache()
        
        # Create a non-serializable object
        class NonSerializable:
            pass
        
        obj = NonSerializable()
        
        with pytest.raises(SerializationError) as exc_info:
            await cache.set_json("key", obj)
        assert "Failed to encode JSON for key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_xadd_with_error(self):
        """Test xadd method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.xadd', side_effect=RedisError("Stream error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.xadd("stream", {"field": "value"})
            assert "Failed to add to stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_xread_with_error(self):
        """Test xread method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.xread', side_effect=RedisError("Stream error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.xread({"stream": "$"})
            assert "Failed to read from stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_xdel_with_error(self):
        """Test xdel method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.xdel', side_effect=RedisError("Stream error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.xdel("stream", "id1", "id2")
            assert "Failed to delete from stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_xlen_with_error(self):
        """Test xlen method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.xlen', side_effect=RedisError("Stream error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.xlen("stream")
            assert "Failed to get stream length" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_xtrim_with_error(self):
        """Test xtrim method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.xtrim', side_effect=RedisError("Stream error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.xtrim("stream", 1000)
            assert "Failed to trim stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lpush_with_error(self):
        """Test lpush method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.lpush', side_effect=RedisError("Push error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.lpush("list", "value1", "value2")
            assert "Failed to push to list" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_llen_with_error(self):
        """Test llen method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.llen', side_effect=RedisError("Length error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.llen("list")
            assert "Failed to get list length" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_info_with_error(self):
        """Test info method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.info', side_effect=RedisError("Info error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.info()
            assert "Failed to get server info" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_flushdb_with_error(self):
        """Test flushdb method with Redis error."""
        cache = BaseCache()
        
        with patch('redis.asyncio.Redis.flushdb', side_effect=RedisError("Flush error")):
            with pytest.raises(CacheError) as exc_info:
                await cache.flushdb()
            assert "Failed to flush database" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_redis_timestamp_with_naive_datetime(self):
        """Test _to_redis_timestamp with naive datetime."""
        cache = BaseCache()
        
        # Test with None
        result = cache._to_redis_timestamp(None)
        assert result is None
        
        # Test with naive datetime (should add UTC)
        dt_naive = datetime(2025, 1, 1, 12, 0, 0)
        result = cache._to_redis_timestamp(dt_naive)
        assert "+00:00" in result
        
        # Test with aware datetime in different timezone
        from datetime import timedelta
        # Create a simple timezone offset (-5 hours for Eastern)
        eastern_offset = timezone(timedelta(hours=-5))
        dt_eastern = datetime(2025, 1, 1, 12, 0, 0, tzinfo=eastern_offset)
        result = cache._to_redis_timestamp(dt_eastern)
        assert "+00:00" in result  # Should be converted to UTC
        
        # Test with aware datetime already in UTC
        dt_aware = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = cache._to_redis_timestamp(dt_aware)
        assert "+00:00" in result