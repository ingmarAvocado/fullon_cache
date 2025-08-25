#!/usr/bin/env python3
"""
BotCache Operations Demo Tool

This tool demonstrates bot coordination and exchange blocking functionality
provided by the BotCache class.

Features:
- Multi-bot coordination with exchange blocking
- Trading conflict prevention and resolution
- Bot status tracking and monitoring
- Position opening state management
- Exchange release and timeout handling
- Bot activity simulation and reporting

Usage:
    python example_bot_cache.py --bots 3 --symbols BTC/USDT,ETH/USDT --duration 30
    python example_bot_cache.py --bots 5 --duration 60 --verbose
    python example_bot_cache.py --operations status --verbose
    python example_bot_cache.py --help
"""

import argparse
import asyncio
import random
import sys
import time

try:
    from fullon_cache import BotCache
except ImportError:
    from ..bot_cache import BotCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.bot")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with BotCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_blocking_demo(cache: BotCache, verbose: bool = False) -> bool:
    """Demonstrate basic exchange blocking operations."""
    print("🔒 === Basic Exchange Blocking Demo ===")

    try:
        bot_id = 1001
        exchange = "binance"
        symbol = "BTC/USDT"

        print("🔄 Testing exchange blocking mechanics...")

        # Test initial state - should not be blocked
        blocking_bot = await cache.is_blocked(exchange, symbol)
        if blocking_bot:
            print(f"❌ Exchange should not be blocked initially (blocked by: {blocking_bot})")
            return False

        if verbose:
            print(f"   ✅ {exchange}:{symbol} is not blocked initially")

        # Block the exchange
        success = await cache.block_exchange(exchange, symbol, bot_id)
        if not success:
            print("❌ Failed to block exchange")
            return False

        print(f"🔒 Bot {bot_id} blocked {exchange}:{symbol}")

        # Test that exchange is now blocked
        blocking_bot = await cache.is_blocked(exchange, symbol)
        if not blocking_bot or blocking_bot != str(bot_id):
            print(
                f"❌ Exchange should be blocked by bot {bot_id}, but is blocked by: {blocking_bot}"
            )
            return False

        if verbose:
            print(f"   ✅ Bot {bot_id} successfully blocked {exchange}:{symbol}")

        # Release the block
        await cache.unblock_exchange(exchange, symbol)

        # Verify exchange is unblocked
        blocking_bot_after = await cache.is_blocked(exchange, symbol)
        if blocking_bot_after:
            print(f"❌ Exchange should be unblocked, but is still blocked by: {blocking_bot_after}")
            return False

        if verbose:
            print(f"   ✅ {exchange}:{symbol} successfully unblocked")

        print("✅ Exchange blocking mechanics working correctly")
        return True

    except Exception as e:
        print(f"❌ Basic blocking demo failed: {e}")
        return False


async def bot_status_demo(cache: BotCache, verbose: bool = False) -> bool:
    """Demonstrate bot status tracking."""
    print("📊 === Bot Status Tracking Demo ===")

    try:
        bot_ids = [2001, 2002, 2003]

        print(f"🔄 Setting up status for {len(bot_ids)} bots...")

        # Set different statuses for bots using update_bot
        for i, bot_id in enumerate(bot_ids):
            status = ["running", "paused", "stopped"][i % 3]
            bot_data = {"status": status, "name": f"Bot_{bot_id}", "strategy": "demo_strategy"}
            success = await cache.update_bot(str(bot_id), bot_data)
            if not success:
                print(f"❌ Failed to set status for bot {bot_id}")
                return False

            if verbose:
                print(f"   🤖 Bot {bot_id}: {status}")

        # Retrieve and verify statuses
        print("🔄 Retrieving bot statuses...")
        all_bots = await cache.get_bots()

        for bot_id in bot_ids:
            bot_data = all_bots.get(str(bot_id))

            if not bot_data or "status" not in bot_data:
                print(f"❌ Failed to retrieve status for bot {bot_id}")
                return False

            if verbose:
                print(f"   📊 Bot {bot_id} status: {bot_data['status']}")

        # Update a bot status
        print("🔄 Updating bot status...")
        update_data = {
            "status": "maintenance",
            "name": f"Bot_{bot_ids[0]}",
            "strategy": "demo_strategy",
        }
        success = await cache.update_bot(str(bot_ids[0]), update_data)
        if not success:
            print("❌ Bot status update failed")
            return False

        # Verify update
        updated_bots = await cache.get_bots()
        updated_bot = updated_bots.get(str(bot_ids[0]))
        if not updated_bot or updated_bot.get("status") != "maintenance":
            print("❌ Bot status update verification failed")
            return False

        print("✅ Bot status tracking working correctly")
        return True

    except Exception as e:
        print(f"❌ Bot status demo failed: {e}")
        return False


async def position_opening_demo(cache: BotCache, verbose: bool = False) -> bool:
    """Demonstrate position opening state management."""
    print("📈 === Position Opening State Demo ===")

    try:
        bot_id = 3001
        symbol = "ETH/USDT"

        print("🔄 Testing position opening states...")

        # Initially should not be opening a position
        is_opening = await cache.is_opening_position("binance", symbol)
        if is_opening:
            print("❌ Bot should not be opening position initially")
            return False

        # Set bot to opening position state
        success = await cache.mark_opening_position("binance", symbol, bot_id)
        if not success:
            print("❌ Failed to mark opening position")
            return False

        # Verify state is set
        is_opening_after = await cache.is_opening_position("binance", symbol)
        if not is_opening_after:
            print("❌ Bot should be in opening position state")
            return False

        if verbose:
            print(f"   📈 Bot {bot_id} is opening position for {symbol}")

        # Clear the opening state
        success = await cache.unmark_opening_position("binance", symbol)
        if not success:
            print("❌ Failed to unmark opening position")
            return False

        # Verify state is cleared
        is_opening_final = await cache.is_opening_position("binance", symbol)
        if is_opening_final:
            print("❌ Bot should not be opening position after clearing")
            return False

        print("✅ Position opening state management working correctly")
        return True

    except Exception as e:
        print(f"❌ Position opening demo failed: {e}")
        return False


async def multi_bot_coordination_demo(
    cache: BotCache,
    bot_count: int = 3,
    symbols: list[str] = None,
    duration: int = 15,
    verbose: bool = False,
) -> bool:
    """Demonstrate multi-bot coordination with conflict resolution."""
    print("🤖 === Multi-Bot Coordination Demo ===")

    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT"]

    try:
        print(f"🔄 Starting coordination demo with {bot_count} bots for {duration}s")
        print(f"📊 Symbols: {', '.join(symbols)}")

        # Start bot simulation tasks
        bot_tasks = []
        for bot_id in range(4001, 4001 + bot_count):
            task = asyncio.create_task(
                simulate_bot_activity(cache, bot_id, symbols, duration, verbose)
            )
            bot_tasks.append(task)

        # Wait for all bots to complete
        results = await asyncio.gather(*bot_tasks, return_exceptions=True)

        # Analyze results
        total_trades = 0
        total_blocks = 0
        successful_bots = 0

        for i, result in enumerate(results):
            bot_id = 4001 + i
            if isinstance(result, dict):
                trades = result.get("trades_executed", 0)
                blocks = result.get("blocked_attempts", 0)
                total_trades += trades
                total_blocks += blocks
                successful_bots += 1

                if verbose:
                    print(f"   🤖 Bot {bot_id}: {trades} trades, {blocks} blocks")
            else:
                print(f"   ❌ Bot {bot_id} failed: {result}")

        print("📊 Coordination Results:")
        print(f"   🤖 Active bots: {successful_bots}/{bot_count}")
        print(f"   ✅ Total trades: {total_trades}")
        print(f"   🚫 Total blocks: {total_blocks}")

        if total_trades > 0:
            efficiency = (total_trades / (total_trades + total_blocks)) * 100
            print(f"   📈 Trading efficiency: {efficiency:.1f}%")

        if successful_bots == bot_count and total_trades > 0:
            print("✅ Multi-bot coordination working correctly")
            return True
        else:
            print("❌ Multi-bot coordination had issues")
            return False

    except Exception as e:
        print(f"❌ Multi-bot coordination demo failed: {e}")
        return False


async def simulate_bot_activity(
    cache: BotCache, bot_id: int, symbols: list[str], duration: int, verbose: bool = False
) -> dict[str, int]:
    """Simulate a single bot's trading activity."""
    stats = {"trades_executed": 0, "blocked_attempts": 0, "successful_blocks": 0}

    start_time = time.time()
    end_time = start_time + duration

    try:
        while time.time() < end_time:
            symbol = random.choice(symbols)
            exchange = "binance"

            # Try to trade the symbol
            can_trade = await cache.can_bot_trade(bot_id, exchange, symbol)

            if can_trade:
                # Block exchange for trading
                await cache.set_exchange_blocked(exchange, symbol, bot_id)
                stats["successful_blocks"] += 1

                if verbose:
                    print(f"   🟢 Bot {bot_id}: Acquired {symbol}")

                # Simulate trading time
                trade_duration = random.uniform(1.0, 3.0)
                await asyncio.sleep(trade_duration)

                # Complete trade and release
                stats["trades_executed"] += 1
                await cache.release_exchange_block(exchange, symbol)

                if verbose:
                    print(f"   ✅ Bot {bot_id}: Completed {symbol}")
            else:
                stats["blocked_attempts"] += 1
                if verbose:
                    print(f"   🔴 Bot {bot_id}: Blocked from {symbol}")

            # Wait before next attempt
            await asyncio.sleep(random.uniform(0.5, 2.0))

        return stats

    except Exception as e:
        logger.error(f"Bot {bot_id} simulation failed", error=str(e))
        return stats


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache BotCache Demo")
    print("============================")

    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False

    start_time = time.time()
    results = {}

    # Parse symbols
    symbols = (
        [s.strip() for s in args.symbols.split(",")] if args.symbols else ["BTC/USDT", "ETH/USDT"]
    )

    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with BotCache() as cache:
            results["basic"] = await basic_blocking_demo(cache, args.verbose)

    if args.operations in ["status", "all"]:
        async with BotCache() as cache:
            results["status"] = await bot_status_demo(cache, args.verbose)

    if args.operations in ["positions", "all"]:
        async with BotCache() as cache:
            results["positions"] = await position_opening_demo(cache, args.verbose)

    if args.operations in ["coordination", "all"]:
        async with BotCache() as cache:
            results["coordination"] = await multi_bot_coordination_demo(
                cache, args.bots, symbols, args.duration, args.verbose
            )

    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)

    print("\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")

    if success_count == total_count:
        print("🎉 All BotCache operations completed successfully!")
        return True
    else:
        failed = [op for op, success in results.items() if not success]
        print(f"❌ Failed operations: {', '.join(failed)}")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--operations",
        choices=["basic", "status", "positions", "coordination", "all"],
        default="all",
        help="Operations to demonstrate (default: all)",
    )
    parser.add_argument(
        "--bots", type=int, default=3, help="Number of bots for coordination demo (default: 3)"
    )
    parser.add_argument(
        "--symbols",
        default="BTC/USDT,ETH/USDT",
        help="Comma-separated list of symbols (default: BTC/USDT,ETH/USDT)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Duration for coordination demo in seconds (default: 15)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with detailed bot activity"
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
