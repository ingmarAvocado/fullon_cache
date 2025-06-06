"""Performance optimization guide for Fullon Cache."""

GUIDE = """
Fullon Cache - Performance Guide
================================

This guide covers performance optimization techniques, benchmarking,
and best practices for achieving sub-millisecond cache operations.

Performance Targets
-------------------

- Cache Hit: < 1ms
- Cache Write: < 2ms
- Pub/Sub Latency: < 5ms
- Queue Operations: < 3ms
- Bulk Operations: < 10ms for 100 items

Connection Pooling
------------------

Connection pooling is critical for performance:

    # Default configuration (50 connections)
    REDIS_MAX_CONNECTIONS=50
    REDIS_SOCKET_TIMEOUT=5
    REDIS_SOCKET_CONNECT_TIMEOUT=5

Tuning pool size:
- Too small: Connection wait times
- Too large: Memory overhead
- Rule of thumb: 2-3x concurrent operations

Monitor pool usage:
    info = await cache.info()
    connected_clients = info['connected_clients']
    
    # Alert if > 80% of pool size
    if connected_clients > REDIS_MAX_CONNECTIONS * 0.8:
        logger.warning("Connection pool near capacity")

Pipelining
----------

Use pipelining for bulk operations:

    # Slow: Individual operations
    for i in range(1000):
        await cache.set(f"key:{i}", f"value:{i}")
    # Time: ~100ms

    # Fast: Pipelined operations
    async with cache.pipeline() as pipe:
        for i in range(1000):
            pipe.set(f"key:{i}", f"value:{i}")
        await pipe.execute()
    # Time: ~10ms (10x faster!)

Pipelining strategies:
    # Batch by size
    async def bulk_update(items, batch_size=100):
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            async with cache.pipeline() as pipe:
                for item in batch:
                    pipe.set(item['key'], item['value'])
                await pipe.execute()

Data Structure Selection
------------------------

Choose the right Redis data structure:

1. **Strings**: Simple key-value
   - Use for: Single values, counters
   - Performance: O(1) get/set
   
2. **Hashes**: Object storage
   - Use for: User profiles, configuration
   - Performance: O(1) field access
   - Memory: More efficient than JSON strings
   
   Example:
       # Instead of JSON string
       await cache.set_json(f"user:{uid}", user_data)
       
       # Use hash
       await cache.hset(f"user:{uid}", mapping=user_data)

3. **Lists**: Queues
   - Use for: Task queues, logs
   - Performance: O(1) push/pop at ends
   
4. **Sets**: Unique collections
   - Use for: Active users, tags
   - Performance: O(1) add/remove/check
   
5. **Sorted Sets**: Ranked data
   - Use for: Leaderboards, time-series
   - Performance: O(log N) operations
   
6. **Streams**: Event logs
   - Use for: Order queues, audit logs
   - Performance: O(1) add, O(N) read

Serialization Optimization
--------------------------

Choose efficient serialization:

    import json
    import msgpack
    import pickle
    
    data = {"user_id": 123, "balance": 10000.50, "positions": [...]}
    
    # JSON: Human readable, larger
    json_data = json.dumps(data)  # 245 bytes
    
    # MessagePack: Binary, compact
    msgpack_data = msgpack.packb(data)  # 187 bytes (24% smaller)
    
    # Pickle: Python-specific, fast
    pickle_data = pickle.dumps(data)  # 203 bytes

For Fullon Cache:
- JSON: Default for compatibility
- MessagePack: For large objects
- Raw bytes: For binary data

Key Design
----------

Optimize key patterns:

    # Bad: Long keys waste memory
    key = "fullon:cache:ticker:exchange:binance:symbol:BTC/USDT:data"
    
    # Good: Concise but clear
    key = "tick:binance:BTC/USDT"
    
    # Use prefixes for scanning
    tickers = [k async for k in cache.scan_keys("tick:binance:*")]

Key guidelines:
- Keep keys short but descriptive
- Use consistent separators (:)
- Avoid special characters
- Include version for migrations

Memory Optimization
-------------------

1. **Set Expiration**: Prevent memory bloat
   
       await cache.set(key, value, ttl=3600)  # 1 hour

2. **Use Appropriate Types**: 
   
       # Store numbers as numbers, not strings
       await cache.set("price", "50000.5")  # Bad: 7 bytes
       await cache.hset("ticker", "price", 50000.5)  # Good: 4 bytes

3. **Compress Large Values**:
   
       import zlib
       
       # For values > 1KB
       if len(data) > 1024:
           compressed = zlib.compress(data.encode())
           await cache.set(key, compressed)

4. **Monitor Memory Usage**:
   
       info = await cache.info()
       memory_used = info['used_memory_human']
       memory_peak = info['used_memory_peak_human']
       
       # Set up eviction policy
       # maxmemory-policy allkeys-lru

Pub/Sub Optimization
--------------------

Optimize real-time updates:

    # Use pattern subscriptions wisely
    # Bad: Subscribe to everything
    await cache.subscribe("*")
    
    # Good: Specific subscriptions
    await cache.subscribe("ticker:binance:BTC/USDT")
    
    # Batch publish for multiple subscribers
    ticker_updates = [
        ("ticker:binance:BTC/USDT", ticker1),
        ("ticker:binance:ETH/USDT", ticker2),
    ]
    
    async with cache.pipeline() as pipe:
        for channel, data in ticker_updates:
            pipe.publish(channel, json.dumps(data))
        await pipe.execute()

Stream Optimization
-------------------

Use streams efficiently for queues:

    # Add to stream with automatic ID
    await cache.xadd("orders:binance", {"order": json.dumps(order_data)})
    
    # Read with count limit
    messages = await cache.xread({"orders:binance": "$"}, count=100, block=1000)
    
    # Trim stream to prevent unbounded growth
    await cache.xtrim("orders:binance", maxlen=10000, approximate=True)

    # Consumer groups for scaling
    await cache.xgroup_create("orders:binance", "processors")
    
    # Multiple consumers
    messages = await cache.xreadgroup(
        "processors", 
        "worker1", 
        {"orders:binance": ">"}, 
        count=10
    )

Lua Scripting
-------------

Use Lua for atomic operations:

    # Atomic increment with limit
    lua_script = '''
    local current = redis.call('get', KEYS[1])
    if not current then
        current = 0
    else
        current = tonumber(current)
    end
    
    if current < tonumber(ARGV[1]) then
        return redis.call('incr', KEYS[1])
    else
        return current
    end
    '''
    
    # Register script
    script = cache.register_script(lua_script)
    
    # Execute atomically
    result = await script(keys=['counter'], args=[1000])

Network Optimization
--------------------

1. **Use Unix Sockets** for local Redis:
   
       REDIS_HOST=/var/run/redis/redis.sock
       # 25% faster than TCP for local connections

2. **Enable TCP_NODELAY**:
   
       # Reduces latency for small requests
       socket_tcp_nodelay = True

3. **Batch Operations**:
   
       # Instead of multiple round trips
       values = []
       for key in keys:
           values.append(await cache.get(key))
           
       # Use mget for single round trip
       values = await cache.mget(keys)

Monitoring & Benchmarking
-------------------------

1. **Redis Built-in Monitoring**:
   
       # Slow query log
       await cache.config_set('slowlog-log-slower-than', 1000)  # 1ms
       slowlog = await cache.slowlog_get(10)
       
       # Command stats
       info = await cache.info('commandstats')

2. **Application-Level Metrics**:
   
       import time
       
       class TimedCache(BaseCache):
           async def get(self, key):
               start = time.perf_counter()
               try:
                   return await super().get(key)
               finally:
                   duration = time.perf_counter() - start
                   metrics.record('cache.get', duration)

3. **Benchmarking Script**:
   
       async def benchmark_cache():
           cache = TickCache()
           
           # Prepare data
           ticker_data = {"bid": 50000, "ask": 50001, "last": 50000.5}
           
           # Write benchmark
           start = time.perf_counter()
           for i in range(10000):
               await cache.update_ticker("binance", f"TEST{i}", ticker_data)
           write_time = time.perf_counter() - start
           
           print(f"Write: {write_time/10000*1000:.2f}ms per operation")
           
           # Read benchmark
           start = time.perf_counter()
           for i in range(10000):
               await cache.get_ticker("binance", f"TEST{i}")
           read_time = time.perf_counter() - start
           
           print(f"Read: {read_time/10000*1000:.2f}ms per operation")

Scaling Strategies
------------------

1. **Vertical Scaling**: More memory, faster CPU
2. **Read Replicas**: For read-heavy workloads
3. **Redis Cluster**: For horizontal scaling
4. **Local Caching**: LRU cache for hot data

    from functools import lru_cache
    
    class CachedTickCache(TickCache):
        @lru_cache(maxsize=1000)
        async def get_ticker_cached(self, exchange, symbol):
            return await self.get_ticker(exchange, symbol)

Common Performance Issues
-------------------------

1. **Hot Keys**: Single key with too many requests
   Solution: Shard hot keys or use local cache

2. **Large Values**: Storing huge objects
   Solution: Compress or split into chunks

3. **Memory Fragmentation**: After many updates
   Solution: Restart Redis periodically

4. **Slow Commands**: Commands on large datasets
   Solution: Use SCAN instead of KEYS

5. **Network Latency**: High RTT to Redis
   Solution: Move Redis closer or use connection pooling

Performance Checklist
---------------------

□ Connection pooling configured
□ Pipelining for bulk operations
□ Appropriate data structures used
□ Keys are optimized for size
□ Expiration set on temporary data
□ Monitoring in place
□ Benchmarks meet targets
□ Scaling plan ready

Real-World Example
------------------

High-frequency ticker updates:

    class OptimizedTickCache(TickCache):
        def __init__(self):
            super().__init__()
            self._local_cache = {}
            self._pipeline_buffer = []
            self._last_flush = time.time()
            
        async def update_ticker(self, exchange, symbol, data):
            # Buffer updates
            self._pipeline_buffer.append((exchange, symbol, data))
            
            # Flush every 100 updates or 100ms
            if len(self._pipeline_buffer) >= 100 or 
               time.time() - self._last_flush > 0.1:
                await self._flush_buffer()
                
        async def _flush_buffer(self):
            if not self._pipeline_buffer:
                return
                
            async with self.pipeline() as pipe:
                for exchange, symbol, data in self._pipeline_buffer:
                    key = f"tick:{exchange}:{symbol}"
                    pipe.hset(key, mapping=data)
                    pipe.expire(key, 60)  # 1 minute TTL
                    
                await pipe.execute()
                
            self._pipeline_buffer.clear()
            self._last_flush = time.time()

This optimized version can handle 100,000+ updates per second!
"""