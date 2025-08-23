"""Performance benchmarking for cache operations.

This example measures the performance of various cache operations.
"""

import asyncio
from fullon_log import get_component_logger
import time
from statistics import mean, stdev


from ..ohlcv_cache import OHLCVCache
from ..orders_cache import OrdersCache
from ..tick_cache import TickCache

logger = get_component_logger("fullon.cache.examples.performance")


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

    tick_cache = TickCache()
    orders_cache = OrdersCache() 
    ohlcv_cache = OHLCVCache()

    try:
        # Import fullon_orm models
        from fullon_orm.models import Tick, Symbol
        
        # Prepare test data
        symbol = Symbol(
            symbol="BTC/USDT",
            cat_ex_id=1,
            base="BTC", 
            quote="USDT"
        )
        
        test_tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            bid=49999.0,
            ask=50001.0,
            last=50000.5,
            volume=1000.0,
            time=time.time()
        )

        # Benchmark ticker operations
        logger.info("\n--- Ticker Cache ---")
        await benchmark_operation(
            "Ticker write",
            lambda: tick_cache.set_ticker(symbol, test_tick),
            1000
        )

        await benchmark_operation(
            "Ticker read",
            lambda: tick_cache.get_ticker(symbol),
            1000
        )

        await benchmark_operation(
            "Ticker get any",
            lambda: tick_cache.get_any_ticker(symbol),
            1000
        )

        await benchmark_operation(
            "Ticker get all",
            lambda: tick_cache.get_all_tickers(exchange_name="binance"),
            100
        )

        # Benchmark order queue
        logger.info("\n--- Order Queue ---")
        await benchmark_operation(
            "Order push",
            lambda: orders_cache.push_open_order(f"order_{time.time()}", "local_id"),
            1000
        )

        await benchmark_operation(
            "Order pop",
            lambda: orders_cache.pop_open_order("local_id"),
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

        # Pipeline performance (using BaseCache pipeline)
        logger.info("\n--- Pipeline Operations ---")
        async def pipeline_test():
            async with tick_cache.pipeline() as pipe:
                for i in range(10):
                    await pipe.hset(f"test:ticker:{i}", "price", str(50000 + i))
                await pipe.execute()

        await benchmark_operation(
            "Pipeline write (10 ops)",
            pipeline_test,
            100
        )

        logger.info("\n=== Benchmark Complete ===")
        logger.info("Target: <5ms for cache operations")
        
    finally:
        await tick_cache.close()
        await orders_cache.close()
        await ohlcv_cache.close()


if __name__ == "__main__":
    asyncio.run(main())
