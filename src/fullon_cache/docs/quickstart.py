"""Quick Start Guide for Fullon Cache."""

GUIDE = """
Fullon Cache Quick Start Guide
==============================

Installation
------------
    pip install fullon_cache
    # or with Poetry
    poetry add fullon_cache

Basic Setup
-----------
1. Create a .env file in your project root:

    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_DB=0
    REDIS_PASSWORD=  # Optional
    
    # Connection pool settings
    REDIS_MAX_CONNECTIONS=50
    REDIS_SOCKET_TIMEOUT=5

2. Import and use the cache:

    from fullon_cache import TickCache, OrdersCache
    import asyncio
    
    async def main():
        # Initialize caches
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        
        # Store ticker data
        await tick_cache.update_ticker(
            symbol="BTC/USDT",
            exchange="binance", 
            data={
                "bid": 50000.0,
                "ask": 50001.0,
                "last": 50000.5,
                "volume": 1234.56,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
        
        # Retrieve ticker price
        price, timestamp = await tick_cache.get_ticker("BTC/USDT", "binance")
        print(f"BTC price: ${price}")
        
        # Get price from any exchange
        any_price = await tick_cache.get_ticker_any("BTC/USDT")
        print(f"BTC price (any exchange): ${any_price}")
        
        # Work with order queues
        await orders_cache.push_open_order("order_12345", "local_order_456")
        
        # Save order data
        await orders_cache.save_order_data("binance", "order_12345", {
            "symbol": "BTC/USDT",
            "side": "buy",
            "size": 0.1,
            "price": 49000
        })
        
        # Get order status
        order = await orders_cache.get_order_status("binance", "order_12345")
        if order:
            print(f"Order status: {order}")
    
    # Run the async function
    asyncio.run(main())

Real-time Ticker Updates
------------------------
Subscribe to real-time price updates using pub/sub:

    async def ticker_listener():
        from fullon_cache import BaseCache
        
        base_cache = BaseCache()
        
        # Subscribe to ticker updates
        async for message in base_cache.subscribe("tickers:binance:BTC/USDT"):
            if message['type'] == 'message':
                print(f"New ticker data: {message['data']}")
                # Parse and process the ticker update

    # Or use blocking wait for next ticker
    async def wait_for_ticker():
        tick_cache = TickCache()
        
        # Wait for next ticker update (blocking)
        price, timestamp = await tick_cache.get_next_ticker("BTC/USDT", "binance")
        print(f"New price: ${price} at {timestamp}")

Working with Positions
----------------------
Track user positions and accounts:

    from fullon_cache import AccountCache
    
    account_cache = AccountCache()
    
    # Update positions
    await account_cache.upsert_positions(
        ex_id=123,  # Exchange account ID
        positions={
            "BTC/USDT": {"size": 0.5, "cost": 25000.0},
            "ETH/USDT": {"size": 10.0, "cost": 20000.0}
        }
    )
    
    # Get specific position
    position = await account_cache.get_position("BTC/USDT", "123")
    print(f"BTC position: {position.size} @ cost {position.cost}")
    
    # Get all positions
    all_positions = await account_cache.get_all_positions()
    for pos in all_positions:
        print(f"{pos.symbol}: {pos.size} units")

Bot Coordination
----------------
Prevent multiple bots from trading the same symbol:

    from fullon_cache import BotCache
    
    bot_cache = BotCache()
    
    # Check if symbol is blocked
    blocker = await bot_cache.is_blocked("binance", "BTC/USDT")
    
    if not blocker:
        # Try to acquire exclusive access
        if await bot_cache.block_exchange("binance", "BTC/USDT", "bot_123"):
            try:
                # Mark opening position
                await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_123")
                
                # Bot has exclusive access to trade this symbol
                # ... place orders ...
                
                # Clear opening state
                await bot_cache.unmark_opening_position("binance", "BTC/USDT")
            finally:
                # Always release the lock
                await bot_cache.unblock_exchange("binance", "BTC/USDT")
        else:
            print("Failed to acquire lock")
    else:
        print(f"Symbol is blocked by bot: {blocker}")

Process Monitoring
------------------
Track system processes:

    from fullon_cache import ProcessCache
    from fullon_cache.process_cache import ProcessType, ProcessStatus
    
    process_cache = ProcessCache()
    
    # Register a new process
    process_id = await process_cache.register_process(
        process_type=ProcessType.BOT,
        component="arbitrage_bot_1",
        params={"exchanges": ["binance", "kraken"]},
        message="Started arbitrage bot"
    )
    
    # Update process status with heartbeat
    await process_cache.update_process(
        process_id=process_id,
        message="Found arbitrage opportunity",
        status=ProcessStatus.RUNNING,
        heartbeat=True
    )
    
    # Get active processes
    active = await process_cache.get_active_processes(
        process_type=ProcessType.BOT,
        since_minutes=5
    )
    for process in active:
        print(f"{process['component']}: {process['message']}")

OHLCV Data
----------
Store and retrieve candlestick data:

    from fullon_cache import OHLCVCache
    
    ohlcv_cache = OHLCVCache()
    
    # Store OHLCV bars
    bars = [
        [1640000000000, 50000, 50100, 49900, 50050, 100.5],  # [time, o, h, l, c, v]
        [1640000060000, 50050, 50150, 50000, 50100, 95.3],
    ]
    await ohlcv_cache.update_ohlcv_bars("BTC/USDT", "1m", bars)
    
    # Get latest bars
    latest_bars = await ohlcv_cache.get_latest_ohlcv_bars("BTC/USDT", "1m", count=100)
    for bar in latest_bars[-5:]:  # Last 5 bars
        print(f"Time: {bar[0]}, Close: {bar[4]}, Volume: {bar[5]}")

Error Handling
--------------
All operations handle errors gracefully:

    from fullon_cache import TickCache, CacheError
    import logging
    
    logger = logging.getLogger(__name__)
    tick_cache = TickCache()
    
    try:
        price, timestamp = await tick_cache.get_ticker("BTC/USDT", "binance")
    except CacheError as e:
        # Handle cache errors (connection issues, etc.)
        logger.error(f"Cache error: {e}")
        # Fallback to database or other source
        price = await get_from_database("binance", "BTC/USDT")

Best Practices
--------------
1. Always close cache connections when done:
   ```python
   cache = TickCache()
   try:
       # Use cache
   finally:
       await cache.close()
   ```
   
2. Use context managers where available:
   ```python
   async with SymbolCache() as cache:
       symbols = await cache.get_symbols("binance")
   ```

3. Handle cache misses gracefully
4. Set appropriate TTLs for cached data
5. Use pub/sub for real-time data
6. Monitor Redis memory usage
7. Use separate Redis DBs for testing

Advanced Features
-----------------
- Pipeline operations for bulk updates
- Stream operations for reliable queues
- Pattern-based key scanning
- Atomic transactions
- Redis Cluster support

For more detailed information:
- API Reference: from fullon_cache.docs import api_reference
- Examples: from fullon_cache.examples import basic_usage
- Performance: from fullon_cache.docs import performance
"""

__all__ = ['GUIDE']
