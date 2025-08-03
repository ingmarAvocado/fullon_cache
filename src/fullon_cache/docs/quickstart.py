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

2. Import and use the cache with fullon_orm models:

    from fullon_cache import TickCache, OrdersCache, AccountCache
    from fullon_orm.models import Tick, Position
    import asyncio
    import time
    
    async def main():
        # Initialize caches
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        account_cache = AccountCache()
        
        # Store ticker data using fullon_orm.Tick model
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            volume=1234.56,
            time=time.time(),
            bid=49999.0,
            ask=50001.0,
            last=50000.5
        )
        
        await tick_cache.update_ticker("binance", tick)
        
        # Retrieve ticker as fullon_orm.Tick object
        cached_tick = await tick_cache.get_ticker("BTC/USDT", "binance")
        print(f"Current BTC price: ${cached_tick.price}")
        
        # Work with positions using fullon_orm.Position model
        position = Position(
            symbol="BTC/USDT",
            cost=5000.0,
            volume=0.1,
            fee=5.0,
            price=50000.0,
            timestamp=time.time(),
            ex_id="binance"
        )
        
        await account_cache.upsert_positions(123, [position])
        print(f"Position stored for BTC/USDT: {position.volume} BTC")
        
        # Get price from ticker
        current_price = await tick_cache.get_price("BTC/USDT", "binance")
        print(f"Current BTC price: ${current_price}")
        
        # Work with order queues
        await orders_cache.push_open_order("order_12345", "local_order_456")
        
        # Create order with fullon_orm.Order model
        from fullon_orm.models import Order
        order = Order(
            ex_order_id="order_12345",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=49000,
            order_type="limit",
            status="open",
            exchange="binance",
            timestamp=time.time()
        )
        
        # Save order using ORM model
        await orders_cache.save_order("binance", order)
        
        # Get order status as fullon_orm.Order object
        retrieved_order = await orders_cache.get_order("binance", "order_12345")
        if retrieved_order:
            print(f"Order status: {retrieved_order.status} - {retrieved_order.symbol} @ ${retrieved_order.price}")
    
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
Track user positions using fullon_orm.Position models:

    from fullon_cache import AccountCache
    from fullon_orm.models import Position
    import time
    
    account_cache = AccountCache()
    
    # Create positions using fullon_orm.Position models
    positions = [
        Position(
            symbol="BTC/USDT",
            cost=25000.0,
            volume=0.5,
            fee=10.0,
            price=50000.0,
            timestamp=time.time(),
            ex_id="123"
        ),
        Position(
            symbol="ETH/USDT",
            cost=20000.0,
            volume=10.0,
            fee=8.0,
            price=2000.0,
            timestamp=time.time(),
            ex_id="123"
        )
    ]
    
    # Update positions with ORM models
    await account_cache.upsert_positions(123, positions)
    
    # Get specific position as fullon_orm.Position object
    position = await account_cache.get_position("BTC/USDT", "123")
    print(f"BTC position: {position.volume} @ cost {position.cost}")
    
    # Get all positions as fullon_orm.Position objects
    all_positions = await account_cache.get_all_positions()
    for pos in all_positions:
        print(f"{pos.symbol}: {pos.volume} units @ ${pos.price}")

Working with Trades
-------------------
Manage trade data using fullon_orm.Trade models:

    from fullon_cache import TradesCache
    from fullon_orm.models import Trade
    import time
    
    trades_cache = TradesCache()
    
    # Create trade using fullon_orm.Trade model
    trade = Trade(
        trade_id="TRD_001",
        symbol="BTC/USDT",
        side="buy",
        volume=0.1,
        price=50000.0,
        cost=5000.0,
        fee=5.0,
        time=time.time(),
        ex_id="binance",
        ex_order_id="ORD_001"
    )
    
    # Push trade to cache
    await trades_cache.push_trade("binance", trade)
    
    # Get all trades (destructive read)
    trades = await trades_cache.get_trades("BTC/USDT", "binance")
    for t in trades:
        print(f"Trade: {t.side} {t.volume} {t.symbol} @ ${t.price}")
    
    # User-specific trade operations
    user_trade = Trade(
        trade_id="USER_TRD_001",
        symbol="ETH/USDT",
        side="sell",
        volume=1.0,
        price=3000.0,
        cost=3000.0,
        fee=3.0,
        time=time.time(),
        uid="user_123"
    )
    
    # Push user trade
    await trades_cache.push_user_trade("user_123", "binance", user_trade)
    
    # Pop user trade
    popped_trade = await trades_cache.pop_user_trade("user_123", "binance")
    if popped_trade:
        print(f"User trade: {popped_trade.side} {popped_trade.volume} {popped_trade.symbol}")

Working with Symbols
--------------------
Manage symbol metadata using fullon_orm.Symbol models:

    from fullon_cache import SymbolCache
    from fullon_orm.models import Symbol
    
    symbol_cache = SymbolCache()
    
    # Create symbol using fullon_orm.Symbol model
    symbol = Symbol(
        symbol="BTC/USDT",
        base="BTC",
        quote="USDT",
        cat_ex_id=1,
        decimals=8,
        updateframe="1h",
        backtest=30,
        futures=False,
        only_ticker=False
    )
    
    # Add symbol to cache
    await symbol_cache.add_symbol(symbol)
    
    # Get symbol using model as search criteria
    search_symbol = Symbol(symbol="BTC/USDT", cat_ex_id=1)
    retrieved_symbol = await symbol_cache.get_symbol_by_model(search_symbol)
    if retrieved_symbol:
        print(f"Symbol: {retrieved_symbol.symbol} - Base: {retrieved_symbol.base}")
    
    # Check if symbol exists
    exists = await symbol_cache.symbol_exists(symbol)
    print(f"Symbol exists: {exists}")
    
    # Get all symbols for the same exchange
    exchange_symbols = await symbol_cache.get_symbols_for_exchange(symbol)
    print(f"Exchange has {len(exchange_symbols)} symbols")
    
    # Update symbol
    symbol.decimals = 10
    await symbol_cache.update_symbol(symbol)
    
    # Delete symbol
    await symbol_cache.delete_symbol(symbol)

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
    from fullon_log import get_component_logger
    
    logger = get_component_logger("fullon.cache.examples")
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

Advanced Integration
--------------------
Combine multiple caches for complex trading workflows:

    from fullon_cache import (
        SymbolCache, TickCache, OrdersCache, 
        TradesCache, AccountCache, BotCache
    )
    from fullon_orm.models import Symbol, Tick, Order, Trade, Position
    import time
    
    # Initialize all caches
    symbol_cache = SymbolCache()
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    trades_cache = TradesCache()
    account_cache = AccountCache()
    bot_cache = BotCache()
    
    try:
        # 1. Setup symbol
        symbol = Symbol(
            symbol="BTC/USDT",
            base="BTC",
            quote="USDT",
            cat_ex_id=1,
            decimals=8
        )
        await symbol_cache.add_symbol(symbol)
        
        # 2. Update market data
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            volume=100.0,
            time=time.time(),
            bid=49999.0,
            ask=50001.0,
            last=50000.0
        )
        await tick_cache.update_ticker("binance", tick)
        
        # 3. Coordinate bot access
        bot_id = "trading_bot_1"
        if await bot_cache.block_exchange("binance", "BTC/USDT", bot_id):
            try:
                # 4. Create and execute order
                order = Order(
                    ex_order_id="ORD_001",
                    symbol="BTC/USDT",
                    side="buy",
                    volume=0.1,
                    price=50000.0,
                    status="filled",
                    order_type="market",
                    exchange="binance",
                    timestamp=time.time()
                )
                await orders_cache.save_order("binance", order)
                
                # 5. Record trade
                trade = Trade(
                    trade_id="TRD_001",
                    symbol="BTC/USDT",
                    side="buy",
                    volume=0.1,
                    price=50000.0,
                    cost=5000.0,
                    fee=5.0,
                    time=time.time(),
                    ex_id="binance",
                    ex_order_id="ORD_001"
                )
                await trades_cache.push_trade("binance", trade)
                
                # 6. Update position
                position = Position(
                    symbol="BTC/USDT",
                    cost=5000.0,
                    volume=0.1,
                    fee=5.0,
                    price=50000.0,
                    timestamp=time.time(),
                    ex_id="binance"
                )
                await account_cache.upsert_positions(123, [position])
                
                print("Complete trading workflow executed successfully!")
                
            finally:
                await bot_cache.unblock_exchange("binance", "BTC/USDT")
    
    finally:
        # Close all caches
        await symbol_cache.close()
        await tick_cache.close()
        await orders_cache.close()
        await trades_cache.close()
        await account_cache.close()
        await bot_cache.close()

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
