"""Performance benchmarking for cache operations.

This example measures the performance of various cache operations.
"""

import asyncio
import logging
import time
from statistics import mean, stdev

from fullon_orm.models import Symbol

from fullon_cache.ohlcv_cache import OHLCVCache
from fullon_cache.orders_cache import OrdersCache
from fullon_cache.symbol_cache import SymbolCache
from fullon_cache.tick_cache import TickCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def benchmark_operation(name: str, operation, iterations: int = 1000):
    """Benchmark a single operation."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        await operation()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    avg = mean(times)
    std = stdev(times) if len(times) > 1 else 0

    logger.info(f"{name}: avg={avg:.3f}ms, std={std:.3f}ms, min={min(times):.3f}ms, max={max(times):.3f}ms")
    return times


async def main():
    """Run performance benchmarks."""
    logger.info("=== Cache Performance Benchmarks ===")

    async with TickCache() as tick_cache:
        async with OrdersCache() as orders_cache:
            async with OHLCVCache() as ohlcv_cache:
                async with SymbolCache() as symbol_cache:

                    # Prepare test data
                    test_ticker = {
                        'symbol': 'BTC/USD',
                        'last': 50000.0,
                        'bid': 49999.0,
                        'ask': 50001.0,
                        'volume': 1000.0,
                        'timestamp': time.time()
                    }

                    test_symbol = Symbol(
                        symbol_id=1,
                        symbol='BTC/USD',
                        cat_ex_id=1,
                        base='BTC',
                        quote='USD',
                        futures=False,
                        decimals=8
                    )

                    # Benchmark ticker operations
                    logger.info("\n--- Ticker Cache ---")
                    await benchmark_operation(
                        "Ticker write",
                        lambda: tick_cache.update_ticker("kraken", "BTC/USD", test_ticker),
                        1000
                    )

                    await benchmark_operation(
                        "Ticker read",
                        lambda: tick_cache.get_ticker("kraken", "BTC/USD"),
                        1000
                    )

                    # Benchmark order queue
                    logger.info("\n--- Order Queue ---")
                    await benchmark_operation(
                        "Order push",
                        lambda: orders_cache.push_open_order("user123", "kraken", f"order_{time.time()}"),
                        1000
                    )

                    await benchmark_operation(
                        "Order pop",
                        lambda: orders_cache.pop_open_order("user123", "kraken"),
                        1000
                    )

                    # Benchmark OHLCV operations
                    logger.info("\n--- OHLCV Cache ---")
                    test_bars = [[time.time(), 50000, 50100, 49900, 50050, 100] for _ in range(100)]

                    await benchmark_operation(
                        "OHLCV write (100 bars)",
                        lambda: ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", test_bars),
                        100
                    )

                    await benchmark_operation(
                        "OHLCV read",
                        lambda: ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 100),
                        1000
                    )

                    # Benchmark symbol operations
                    logger.info("\n--- Symbol Cache ---")
                    await symbol_cache.update_symbol("BTC/USD", test_symbol)

                    await benchmark_operation(
                        "Symbol read (cache hit)",
                        lambda: symbol_cache.get_symbol("BTC/USD"),
                        1000
                    )

                    # Test cache miss scenario
                    await symbol_cache.delete_symbol("ETH/USD")
                    await benchmark_operation(
                        "Symbol read (cache miss)",
                        lambda: symbol_cache.get_symbol("ETH/USD"),
                        10  # Less iterations for cache miss
                    )

                    # Pipeline performance
                    logger.info("\n--- Pipeline Operations ---")
                    async def pipeline_test():
                        async with tick_cache.redis.pipeline() as pipe:
                            for i in range(10):
                                pipe.hset(f"test:ticker:{i}", mapping=test_ticker)
                            await pipe.execute()

                    await benchmark_operation(
                        "Pipeline write (10 ops)",
                        pipeline_test,
                        100
                    )

                    logger.info("\n=== Benchmark Complete ===")
                    logger.info("Target: <1ms for cache hits")


if __name__ == "__main__":
    asyncio.run(main())
