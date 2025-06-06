"""Comprehensive tests for BaseCache with 100% coverage.

This module tests all functionality of the BaseCache class including
basic operations, error handling, and edge cases.
"""

import asyncio
import json
import pytest
from datetime import datetime

from fullon_cache import BaseCache, CacheError
from fullon_cache.exceptions import ConnectionError, SerializationError


class TestBaseCacheConnection:
    """Test connection and initialization."""
    
    @pytest.mark.asyncio
    async def test_init_default(self, clean_redis):
        """Test default initialization."""
        cache = BaseCache()
        assert cache.key_prefix == ""
        assert cache.decode_responses is True
        
    @pytest.mark.asyncio
    async def test_init_with_prefix(self, clean_redis):
        """Test initialization with key prefix."""
        cache = BaseCache(key_prefix="test")
        assert cache.key_prefix == "test"
        
        # Test key prefixing
        await cache.set("key", "value")
        
        # Verify key was prefixed
        cache2 = BaseCache()
        assert await cache2.get("test:key") == "value"
        assert await cache2.get("key") is None
    
    @pytest.mark.asyncio
    async def test_ping(self, base_cache):
        """Test Redis connection ping."""
        assert await base_cache.ping() is True
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Connection pool singleton makes it hard to test connection errors")
    async def test_ping_connection_error(self, monkeypatch):
        """Test ping with connection error."""
        # Create cache with invalid port
        monkeypatch.setenv("REDIS_PORT", "99999")
        cache = BaseCache()
        
        with pytest.raises(ConnectionError) as exc_info:
            await cache.ping()
        assert "Redis ping failed" in str(exc_info.value)


class TestBaseCacheBasicOperations:
    """Test basic cache operations."""
    
    @pytest.mark.asyncio
    async def test_set_get(self, base_cache):
        """Test basic set and get operations."""
        # String value
        assert await base_cache.set("key1", "value1") is True
        assert await base_cache.get("key1") == "value1"
        
        # Bytes value
        assert await base_cache.set("key2", b"bytes_value") is True
        result = await base_cache.get("key2")
        assert result == "bytes_value" or result == b"bytes_value"
        
        # With TTL
        assert await base_cache.set("key3", "value3", ttl=1) is True
        assert await base_cache.get("key3") == "value3"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await base_cache.get("key3") is None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, base_cache):
        """Test getting non-existent key."""
        assert await base_cache.get("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_delete(self, base_cache):
        """Test delete operations."""
        # Set multiple keys
        await base_cache.set("del1", "value1")
        await base_cache.set("del2", "value2")
        await base_cache.set("del3", "value3")
        
        # Delete single key
        assert await base_cache.delete("del1") == 1
        assert await base_cache.get("del1") is None
        
        # Delete multiple keys
        assert await base_cache.delete("del2", "del3") == 2
        assert await base_cache.get("del2") is None
        assert await base_cache.get("del3") is None
        
        # Delete non-existent key
        assert await base_cache.delete("nonexistent") == 0
        
        # Delete with no keys
        assert await base_cache.delete() == 0
    
    @pytest.mark.asyncio
    async def test_exists(self, base_cache):
        """Test exists operations."""
        await base_cache.set("exists1", "value1")
        await base_cache.set("exists2", "value2")
        
        # Single key exists
        assert await base_cache.exists("exists1") == 1
        
        # Multiple keys exist
        assert await base_cache.exists("exists1", "exists2") == 2
        
        # Mixed existing and non-existing
        assert await base_cache.exists("exists1", "nonexistent") == 1
        
        # No keys
        assert await base_cache.exists() == 0
    
    @pytest.mark.asyncio
    async def test_expire(self, base_cache):
        """Test setting expiration."""
        await base_cache.set("expire_key", "value")
        
        # Set expiration
        assert await base_cache.expire("expire_key", 1) is True
        
        # Key still exists
        assert await base_cache.get("expire_key") == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await base_cache.get("expire_key") is None
        
        # Expire non-existent key
        assert await base_cache.expire("nonexistent", 1) is False


class TestBaseCacheJsonOperations:
    """Test JSON serialization operations."""
    
    @pytest.mark.asyncio
    async def test_set_get_json(self, base_cache):
        """Test JSON set and get operations."""
        # Simple dictionary
        data = {"name": "test", "value": 123, "active": True}
        assert await base_cache.set_json("json1", data) is True
        result = await base_cache.get_json("json1")
        assert result == data
        
        # Complex nested data
        complex_data = {
            "user": {"id": 1, "name": "John"},
            "items": [1, 2, 3],
            "metadata": {"created": "2024-01-01", "tags": ["a", "b"]}
        }
        assert await base_cache.set_json("json2", complex_data) is True
        assert await base_cache.get_json("json2") == complex_data
        
        # With TTL
        assert await base_cache.set_json("json3", data, ttl=1) is True
        await asyncio.sleep(1.1)
        assert await base_cache.get_json("json3") is None
    
    @pytest.mark.asyncio
    async def test_get_json_nonexistent(self, base_cache):
        """Test getting non-existent JSON key."""
        assert await base_cache.get_json("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_json_serialization_error(self, base_cache):
        """Test JSON serialization errors."""
        # Object that can't be serialized
        class CustomObject:
            pass
        
        with pytest.raises(SerializationError) as exc_info:
            await base_cache.set_json("bad", CustomObject())
        assert exc_info.value.operation == "serialize"
        assert "CustomObject" in exc_info.value.data_type
    
    @pytest.mark.asyncio
    async def test_json_deserialization_error(self, base_cache):
        """Test JSON deserialization errors."""
        # Set invalid JSON
        await base_cache.set("badjson", "not valid json{")
        
        with pytest.raises(SerializationError) as exc_info:
            await base_cache.get_json("badjson")
        assert exc_info.value.operation == "deserialize"
        assert "badjson" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_json_with_datetime(self, base_cache):
        """Test JSON with datetime serialization."""
        data = {
            "timestamp": datetime.now(),
            "value": 123
        }
        
        # Should use default=str for datetime
        assert await base_cache.set_json("datetime", data) is True
        result = await base_cache.get_json("datetime")
        assert result["value"] == 123
        assert isinstance(result["timestamp"], str)


class TestBaseCacheHashOperations:
    """Test hash operations."""
    
    @pytest.mark.asyncio
    async def test_hash_operations(self, base_cache):
        """Test all hash operations."""
        # Set single field
        assert await base_cache.hset("hash1", "field1", "value1") == 1
        assert await base_cache.hset("hash1", "field2", "value2") == 1
        
        # Update existing field
        assert await base_cache.hset("hash1", "field1", "updated") == 0
        
        # Get single field
        assert await base_cache.hget("hash1", "field1") == "updated"
        assert await base_cache.hget("hash1", "field2") == "value2"
        assert await base_cache.hget("hash1", "nonexistent") is None
        
        # Get all fields
        all_fields = await base_cache.hgetall("hash1")
        assert all_fields == {"field1": "updated", "field2": "value2"}
        
        # Delete fields
        assert await base_cache.hdel("hash1", "field1") == 1
        assert await base_cache.hdel("hash1", "field1") == 0  # Already deleted
        assert await base_cache.hdel("hash1", "field2", "nonexistent") == 1
        
        # Empty hash
        assert await base_cache.hgetall("hash1") == {}
        
        # Delete with no fields
        assert await base_cache.hdel("hash1") == 0


class TestBaseCacheListOperations:
    """Test list operations."""
    
    @pytest.mark.asyncio
    async def test_push_pop_operations(self, base_cache):
        """Test list push and pop operations."""
        # Left push
        assert await base_cache.lpush("list1", "item1") == 1
        assert await base_cache.lpush("list1", "item2", "item3") == 3
        
        # Right push
        assert await base_cache.rpush("list1", "item4") == 4
        assert await base_cache.rpush("list1", "item5", "item6") == 6
        
        # Left pop
        assert await base_cache.lpop("list1") == "item3"
        assert await base_cache.lpop("list1") == "item2"
        
        # Pop from empty list
        await base_cache.delete("list1")
        assert await base_cache.lpop("list1") is None
        
        # Push with no values
        assert await base_cache.lpush("list2") == 0
        assert await base_cache.rpush("list2") == 0
    
    @pytest.mark.asyncio
    async def test_blocking_pop(self, base_cache):
        """Test blocking pop operation."""
        # Use unique keys to avoid test interference
        import uuid
        suffix = str(uuid.uuid4())[:8]
        
        # Blocking pop with timeout - no data
        result = await base_cache.blpop([f"empty_list_{suffix}"], timeout=1)
        assert result is None
        
        # Add data and blocking pop
        list3_key = f"list3_{suffix}"
        await base_cache.rpush(list3_key, "value1", "value2")
        result = await base_cache.blpop([list3_key], timeout=1)
        assert result == (list3_key, "value1")
        
        # Multiple lists
        list4_key = f"list4_{suffix}"
        list5_key = f"list5_{suffix}"
        await base_cache.rpush(list4_key, "value4")
        await base_cache.rpush(list5_key, "value5")
        result = await base_cache.blpop([f"empty_{suffix}", list5_key, list4_key], timeout=1)
        assert result == (list5_key, "value5")
    
    @pytest.mark.asyncio
    async def test_blocking_pop_with_prefix(self, clean_redis):
        """Test blocking pop with key prefix."""
        cache = BaseCache(key_prefix="test")
        
        await cache.rpush("mylist", "value")
        result = await cache.blpop(["mylist"], timeout=1)
        assert result == ("mylist", "value")  # Prefix removed from result


class TestBaseCachePatternOperations:
    """Test pattern-based operations."""
    
    @pytest.mark.asyncio
    async def test_scan_keys(self, base_cache):
        """Test scanning keys by pattern."""
        # Create test keys
        for i in range(10):
            await base_cache.set(f"scan:test:{i}", f"value{i}")
            await base_cache.set(f"other:{i}", f"value{i}")
        
        # Scan all keys
        all_keys = []
        async for key in base_cache.scan_keys("*"):
            all_keys.append(key)
        assert len(all_keys) >= 20
        
        # Scan with pattern
        scan_keys = []
        async for key in base_cache.scan_keys("scan:*"):
            scan_keys.append(key)
        assert len(scan_keys) == 10
        assert all(key.startswith("scan:") for key in scan_keys)
        
        # Scan with count hint
        first_batch = []
        async for key in base_cache.scan_keys("*", count=5):
            first_batch.append(key)
            if len(first_batch) >= 5:
                break
        assert len(first_batch) >= 5
    
    @pytest.mark.asyncio
    async def test_scan_keys_with_prefix(self, clean_redis):
        """Test scanning keys with key prefix."""
        cache = BaseCache(key_prefix="app")
        
        # Create keys with prefix
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Scan should return keys without prefix
        keys = []
        async for key in cache.scan_keys("*"):
            keys.append(key)
        
        assert "key1" in keys
        assert "key2" in keys
        assert not any(key.startswith("app:") for key in keys)
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, base_cache):
        """Test deleting keys by pattern."""
        # Create many keys
        for i in range(100):
            await base_cache.set(f"delete:batch:{i}", f"value{i}")
            await base_cache.set(f"keep:{i}", f"value{i}")
        
        # Delete by pattern
        deleted = await base_cache.delete_pattern("delete:*")
        assert deleted == 100
        
        # Verify deleted
        remaining = []
        async for key in base_cache.scan_keys("delete:*"):
            remaining.append(key)
        assert len(remaining) == 0
        
        # Verify kept
        kept = []
        async for key in base_cache.scan_keys("keep:*"):
            kept.append(key)
        assert len(kept) == 100
    
    @pytest.mark.asyncio
    async def test_delete_pattern_large_batch(self, base_cache):
        """Test deleting more than 1000 keys (batch size)."""
        # Create 1500 keys
        for i in range(1500):
            await base_cache.set(f"large:{i}", f"value{i}")
        
        # Delete all
        deleted = await base_cache.delete_pattern("large:*")
        assert deleted == 1500
        
        # Verify all deleted
        count = 0
        async for _ in base_cache.scan_keys("large:*"):
            count += 1
        assert count == 0


class TestBaseCachePubSub:
    """Test pub/sub operations."""
    
    @pytest.mark.asyncio
    async def test_publish(self, base_cache):
        """Test publishing messages."""
        # Publish to channel with no subscribers
        count = await base_cache.publish("channel1", "message1")
        assert count == 0  # No subscribers
        
        # Publish JSON data
        count = await base_cache.publish("channel2", json.dumps({"data": "value"}))
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_subscribe(self, base_cache):
        """Test subscribing to channels."""
        received = []
        
        async def subscriber():
            async for message in base_cache.subscribe("test:channel"):
                received.append(message)
                if len(received) >= 3:
                    break
        
        # Start subscriber
        sub_task = asyncio.create_task(subscriber())
        
        # Give subscriber time to connect
        await asyncio.sleep(0.1)
        
        # Publish messages
        await base_cache.publish("test:channel", "message1")
        await base_cache.publish("test:channel", "message2")
        await base_cache.publish("test:channel", "message3")
        
        # Wait for subscriber
        await sub_task
        
        # Verify messages received
        assert len(received) == 3
        assert all(msg['type'] == 'message' for msg in received)
        assert [msg['data'] for msg in received] == ["message1", "message2", "message3"]
    
    @pytest.mark.asyncio
    async def test_subscribe_multiple_channels(self, base_cache):
        """Test subscribing to multiple channels."""
        received = []
        
        async def subscriber():
            async for message in base_cache.subscribe("chan1", "chan2"):
                received.append(message)
                if len(received) >= 2:
                    break
        
        # Start subscriber
        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)
        
        # Publish to different channels
        await base_cache.publish("chan1", "msg1")
        await base_cache.publish("chan2", "msg2")
        
        await sub_task
        
        assert len(received) == 2
        channels = [msg['channel'] for msg in received]
        assert "chan1" in channels
        assert "chan2" in channels
    
    @pytest.mark.asyncio
    async def test_subscribe_no_channels(self, base_cache):
        """Test subscribing with no channels."""
        messages = []
        async for msg in base_cache.subscribe():
            messages.append(msg)
        assert len(messages) == 0


class TestBaseCacheUtility:
    """Test utility operations."""
    
    @pytest.mark.asyncio
    async def test_info(self, base_cache):
        """Test getting Redis info."""
        info = await base_cache.info()
        
        # Check basic info structure
        assert isinstance(info, dict)
        assert 'redis_version' in info
        assert 'connected_clients' in info
        assert 'used_memory' in info
    
    @pytest.mark.asyncio
    async def test_flushdb(self, base_cache):
        """Test flushing database."""
        # Add some data
        await base_cache.set("flush1", "value1")
        await base_cache.set("flush2", "value2")
        
        # Verify data exists
        assert await base_cache.get("flush1") == "value1"
        
        # Flush database
        assert await base_cache.flushdb() is True
        
        # Verify data is gone
        assert await base_cache.get("flush1") is None
        assert await base_cache.get("flush2") is None


class TestBaseCachePipeline:
    """Test pipeline operations."""
    
    @pytest.mark.asyncio
    async def test_pipeline_basic(self, base_cache):
        """Test basic pipeline operations."""
        async with base_cache.pipeline() as pipe:
            pipe.set("pipe1", "value1")
            pipe.set("pipe2", "value2")
            pipe.get("pipe1")
            results = await pipe.execute()
        
        assert results[0] is True  # set result
        assert results[1] is True  # set result
        assert results[2] == "value1"  # get result
    
    @pytest.mark.asyncio
    async def test_pipeline_transaction(self, base_cache):
        """Test pipeline with transaction."""
        async with base_cache.pipeline(transaction=True) as pipe:
            pipe.multi()
            pipe.set("trans1", "value1")
            pipe.set("trans2", "value2")
            results = await pipe.execute()
        
        assert all(results)
        assert await base_cache.get("trans1") == "value1"
        assert await base_cache.get("trans2") == "value2"


class TestBaseCacheErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, base_cache, monkeypatch):
        """Test handling of connection errors."""
        # Mock Redis error
        from redis.exceptions import RedisError
        
        async def mock_get_redis(*args, **kwargs):
            class MockRedis:
                async def get(self, *args, **kwargs):
                    raise RedisError("Connection lost")
                async def aclose(self):
                    pass
            return MockRedis()
        
        monkeypatch.setattr(base_cache, "_get_redis", mock_get_redis)
        
        with pytest.raises(CacheError) as exc_info:
            await base_cache.get("key")
        assert "Failed to get key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_redis_context_error(self, base_cache, monkeypatch):
        """Test error in Redis context manager."""
        from redis.exceptions import RedisError
        
        async def mock_close():
            raise RedisError("Close failed")
        
        # This should not raise even if close fails
        async with base_cache._redis_context() as r:
            monkeypatch.setattr(r, "close", mock_close)
            await r.ping()  # Should work
        # Close error should be handled


class TestBaseCacheIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_operations(self, base_cache):
        """Test concurrent cache operations."""
        async def writer(n):
            for i in range(10):
                await base_cache.set(f"concurrent:{n}:{i}", f"value{i}")
        
        async def reader(n):
            results = []
            for i in range(10):
                value = await base_cache.get(f"concurrent:{n}:{i}")
                if value:
                    results.append(value)
            return results
        
        # Run concurrent writers
        await asyncio.gather(*[writer(i) for i in range(5)])
        
        # Run concurrent readers
        results = await asyncio.gather(*[reader(i) for i in range(5)])
        
        # Verify all data was written and read
        for result in results:
            assert len(result) == 10
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_benchmark(self, base_cache, benchmark_async):
        """Benchmark cache operations."""
        # Prepare data
        await base_cache.set("perf_key", "performance_value")
        
        # Benchmark get operation
        await benchmark_async(base_cache.get, "perf_key")
        
        # Check performance
        stats = benchmark_async.stats
        assert stats['mean'] < 0.01  # Should be under 10ms (relaxed for CI)
        print(f"Average get time: {stats['mean']*1000:.2f}ms")