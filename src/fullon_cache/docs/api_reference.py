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

Symbol metadata caching with fullon_orm.Symbol model support and auto-refresh from database.

Class: SymbolCache()
--------------------

Note: Does NOT inherit from BaseCache, uses composition instead.

New ORM-Based Methods (Recommended):
    await add_symbol(symbol: Symbol) -> bool
        Add symbol using fullon_orm.Symbol model
        Args:
            symbol: fullon_orm.Symbol model instance
        Returns: True if successful, False otherwise
        
    await update_symbol(symbol: Symbol) -> bool
        Update symbol using fullon_orm.Symbol model
        Args:
            symbol: fullon_orm.Symbol model instance with updates
        Returns: True if successful, False otherwise
        
    await delete_symbol(symbol: Symbol) -> bool
        Delete symbol using fullon_orm.Symbol model
        Args:
            symbol: fullon_orm.Symbol model instance
        Returns: True if successful, False otherwise
        
    await get_symbol_by_model(symbol: Symbol) -> Optional[Symbol]
        Get symbol using fullon_orm.Symbol model as search criteria
        Args:
            symbol: fullon_orm.Symbol model with search criteria
        Returns: fullon_orm.Symbol model or None if not found
        
    await symbol_exists(symbol: Symbol) -> bool
        Check if symbol exists using fullon_orm.Symbol model
        Args:
            symbol: fullon_orm.Symbol model to check
        Returns: True if symbol exists, False otherwise
        
    await get_symbols_for_exchange(symbol: Symbol) -> List[Symbol]
        Get all symbols for the same exchange as the provided symbol
        Args:
            symbol: fullon_orm.Symbol model to identify exchange
        Returns: List of fullon_orm.Symbol models for the same exchange

Legacy Methods (Backward Compatible):
    await get_symbols(exchange: str, loop: int = 0, force: bool = False) -> List[Symbol]
        Get all symbols for an exchange
        - loop: Retry attempts on failure
        - force: Force refresh from database
        
    await get_symbols_by_ex_id(ex_id: int, loop: int = 0, force: bool = False) -> List[Symbol]
        Get symbols by exchange ID
        
    await get_symbol(symbol: str, cat_ex_id: Optional[str] = None,
                    exchange_name: Optional[str] = None, loop: int = 0) -> Optional[Symbol]
        Get specific symbol by name and exchange
        
    await delete_symbol_legacy(symbol: str, cat_ex_id: Optional[str] = None,
                       exchange_name: Optional[str] = None) -> None
        Delete symbol from cache (also removes associated tickers)

Resource Management:
    await close()
        Close connections
        
    async with SymbolCache() as cache:
        Context manager support

Examples:

New ORM-Based Usage (Recommended):
    from fullon_orm.models import Symbol
    
    cache = SymbolCache()
    
    # Create and add symbol with ORM model
    symbol = Symbol(
        symbol="BTC/USDT",
        cat_ex_id=1,
        base="BTC",
        quote="USDT",
        decimals=8,
        updateframe="1h",
        backtest=30,
        futures=False,
        only_ticker=False
    )
    
    success = await cache.add_symbol(symbol)
    if success:
        print("Symbol added successfully")
    
    # Get symbol using ORM model as search criteria
    search_symbol = Symbol(symbol="BTC/USDT", cat_ex_id=1)
    retrieved_symbol = await cache.get_symbol_by_model(search_symbol)
    if retrieved_symbol:
        print(f"Symbol ID: {retrieved_symbol.symbol_id}")
        print(f"Decimals: {retrieved_symbol.decimals}")
        print(f"Base: {retrieved_symbol.base}")
    
    # Check if symbol exists
    exists = await cache.symbol_exists(symbol)
    print(f"Symbol exists: {exists}")
    
    # Update symbol with new data
    symbol.decimals = 10
    symbol.backtest = 60
    success = await cache.update_symbol(symbol)
    if success:
        print("Symbol updated successfully")
    
    # Get all symbols for the same exchange
    exchange_symbols = await cache.get_symbols_for_exchange(symbol)
    print(f"Found {len(exchange_symbols)} symbols on same exchange")
    
    # Delete symbol using ORM model
    success = await cache.delete_symbol(symbol)
    if success:
        print("Symbol deleted successfully")

Legacy Usage (Still Supported):
    async with SymbolCache() as cache:
        # Get all Binance symbols
        symbols = await cache.get_symbols("binance")
        print(f"Found {len(symbols)} symbols")
        
        # Get specific symbol
        btc = await cache.get_symbol("BTC/USDT", exchange_name="binance")
        if btc:
            print(f"Symbol ID: {btc.symbol_id}")
            print(f"Base: {btc.base}, Quote: {btc.quote}")
            print(f"Decimals: {btc.decimals}")
        
        # Get symbols by exchange ID
        symbols_by_id = await cache.get_symbols_by_ex_id(1)
        print(f"Exchange ID 1 has {len(symbols_by_id)} symbols")
        
        # Delete symbol (legacy method)
        await cache.delete_symbol_legacy("BTC/USDT", exchange_name="binance")

fullon_orm.Symbol Model Properties:
    symbol_id: Optional[int]       # Auto-incrementing primary key
    symbol: str                    # Trading pair (e.g., "BTC/USDT")
    cat_ex_id: int                 # Exchange type ID (foreign key)
    base: str                      # Base currency (e.g., "BTC")
    quote: Optional[str]           # Quote currency (e.g., "USDT")
    decimals: int                  # Price decimal precision (default: 8)
    updateframe: str               # OHLCV update timeframe (default: "1h")
    backtest: int                  # Days of historical data (default: 30)
    futures: bool                  # Futures contract flag (default: False)
    only_ticker: bool              # Only collect ticker data (default: False)
    
    # Relationships:
    cat_exchange: Exchange         # The exchange this symbol belongs to
    feeds: List[Feed]              # Strategy feeds using this symbol
    
    # Hybrid properties:
    exchange_name: str             # Exchange name from cat_exchange
    ohlcv_view: str                # OHLCV view definition
    
    # Methods:
    to_dict() -> dict              # Convert to dictionary
    from_dict(data: dict) -> Symbol  # Create from dictionary (class method)

Key Features:
- Auto-refresh from database when symbols not in cache
- 24-hour TTL for cached data
- Automatic ticker cleanup when symbols are deleted
- Exchange name resolution from cat_ex_id
- Type-safe ORM model integration
- Backward compatibility with legacy string-based methods
- Proper error handling and logging
- Redis key patterns:
  - Symbol cache: "symbols_list:{exchange_name}"
  - By exchange ID: "symbols_list:ex_id:{ex_id}"
  - Associated tickers: "tickers:{exchange_name}"
  
Note: Exchange name mapping from cat_ex_id requires proper implementation
in production environments. Current implementation uses fallback mapping.
"""

TICK_CACHE = """
TickCache API Reference
=======================

Real-time ticker data management with fullon_orm.Tick model support.

Class: TickCache()
------------------

Inherits from: SymbolCache

New ORM-Based Methods (Recommended):
    await update_ticker(exchange: str, ticker: Tick) -> bool
        Update ticker using fullon_orm.Tick model
        Args:
            exchange: Exchange name
            ticker: fullon_orm.Tick model instance
        Returns: True if successful, False otherwise
        
    await get_ticker(symbol: str, exchange: str) -> Optional[Tick]
        Get ticker as fullon_orm.Tick model
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            exchange: Exchange name (e.g., "binance")
        Returns: fullon_orm.Tick model or None if not found
        
    await get_price_tick(symbol: str, exchange: Optional[str] = None) -> Optional[Tick]
        Get full tick data (not just price) as fullon_orm.Tick model
        Args:
            symbol: Trading symbol
            exchange: Exchange name (optional, searches all exchanges if None)
        Returns: fullon_orm.Tick model or None if not found

Legacy Methods (Backward Compatible):
    await update_ticker_legacy(symbol: str, exchange: str, data: Dict[str, Any]) -> int
        Update ticker data and publish to subscribers
        
    await get_ticker_legacy(symbol: str, exchange: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]
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

Examples:

New ORM-Based Usage (Recommended):
    from fullon_orm.models import Tick
    import time
    
    cache = TickCache()
    
    # Create and update ticker with ORM model
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
    
    success = await cache.update_ticker("binance", tick)
    if success:
        print("Ticker updated successfully")
    
    # Get ticker as ORM model
    ticker = await cache.get_ticker("BTC/USDT", "binance")
    if ticker:
        print(f"Price: {ticker.price}, Volume: {ticker.volume}")
        print(f"Spread: {ticker.spread}, Spread %: {ticker.spread_percentage}")
    
    # Get price tick from any exchange
    price_tick = await cache.get_price_tick("BTC/USDT")
    if price_tick:
        print(f"Best price: {price_tick.price} on {price_tick.exchange}")

Legacy Usage (Still Supported):
    cache = TickCache()
    
    # Update ticker with dictionary
    await cache.update_ticker_legacy("BTC/USDT", "binance", {
        "price": 50000.0,
        "bid": 49999.0,
        "ask": 50001.0,
        "last": 50000.5,
        "volume": 1234.56,
        "time": "2023-01-01T00:00:00Z"
    })
    
    # Get price
    price = await cache.get_price("BTC/USDT", "binance")
    
    # Get from any exchange  
    any_price = await cache.get_ticker_any("BTC/USDT")
    
    # Get ticker as tuple
    price, timestamp = await cache.get_ticker_legacy("BTC/USDT", "binance")

fullon_orm.Tick Model Properties:
    symbol: str          # Trading pair (e.g., "BTC/USDT")
    exchange: str        # Exchange name (e.g., "binance")
    price: float         # Current price
    volume: float        # Volume at this price level
    time: float          # Unix timestamp
    bid: Optional[float] # Bid price
    ask: Optional[float] # Ask price
    last: Optional[float] # Last traded price
    
    # Computed properties:
    spread: float        # ask - bid (if both available)
    spread_percentage: float # spread / mid_price * 100 (if both available)
    
    # Methods:
    to_dict() -> dict    # Convert to dictionary
    from_dict(data: dict) -> Tick  # Create from dictionary (class method)
"""

ACCOUNT_CACHE = """
AccountCache API Reference
==========================

User account and position management with fullon_orm.Position model support.

Class: AccountCache()
--------------------

Inherits from: TickCache

New ORM-Based Methods (Recommended):
    await upsert_positions(ex_id: int, positions: List[Position], 
                          update_date: bool = False) -> bool
        Upsert positions using fullon_orm.Position models
        Args:
            ex_id: Exchange ID
            positions: List of fullon_orm.Position models
            update_date: If True, only update timestamp for existing positions
        Returns: True if successful, False otherwise
        
    await upsert_position(position: Position) -> bool
        Upsert single position using fullon_orm.Position model
        Args:
            position: fullon_orm.Position model
        Returns: True if successful, False otherwise
        
    await get_position(symbol: str, ex_id: str, latest: bool = False,
                      cur_timestamp: Optional[float] = None) -> Position
        Get position as fullon_orm.Position model
        Args:
            symbol: Trading symbol
            ex_id: Exchange ID
            latest: Whether to wait for latest position (simplified - ignored)
            cur_timestamp: Current timestamp (simplified - ignored)
        Returns: fullon_orm.Position model (empty Position if not found)
        
    await get_all_positions() -> List[Position]
        Get all positions as fullon_orm.Position models
        Returns: List of fullon_orm.Position models across all accounts

Account Management:
    await upsert_user_account(ex_id: int, account: dict = {}, 
                             update_date: str = "") -> bool
        Update or insert account data
        Args:
            ex_id: Exchange ID
            account: Account information dictionary
            update_date: If provided, only update the date field
        Returns: True if successful, False otherwise
        
    await get_full_account(exchange: int, currency: str) -> dict
        Get complete account data for exchange/currency
        Args:
            exchange: Exchange ID
            currency: Base currency
        Returns: Account data for the currency or empty dict
        
    await get_all_accounts() -> dict
        Get all accounts data
        Returns: Dictionary of all account data
        
    await clean_positions() -> int
        Remove all positions from Redis
        Returns: Number of keys deleted (0, 1, or 2)

Legacy Methods (Backward Compatible):
    await upsert_positions_legacy(ex_id: int, positions: Dict[str, Dict[str, float]], 
                                 update_date: bool = False) -> bool
        Legacy method - use upsert_positions() instead
        Args:
            ex_id: Exchange ID
            positions: Positions dict with expected format:
                {symbol: {'cost': float, 'volume': float, 'fee': float, 'price': float, 'timestamp': str}}
            update_date: If True, only update timestamp for existing positions
        Returns: True if successful, False otherwise

Examples:

New ORM-Based Usage (Recommended):
    from fullon_orm.models import Position
    import time
    
    cache = AccountCache()
    
    # Create positions with ORM models
    positions = [
        Position(
            symbol="BTC/USDT",
            cost=25000.0,
            volume=0.5,
            fee=25.0,
            count=1.0,
            price=50000.0,
            timestamp=time.time(),
            ex_id="123",
            side="long"
        ),
        Position(
            symbol="ETH/USDT",
            cost=20000.0,
            volume=10.0,
            fee=20.0,
            count=1.0,
            price=2000.0,
            timestamp=time.time(),
            ex_id="123",
            side="long"
        )
    ]
    
    # Upsert positions with ORM models
    success = await cache.upsert_positions(123, positions)
    if success:
        print("Positions updated successfully")
    
    # Get specific position as ORM model
    position = await cache.get_position("BTC/USDT", "123")
    print(f"BTC position: Volume={position.volume}, Cost={position.cost}")
    print(f"Side: {position.side}, Fee: {position.fee}")
    
    # Upsert single position
    new_position = Position(
        symbol="ADA/USDT",
        cost=1000.0,
        volume=1000.0,
        fee=1.0,
        count=1.0,
        price=1.0,
        timestamp=time.time(),
        ex_id="123",
        side="long"
    )
    success = await cache.upsert_position(new_position)
    print(f"Single position upsert: {success}")
    
    # Get all positions as ORM models
    all_positions = await cache.get_all_positions()
    print(f"Total positions: {len(all_positions)}")
    for pos in all_positions:
        print(f"  {pos.symbol}: Volume={pos.volume}, Cost={pos.cost}")

Legacy Usage (Still Supported):
    cache = AccountCache()
    
    # Update positions with legacy dict format
    positions_dict = {
        "BTC/USDT": {"cost": 25000.0, "volume": 0.5, "fee": 25.0, "price": 50000.0, "timestamp": time.time()},
        "ETH/USDT": {"cost": 20000.0, "volume": 10.0, "fee": 20.0, "price": 2000.0, "timestamp": time.time()}
    }
    
    await cache.upsert_positions_legacy(123, positions_dict)  # Use legacy method for dict format
    
    # Get specific position (always returns Position model)
    position = await cache.get_position("BTC/USDT", "123")
    print(f"Volume: {position.volume}, Cost: {position.cost}")
    
    # Account operations
    account_data = {
        "balance": 10000.0,
        "equity": 12000.0,
        "margin": 2000.0
    }
    await cache.upsert_user_account(123, account_data)

fullon_orm.Position Model Properties:
    symbol: str                    # Trading pair (e.g., "BTC/USDT")
    cost: float                    # Total cost of position
    volume: float                  # Position volume/size
    fee: float                     # Trading fees paid
    count: Optional[float]         # Position count (optional for backward compatibility)
    price: float                   # Average position price
    timestamp: float               # Position timestamp
    ex_id: str                     # Exchange ID
    side: Optional[str]            # Position side ("long", "short")
    realized_pnl: Optional[float]  # Realized profit/loss
    unrealized_pnl: Optional[float] # Unrealized profit/loss
    
    # Methods:
    to_dict() -> dict              # Convert to dictionary
    from_dict(data: dict) -> Position  # Create from dictionary (class method)

Key Features:
- Union type support: accepts both Position models and legacy dicts
- Always returns Position models for type safety
- Automatic timestamp management with UTC timezone
- Flexible validation (count field optional for backward compatibility)
- Full backward compatibility with existing code
- Proper error handling and logging
- Redis key patterns:
  - Positions: "account_positions" (hash with ex_id as key)
  - Accounts: "accounts" (hash with ex_id as key)

Note: The upsert_positions() method now only accepts List[Position] for type safety.
Use upsert_positions_legacy() for the old dict format or convert dicts to Position models.
"""

ORDERS_CACHE = """
OrdersCache API Reference
=========================

Order queue and status management with fullon_orm.Order model support.

Class: OrdersCache()
--------------------

Inherits from: AccountCache

New ORM-Based Methods (Recommended):
    await save_order(exchange: str, order: Order) -> bool
        Save order using fullon_orm.Order model
        Args:
            exchange: Exchange name
            order: fullon_orm.Order model instance
        Returns: True if successful, False otherwise
        
    await update_order(exchange: str, order: Order) -> bool
        Update existing order with new data
        Args:
            exchange: Exchange name
            order: fullon_orm.Order model with updates
        Returns: True if successful, False otherwise
        
    await get_order(exchange: str, order_id: str) -> Optional[Order]
        Get order as fullon_orm.Order model
        Args:
            exchange: Exchange name
            order_id: Order ID (ex_order_id or order_id)
        Returns: fullon_orm.Order model or None if not found

Legacy Methods (Backward Compatible):
    await save_order_data(ex_id: str, oid: str, data: Dict = {}) -> None
        Save order data with automatic expiration
        
    await get_order_status(ex_id: str, oid: str) -> Optional[Order]
        Get order status and data
        
    await get_orders(ex_id: str) -> List[Order]
        Get all orders for an exchange

Order Queue Operations:
    await push_open_order(oid: str, local_oid: str) -> None
        Push order ID pair to processing queue
        
    await pop_open_order(oid: str) -> Optional[str]
        Pop local order ID for given order ID

Account Data:
    await get_full_accounts(ex_id: str) -> Optional[Any]
        Get full account data (inherited)

Examples:

New ORM-Based Usage (Recommended):
    from fullon_orm.models import Order
    
    cache = OrdersCache()
    
    # Create and save order with ORM model
    order = Order(
        ex_order_id="EX_12345",
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        volume=0.1,
        price=50000.0,
        status="open",
        order_type="limit",
        bot_id=123,
        uid=456,
        ex_id=789
    )
    
    success = await cache.save_order(exchange="binance", order=order)
    if success:
        print("Order saved successfully")
    
    # Get order as ORM model
    retrieved_order = await cache.get_order("binance", "EX_12345")
    if retrieved_order:
        print(f"Order status: {retrieved_order.status}")
        print(f"Volume: {retrieved_order.volume}")
    
    # Update order with partial data
    update_order = Order(
        ex_order_id="EX_12345",
        status="filled",
        final_volume=0.095
    )
    
    success = await cache.update_order("binance", update_order)
    if success:
        print("Order updated successfully")

Legacy Usage (Still Supported):
    cache = OrdersCache()
    
    # Queue order for processing
    await cache.push_open_order("order123", "local456")
    
    # Save order data
    await cache.save_order_data("binance", "order123", {
        "symbol": "BTC/USDT",
        "side": "buy",
        "volume": 0.1,
        "price": 50000,
        "status": "open"
    })
    
    # Check order status
    order = await cache.get_order_status("binance", "order123")
    if order:
        print(f"Order status: {order.status}")
        print(f"Ex Order ID: {order.ex_order_id}")

fullon_orm.Order Model Properties:
    order_id: Optional[int]        # Internal order ID
    ex_order_id: Optional[str]     # Exchange order ID
    exchange: Optional[str]        # Exchange name
    symbol: Optional[str]          # Trading pair
    side: Optional[str]            # 'buy' or 'sell'
    order_type: Optional[str]      # 'limit', 'market', etc.
    volume: Optional[float]        # Order volume
    final_volume: Optional[float]  # Filled volume
    price: Optional[float]         # Order price
    status: Optional[str]          # 'open', 'filled', 'canceled', etc.
    timestamp: Optional[datetime]  # Order timestamp
    bot_id: Optional[int]          # Bot ID that created order
    uid: Optional[int]             # User ID
    ex_id: Optional[int]           # Exchange account ID
    cat_ex_id: Optional[int]       # Catalog exchange ID
    command: Optional[str]         # Trading command
    reason: Optional[str]          # Order reason
    futures: Optional[bool]        # Futures order flag
    leverage: Optional[float]      # Leverage amount
    tick: Optional[float]          # Tick size
    plimit: Optional[float]        # Price limit
    
    # Methods:
    to_dict() -> dict             # Convert to dictionary
    from_dict(data: dict) -> Order  # Create from dictionary (class method)

Key Features:
- Automatic TTL for cancelled orders (1 hour)
- Backward compatibility with legacy methods
- Type-safe ORM model integration
- Proper error handling and logging
- Redis key pattern: order_status:{exchange}
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

Trade queue and status management with fullon_orm.Trade model support.

Class: TradesCache()
--------------------

Inherits from: OrdersCache (inherits all methods from AccountCache, TickCache, etc.)

New ORM-Based Methods (Recommended):
    await push_trade(exchange: str, trade: Trade) -> bool
        Push trade using fullon_orm.Trade model
        Args:
            exchange: Exchange name
            trade: fullon_orm.Trade model instance
        Returns: True if successful, False otherwise
        
    await get_trades(symbol: str, exchange: str) -> List[Trade]
        Get all trades as fullon_orm.Trade models (destructive read)
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            exchange: Exchange name (e.g., "binance")
        Returns: List of fullon_orm.Trade models
        Note: This method removes all trades from the queue
        
    await push_user_trade(uid: str, exchange: str, trade: Trade) -> bool
        Push user trade using fullon_orm.Trade model
        Args:
            uid: User ID
            exchange: Exchange name
            trade: fullon_orm.Trade model instance
        Returns: True if successful, False otherwise
        
    await pop_user_trade(uid: str, exchange: str, timeout: int = 0) -> Optional[Trade]
        Pop user trade as fullon_orm.Trade model
        Args:
            uid: User ID
            exchange: Exchange name
            timeout: Blocking timeout in seconds (0 for non-blocking)
        Returns: fullon_orm.Trade model or None if not found

Legacy Methods (Backward Compatible):
    await push_trade_list(symbol: str, exchange: str, trade: Union[Dict, Trade] = {}) -> int
        Push trade to trade list (accepts Trade model or dict)
        
    await get_trades_list(symbol: str, exchange: str) -> List[Dict[str, Any]]
        Get all trades as dictionaries (destructive read)
        
    await push_my_trades_list(uid: str, exchange: str, trade: Union[Dict, Trade] = {}) -> int
        Push user trade (accepts Trade model or dict)
        
    await pop_my_trade(uid: str, exchange: str, timeout: int = 0) -> Optional[Dict[str, Any]]
        Pop user trade as dictionary

Trade Status Management:
    await update_trade_status(key: str) -> bool
        Update trade status timestamp
        
    await get_trade_status(key: str) -> Optional[datetime]
        Get trade status timestamp
        
    await get_all_trade_statuses(prefix: str = "TRADE:STATUS") -> Dict[str, datetime]
        Get all trade statuses
        
    await get_trade_status_keys(prefix: str = "TRADE:STATUS") -> List[str]
        Get all trade status keys

User Trade Status:
    await update_user_trade_status(key: str, timestamp: Optional[datetime] = None) -> bool
        Update user trade status
        
    await delete_user_trade_statuses() -> bool
        Delete all user trade statuses

Examples:

New ORM-Based Usage (Recommended):
    from fullon_orm.models import Trade
    from datetime import datetime, timezone
    
    cache = TradesCache()
    
    # Create and push trade with ORM model
    trade = Trade(
        trade_id=12345,
        ex_trade_id="EX_TRD_001",
        ex_order_id="EX_ORD_001",
        uid=1,
        ex_id=1,
        symbol="BTC/USDT",
        order_type="limit",
        side="buy",
        volume=0.1,
        price=50000.0,
        cost=5000.0,
        fee=5.0,
        time=datetime.now(timezone.utc)
    )
    
    success = await cache.push_trade("binance", trade)
    if success:
        print("Trade pushed successfully")
    
    # Get all trades as ORM models (destructive read)
    trades = await cache.get_trades("BTC/USDT", "binance")
    print(f"Retrieved {len(trades)} trades")
    for t in trades:
        print(f"Trade {t.trade_id}: {t.side} {t.volume} @ ${t.price}")
    
    # User trade operations
    user_trade = Trade(
        trade_id=67890,
        ex_trade_id="USER_TRD_001",
        symbol="ETH/USDT",
        side="sell",
        volume=1.0,
        price=3000.0,
        cost=3000.0,
        fee=3.0,
        time=datetime.now(timezone.utc)
    )
    
    # Push user trade
    success = await cache.push_user_trade("123", "binance", user_trade)
    
    # Pop user trade (blocking for 5 seconds)
    popped_trade = await cache.pop_user_trade("123", "binance", timeout=5)
    if popped_trade:
        print(f"Popped trade: {popped_trade.symbol} {popped_trade.side}")

Legacy Usage (Still Supported):
    cache = TradesCache()
    
    # Push trade with dictionary
    trade_data = {
        "trade_id": 12345,
        "symbol": "BTC/USDT",
        "side": "buy",
        "volume": 0.1,
        "price": 50000.0,
        "cost": 5000.0,
        "fee": 5.0
    }
    
    result = await cache.push_trade_list("BTC/USDT", "binance", trade_data)
    print(f"Push result: {result}")
    
    # Get trades as dictionaries
    trade_dicts = await cache.get_trades_list("BTC/USDT", "binance")
    for td in trade_dicts:
        print(f"Trade {td.get('trade_id')}: {td.get('side')} {td.get('volume')}")
    
    # User trade operations
    user_trade_data = {
        "trade_id": 22222,
        "symbol": "ADA/USDT",
        "side": "buy",
        "volume": 1000.0,
        "price": 0.5
    }
    
    result = await cache.push_my_trades_list("456", "binance", user_trade_data)
    popped_data = await cache.pop_my_trade("456", "binance")
    
    # Status operations
    await cache.update_trade_status("binance")
    status = await cache.get_trade_status("binance")

fullon_orm.Trade Model Properties:
    trade_id: Optional[int]        # Internal trade ID
    ex_trade_id: Optional[str]     # Exchange trade ID
    ex_order_id: Optional[str]     # Exchange order ID
    uid: Optional[int]             # User ID
    ex_id: Optional[int]           # Exchange account ID
    symbol: Optional[str]          # Trading pair (e.g., "BTC/USDT")
    order_type: Optional[str]      # Order type that generated this trade
    side: Optional[str]            # 'buy' or 'sell'
    volume: Optional[float]        # Trade volume
    price: Optional[float]         # Trade price
    cost: Optional[float]          # Total cost (volume * price)
    fee: Optional[float]           # Trading fee
    cur_volume: Optional[float]    # Current cumulative volume
    cur_avg_price: Optional[float] # Current average price
    cur_avg_cost: Optional[float]  # Current average cost
    cur_fee: Optional[float]       # Current cumulative fee
    roi: Optional[float]           # Return on investment
    roi_pct: Optional[float]       # ROI percentage
    total_fee: Optional[float]     # Total fees paid
    leverage: Optional[float]      # Leverage used
    time: Optional[datetime]       # Trade timestamp
    
    # Methods:
    to_dict() -> dict             # Convert to dictionary
    from_dict(data: dict) -> Trade  # Create from dictionary (class method)

Key Features:
- Automatic symbol normalization (removes "/" for Redis keys)
- FIFO trade queues using Redis lists
- Destructive read operations (get operations clear the queue)
- User-specific trade queues for personalized data
- Trade status timestamp tracking
- Backward compatibility with legacy dict-based methods
- Type-safe ORM model integration
- Proper error handling and logging
- Redis key patterns:
  - Public trades: "trades:{exchange}:{normalized_symbol}"
  - User trades: "user_trades:{uid}:{exchange}"
  - Trade status: "TRADE:STATUS:{key}"
  - User trade status: "USER_TRADE:STATUS:{key}"
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
