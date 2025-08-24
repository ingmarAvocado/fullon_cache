"""Documentation module for fullon_cache.

This module provides comprehensive documentation for the fullon_cache library,
including quick start guides, API references, and usage examples.
"""

QUICKSTART = """
# Fullon Cache Quick Start Guide

## Installation

The fullon_cache library is designed to be used as part of the fullon trading system.
Install it using poetry:

```bash
poetry install
```

## Basic Usage

All cache classes support async context managers for automatic resource cleanup:

```python
from fullon_cache import TickCache

# Recommended: use context manager for automatic cleanup
async with TickCache() as cache:
    await cache.update_ticker("binance", "BTC/USDT", {
        "symbol": "BTC/USDT", 
        "last": 50000.0,
        "bid": 49950.0,
        "ask": 50050.0
    })
    
    ticker = await cache.get_ticker("binance", "BTC/USDT")
    print(f"BTC/USDT: ${ticker['last']}")

# Manual resource management (if needed)
cache = TickCache()
try:
    await cache.update_ticker("binance", "BTC/USDT", {...})
finally:
    await cache.close()
```

## Available Cache Classes

- BaseCache: Foundation class with Redis operations
- TickCache: Real-time ticker data with pub/sub
- AccountCache: User positions and account data
- OrdersCache: Order queue management
- TradesCache: Trade data queuing
- BotCache: Bot coordination and blocking
- ProcessCache: Process monitoring
- OHLCVCache: Candlestick data storage

## Key Features

- 100% async/await support
- Context manager support for automatic cleanup
- Redis-backed with connection pooling
- fullon_orm integration for type safety
- Comprehensive error handling
- Structured logging with fullon-log
- Parallel testing support
"""

API_REFERENCE = """
# API Reference

For detailed API documentation, use Python's built-in help system:

```python
from fullon_cache import TickCache
help(TickCache)
```

Each cache class has comprehensive docstrings with examples.
"""

def get_all_docs() -> dict[str, str]:
    """Get all available documentation.
    
    Returns:
        Dict mapping doc names to content
    """
    return {
        "QUICKSTART": QUICKSTART,
        "API_REFERENCE": API_REFERENCE,
    }