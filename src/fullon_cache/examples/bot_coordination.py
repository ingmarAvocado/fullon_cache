#!/usr/bin/env python3
"""
Multi-Bot Coordination Demo Tool

This tool demonstrates how multiple bots can coordinate to avoid conflicts
when trading the same symbols on exchanges.

Features:
- Multi-bot coordination with real-time status updates
- Exchange blocking visualization and conflict resolution
- Beautiful output with emojis and status indicators
- Configurable bot count and simulation duration
- Trading conflict prevention demonstration

Usage:
    python bot_coordination.py --bots 3 --symbols BTC/USDT,ETH/USDT --duration 30
    python bot_coordination.py --bots 5 --duration 60 --verbose
    python bot_coordination.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import BotCache
except ImportError:
    from ..bot_cache import BotCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.bot_coordination")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with BotCache() as cache:
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def simulate_bot(bot_id: int, symbols: List[str], duration: int, verbose: bool = False) -> Dict[str, Any]:
    """Simulate a bot trying to trade various symbols."""
    print(f"🤖 Starting Bot {bot_id}")
    
    stats = {
        "successful_blocks": 0,
        "blocked_attempts": 0,
        "trades_executed": 0
    }
    
    start_time = time.time()
    end_time = start_time + duration
    
    try:
        async with BotCache() as bot_cache:
            while time.time() < end_time:
                symbol = random.choice(symbols)
                exchange = "binance"
                
                # Try to block the exchange for trading
                can_trade = await bot_cache.can_bot_trade(bot_id, exchange, symbol)
                
                if can_trade:
                    # Successfully got permission to trade
                    await bot_cache.set_exchange_blocked(exchange, symbol, bot_id)
                    stats["successful_blocks"] += 1
                    
                    if verbose:
                        print(f"   🟢 Bot {bot_id}: Acquired {exchange}:{symbol}")
                    
                    # Simulate trading time
                    trade_duration = random.uniform(1, 3)
                    await asyncio.sleep(trade_duration)
                    
                    # Execute trade and release
                    stats["trades_executed"] += 1
                    await bot_cache.release_exchange_block(exchange, symbol)
                    
                    if verbose:
                        print(f"   ✅ Bot {bot_id}: Completed trade on {symbol}")
                        
                else:
                    stats["blocked_attempts"] += 1
                    if verbose:
                        print(f"   🔴 Bot {bot_id}: Blocked from {symbol} (another bot trading)")
                
                # Wait before next attempt
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        print(f"✅ Bot {bot_id} completed: {stats['trades_executed']} trades, "
              f"{stats['blocked_attempts']} blocks")
        return stats
        
    except Exception as e:
        print(f"❌ Bot {bot_id} failed: {e}")
        return stats


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache Multi-Bot Coordination Demo")
    print("===========================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    symbols = args.symbols.split(',')
    symbols = [s.strip() for s in symbols]
    
    print(f"\n🔄 Starting {args.bots} bots for {args.duration}s")
    print(f"📊 Symbols: {', '.join(symbols)}")
    
    start_time = time.time()
    
    # Start all bots
    bot_tasks = []
    for bot_id in range(1, args.bots + 1):
        task = asyncio.create_task(
            simulate_bot(bot_id, symbols, args.duration, args.verbose)
        )
        bot_tasks.append(task)
    
    # Wait for all bots to complete
    results = await asyncio.gather(*bot_tasks, return_exceptions=True)
    
    elapsed = time.time() - start_time
    
    # Compile statistics
    total_trades = 0
    total_blocks = 0
    total_successful = 0
    
    for i, result in enumerate(results):
        if isinstance(result, dict):
            total_trades += result["trades_executed"]
            total_blocks += result["blocked_attempts"]
            total_successful += result["successful_blocks"]
        else:
            print(f"❌ Bot {i+1} encountered error: {result}")
    
    # Summary
    print(f"\n📊 === Coordination Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"🤖 Bots: {args.bots}")
    print(f"📊 Symbols: {len(symbols)}")
    print(f"✅ Total trades executed: {total_trades}")
    print(f"🔒 Total blocking events: {total_successful}")
    print(f"🚫 Total blocked attempts: {total_blocks}")
    
    if total_trades > 0:
        efficiency = (total_trades / (total_trades + total_blocks)) * 100
        print(f"📈 Trading efficiency: {efficiency:.1f}%")
        print("🎉 Bot coordination demo completed successfully!")
        return True
    else:
        print("❌ No trades were executed")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--bots",
        type=int,
        default=3,
        help="Number of bots to simulate (default: 3)"
    )
    parser.add_argument(
        "--symbols",
        default="BTC/USDT,ETH/USDT",
        help="Comma-separated list of symbols (default: BTC/USDT,ETH/USDT)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Demo duration in seconds (default: 15)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed bot activity"
    )
    
    args = parser.parse_args()
    
    try:
        success = asyncio.run(run_demo(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🔄 Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


# Support both direct execution and import
if __name__ == "__main__":
    main()