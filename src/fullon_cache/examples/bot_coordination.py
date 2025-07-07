"""Bot coordination examples for Fullon Cache.

This module demonstrates how multiple bots can coordinate to avoid
conflicts when trading the same symbols on exchanges.
"""

EXAMPLE = '''
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

from fullon_cache import BotCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def simulate_bot(bot_id: str, exchange: str, symbols: List[str], cache: BotCache):
    """Simulate a bot trying to trade multiple symbols."""
    logger.info(f"Bot {bot_id} starting on {exchange}")
    
    traded_symbols = []
    
    for symbol in symbols:
        # Check if symbol is blocked by another bot
        blocker = await cache.is_blocked(exchange, symbol)
        
        if blocker:
            logger.warning(f"Bot {bot_id}: {symbol} is blocked by {blocker}")
            continue
            
        # Try to block the symbol for exclusive access
        if await cache.block_exchange(exchange, symbol, bot_id):
            logger.info(f"Bot {bot_id}: Successfully blocked {symbol}")
            
            # Mark that we're opening a position
            await cache.mark_opening_position(exchange, symbol, bot_id)
            
            # Simulate trading
            logger.info(f"Bot {bot_id}: Trading {symbol}...")
            await asyncio.sleep(2)  # Simulate order placement
            
            # Clear opening position state
            await cache.unmark_opening_position(exchange, symbol)
            
            traded_symbols.append(symbol)
            
            # In real usage, you might keep the block until position is closed
            # For demo, we'll release it after a delay
            await asyncio.sleep(3)
            await cache.unblock_exchange(exchange, symbol)
            logger.info(f"Bot {bot_id}: Released {symbol}")
        else:
            logger.warning(f"Bot {bot_id}: Failed to block {symbol}")
    
    # Update bot status
    await cache.update_bot(bot_id, {
        "status": "completed",
        "traded_symbols": ",".join(traded_symbols),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return traded_symbols


async def monitor_blocks(cache: BotCache, duration: int = 10):
    """Monitor active blocks for a duration."""
    logger.info("Starting block monitor...")
    
    end_time = asyncio.get_event_loop().time() + duration
    
    while asyncio.get_event_loop().time() < end_time:
        blocks = await cache.get_blocks()
        
        if blocks:
            logger.info("Current blocks:")
            for block in blocks:
                logger.info(f"  - {block['exchange']}:{block['symbol']} -> Bot {block['bot_id']}")
        else:
            logger.info("No active blocks")
            
        await asyncio.sleep(2)


async def check_position_opening_states(cache: BotCache, exchange: str, symbols: List[str]):
    """Check if any positions are being opened."""
    logger.info("\\nChecking position opening states...")
    
    for symbol in symbols:
        is_opening = await cache.is_opening_position(exchange, symbol)
        if is_opening:
            logger.info(f"{symbol}: Position is being opened")
        else:
            logger.info(f"{symbol}: No position opening")


async def main():
    """Run bot coordination examples."""
    print("Fullon Cache Bot Coordination Examples")
    print("=====================================")
    
    cache = BotCache()
    
    try:
        # Symbols to trade
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        exchange = "binance"
        
        # Start monitor task
        monitor_task = asyncio.create_task(
            monitor_blocks(cache, duration=15)
        )
        
        # Simulate multiple bots trying to trade same symbols
        bot_tasks = [
            asyncio.create_task(
                simulate_bot(f"bot_{i}", exchange, symbols, cache)
            )
            for i in range(3)
        ]
        
        # Wait a bit then check position states
        await asyncio.sleep(3)
        await check_position_opening_states(cache, exchange, symbols)
        
        # Wait for all bots to complete
        results = await asyncio.gather(*bot_tasks)
        
        # Show results
        print("\\nTrading Results:")
        for i, traded in enumerate(results):
            print(f"Bot {i}: Traded {len(traded)} symbols: {traded}")
        
        # Get final bot statuses
        await monitor_task
        
        print("\\nFinal Bot Statuses:")
        bot_statuses = await cache.get_bots()
        for bot_id, status in bot_statuses.items():
            print(f"{bot_id}: {status}")
            
    finally:
        # Cleanup
        await cache.del_status()
        await cache.close()


if __name__ == "__main__":
    asyncio.run(main())
'''

# Make the example runnable when imported
async def main():
    """Execute the bot coordination examples."""
    exec_globals = {}
    exec(EXAMPLE, exec_globals)
    await exec_globals['main']()

__all__ = ['EXAMPLE', 'main']
