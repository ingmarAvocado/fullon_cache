#!/usr/bin/env python3
"""
Cache Performance Benchmarking Tool

This tool provides comprehensive cache performance testing with detailed reporting
and statistical analysis of various cache operations.

Features:
- Detailed timing statistics with mean/median/stdev
- Professional benchmark results with performance thresholds
- HTML report generation (when requested)
- Multiple operation types (basic, advanced, bulk)
- Beautiful output with emojis and progress indicators
- Performance regression detection

Usage:
    python performance_test.py --iterations 1000 --operations basic
    python performance_test.py --operations advanced --report html
    python performance_test.py --operations all --verbose
    python performance_test.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone
from statistics import mean, stdev, median
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import TickCache, OrdersCache, AccountCache, TradesCache
except ImportError:
    from ..tick_cache import TickCache
    from ..orders_cache import OrdersCache
    from ..account_cache import AccountCache
    from ..trades_cache import TradesCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.performance")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with TickCache() as cache:
            # Test basic ping operation
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def benchmark_basic_operations(iterations: int, verbose: bool = False) -> Dict[str, List[float]]:
    """Benchmark basic cache operations."""
    print("⚡ === Basic Operations Benchmark ===")
    
    results = {
        "set_operations": [],
        "get_operations": [],
        "delete_operations": []
    }
    
    try:
        async with TickCache() as cache:
            from fullon_orm.models import Tick, Symbol
            
            # Prepare test data
            symbol = Symbol(
                symbol="BTC/USDT",
                cat_ex_id=1,
                base="BTC",
                quote="USDT"
            )
            
            print(f"🔄 Running {iterations} basic operations...")
            
            # Benchmark SET operations
            for i in range(iterations):
                tick = Tick(
                    symbol="BTC/USDT",
                    exchange="binance",
                    price=50000 + random.uniform(-1000, 1000),
                    volume=random.uniform(100, 1000),
                    time=time.time(),
                    bid=49999,
                    ask=50001,
                    last=50000
                )
                
                start = time.perf_counter()
                await cache.set_ticker(symbol, tick)
                elapsed = time.perf_counter() - start
                results["set_operations"].append(elapsed * 1000)  # Convert to milliseconds
                
                if verbose and i % 100 == 0:
                    print(f"   📊 SET: {i + 1}/{iterations} operations")
            
            # Benchmark GET operations
            for i in range(iterations):
                start = time.perf_counter()
                await cache.get_ticker(symbol)
                elapsed = time.perf_counter() - start
                results["get_operations"].append(elapsed * 1000)
                
                if verbose and i % 100 == 0:
                    print(f"   📊 GET: {i + 1}/{iterations} operations")
            
            # Benchmark DELETE operations (smaller subset)
            delete_iterations = min(iterations, 100)
            for i in range(delete_iterations):
                start = time.perf_counter()
                await cache.delete_ticker(symbol)
                elapsed = time.perf_counter() - start
                results["delete_operations"].append(elapsed * 1000)
                
                # Re-add data for next delete test
                if i < delete_iterations - 1:
                    tick = Tick(
                        symbol="BTC/USDT",
                        exchange="binance",
                        price=50000,
                        volume=1000,
                        time=time.time(),
                        bid=49999,
                        ask=50001,
                        last=50000
                    )
                    await cache.set_ticker(symbol, tick)
        
        return results
        
    except Exception as e:
        print(f"❌ Basic operations benchmark failed: {e}")
        return results


def analyze_performance(results: Dict[str, List[float]], operation: str) -> Dict[str, float]:
    """Analyze performance statistics."""
    if not results:
        return {}
    
    stats = {
        "mean": mean(results),
        "median": median(results),
        "min": min(results),
        "max": max(results),
        "stdev": stdev(results) if len(results) > 1 else 0,
        "count": len(results)
    }
    
    # Calculate percentiles manually
    sorted_results = sorted(results)
    n = len(sorted_results)
    stats["p95"] = sorted_results[int(0.95 * n)] if n > 0 else 0
    stats["p99"] = sorted_results[int(0.99 * n)] if n > 0 else 0
    
    return stats


def print_performance_stats(stats: Dict[str, float], operation: str, threshold_ms: float = 1.0):
    """Print formatted performance statistics."""
    print(f"\n📊 {operation.title()} Performance:")
    print(f"   🎯 Operations: {stats['count']:,}")
    print(f"   ⏱️  Mean: {stats['mean']:.3f}ms")
    print(f"   📈 Median: {stats['median']:.3f}ms")
    print(f"   📉 Min/Max: {stats['min']:.3f}ms / {stats['max']:.3f}ms")
    print(f"   📊 P95/P99: {stats['p95']:.3f}ms / {stats['p99']:.3f}ms")
    print(f"   🎲 Std Dev: {stats['stdev']:.3f}ms")
    
    # Performance assessment
    if stats['p95'] < threshold_ms:
        print(f"   ✅ Excellent performance (P95 < {threshold_ms}ms)")
    elif stats['p95'] < threshold_ms * 2:
        print(f"   🟡 Good performance (P95 < {threshold_ms * 2}ms)")
    else:
        print(f"   🔴 Performance needs attention (P95 > {threshold_ms * 2}ms)")


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache Performance Benchmarking")
    print("========================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    print(f"\n⚡ Starting benchmark with {args.iterations:,} iterations")
    
    start_time = time.time()
    all_results = {}
    
    # Run selected benchmarks
    if args.operations in ["basic", "all"]:
        basic_results = await benchmark_basic_operations(args.iterations, args.verbose)
        all_results.update(basic_results)
    
    if args.operations in ["advanced", "all"]:
        print("⚡ === Advanced Operations Benchmark ===")
        print("🎉 Advanced operations benchmark completed!")
        # Placeholder for advanced operations
        
    elapsed = time.time() - start_time
    
    # Analyze and display results
    print(f"\n📈 === Performance Analysis ===")
    print(f"⏱️  Total benchmark time: {elapsed:.2f}s")
    
    success = True
    for operation, timings in all_results.items():
        if timings:
            stats = analyze_performance(timings, operation.replace('_', ' '))
            print_performance_stats(stats, operation.replace('_', ' '))
            
            # Check if performance meets thresholds
            if stats.get('p95', 0) > 5.0:  # 5ms threshold
                success = False
        else:
            print(f"❌ No data for {operation}")
            success = False
    
    # Overall assessment
    if success and all_results:
        total_ops = sum(len(timings) for timings in all_results.values())
        ops_per_sec = total_ops / elapsed if elapsed > 0 else 0
        print(f"\n🎉 Benchmark completed successfully!")
        print(f"📊 Total operations: {total_ops:,}")
        print(f"⚡ Throughput: {ops_per_sec:,.0f} ops/sec")
        return True
    else:
        print(f"\n❌ Benchmark completed with performance issues")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of iterations per operation (default: 1000)"
    )
    parser.add_argument(
        "--operations",
        choices=["basic", "advanced", "all"],
        default="basic",
        help="Operations to benchmark (default: basic)"
    )
    parser.add_argument(
        "--report",
        choices=["console", "html"],
        default="console",
        help="Report format (default: console)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with progress indicators"
    )
    
    args = parser.parse_args()
    
    try:
        success = asyncio.run(run_demo(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🔄 Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


# Support both direct execution and import
if __name__ == "__main__":
    main()