"""Migration guide from old cache system to new."""

GUIDE = """
Migration Guide - From Old Cache to Fullon Cache
================================================

This guide helps you migrate from the old cache system (shit_version)
to the new async Fullon Cache.

Key Differences
---------------

1. **Async/Await**: All operations are now asynchronous
   
   Old:
       cache = Cache()
       ticker = cache.get_ticker("binance", "BTC/USDT")
       
   New:
       cache = TickCache()
       ticker = await cache.get_ticker("binance", "BTC/USDT")

2. **No Deep Inheritance**: Flat architecture with composition
   
   Old:
       class Cache(process_cache.Cache):  # Deep inheritance
           pass
           
   New:
       class TickCache:  # Independent class
           def __init__(self):
               self.base = BaseCache()

3. **ORM Models**: Using fullon_orm models instead of structs
   
   Old:
       return TickerStruct(**data)
       
   New:
       from fullon_orm.models import Ticker
       return Ticker(**data)

4. **Configuration**: Environment variables via .env
   
   Old:
       self.host = 'localhost' if local else config.REDIS_HOST
       
   New:
       # Automatically loaded from .env
       self.host = os.getenv('REDIS_HOST', 'localhost')

Module Migration
----------------

### BaseCache

Old:
    from base_cache import Cache
    cache = Cache()
    cache.test()  # Ping
    cache.prepare_cache()  # Flush

New:
    from fullon_cache import BaseCache
    cache = BaseCache()
    await cache.ping()
    await cache.flushdb()

### ProcessCache

Old:
    cache = ProcessCache()
    cache.new_process(timestamp, params, message, component)
    processes = cache.get_top(delta=300, component='bot')

New:
    cache = ProcessCache()
    process_id = await cache.register_process(
        process_type='bot',
        component=component,
        params=params,
        message=message
    )
    processes = await cache.get_active_processes(
        process_type='bot',
        since_minutes=5
    )

### TickCache

Old:
    cache = TickCache()
    cache.update_ticker(exchange, symbol, ticker)
    ticker = cache.get_ticker(exchange, symbol)
    price = cache.round_down(value, symbol)

New:
    cache = TickCache()
    await cache.update_ticker(exchange, symbol, ticker_data)
    ticker = await cache.get_ticker(exchange, symbol)
    price = await cache.round_price(value, symbol, exchange)
    
    # New: Real-time subscriptions
    async for ticker in cache.ticker_stream(exchange, symbol):
        print(f"New price: {ticker.last}")

### OrdersCache

Old:
    cache = OrdersCache()
    cache.push_open_order(order)
    order = cache.pop_open_order(exchange, wait=True)
    cache.save_order_data(ex_id, order_id, status)

New:
    cache = OrdersCache()
    order_id = await cache.push_order(order_data)
    order = await cache.pop_order(exchange, timeout=5)
    await cache.update_order_status(order_id, status)
    
    # New: Stream-based operations
    orders = await cache.pop_orders(exchange, count=10)

### AccountCache

Old:
    cache = AccountCache()
    cache.upsert_positions(uid, ex_id, positions)
    position = cache.get_position(uid, ex_id, symbol)
    cache.upsert_user_account(uid, ex_id, account_data)

New:
    cache = AccountCache()
    await cache.upsert_positions(user_id, exchange, positions)
    position = await cache.get_position(user_id, exchange, symbol)
    await cache.update_account(user_id, exchange, account_data)
    
    # New: Bulk operations
    all_positions = await cache.get_all_positions(user_id, exchange)

### BotCache

Old:
    cache = BotCache()
    result = cache.block_exchange(bot_id, symbol, ex_id)
    cache.unblock_exchange(bot_id, symbol, ex_id)
    status = cache.is_opening_position(bot_id, symbol)

New:
    cache = BotCache()
    acquired = await cache.acquire_symbol_lock(bot_id, exchange, symbol)
    await cache.release_symbol_lock(bot_id, exchange, symbol)
    is_opening = await cache.is_opening_position(bot_id, symbol)
    
    # New: Atomic operations
    async with cache.symbol_lock(bot_id, exchange, symbol):
        # Exclusive access to symbol
        await place_orders()

Data Structure Changes
----------------------

### Ticker Data

Old:
    ticker = {
        'time': '2024-01-01T00:00:00Z',
        'bid': '50000',
        'ask': '50001',
        'last': '50000.5'
    }

New:
    ticker_data = {
        'timestamp': '2024-01-01T00:00:00Z',  # Renamed
        'bid': 50000.0,                       # Float, not string
        'ask': 50001.0,
        'last': 50000.5,
        'volume': 1234.56                     # Additional fields
    }

### Order Data

Old:
    order = {
        'orderId': '12345',
        'updateTime': timestamp
    }

New:
    order_data = {
        'order_id': '12345',      # Snake case
        'updated_at': timestamp,  # Clearer naming
        'status': 'open',         # Explicit status
        'metadata': {}            # Extensible
    }

Error Handling
--------------

Old:
    try:
        ticker = cache.get_ticker(exchange, symbol)
    except Exception as error:
        logger.error(error)
        return None

New:
    from fullon_cache import CacheError, KeyNotFoundError
    
    try:
        ticker = await cache.get_ticker(exchange, symbol)
    except KeyNotFoundError:
        # Handle missing key specifically
        ticker = await fetch_from_api(exchange, symbol)
    except CacheError as e:
        # Handle other cache errors
        logger.error(f"Cache error: {e}")
        # Fallback logic

Testing Changes
---------------

Old:
    def test_ticker_update():
        cache = TickCache()
        cache.update_ticker("binance", "BTC/USDT", data)
        assert cache.get_ticker("binance", "BTC/USDT")

New:
    async def test_ticker_update(cache):  # Fixture provides cache
        await cache.update_ticker("binance", "BTC/USDT", data)
        ticker = await cache.get_ticker("binance", "BTC/USDT")
        assert ticker.symbol == "BTC/USDT"

Performance Improvements
------------------------

1. **Connection Pooling**: Automatic, efficient connection reuse
2. **Pipelining**: Batch operations for better performance
3. **Streams**: More efficient than list-based queues
4. **Pub/Sub**: Real-time updates without polling
5. **Binary Protocol**: Optional msgpack serialization

Migration Checklist
-------------------

□ Update imports from old cache to fullon_cache
□ Add async/await to all cache operations
□ Update data structures to match new format
□ Replace struct classes with ORM models
□ Update error handling to use specific exceptions
□ Modify tests to use async fixtures
□ Update configuration to use .env
□ Remove deep inheritance, use composition
□ Add proper type hints
□ Implement graceful fallbacks

Step-by-Step Migration
----------------------

1. **Phase 1**: Infrastructure
   - Install fullon_cache
   - Set up .env configuration
   - Update test infrastructure

2. **Phase 2**: Read Operations
   - Migrate get operations to async
   - Update data parsing
   - Add error handling

3. **Phase 3**: Write Operations
   - Migrate set/update operations
   - Update data formatting
   - Implement new features

4. **Phase 4**: Advanced Features
   - Implement pub/sub subscriptions
   - Use streams for queues
   - Add monitoring

5. **Phase 5**: Optimization
   - Enable pipelining
   - Implement caching strategies
   - Performance testing

Common Issues
-------------

1. **Forgetting await**
   
   Error: TypeError: 'coroutine' object is not subscriptable
   Fix: Add 'await' before cache operations

2. **String vs Numeric Types**
   
   Old cache stored numbers as strings
   New cache uses proper types
   Fix: Remove unnecessary type conversions

3. **Key Pattern Changes**
   
   Old: "ticker_binance_BTC/USDT"
   New: "ticker:binance:BTC/USDT"
   Fix: Update key patterns or use migration script

4. **Missing Async Context**
   
   Error: RuntimeError: no running event loop
   Fix: Use asyncio.run() or proper async context

Migration Script Example
------------------------

    import asyncio
    from old_cache import Cache as OldCache
    from fullon_cache import TickCache, OrdersCache
    
    async def migrate_tickers():
        '''Migrate ticker data from old to new cache'''
        old = OldCache()
        new = TickCache()
        
        # Get all old tickers
        pattern = "ticker_*"
        for key in old.get_keys(pattern):
            # Parse old key format
            parts = key.split('_')
            if len(parts) >= 3:
                exchange = parts[1]
                symbol = '_'.join(parts[2:])
                
                # Get old data
                old_data = old.get(key)
                if old_data:
                    # Transform to new format
                    new_data = {
                        'bid': float(old_data.get('bid', 0)),
                        'ask': float(old_data.get('ask', 0)),
                        'last': float(old_data.get('last', 0)),
                        'timestamp': old_data.get('time')
                    }
                    
                    # Save to new cache
                    await new.update_ticker(exchange, symbol, new_data)
                    
        print("Ticker migration complete")
    
    # Run migration
    asyncio.run(migrate_tickers())
"""
