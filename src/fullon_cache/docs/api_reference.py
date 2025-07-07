"""API Reference documentation for Fullon Cache.

This module contains detailed API documentation for all cache classes.
Each constant provides complete method signatures and usage examples.
"""

BASE_CACHE = """
BaseCache API Reference
======================

The BaseCache class provides core Redis operations used by all cache modules.

Class: BaseCache(key_prefix="", decode_responses=True)
------------------------------------------------------

Parameters:
    key_prefix (str): Optional prefix for all keys
    decode_responses (bool): Whether to decode Redis responses

Resource Management:
    await close() -> None
        Close all connections and cleanup resources

Basic Operations:
    await get(key: str) -> Optional[str]
        Get a value from cache
        
    await set(key: str, value: Union[str, bytes], ttl: Optional[int] = None) -> bool
        Set a value with optional TTL in seconds
        
    await delete(*keys: str) -> int
        Delete one or more keys, returns count deleted
        
    await exists(*keys: str) -> int
        Check how many of the specified keys exist
        
    await expire(key: str, ttl: int) -> bool
        Set expiration on a key in seconds

JSON Operations:
    await get_json(key: str) -> Optional[Any]
        Get and deserialize JSON data
        
    await set_json(key: str, value: Any, ttl: Optional[int] = None) -> bool
        Serialize and set JSON data

Hash Operations:
    await hget(key: str, field: str) -> Optional[str]
        Get a field from a hash
        
    await hset(key: str, field: Optional[str] = None, value: Optional[str] = None, 
              mapping: Optional[Dict[str, Any]] = None) -> int
        Set field(s) in a hash. Can use field/value OR mapping dict
        
    await hgetall(key: str) -> Dict[str, str]
        Get all fields from a hash
        
    await hdel(key: str, *fields: str) -> int
        Delete fields from a hash

List Operations:
    await lpush(key: str, *values: str) -> int
        Push values to the left of a list
        
    await rpush(key: str, *values: str) -> int
        Push values to the right of a list
        
    await lpop(key: str) -> Optional[str]
        Pop from the left of a list
        
    await blpop(keys: List[str], timeout: int = 0) -> Optional[tuple]
        Blocking pop from the left of multiple lists
        
    await lrange(key: str, start: int, stop: int) -> List[str]
        Get range of elements from list
        
    await ltrim(key: str, start: int, stop: int) -> bool
        Trim list to specified range
        
    await llen(key: str) -> int
        Get length of list

Set Operations:
    await scard(key: str) -> int
        Get number of members in a set

Key Scanning:
    async for key in scan_keys(pattern: str = "*", count: int = 100):
        Scan for keys matching pattern (async iterator)
        
    async for key in scan_iter(pattern: str = "*", count: int = 100):
        Alternative key scanning method
        
    await delete_pattern(pattern: str) -> int
        Delete all keys matching pattern

Pub/Sub:
    await publish(channel: str, message: str) -> int
        Publish message to channel, returns subscriber count
        
    async for message in subscribe(*channels: str):
        Subscribe to channels and receive messages as dict

Stream Operations:
    await xadd(stream: str, fields: Dict[str, Any], maxlen: Optional[int] = None, 
               approximate: bool = True) -> str
        Add entry to stream, returns entry ID
        
    await xread(streams: Dict[str, str], count: Optional[int] = None, 
                block: Optional[int] = None) -> List
        Read from streams
        
    await xdel(stream: str, *ids: str) -> int
        Delete entries from stream
        
    await xlen(stream: str) -> int
        Get length of stream
        
    await xtrim(stream: str, maxlen: int, approximate: bool = True) -> int
        Trim stream to maxlen

Pipeline:
    async with cache.pipeline(transaction: bool = True) as pipe:
        Execute multiple commands in a pipeline/transaction

Utility:
    await ping() -> bool
        Check Redis connection
        
    await info() -> dict
        Get Redis server information
        
    await flushdb() -> bool
        Clear entire database (use with caution!)

Example:
    cache = BaseCache()
    
    # Basic operations
    await cache.set("user:123", "John Doe", ttl=3600)
    name = await cache.get("user:123")
    
    # JSON operations
    await cache.set_json("config", {"debug": True, "timeout": 30})
    config = await cache.get_json("config")
    
    # Hash operations with mapping
    await cache.hset("user:123:profile", mapping={"name": "John", "age": "30"})
    profile = await cache.hgetall("user:123:profile")
    
    # Pipeline for atomic operations
    async with cache.pipeline() as pipe:
        pipe.set("key1", "value1")
        pipe.set("key2", "value2")
        pipe.incr("counter")
        results = await pipe.execute()
"""

PROCESS_CACHE = """
ProcessCache API Reference
==========================

Process monitoring and health tracking for system components.

Class: ProcessCache()
--------------------

Inherits from: BaseCache

Modern Process Management:
    await register_process(process_type: ProcessType, component: str, 
                          params: Optional[Dict[str, Any]] = None,
                          message: Optional[str] = None, 
                          status: ProcessStatus = ProcessStatus.STARTING) -> str
        Register a new process, returns process_id
        
    await update_process(process_id: str, status: Optional[ProcessStatus] = None,
                        message: Optional[str] = None, params: Optional[Dict[str, Any]] = None,
                        heartbeat: bool = True) -> bool
        Update process status and heartbeat
        
    await get_process(process_id: str) -> Optional[Dict[str, Any]]
        Get process details by ID
        
    await get_active_processes(process_type: Optional[ProcessType] = None,
                              component: Optional[str] = None, since_minutes: int = 5,
                              include_heartbeat_check: bool = True) -> List[Dict[str, Any]]
        Get active processes with optional filters
        
    await stop_process(process_id: str, message: Optional[str] = None) -> bool
        Mark process as stopped
        
    await cleanup_stale_processes(stale_minutes: int = 30) -> int
        Remove processes without recent heartbeat

System Monitoring:
    await get_process_history(component: str, limit: int = 100) -> List[Dict[str, Any]]
        Get process history for a component
        
    await get_component_status(component: str) -> Optional[Dict[str, Any]]
        Get current status of a component
        
    await get_system_health() -> Dict[str, Any]
        Get overall system health metrics
        
    await broadcast_message(process_type: ProcessType, message: str, 
                           data: Optional[Dict[str, Any]] = None) -> int
        Broadcast message to processes

Metrics:
    await get_metrics() -> Dict[str, Any]
        Get process metrics and statistics

Legacy Methods (for backward compatibility):
    await delete_from_top(component: Optional[str] = None) -> int
    await get_top(deltatime: Optional[int] = None, comp: Optional[str] = None) -> List[dict]
    await update_process_legacy(tipe: str, key: str, message: str = "") -> bool
    await new_process(tipe: str, key: str, params: Dict[str, Any], 
                     pid: Optional[Any] = None, message: str = "") -> int
    await get_process_legacy(tipe: str, key: str) -> Dict[str, Any]
    await delete_process(tipe: str, key: str = '') -> bool

ProcessType Enum:
    TICK = "tick"
    OHLCV = "ohlcv"
    BOT = "bot"
    ACCOUNT = "account"
    ORDER = "order"
    BOT_STATUS_SERVICE = "bot_status_service"
    CRAWLER = "crawler"
    USER_TRADES_SERVICE = "user_trades_service"

ProcessStatus Enum:
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    STALE = "stale"
"""

EXCHANGE_CACHE = """
ExchangeCache API Reference
===========================

Exchange-specific caching and WebSocket error management.

Class: ExchangeCache()
---------------------

Inherits from: ProcessCache

WebSocket Error Management:
    await push_ws_error(error: str, ex_id: str) -> None
        Push WebSocket error to exchange-specific queue
        
    await pop_ws_error(ex_id: str, timeout: int = 0) -> Optional[str]  
        Pop WebSocket error from queue (blocking if timeout > 0)

Note: ExchangeCache inherits all methods from ProcessCache and BaseCache.
It primarily adds WebSocket error queue management for each exchange.

Example:
    cache = ExchangeCache()
    
    # Push error to queue
    await cache.push_ws_error("Connection lost", "binance")
    
    # Pop error (blocking for 5 seconds)
    error = await cache.pop_ws_error("binance", timeout=5)
    if error:
        print(f"WebSocket error: {error}")
"""

SYMBOL_CACHE = """
SymbolCache API Reference
=========================

Symbol metadata caching with auto-refresh from database.

Class: SymbolCache()
--------------------

Note: Does NOT inherit from BaseCache, uses composition instead.

Symbol Operations:
    await get_symbols(exchange: str, loop: int = 0, force: bool = False) -> List[Symbol]
        Get all symbols for an exchange
        - loop: Retry attempts on failure
        - force: Force refresh from database
        
    await get_symbols_by_ex_id(ex_id: int, loop: int = 0, force: bool = False) -> List[Symbol]
        Get symbols by exchange ID
        
    await get_symbol(symbol: str, cat_ex_id: Optional[str] = None,
                    exchange_name: Optional[str] = None, loop: int = 0) -> Optional[Symbol]
        Get specific symbol by name and exchange
        
    await delete_symbol(symbol: str, cat_ex_id: Optional[str] = None,
                       exchange_name: Optional[str] = None) -> None
        Delete symbol from cache (also removes associated tickers)

Resource Management:
    await close()
        Close connections
        
    async with SymbolCache() as cache:
        Context manager support

Example:
    async with SymbolCache() as cache:
        # Get all Binance symbols
        symbols = await cache.get_symbols("binance")
        
        # Get specific symbol
        btc = await cache.get_symbol("BTC/USDT", exchange_name="binance")
        if btc:
            print(f"Symbol ID: {btc.symbol_id}, Min size: {btc.min_order_size}")
"""

TICK_CACHE = """
TickCache API Reference
=======================

Real-time ticker data management.

Class: TickCache()
------------------

Inherits from: SymbolCache

Ticker Operations:
    await update_ticker(symbol: str, exchange: str, data: Dict[str, Any]) -> int
        Update ticker data and publish to subscribers
        
    await get_ticker(symbol: str, exchange: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]
        Get ticker price and timestamp
        
    await get_ticker_any(symbol: str) -> float
        Get ticker from any available exchange
        
    await get_tickers(exchange: Optional[str] = "") -> List[Tick]
        Get all tickers, optionally filtered by exchange
        
    await del_exchange_ticker(exchange: str) -> int
        Delete all tickers for an exchange

Price Operations:
    await get_price(symbol: str, exchange: Optional[str] = None) -> float
        Get current price (0.0 if not found)
        
    await get_next_ticker(symbol: str, exchange: str) -> Tuple[float, Optional[str]]
        Get next ticker via pub/sub (blocking)

Utility:
    await round_down(symbol: str, exchange: str, sizes: List[float], 
                    futures: bool) -> Tuple[float, float, float]
        Round sizes down to symbol specifications
        Returns: (rounded_size1, rounded_size2, rounded_size3)
        
    await get_tick_crawlers() -> Dict[str, Any]
        Get tick crawler configuration

Example:
    cache = TickCache()
    
    # Update ticker
    await cache.update_ticker("BTC/USDT", "binance", {
        "bid": 50000.0,
        "ask": 50001.0,
        "last": 50000.5,
        "volume": 1234.56
    })
    
    # Get price
    price = await cache.get_price("BTC/USDT", "binance")
    
    # Get from any exchange  
    any_price = await cache.get_ticker_any("BTC/USDT")
"""

ACCOUNT_CACHE = """
AccountCache API Reference
==========================

User account and position management.

Class: AccountCache()
--------------------

Inherits from: TickCache

Position Management:
    await upsert_positions(ex_id: int, positions: Dict[str, Dict[str, float]], 
                          update_date: bool = False) -> bool
        Update or insert positions for an exchange account
        
    await get_position(symbol: str, ex_id: str, latest: bool = False,
                      cur_timestamp: Optional[float] = None) -> Position
        Get position for symbol/exchange
        
    await get_all_positions() -> List[Position]
        Get all positions across all accounts
        
    await clean_positions() -> int
        Remove positions with zero size

Account Management:
    await upsert_user_account(ex_id: int, account: dict = {}, 
                             update_date: str = "") -> bool
        Update or insert account data
        
    await get_full_account(exchange: int, currency: str) -> dict
        Get complete account data for exchange/currency
        
    await get_all_accounts() -> dict
        Get all accounts

Example:
    cache = AccountCache()
    
    # Update positions
    await cache.upsert_positions(123, {
        "BTC/USDT": {"size": 0.5, "cost": 25000.0},
        "ETH/USDT": {"size": 10.0, "cost": 20000.0}
    })
    
    # Get specific position
    position = await cache.get_position("BTC/USDT", "123")
    print(f"Size: {position.size}, Cost: {position.cost}")
"""

ORDERS_CACHE = """
OrdersCache API Reference
=========================

Order queue and status management.

Class: OrdersCache()
--------------------

Inherits from: AccountCache

Order Queue Operations:
    await push_open_order(oid: str, local_oid: str) -> None
        Push order ID pair to processing queue
        
    await pop_open_order(oid: str) -> Optional[str]
        Pop local order ID for given order ID

Order Data Management:
    await save_order_data(ex_id: str, oid: str, data: Dict = {}) -> None
        Save order data with automatic expiration
        
    await get_order_status(ex_id: str, oid: str) -> Optional[Order]
        Get order status and data
        
    await get_orders(ex_id: str) -> List[Order]
        Get all orders for an exchange

Account Data:
    await get_full_accounts(ex_id: str) -> Optional[Any]
        Get full account data (inherited)

Example:
    cache = OrdersCache()
    
    # Queue order for processing
    await cache.push_open_order("order123", "local456")
    
    # Save order data
    await cache.save_order_data("binance", "order123", {
        "symbol": "BTC/USDT",
        "side": "buy",
        "size": 0.1,
        "price": 50000
    })
    
    # Check order status
    order = await cache.get_order_status("binance", "order123")
    if order:
        print(f"Order status: {order.status}")
"""

BOT_CACHE = """
BotCache API Reference
======================

Bot coordination and exchange blocking.

Class: BotCache()
-----------------

Inherits from: AccountCache

Exchange Blocking (prevents multiple bots on same symbol):
    await is_blocked(ex_id: str, symbol: str) -> str
        Check if exchange/symbol is blocked, returns bot_id or empty
        
    await block_exchange(ex_id: str, symbol: str, bot_id: Union[str, int]) -> bool
        Block exchange/symbol for exclusive bot use
        
    await unblock_exchange(ex_id: str, symbol: str) -> bool
        Release exchange/symbol block
        
    await get_blocks() -> List[Dict[str, str]]
        Get all current blocks

Position Opening State:
    await is_opening_position(ex_id: str, symbol: str) -> bool
        Check if bot is currently opening a position
        
    await mark_opening_position(ex_id: str, symbol: str, bot_id: Union[str, int]) -> bool
        Mark that bot is opening a position
        
    await unmark_opening_position(ex_id: str, symbol: str) -> bool
        Clear position opening state

Bot Status:
    await update_bot(bot_id: str, bot: Dict[str, Union[str, int, float]]) -> bool
        Update bot status information
        
    await get_bots() -> Dict[str, Dict[str, Any]]
        Get all bot statuses
        
    await del_bot(bot_id: str) -> bool
        Delete bot status
        
    await del_status() -> bool
        Delete all bot statuses

Example:
    cache = BotCache()
    
    # Check if can trade
    blocker = await cache.is_blocked("binance", "BTC/USDT")
    if not blocker:
        # Block for our bot
        await cache.block_exchange("binance", "BTC/USDT", "bot_123")
        
        # Mark opening position
        await cache.mark_opening_position("binance", "BTC/USDT", "bot_123")
        
        # ... do trading ...
        
        # Release when done
        await cache.unmark_opening_position("binance", "BTC/USDT")
        await cache.unblock_exchange("binance", "BTC/USDT")
"""

TRADES_CACHE = """
TradesCache API Reference
=========================

Trade queue and status management.

Class: TradesCache()
--------------------

Inherits from: OrdersCache

Public Trade Queue:
    await push_trade_list(symbol: str, exchange: str, trade: Union[Dict, Trade] = {}) -> int
        Push trade to public trade list
        
    await get_trades_list(symbol: str, exchange: str) -> List[Dict[str, Any]]
        Get all trades for symbol/exchange

Trade Status Management:
    await update_trade_status(key: str) -> bool
        Update trade status timestamp
        
    await get_trade_status(key: str) -> Optional[datetime]
        Get trade status timestamp
        
    await get_all_trade_statuses(prefix: str = "TRADE:STATUS") -> Dict[str, datetime]
        Get all trade statuses
        
    await get_trade_status_keys(prefix: str = "TRADE:STATUS") -> List[str]
        Get all trade status keys

User Trade Operations:
    await push_my_trades_list(uid: str, exchange: str, trade: Union[Dict, Trade] = {}) -> int
        Push user's private trade
        
    await pop_my_trade(uid: str, exchange: str, timeout: int = 0) -> Optional[Dict[str, Any]]
        Pop user's trade from queue
        
    await update_user_trade_status(key: str, timestamp: Optional[datetime] = None) -> bool
        Update user trade status
        
    await delete_user_trade_statuses() -> bool
        Delete all user trade statuses

Example:
    cache = TradesCache()
    
    # Push public trade
    await cache.push_trade_list("BTC/USDT", "binance", {
        "id": "trade123",
        "price": 50000,
        "size": 0.1,
        "side": "buy",
        "timestamp": datetime.now(timezone.utc)
    })
    
    # Push user trade
    await cache.push_my_trades_list("user123", "binance", {
        "id": "mytrade456",
        "price": 50100,
        "size": 0.05
    })
    
    # Pop user trade
    trade = await cache.pop_my_trade("user123", "binance", timeout=5)
"""

OHLCV_CACHE = """
OHLCVCache API Reference
========================

Candlestick (OHLCV) data caching.

Class: OHLCVCache()
-------------------

Inherits from: BotCache

OHLCV Operations:
    await update_ohlcv_bars(symbol: str, timeframe: str, 
                           bars: List[List[float]]) -> None
        Update OHLCV bars for symbol/timeframe
        Each bar: [timestamp, open, high, low, close, volume]
        
    await get_latest_ohlcv_bars(symbol: str, timeframe: str, 
                               count: int) -> List[List[float]]
        Get latest N bars for symbol/timeframe

Note: Symbol names have "/" removed for Redis keys (e.g., "BTC/USDT" -> "BTCUSDT")

Timeframes: 
    Common: "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"

Example:
    cache = OHLCVCache()
    
    # Update bars
    bars = [
        [1640000000000, 50000, 50100, 49900, 50050, 100.5],
        [1640000060000, 50050, 50150, 50000, 50100, 95.3],
    ]
    await cache.update_ohlcv_bars("BTC/USDT", "1m", bars)
    
    # Get latest 100 bars
    latest = await cache.get_latest_ohlcv_bars("BTC/USDT", "1m", 100)
    for bar in latest[-5:]:  # Last 5 bars
        print(f"Time: {bar[0]}, Close: {bar[4]}, Volume: {bar[5]}")
"""


def get_all_references() -> dict:
    """Get all API references in a structured format.
    
    Returns:
        Dict mapping cache class names to their API documentation
    """
    return {
        'BaseCache': BASE_CACHE,
        'ProcessCache': PROCESS_CACHE,
        'ExchangeCache': EXCHANGE_CACHE,
        'SymbolCache': SYMBOL_CACHE,
        'TickCache': TICK_CACHE,
        'AccountCache': ACCOUNT_CACHE,
        'OrdersCache': ORDERS_CACHE,
        'BotCache': BOT_CACHE,
        'TradesCache': TRADES_CACHE,
        'OHLCVCache': OHLCV_CACHE,
    }


# Make individual references easily accessible
__all__ = [
    'BASE_CACHE',
    'PROCESS_CACHE', 
    'EXCHANGE_CACHE',
    'SYMBOL_CACHE',
    'TICK_CACHE',
    'ACCOUNT_CACHE',
    'ORDERS_CACHE',
    'BOT_CACHE',
    'TRADES_CACHE',
    'OHLCV_CACHE',
    'get_all_references',
]