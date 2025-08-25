#!/usr/bin/env python3
"""
TickCache Operations Demo Tool

This tool demonstrates real-time ticker data management and pub/sub functionality
provided by the TickCache class.

Features:
- Real-time ticker data caching and retrieval
- Pub/Sub pattern for live price feeds
- Price monitoring across multiple exchanges
- Symbol-based ticker operations
- Live price updates and notifications
- Ticker data validation and formatting

Usage:
    python example_tick_cache.py --operations basic --exchanges binance,kraken
    python example_tick_cache.py --operations pubsub --symbols BTC/USDT,ETH/USDT --duration 30
    python example_tick_cache.py --operations monitoring --verbose
    python example_tick_cache.py --help
"""

import argparse
import asyncio
import random
import sys
import time

try:
    from fullon_cache import BaseCache, TickCache
except ImportError:
    from ..base_cache import BaseCache
    from ..tick_cache import TickCache

from fullon_log import get_component_logger
from fullon_orm.models import Symbol, Tick

logger = get_component_logger("fullon.cache.examples.tick")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with TickCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_ticker_operations(
    cache: TickCache, exchanges: list[str] = None, verbose: bool = False
) -> bool:
    """Demonstrate basic ticker operations."""
    print("📊 === Basic Ticker Operations Demo ===")

    if exchanges is None:
        exchanges = ["binance", "kraken"]

    try:
        # Create test symbols
        symbols = [
            Symbol(symbol="BTC/USDT", cat_ex_id=1, base="BTC", quote="USDT"),
            Symbol(symbol="ETH/USDT", cat_ex_id=2, base="ETH", quote="USDT"),
            Symbol(symbol="ADA/USDT", cat_ex_id=3, base="ADA", quote="USDT"),
        ]

        print(f"🔄 Setting ticker data for {len(symbols)} symbols on {len(exchanges)} exchanges...")

        # Set ticker data for each symbol/exchange combination
        ticker_count = 0
        for symbol in symbols:
            for exchange in exchanges:
                # Generate realistic price data
                base_prices = {"BTC/USDT": 47000, "ETH/USDT": 3100, "ADA/USDT": 1.2}
                base_price = base_prices.get(symbol.symbol, 100)
                current_price = base_price * (1 + random.uniform(-0.02, 0.02))

                tick = Tick(
                    symbol=symbol.symbol,
                    exchange=exchange,
                    price=current_price,
                    volume=random.uniform(100, 1000),
                    time=time.time(),
                    bid=current_price * 0.999,
                    ask=current_price * 1.001,
                    last=current_price,
                )

                success = await cache.set_ticker(tick)
                if success:
                    ticker_count += 1
                    if verbose:
                        print(f"   📈 {exchange}: {symbol.symbol} @ ${current_price:,.2f}")
                else:
                    print(f"❌ Failed to set ticker for {exchange}:{symbol.symbol}")
                    return False

        print(f"✅ Set {ticker_count} tickers successfully")

        # Retrieve ticker data
        print("🔄 Retrieving ticker data...")
        for symbol in symbols:
            for exchange in exchanges:
                ticker = await cache.get_ticker(symbol, exchange)
                if ticker:
                    if verbose:
                        print(
                            f"   📊 {exchange}:{symbol.symbol} = ${ticker.price:,.2f} "
                            + f"(Vol: {ticker.volume:.2f})"
                        )
                else:
                    print(f"❌ Failed to retrieve ticker for {exchange}:{symbol.symbol}")
                    return False

        # Test price retrieval using get_ticker method
        print("🔄 Testing best price retrieval...")
        for symbol in symbols:
            # Get ticker from binance exchange
            ticker = await cache.get_ticker(symbol, "binance")
            if ticker and ticker.price > 0:
                if verbose:
                    print(f"   💰 Best price for {symbol.symbol}: ${ticker.price:,.2f}")
            else:
                print(f"❌ No ticker available for {symbol.symbol}")
                return False

        print("✅ Basic ticker operations completed successfully")
        return True

    except Exception as e:
        print(f"❌ Basic ticker operations failed: {e}")
        return False


async def pubsub_demo(
    cache: TickCache, symbols: list[str] = None, duration: int = 15, verbose: bool = False
) -> bool:
    """Demonstrate pub/sub functionality for real-time updates."""
    print("📡 === Pub/Sub Real-Time Demo ===")

    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT"]

    try:
        # Create symbol objects
        symbol_objects = []
        for sym in symbols:
            base, quote = sym.split("/")
            symbol_obj = Symbol(symbol=sym, cat_ex_id=1, base=base, quote=quote)
            symbol_objects.append(symbol_obj)

        # Start publisher task
        publisher_task = asyncio.create_task(
            ticker_publisher(cache, symbol_objects, duration, verbose)
        )

        # Start subscriber task
        base_cache = BaseCache()
        subscriber_task = asyncio.create_task(
            ticker_subscriber(base_cache, symbols, duration, verbose)
        )

        # Wait for both tasks
        pub_result, sub_result = await asyncio.gather(
            publisher_task, subscriber_task, return_exceptions=True
        )

        await base_cache.close()

        # Check results
        if isinstance(pub_result, dict) and isinstance(sub_result, int):
            print(f"📊 Publisher sent: {sum(pub_result.values())} tickers")
            print(f"📊 Subscriber received: {sub_result} messages")

            if sum(pub_result.values()) > 0 and sub_result > 0:
                print("✅ Pub/Sub demo completed successfully")
                return True

        print("❌ Pub/Sub demo had issues")
        return False

    except Exception as e:
        print(f"❌ Pub/Sub demo failed: {e}")
        return False


async def ticker_publisher(
    cache: TickCache, symbols: list, duration: int, verbose: bool = False
) -> dict[str, int]:
    """Publish ticker updates for testing."""
    stats = {symbol.symbol: 0 for symbol in symbols}
    start_time = time.time()
    end_time = start_time + duration

    try:
        while time.time() < end_time:
            for symbol in symbols:
                # Generate price update
                base_prices = {"BTC/USDT": 47000, "ETH/USDT": 3100, "ADA/USDT": 1.2}
                base_price = base_prices.get(symbol.symbol, 100)
                current_price = base_price * (1 + random.uniform(-0.01, 0.01))

                tick = Tick(
                    symbol=symbol.symbol,
                    exchange="binance",
                    price=current_price,
                    volume=random.uniform(100, 1000),
                    time=time.time(),
                    bid=current_price * 0.999,
                    ask=current_price * 1.001,
                    last=current_price,
                )

                success = await cache.set_ticker(tick)
                if success:
                    stats[symbol.symbol] += 1
                    if verbose:
                        print(f"   📤 Published {symbol.symbol} @ ${current_price:,.2f}")

            await asyncio.sleep(1)  # Publish every second

        return stats

    except Exception as e:
        logger.error("Publisher failed", error=str(e))
        return stats


async def ticker_subscriber(
    base_cache: BaseCache, symbols: list[str], duration: int, verbose: bool = False
) -> int:
    """Subscribe to ticker updates."""
    received_count = 0

    try:
        # Subscribe to ticker channels
        channel_pattern = "tickers:binance:*"

        timeout_task = asyncio.create_task(asyncio.sleep(duration))
        subscription_task = asyncio.create_task(
            subscribe_to_tickers(base_cache, channel_pattern, verbose)
        )

        done, pending = await asyncio.wait(
            [timeout_task, subscription_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Get result from subscription task if it completed
        for task in done:
            if task == subscription_task:
                received_count = task.result()
                break

        return received_count

    except Exception as e:
        logger.error("Subscriber failed", error=str(e))
        return received_count


async def subscribe_to_tickers(base_cache: BaseCache, channel: str, verbose: bool = False) -> int:
    """Subscribe to ticker channel and count messages."""
    received_count = 0

    try:
        async for message in base_cache.subscribe(channel):
            if message["type"] == "message":
                received_count += 1
                if verbose:
                    print(f"   📥 Received: {message['channel']} -> {message['data']}")
                elif received_count % 5 == 0:
                    print(f"   📊 Received {received_count} ticker updates")
    except asyncio.CancelledError:
        pass

    return received_count


async def price_monitoring_demo(cache: TickCache, verbose: bool = False) -> bool:
    """Demonstrate price monitoring and alerts."""
    print("📈 === Price Monitoring Demo ===")

    try:
        # Set up monitoring symbols
        symbols = [
            Symbol(symbol="BTC/USDT", cat_ex_id=1, base="BTC", quote="USDT"),
            Symbol(symbol="ETH/USDT", cat_ex_id=2, base="ETH", quote="USDT"),
        ]

        # Set initial prices
        initial_prices = {}
        for symbol in symbols:
            base_price = 47000 if symbol.symbol == "BTC/USDT" else 3100
            tick = Tick(
                symbol=symbol.symbol,
                exchange="binance",
                price=base_price,
                volume=1000,
                time=time.time(),
                bid=base_price * 0.999,
                ask=base_price * 1.001,
                last=base_price,
            )

            await cache.set_ticker(symbol, tick)
            initial_prices[symbol.symbol] = base_price

            if verbose:
                print(f"   📊 Initial {symbol.symbol}: ${base_price:,.2f}")

        print("🔄 Monitoring price changes over 10 seconds...")

        # Monitor prices with simulated updates
        for _i in range(10):
            await asyncio.sleep(1)

            for symbol in symbols:
                # Simulate price movement
                old_price = initial_prices[symbol.symbol]
                new_price = old_price * (1 + random.uniform(-0.005, 0.005))

                tick = Tick(
                    symbol=symbol.symbol,
                    exchange="binance",
                    price=new_price,
                    volume=random.uniform(500, 1500),
                    time=time.time(),
                    bid=new_price * 0.999,
                    ask=new_price * 1.001,
                    last=new_price,
                )

                await cache.set_ticker(symbol, tick)

                # Calculate change
                change_pct = ((new_price - old_price) / old_price) * 100
                trend = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"

                if verbose or abs(change_pct) > 0.1:  # Show significant moves
                    print(f"   {trend} {symbol.symbol}: ${new_price:,.2f} ({change_pct:+.2f}%)")

                initial_prices[symbol.symbol] = new_price

        print("✅ Price monitoring demo completed successfully")
        return True

    except Exception as e:
        print(f"❌ Price monitoring demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache TickCache Demo")
    print("==============================")

    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False

    start_time = time.time()
    results = {}

    # Parse parameters
    exchanges = (
        [e.strip() for e in args.exchanges.split(",")] if args.exchanges else ["binance", "kraken"]
    )
    symbols = (
        [s.strip() for s in args.symbols.split(",")] if args.symbols else ["BTC/USDT", "ETH/USDT"]
    )

    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with TickCache() as cache:
            results["basic"] = await basic_ticker_operations(cache, exchanges, args.verbose)

    if args.operations in ["pubsub", "all"]:
        async with TickCache() as cache:
            results["pubsub"] = await pubsub_demo(cache, symbols, args.duration, args.verbose)

    if args.operations in ["monitoring", "all"]:
        async with TickCache() as cache:
            results["monitoring"] = await price_monitoring_demo(cache, args.verbose)

    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)

    print("\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")

    if success_count == total_count:
        print("🎉 All TickCache operations completed successfully!")
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
        choices=["basic", "pubsub", "monitoring", "all"],
        default="all",
        help="Operations to demonstrate (default: all)",
    )
    parser.add_argument(
        "--exchanges",
        default="binance,kraken",
        help="Comma-separated list of exchanges (default: binance,kraken)",
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
        help="Duration for pub/sub demo in seconds (default: 15)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with detailed ticker info"
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
