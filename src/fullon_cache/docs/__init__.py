"""Documentation module for Fullon Cache.

This module contains documentation strings and guides for using the cache system.
"""

# Placeholder documentation - should be implemented later
QUICKSTART = """
# Fullon Cache Quickstart Guide

## Installation
```bash
pip install fullon-cache[uvloop]
```

## Basic Usage
```python
import asyncio
from fullon_cache import TickCache
from fullon_orm.models import Tick, Symbol

async def main():
    cache = TickCache()
    
    # Create symbol and tick
    symbol = Symbol(symbol="BTC/USDT", cat_ex_id=1, base="BTC", quote="USDT")
    tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0, volume=100.0, time=time.time())
    
    # Store and retrieve
    await cache.set_ticker(symbol, tick)
    result = await cache.get_ticker(symbol)
    
    await cache.close()

if __name__ == "__main__":
    asyncio.run(main())
```
"""

def get_all_docs():
    """Get all available documentation."""
    return {
        'quickstart': QUICKSTART,
    }

__all__ = ['QUICKSTART', 'get_all_docs']