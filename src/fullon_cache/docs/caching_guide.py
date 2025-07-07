"""Caching patterns and best practices guide."""

GUIDE = """
Fullon Cache - Caching Guide
============================

This guide covers caching patterns, strategies, and best practices for
optimal performance and reliability.

Caching Strategies
------------------

1. **Cache-Aside (Lazy Loading)**
   - Load data into cache only when needed
   - Best for: Read-heavy workloads with unpredictable access patterns
   
   Example:
       async def get_user(user_id):
           # Try cache first
           user = await cache.get_json(f"user:{user_id}")
           if user:
               return user
               
           # Cache miss - load from database
           user = await db.get_user(user_id)
           if user:
               # Cache for 1 hour
               await cache.set_json(f"user:{user_id}", user, ttl=3600)
               
           return user

2. **Write-Through**
   - Write to cache and database simultaneously
   - Best for: Critical data that must stay consistent
   
   Example:
       async def update_ticker(exchange, symbol, ticker_data):
           # Update cache
           await tick_cache.update_ticker(exchange, symbol, ticker_data)
           
           # Also persist to database
           await db.save_ticker(exchange, symbol, ticker_data)

3. **Write-Behind (Write-Back)**
   - Write to cache immediately, database later
   - Best for: High-frequency updates where some delay is acceptable
   
   Example:
       async def record_trade(trade):
           # Quick write to cache/queue
           await trades_cache.push_trade(trade)
           
           # Background worker processes queue
           # and writes to database in batches

TTL Strategies
--------------

Different data types require different expiration strategies:

1. **Market Data**: Short TTL (seconds to minutes)
   - Tickers: 5-30 seconds
   - Order books: 1-5 seconds
   - OHLCV: 1-5 minutes

2. **Reference Data**: Long TTL (hours to days)
   - Exchange info: 24 hours
   - Symbol info: 24 hours
   - User profiles: 1-4 hours

3. **Session Data**: Medium TTL (minutes to hours)
   - Bot status: 5-30 minutes
   - Active orders: Until filled/cancelled + 1 hour
   - Positions: While open + 1 hour archive

Example TTL configuration:
    # In .env
    CACHE_TTL_TICKER=30
    CACHE_TTL_EXCHANGE=86400
    CACHE_TTL_ORDER=3600
    CACHE_TTL_POSITION=7200

Key Naming Conventions
----------------------

Use hierarchical, descriptive keys:

    type:identifier:subidentifier

Examples:
    ticker:binance:BTC/USDT
    order:status:ORD123456
    position:user:123:binance:BTC/USDT
    bot:status:bot_1
    queue:orders:binance
    stream:trades:kraken

Benefits:
- Easy to scan/delete by pattern
- Clear organization
- Prevents key collisions
- Enables efficient monitoring

Cache Warming
-------------

Pre-load frequently accessed data:

    async def warm_cache():
        # Load all active symbols
        symbols = await db.get_active_symbols()
        for symbol in symbols:
            await symbol_cache.refresh_symbol(symbol)
            
        # Load recent tickers
        tickers = await db.get_recent_tickers(minutes=5)
        for ticker in tickers:
            await tick_cache.update_ticker(
                ticker.exchange, 
                ticker.symbol, 
                ticker.data
            )

Run cache warming:
- On application startup
- After cache flush
- Periodically for critical data

Handling Cache Misses
---------------------

Always handle cache misses gracefully:

    async def get_data_with_fallback(key):
        try:
            # Try cache
            data = await cache.get_json(key)
            if data:
                return data
        except CacheError:
            logger.warning(f"Cache error for {key}, falling back to DB")
            
        # Fallback to database
        data = await db.get_data(key)
        
        # Try to repopulate cache (don't fail if cache is down)
        try:
            if data:
                await cache.set_json(key, data, ttl=3600)
        except CacheError:
            pass
            
        return data

Cache Invalidation
------------------

Keep cache consistent with these patterns:

1. **Time-based**: Use TTL for automatic expiration
2. **Event-based**: Invalidate on specific events
3. **Version-based**: Include version in key

Example event-based invalidation:
    async def update_symbol_info(symbol):
        # Update database
        await db.update_symbol(symbol)
        
        # Invalidate related caches
        await symbol_cache.delete_symbol(symbol.exchange, symbol.name)
        await tick_cache.delete_ticker(symbol.exchange, symbol.name)

Monitoring and Metrics
----------------------

Monitor cache health:

    async def get_cache_metrics():
        info = await cache.info()
        
        return {
            'memory_used': info['used_memory_human'],
            'hit_rate': info['keyspace_hits'] / 
                       (info['keyspace_hits'] + info['keyspace_misses']),
            'connected_clients': info['connected_clients'],
            'total_keys': sum(db['keys'] for db in info.values() 
                            if isinstance(db, dict) and 'keys' in db),
            'evicted_keys': info.get('evicted_keys', 0)
        }

Set up alerts for:
- High memory usage (>80%)
- Low hit rate (<90%)
- High eviction rate
- Connection pool exhaustion

Performance Tips
----------------

1. **Use Pipelining** for bulk operations:
   
       async with cache.pipeline() as pipe:
           for key, value in items:
               pipe.set(key, value)
           await pipe.execute()

2. **Avoid Hot Keys** by sharding:
   
       # Instead of single counter
       await cache.incr("global:counter")
       
       # Use sharded counters
       shard = hash(request_id) % 10
       await cache.incr(f"counter:shard:{shard}")

3. **Use Appropriate Data Structures**:
   - Hashes for objects (uses less memory)
   - Sets for unique collections
   - Sorted sets for leaderboards/rankings
   - Streams for event logs/queues

4. **Enable Compression** for large values:
   
       import zlib
       
       # Compress before caching
       compressed = zlib.compress(json.dumps(large_data).encode())
       await cache.set("large:data", compressed)
       
       # Decompress after retrieval
       compressed = await cache.get("large:data")
       data = json.loads(zlib.decompress(compressed))

5. **Use Connection Pooling** (enabled by default)

6. **Batch Operations** when possible

7. **Monitor Slow Commands** with Redis SLOWLOG

Common Pitfalls
---------------

1. **Cache Stampede**: Multiple clients regenerating same expired key
   Solution: Use locks or probabilistic early expiration

2. **Memory Exhaustion**: No eviction policy set
   Solution: Configure maxmemory and eviction policy

3. **Inconsistent Data**: Cache not invalidated properly
   Solution: Use event-based invalidation

4. **Hot Keys**: Single key receiving too many requests
   Solution: Shard hot keys or use local caching

5. **Large Values**: Storing very large objects
   Solution: Compress or store in chunks

Security Considerations
-----------------------

1. Use authentication (REDIS_PASSWORD)
2. Encrypt sensitive data before caching
3. Use separate Redis instances/DBs for different security levels
4. Implement access control in application layer
5. Regularly rotate credentials
6. Monitor for suspicious access patterns

Testing Cache Logic
-------------------

Always test cache behavior:

    async def test_cache_fallback():
        # Test normal operation
        await cache.set("key", "value")
        assert await get_data_with_fallback("key") == "value"
        
        # Test cache miss
        await cache.delete("key")
        db_value = await get_data_with_fallback("key")
        assert db_value == expected_db_value
        
        # Test cache down scenario
        cache._pool.close()  # Simulate cache down
        fallback_value = await get_data_with_fallback("key")
        assert fallback_value == expected_db_value
"""
