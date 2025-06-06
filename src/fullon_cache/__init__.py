"""Fullon Cache - High-Performance Redis Caching for Crypto Trading

This library provides a comprehensive caching system designed specifically for cryptocurrency
trading operations. It uses Redis for storing real-time market data, order information,
bot states, and more.

Quick Start:
-----------
    # Basic ticker caching
    from fullon_cache import TickCache
    
    cache = TickCache()
    await cache.update_ticker("BTC/USDT", "binance", ticker_data)
    price, timestamp = await cache.get_ticker("BTC/USDT", "binance")
    
    # Order queue management  
    from fullon_cache import OrdersCache
    
    orders = OrdersCache()
    await orders.push_open_order("order_id", "local_id")
    await orders.save_order_data("binance", "order_id", order_data)
    
    # Real-time ticker subscription
    from fullon_cache import BaseCache
    base = BaseCache()
    async for msg in base.subscribe("tickers:binance:BTC/USDT"):
        print(f"New ticker: {msg['data']}")

Key Features:
------------
- **Async/Await**: Fully asynchronous operations using redis-py
- **Real-time Data**: Pub/Sub for ticker updates, Streams for queues
- **ORM Integration**: Direct use of fullon_orm models
- **Auto-Discovery**: Self-documenting with examples and guides
- **High Performance**: Connection pooling, pipelining, efficient serialization
- **Battle-Tested**: 100% test coverage with parallel test support

Cache Modules:
-------------
- BaseCache: Core Redis operations and connection management
- ProcessCache: System process monitoring and tracking
- ExchangeCache: Exchange metadata and configuration
- SymbolCache: Trading symbol information
- TickCache: Real-time ticker data with pub/sub
- AccountCache: User accounts and positions
- OrdersCache: Order queue management with streams
- BotCache: Bot coordination and exchange blocking
- TradesCache: Trade data queuing and processing
- OHLCVCache: Candlestick/bar data storage

Configuration:
-------------
Uses .env files for all configuration:
    
    # .env file
    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_DB=0
    REDIS_PASSWORD=optional
    
    # Connection pool
    REDIS_MAX_CONNECTIONS=50
    REDIS_SOCKET_TIMEOUT=5

Documentation:
-------------
    # Access comprehensive guides
    from fullon_cache.docs import quickstart, api_reference
    print(quickstart.GUIDE)
    
    # Run examples
    from fullon_cache.examples import basic_usage
    await basic_usage.main()
    
    # Get help on any module
    from fullon_cache import TickCache
    help(TickCache)

Performance Tips:
----------------
1. Use pipelining for bulk operations
2. Enable connection pooling (default)
3. Use msgpack for complex data serialization
4. Monitor memory usage with INFO commands
5. Use Redis Cluster for horizontal scaling

Error Handling:
--------------
All cache operations handle Redis connection errors gracefully:
- Automatic reconnection with exponential backoff
- Circuit breaker pattern for failing Redis
- Detailed logging for debugging
- Graceful degradation on cache miss

For more information:
- Documentation: from fullon_cache.docs import quickstart, api_reference
- Examples: from fullon_cache.examples import basic_usage, bot_coordination
- All docs: from fullon_cache.docs import get_all_docs
"""

__version__ = "0.1.0"
__author__ = "Fullon Project"
__all__ = [
    # Core
    "BaseCache",
    # Cache modules  
    "ProcessCache",
    "ExchangeCache", 
    "SymbolCache",
    "TickCache",
    "AccountCache",
    "OrdersCache",
    "BotCache",
    "TradesCache",
    "OHLCVCache",
    # Utilities
    "CacheError",
    "ConnectionError", 
    "SerializationError",
    "StreamError",
    "ConnectionPool",
    # Documentation
    "docs",
    "examples",
]

# Import all cache modules for easy access
from .base_cache import BaseCache
from .process_cache import ProcessCache
from .exchange_cache import ExchangeCache
from .symbol_cache import SymbolCache
from .tick_cache import TickCache
from .account_cache import AccountCache
from .orders_cache import OrdersCache
from .bot_cache import BotCache
from .trades_cache import TradesCache
from .ohlcv_cache import OHLCVCache

# Exceptions
from .exceptions import CacheError, ConnectionError, SerializationError, StreamError

# Connection pool
from .connection import ConnectionPool

# Make docs and examples available
from . import docs, examples