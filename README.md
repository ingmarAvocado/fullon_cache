# Fullon Cache

A high-performance Redis-based caching system for cryptocurrency trading operations.

## Overview

This library provides a hierarchical caching system designed specifically for crypto trading bots and services. It uses Redis for storing real-time market data, order information, bot states, and more.

## Features

- **Real-time ticker data** with pub/sub support
- **Order queue management** with FIFO operations
- **Bot coordination** with exchange blocking mechanisms
- **Account and position tracking**
- **OHLCV data caching** for technical analysis
- **Process monitoring** for system health
- **Async/await support** throughout

## Installation

```bash
poetry add git+ssh://git@github.com/ingmarAvocado/fullon_cache.git
```

## Quick Start

```python
import asyncio
from fullon_cache import TickCache, OrdersCache

async def main():
    # Initialize caches
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    
    # Update ticker data
    await tick_cache.update_ticker("binance", "BTC/USDT", {
        "bid": 50000.0,
        "ask": 50001.0,
        "last": 50000.5,
        "timestamp": "2024-01-01T00:00:00Z"
    })
    
    # Get ticker data
    ticker = await tick_cache.get_ticker("binance", "BTC/USDT")
    print(f"BTC price: {ticker.last}")
    
    # Push order to queue
    await orders_cache.push_open_order({
        "order_id": "12345",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.1,
        "price": 49000
    })
    
    # Pop order from queue
    order = await orders_cache.pop_open_order("binance", timeout=5)
    if order:
        print(f"Processing order: {order.order_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture

The cache system follows a hierarchical inheritance pattern where each cache module extends the functionality of its parent:

- `BaseCache` - Redis connection management
- `ProcessCache` - Process monitoring
- `ExchangeCache` - Exchange metadata
- `SymbolCache` - Symbol information
- `TickCache` - Real-time ticker data
- `AccountCache` - Account and positions
- `OrdersCache` - Order management
- `BotCache` - Bot coordination
- `TradesCache` - Trade data
- `OHLCVCache` - Candlestick data

## Development

### Setup

```bash
# Clone the repository
git clone git@github.com:ingmarAvocado/fullon_cache.git
cd fullon_cache

# Install dependencies
poetry install

# Run tests
poetry run pytest -xvs

# Run linting
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/

# Run type checking
poetry run mypy src/ tests/
```

### Testing

Tests are designed to run in parallel without mocking (except for extreme cases):

```bash
# Run all tests in parallel
poetry run pytest -n auto

# Run specific test file
poetry run pytest tests/test_tick_cache.py -xvs

# Run with coverage
poetry run pytest --cov=fullon_cache --cov-report=html
```

## Configuration

This library uses `.env` files for all configuration. Create a `.env` file in your project root:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # Optional

# Connection Pool Settings
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Cache TTL Settings (in seconds)
CACHE_TTL_EXCHANGE=86400  # 24 hours
CACHE_TTL_SYMBOL=86400    # 24 hours
CACHE_TTL_ORDER=3600      # 1 hour for cancelled orders
```

The library automatically loads the `.env` file when imported. No additional configuration files or settings modules are needed.

## License

MIT License - see LICENSE file for details.