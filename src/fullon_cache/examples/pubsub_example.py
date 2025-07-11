"""Pub/Sub examples for Fullon Cache.

This module demonstrates real-time ticker updates using Redis pub/sub.
"""

EXAMPLE = '''
import asyncio
import logging
from datetime import datetime, timezone
import random
import time
from typing import Dict, Any

from fullon_cache import TickCache, BaseCache
from fullon_orm.models import Tick

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ticker_publisher(cache: TickCache, exchange: str, symbols: list, duration: int = 10):
    """Simulate ticker updates being published."""
    logger.info(f"Starting ticker publisher for {exchange}")
    
    end_time = asyncio.get_event_loop().time() + duration
    
    while asyncio.get_event_loop().time() < end_time:
        for symbol in symbols:
            # Generate random price data
            base_price = 50000 if symbol == "BTC/USDT" else 3000
            price = base_price + random.uniform(-100, 100)
            
            # Create ticker using fullon_orm.Tick model
            tick = Tick(
                symbol=symbol,
                exchange=exchange,
                price=price,
                volume=random.uniform(100, 1000),
                time=time.time(),
                bid=price - 0.5,
                ask=price + 0.5,
                last=price
            )
            
            # Update ticker (this also publishes to subscribers)
            await cache.update_ticker(exchange, tick)
            
        await asyncio.sleep(1)  # Update every second
    
    logger.info(f"Publisher for {exchange} finished")


async def ticker_subscriber(base_cache: BaseCache, channel: str, duration: int = 10):
    """Subscribe to ticker updates."""
    logger.info(f"Starting subscriber for channel: {channel}")
    
    try:
        # Subscribe to channel
        async for message in base_cache.subscribe(channel):
            # Message format: {'type': 'message', 'channel': 'channel_name', 'data': 'message_data'}
            if message['type'] == 'message':
                logger.info(f"Received on {message['channel']}: {message['data']}")
                
            # Check if we should stop
            if asyncio.get_event_loop().time() > asyncio.get_event_loop().time() + duration:
                break
                
    except asyncio.CancelledError:
        logger.info(f"Subscriber for {channel} cancelled")
        raise
    except Exception as e:
        logger.error(f"Subscriber error: {e}")


async def price_monitor(cache: TickCache, symbols: list, interval: int = 2):
    """Monitor prices using direct cache access."""
    logger.info("Starting price monitor")
    
    for _ in range(5):  # Check 5 times
        print("\\n--- Current Prices ---")
        for symbol in symbols:
            # Get price from any exchange
            price = await cache.get_price(symbol)
            if price > 0:
                print(f"{symbol}: ${price:,.2f}")
            else:
                print(f"{symbol}: No price available")
                
            # Also demonstrate getting full ticker as ORM model
            ticker = await cache.get_ticker(symbol, "binance")
            if ticker:
                print(f"  Full ticker: Bid=${ticker.bid:.2f}, Ask=${ticker.ask:.2f}, Volume={ticker.volume:.2f}")
                
        await asyncio.sleep(interval)


async def advanced_pubsub_example():
    """Demonstrate advanced pub/sub patterns."""
    tick_cache = TickCache()
    base_cache = BaseCache()
    
    try:
        # Channels to use
        channels = [
            "tickers:binance:*",  # All Binance tickers
            "tickers:kraken:BTC/USDT",  # Specific ticker
        ]
        
        # Start multiple subscribers
        subscriber_tasks = []
        for channel in channels:
            task = asyncio.create_task(
                ticker_subscriber(base_cache, channel, duration=15)
            )
            subscriber_tasks.append(task)
        
        # Give subscribers time to connect
        await asyncio.sleep(0.5)
        
        # Start publishers
        publisher_tasks = [
            asyncio.create_task(
                ticker_publisher(tick_cache, "binance", ["BTC/USDT", "ETH/USDT"], duration=10)
            ),
            asyncio.create_task(
                ticker_publisher(tick_cache, "kraken", ["BTC/USDT"], duration=10)
            ),
        ]
        
        # Wait for publishers to finish
        await asyncio.gather(*publisher_tasks)
        
        # Cancel subscribers
        for task in subscriber_tasks:
            task.cancel()
            
        # Wait for cleanup
        await asyncio.gather(*subscriber_tasks, return_exceptions=True)
        
    finally:
        await tick_cache.close()
        await base_cache.close()


async def main():
    """Run pub/sub examples."""
    print("Fullon Cache Pub/Sub Examples")
    print("=============================")
    
    tick_cache = TickCache()
    
    try:
        # Basic example: publish and monitor
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        # Start publisher and monitor concurrently
        await asyncio.gather(
            ticker_publisher(tick_cache, "binance", symbols, duration=10),
            price_monitor(tick_cache, symbols, interval=2)
        )
        
        print("\\n--- Advanced Pub/Sub Example ---")
        await advanced_pubsub_example()
        
    finally:
        await tick_cache.close()
    
    print("\\nPub/Sub examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
'''

# Make the example runnable when imported
async def main():
    """Execute the pub/sub examples."""
    exec_globals = {}
    exec(EXAMPLE, exec_globals)
    await exec_globals['main']()

__all__ = ['EXAMPLE', 'main']
