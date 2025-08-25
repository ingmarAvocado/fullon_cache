#!/usr/bin/env python3
"""
OHLCVCache Operations Demo Tool

This tool demonstrates OHLCV (candlestick) data caching and management
functionality provided by the OHLCVCache class.

Features:
- OHLCV bar data storage and retrieval
- Multiple timeframe support (1m, 5m, 1h, 1d)
- Bulk OHLCV data operations
- Symbol normalization and key management
- Historical data querying and filtering
- OHLCV data validation and statistics

Usage:
    python example_ohlcv_cache.py --operations basic --bars 100 --timeframes 1m,5m,1h
    python example_ohlcv_cache.py --operations bulk --symbols BTC/USDT,ETH/USDT --verbose
    python example_ohlcv_cache.py --operations analysis --verbose
    python example_ohlcv_cache.py --help
"""

import argparse
import asyncio
import random
import sys
import time
from datetime import UTC, datetime, timedelta

try:
    from fullon_cache import OHLCVCache
except ImportError:
    from ..ohlcv_cache import OHLCVCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.ohlcv")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with OHLCVCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


def generate_ohlcv_bar(
    timestamp: datetime, open_price: float, volatility: float = 0.02
) -> list[float]:
    """Generate a realistic OHLCV bar."""
    # Generate price movements
    price_change = random.uniform(-volatility, volatility)
    close_price = open_price * (1 + price_change)

    # High/Low around open/close range
    price_range = abs(close_price - open_price) * random.uniform(1.2, 2.0)
    high_price = max(open_price, close_price) + price_range * random.uniform(0, 0.5)
    low_price = min(open_price, close_price) - price_range * random.uniform(0, 0.5)

    # Volume
    volume = random.uniform(100, 1000)

    return [
        int(timestamp.timestamp()),  # timestamp
        open_price,  # open
        high_price,  # high
        low_price,  # low
        close_price,  # close
        volume,  # volume
    ]


async def basic_ohlcv_operations(
    cache: OHLCVCache, bar_count: int = 100, timeframes: list[str] = None, verbose: bool = False
) -> bool:
    """Demonstrate basic OHLCV operations."""
    print("📊 === Basic OHLCV Operations Demo ===")

    if timeframes is None:
        timeframes = ["1m", "5m", "1h"]

    try:
        symbols = ["BTC/USDT", "ETH/USDT"]

        print(
            f"🔄 Creating {bar_count} OHLCV bars for {len(symbols)} symbols "
            + f"on {len(timeframes)} timeframes..."
        )

        # Create OHLCV data for each symbol/timeframe combination
        total_bars = 0
        for symbol in symbols:
            # Normalize symbol (remove "/")
            symbol_key = symbol.replace("/", "")

            base_prices = {"BTCUSDT": 47000.0, "ETHUSDT": 3100.0}
            base_price = base_prices.get(symbol_key, 1000.0)
            current_price = base_price

            for timeframe in timeframes:
                print(f"   📈 Processing {symbol} {timeframe}...")

                # Generate historical bars
                bars_data = []
                base_time = datetime.now(UTC) - timedelta(hours=bar_count)

                # Different time intervals based on timeframe
                interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}
                minutes = interval_minutes.get(timeframe, 60)

                for i in range(bar_count):
                    bar_time = base_time + timedelta(minutes=i * minutes)
                    bar_data = generate_ohlcv_bar(bar_time, current_price)
                    bars_data.append(bar_data)

                    # Update current price for next bar
                    current_price = bar_data[4]  # close price

                # Store bars
                await cache.update_ohlcv_bars(symbol_key, timeframe, bars_data)
                total_bars += len(bars_data)
                if verbose:
                    print(f"      ✅ Stored {len(bars_data)} bars")

        print(f"✅ Stored {total_bars} OHLCV bars successfully")

        # Retrieve and verify data
        print("🔄 Retrieving OHLCV data...")

        for symbol in symbols:
            symbol_key = symbol.replace("/", "")

            for timeframe in timeframes:
                retrieved_bars = await cache.get_latest_ohlcv_bars(symbol_key, timeframe, 100)

                if retrieved_bars and len(retrieved_bars) > 0:
                    if verbose:
                        sample_bar = retrieved_bars[-1]  # Latest bar
                        print(
                            f"      📊 {symbol} {timeframe}: {len(retrieved_bars)} bars, "
                            f"latest close: ${sample_bar[4]:.2f}"
                        )
                else:
                    print(f"      ❌ No data retrieved for {symbol} {timeframe}")
                    return False

        print("✅ Basic OHLCV operations completed successfully")
        return True

    except Exception as e:
        print(f"❌ Basic OHLCV operations failed: {e}")
        return False


async def bulk_ohlcv_operations(
    cache: OHLCVCache, symbols: list[str] = None, verbose: bool = False
) -> bool:
    """Demonstrate bulk OHLCV operations."""
    print("📦 === Bulk OHLCV Operations Demo ===")

    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]

    try:
        timeframe = "1h"
        bars_per_symbol = 50

        print(f"🔄 Bulk loading OHLCV data for {len(symbols)} symbols...")

        # Prepare bulk data
        all_operations = []
        base_prices = {"BTC/USDT": 47000, "ETH/USDT": 3100, "ADA/USDT": 1.2}

        for symbol in symbols:
            symbol_key = symbol.replace("/", "")
            base_price = base_prices.get(symbol, 1000.0)

            # Generate bars
            bars_data = []
            current_price = base_price
            base_time = datetime.now(UTC) - timedelta(hours=bars_per_symbol)

            for i in range(bars_per_symbol):
                bar_time = base_time + timedelta(hours=i)
                bar_data = generate_ohlcv_bar(bar_time, current_price)
                bars_data.append(bar_data)
                current_price = bar_data[4]  # Update for next bar

            all_operations.append((symbol_key, bars_data))

            if verbose:
                print(f"   📈 Prepared {len(bars_data)} bars for {symbol}")

        # Execute bulk operations
        print("🔄 Executing bulk storage operations...")
        start_time = time.time()

        for symbol_key, bars_data in all_operations:
            await cache.update_ohlcv_bars(symbol_key, timeframe, bars_data)

        bulk_time = time.time() - start_time
        total_bars = sum(len(bars) for _, bars in all_operations)

        print(f"✅ Bulk operations completed in {bulk_time:.2f}s")
        print(f"   📊 Symbols processed: {len(symbols)}")
        print(f"   📈 Total bars stored: {total_bars}")
        print(f"   ⚡ Throughput: {total_bars / bulk_time:.1f} bars/sec")

        # Verify bulk data
        print("🔄 Verifying bulk data integrity...")

        verification_success = True
        for symbol in symbols:
            symbol_key = symbol.replace("/", "")
            retrieved_bars = await cache.get_latest_ohlcv_bars(symbol_key, timeframe, 100)

            if (
                not retrieved_bars or len(retrieved_bars) < bars_per_symbol * 0.9
            ):  # Allow 10% tolerance
                print(f"   ❌ Verification failed for {symbol}")
                verification_success = False
            elif verbose:
                print(f"   ✅ {symbol}: {len(retrieved_bars)} bars verified")

        if verification_success:
            print("✅ Bulk OHLCV operations completed successfully")
            return True
        else:
            print("❌ Some bulk operations failed")
            return False

    except Exception as e:
        print(f"❌ Bulk OHLCV operations failed: {e}")
        return False


async def ohlcv_analysis_demo(cache: OHLCVCache, verbose: bool = False) -> bool:
    """Demonstrate OHLCV data analysis and statistics."""
    print("📈 === OHLCV Data Analysis Demo ===")

    try:
        # Create analysis dataset
        symbol = "BTC/USDT"
        symbol_key = symbol.replace("/", "")
        timeframes = ["5m", "1h", "1d"]

        print("🔄 Creating analysis dataset...")

        analysis_data = {}
        base_price = 47000.0

        for timeframe in timeframes:
            # Different bar counts for different timeframes
            bar_counts = {"5m": 288, "1h": 24, "1d": 7}  # 1 day, 1 day, 1 week
            bar_count = bar_counts.get(timeframe, 24)

            # Different intervals
            interval_minutes = {"5m": 5, "1h": 60, "1d": 1440}
            minutes = interval_minutes.get(timeframe, 60)

            # Generate data with trends
            bars_data = []
            current_price = base_price
            base_time = datetime.now(UTC) - timedelta(minutes=bar_count * minutes)

            for i in range(bar_count):
                bar_time = base_time + timedelta(minutes=i * minutes)

                # Add slight uptrend
                trend_factor = 1 + (i * 0.001)  # 0.1% per bar trend
                volatility = {"5m": 0.005, "1h": 0.02, "1d": 0.05}.get(timeframe, 0.02)

                bar_data = generate_ohlcv_bar(bar_time, current_price * trend_factor, volatility)
                bars_data.append(bar_data)
                current_price = bar_data[4]

            # Store data
            await cache.update_ohlcv_bars(symbol_key, timeframe, bars_data)
            analysis_data[timeframe] = bars_data

            if verbose:
                print(f"   📊 Created {len(bars_data)} bars for {timeframe}")

        # Perform analysis
        print("🔄 Analyzing OHLCV data...")

        analysis_results = {}
        for timeframe in timeframes:
            # Retrieve data
            bars = await cache.get_latest_ohlcv_bars(symbol_key, timeframe, 100)

            if not bars:
                print(f"   ❌ No data for analysis: {timeframe}")
                return False

            # Calculate statistics
            opens = [bar[1] for bar in bars]
            highs = [bar[2] for bar in bars]
            lows = [bar[3] for bar in bars]
            closes = [bar[4] for bar in bars]
            volumes = [bar[5] for bar in bars]

            # Basic statistics
            price_change = ((closes[-1] - opens[0]) / opens[0]) * 100
            highest = max(highs)
            lowest = min(lows)
            avg_volume = sum(volumes) / len(volumes)
            volatility = ((highest - lowest) / opens[0]) * 100

            analysis_results[timeframe] = {
                "bars_count": len(bars),
                "price_change": price_change,
                "highest": highest,
                "lowest": lowest,
                "avg_volume": avg_volume,
                "volatility": volatility,
            }

        # Display analysis results
        print(f"📊 OHLCV Analysis for {symbol}:")

        for timeframe, results in analysis_results.items():
            print(f"\n   📈 {timeframe.upper()} Timeframe:")
            print(f"      📊 Bars: {results['bars_count']}")
            print(f"      📈 Price Change: {results['price_change']:+.2f}%")
            print(f"      🔺 High: ${results['highest']:,.2f}")
            print(f"      🔻 Low: ${results['lowest']:,.2f}")
            print(f"      📊 Avg Volume: {results['avg_volume']:.2f}")
            print(f"      📊 Volatility: {results['volatility']:.2f}%")

        # Cross-timeframe comparison
        print("\n📊 Cross-Timeframe Analysis:")
        timeframe_changes = {
            tf: results["price_change"] for tf, results in analysis_results.items()
        }

        most_bullish = max(timeframe_changes.items(), key=lambda x: x[1])
        most_bearish = min(timeframe_changes.items(), key=lambda x: x[1])

        print(f"   📈 Most bullish timeframe: {most_bullish[0]} ({most_bullish[1]:+.2f}%)")
        print(f"   📉 Most bearish timeframe: {most_bearish[0]} ({most_bearish[1]:+.2f}%)")

        # Trend consistency
        all_positive = all(change > 0 for change in timeframe_changes.values())
        all_negative = all(change < 0 for change in timeframe_changes.values())

        if all_positive:
            print("   🟢 Consistent uptrend across all timeframes")
        elif all_negative:
            print("   🔴 Consistent downtrend across all timeframes")
        else:
            print("   🟡 Mixed trends across timeframes")

        print("✅ OHLCV analysis completed successfully")
        return True

    except Exception as e:
        print(f"❌ OHLCV analysis failed: {e}")
        return False


async def ohlcv_performance_demo(cache: OHLCVCache, verbose: bool = False) -> bool:
    """Demonstrate OHLCV performance characteristics."""
    print("⚡ === OHLCV Performance Demo ===")

    try:
        symbol_key = "PERFUSDT"
        timeframe = "1m"

        # Performance test parameters
        test_sizes = [100, 500, 1000, 2000]

        print("🔄 Running OHLCV performance tests...")

        performance_results = {}

        for bar_count in test_sizes:
            print(f"   ⚡ Testing {bar_count} bars...")

            # Generate test data
            bars_data = []
            base_price = 1000.0
            base_time = datetime.now(UTC) - timedelta(minutes=bar_count)

            for i in range(bar_count):
                bar_time = base_time + timedelta(minutes=i)
                bar_data = generate_ohlcv_bar(bar_time, base_price)
                bars_data.append(bar_data)

            # Measure write performance
            write_start = time.time()
            await cache.update_ohlcv_bars(symbol_key, timeframe, bars_data)
            write_time = time.time() - write_start

            # Measure read performance
            read_start = time.time()
            retrieved_bars = await cache.get_latest_ohlcv_bars(symbol_key, timeframe, 100)
            read_time = time.time() - read_start

            # Verify data integrity
            data_integrity = (
                retrieved_bars and len(retrieved_bars) >= bar_count * 0.95
            )  # 95% tolerance

            performance_results[bar_count] = {
                "write_time": write_time,
                "read_time": read_time,
                "write_throughput": bar_count / write_time if write_time > 0 else 0,
                "read_throughput": len(retrieved_bars) / read_time
                if read_time > 0 and retrieved_bars
                else 0,
                "data_integrity": data_integrity,
            }

            if verbose:
                print(f"      📊 Write: {write_time:.3f}s ({bar_count / write_time:.0f} bars/sec)")
                print(
                    f"      📊 Read: {read_time:.3f}s "
                    + f"({len(retrieved_bars) / read_time:.0f} bars/sec)"
                )
                print(f"      ✅ Integrity: {'OK' if data_integrity else 'FAIL'}")

        # Display performance summary
        print("\n📊 OHLCV Performance Summary:")
        print("   Bars  | Write (ms) | Read (ms) | Write T/put | Read T/put | Status")
        print("   ------|------------|-----------|-------------|------------|--------")

        all_tests_passed = True
        for bar_count, results in performance_results.items():
            write_ms = results["write_time"] * 1000
            read_ms = results["read_time"] * 1000
            write_tput = results["write_throughput"]
            read_tput = results["read_throughput"]
            status = "✅ PASS" if results["data_integrity"] else "❌ FAIL"

            if not results["data_integrity"]:
                all_tests_passed = False

            print(
                f"   {bar_count:5d} | {write_ms:8.1f} | {read_ms:7.1f} | "
                + f"{write_tput:9.0f} | {read_tput:8.0f} | {status}"
            )

        # Performance assessment
        avg_write_throughput = sum(
            r["write_throughput"] for r in performance_results.values()
        ) / len(performance_results)
        avg_read_throughput = sum(r["read_throughput"] for r in performance_results.values()) / len(
            performance_results
        )

        print("\n📈 Average Performance:")
        print(f"   📤 Write throughput: {avg_write_throughput:.0f} bars/sec")
        print(f"   📥 Read throughput: {avg_read_throughput:.0f} bars/sec")

        if all_tests_passed and avg_write_throughput > 500 and avg_read_throughput > 1000:
            print("🎉 Performance tests passed with excellent results!")
            return True
        elif all_tests_passed:
            print("✅ Performance tests passed")
            return True
        else:
            print("❌ Some performance tests failed")
            return False

    except Exception as e:
        print(f"❌ OHLCV performance demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache OHLCVCache Demo")
    print("===============================")

    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False

    start_time = time.time()
    results = {}

    # Parse parameters
    timeframes = (
        [tf.strip() for tf in args.timeframes.split(",")] if args.timeframes else ["1m", "5m", "1h"]
    )
    symbols = (
        [s.strip() for s in args.symbols.split(",")] if args.symbols else ["BTC/USDT", "ETH/USDT"]
    )

    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with OHLCVCache() as cache:
            results["basic"] = await basic_ohlcv_operations(
                cache, args.bars, timeframes, args.verbose
            )

    if args.operations in ["bulk", "all"]:
        async with OHLCVCache() as cache:
            results["bulk"] = await bulk_ohlcv_operations(cache, symbols, args.verbose)

    if args.operations in ["analysis", "all"]:
        async with OHLCVCache() as cache:
            results["analysis"] = await ohlcv_analysis_demo(cache, args.verbose)

    if args.operations in ["performance", "all"]:
        async with OHLCVCache() as cache:
            results["performance"] = await ohlcv_performance_demo(cache, args.verbose)

    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)

    print("\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")

    if success_count == total_count:
        print("🎉 All OHLCVCache operations completed successfully!")
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
        choices=["basic", "bulk", "analysis", "performance", "all"],
        default="all",
        help="Operations to demonstrate (default: all)",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=100,
        help="Number of OHLCV bars for basic operations (default: 100)",
    )
    parser.add_argument(
        "--timeframes",
        default="1m,5m,1h",
        help="Comma-separated list of timeframes (default: 1m,5m,1h)",
    )
    parser.add_argument(
        "--symbols",
        default="BTC/USDT,ETH/USDT",
        help="Comma-separated list of symbols (default: BTC/USDT,ETH/USDT)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with detailed OHLCV info"
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
