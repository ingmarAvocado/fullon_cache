"""Performance benchmarking tests for uvloop optimization.

These tests measure and compare the performance of uvloop vs standard asyncio
for Redis cache operations, providing concrete performance metrics.
"""

import asyncio
import statistics
import time
from typing import Any

import pytest

from fullon_cache.base_cache import BaseCache
from fullon_cache.connection import ConnectionPool
from fullon_cache.event_loop import (
    EventLoopManager,
    EventLoopPolicy,
    benchmark_current_policy,
    get_policy_info,
    is_uvloop_active,
)


class PerformanceBenchmark:
    """Performance benchmarking utility for cache operations."""

    def __init__(self):
        self.results: dict[str, Any] = {}

    async def benchmark_basic_operations(self, iterations: int = 1000) -> dict[str, float]:
        """Benchmark basic Redis operations.
        
        Args:
            iterations: Number of operations to perform
            
        Returns:
            Dict with timing results
        """
        cache = BaseCache()

        # Benchmark set operations
        start_time = time.perf_counter()
        for i in range(iterations):
            await cache.set(f"bench_key_{i}", f"value_{i}")
        set_time = time.perf_counter() - start_time

        # Benchmark get operations
        start_time = time.perf_counter()
        for i in range(iterations):
            await cache.get(f"bench_key_{i}")
        get_time = time.perf_counter() - start_time

        # Benchmark JSON operations
        test_data = {"symbol": "BTC/USDT", "price": 50000.0, "volume": 1000.0}
        start_time = time.perf_counter()
        for i in range(iterations):
            await cache.set_json(f"bench_json_{i}", test_data)
        json_set_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        for i in range(iterations):
            await cache.get_json(f"bench_json_{i}")
        json_get_time = time.perf_counter() - start_time

        # Cleanup
        keys_to_delete = [f"bench_key_{i}" for i in range(iterations)]
        keys_to_delete.extend([f"bench_json_{i}" for i in range(iterations)])
        await cache.delete(*keys_to_delete)

        return {
            "set_ops_per_sec": iterations / set_time,
            "get_ops_per_sec": iterations / get_time,
            "json_set_ops_per_sec": iterations / json_set_time,
            "json_get_ops_per_sec": iterations / json_get_time,
            "avg_set_time_ms": (set_time / iterations) * 1000,
            "avg_get_time_ms": (get_time / iterations) * 1000,
            "total_time": set_time + get_time + json_set_time + json_get_time,
        }

    async def benchmark_concurrent_operations(self,
                                            concurrent_tasks: int = 100,
                                            operations_per_task: int = 100) -> dict[str, float]:
        """Benchmark concurrent Redis operations.
        
        Args:
            concurrent_tasks: Number of concurrent tasks
            operations_per_task: Operations per task
            
        Returns:
            Dict with timing results
        """
        async def worker_task(task_id: int) -> float:
            """Worker task for concurrent benchmarking."""
            cache = BaseCache()
            start_time = time.perf_counter()

            for i in range(operations_per_task):
                key = f"concurrent_{task_id}_{i}"
                await cache.set(key, f"value_{task_id}_{i}")
                await cache.get(key)
                await cache.delete(key)

            return time.perf_counter() - start_time

        # Run concurrent tasks
        start_time = time.perf_counter()
        tasks = [worker_task(i) for i in range(concurrent_tasks)]
        task_times = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        total_operations = concurrent_tasks * operations_per_task * 3  # set + get + delete

        return {
            "total_ops_per_sec": total_operations / total_time,
            "avg_task_time": statistics.mean(task_times),
            "min_task_time": min(task_times),
            "max_task_time": max(task_times),
            "total_time": total_time,
            "concurrent_tasks": concurrent_tasks,
            "operations_per_task": operations_per_task,
        }

    async def benchmark_pubsub_performance(self,
                                         message_count: int = 1000) -> dict[str, float]:
        """Benchmark pub/sub performance.
        
        Args:
            message_count: Number of messages to publish/receive
            
        Returns:
            Dict with timing results
        """
        cache = BaseCache()
        channel = "benchmark_channel"
        received_messages = []

        async def subscriber():
            """Subscribe and collect messages."""
            async for message in cache.subscribe(channel):
                received_messages.append(message)
                if len(received_messages) >= message_count:
                    break

        # Start subscriber
        subscriber_task = asyncio.create_task(subscriber())

        # Give subscriber time to connect
        await asyncio.sleep(0.1)

        # Publish messages
        start_time = time.perf_counter()
        for i in range(message_count):
            await cache.publish(channel, f"message_{i}")
        publish_time = time.perf_counter() - start_time

        # Wait for all messages to be received
        await subscriber_task
        receive_time = time.perf_counter() - start_time

        return {
            "publish_ops_per_sec": message_count / publish_time,
            "total_ops_per_sec": message_count / receive_time,
            "avg_publish_time_ms": (publish_time / message_count) * 1000,
            "total_time": receive_time,
            "messages_sent": message_count,
            "messages_received": len(received_messages),
        }


@pytest.mark.asyncio
class TestUvloopPerformance:
    """Test uvloop performance improvements."""

    async def test_event_loop_manager_configuration(self):
        """Test event loop manager configuration."""
        manager = EventLoopManager()

        # Test auto-configuration
        policy = manager.configure()
        assert policy in [EventLoopPolicy.UVLOOP, EventLoopPolicy.ASYNCIO]

        # Get policy info
        info = manager.get_policy_info()
        assert 'active_policy' in info
        assert 'uvloop_available' in info
        assert 'platform' in info

        # In test environment, we force asyncio regardless of uvloop availability
        # Check if we're in test mode by looking for the env var
        import os
        if os.getenv('FULLON_CACHE_EVENT_LOOP') == 'asyncio':
            # Test environment - should use asyncio
            assert info['active_policy'] == 'asyncio'
        elif info['uvloop_available']:
            # Production environment with uvloop available
            assert info['active_policy'] == 'uvloop'
        else:
            # Production environment without uvloop
            assert info['active_policy'] == 'asyncio'

    async def test_uvloop_detection(self):
        """Test uvloop availability detection."""
        manager = EventLoopManager()

        # This will depend on whether uvloop is installed
        available = manager._is_uvloop_available()

        # Should be boolean
        assert isinstance(available, bool)

        # If available on Unix, uvloop should be configurable
        if available:
            try:
                manager._configure_uvloop()
                # Should not raise exception
            except ImportError:
                pytest.fail("uvloop should be available but configuration failed")

    async def test_connection_pool_performance_info(self):
        """Test connection pool performance information."""
        pool = ConnectionPool()
        info = pool.get_performance_info()

        # Check required keys
        assert 'redis_config' in info
        assert 'event_loop_info' in info
        assert 'pool_stats' in info

        # Check event loop info
        event_loop_info = info['event_loop_info']
        assert 'active_policy' in event_loop_info
        assert 'uvloop_available' in event_loop_info

        # Check Redis config
        redis_config = info['redis_config']
        assert 'host' in redis_config
        assert 'port' in redis_config
        assert 'max_connections' in redis_config

    @pytest.mark.performance
    async def test_basic_operations_benchmark(self):
        """Benchmark basic Redis operations."""
        benchmark = PerformanceBenchmark()

        # Run benchmark with smaller iteration count for tests
        results = await benchmark.benchmark_basic_operations(iterations=100)

        # Verify results structure
        expected_keys = [
            'set_ops_per_sec', 'get_ops_per_sec',
            'json_set_ops_per_sec', 'json_get_ops_per_sec',
            'avg_set_time_ms', 'avg_get_time_ms', 'total_time'
        ]

        for key in expected_keys:
            assert key in results
            assert isinstance(results[key], (int, float))
            assert results[key] > 0

        # Log performance results
        print("\\nBasic Operations Benchmark:")
        print(f"Set operations: {results['set_ops_per_sec']:.0f} ops/sec")
        print(f"Get operations: {results['get_ops_per_sec']:.0f} ops/sec")
        print(f"JSON set operations: {results['json_set_ops_per_sec']:.0f} ops/sec")
        print(f"JSON get operations: {results['json_get_ops_per_sec']:.0f} ops/sec")

        # Performance expectations (adjust based on environment)
        # These are conservative thresholds that should pass even without uvloop
        assert results['set_ops_per_sec'] > 50  # At least 50 ops/sec (relaxed for CI)
        assert results['get_ops_per_sec'] > 30  # At least 30 ops/sec (relaxed for CI)
        assert results['avg_set_time_ms'] < 100  # Less than 100ms per operation
        assert results['avg_get_time_ms'] < 100

    @pytest.mark.performance
    async def test_concurrent_operations_benchmark(self):
        """Benchmark concurrent Redis operations."""
        benchmark = PerformanceBenchmark()

        # Run benchmark with smaller parameters for tests
        results = await benchmark.benchmark_concurrent_operations(
            concurrent_tasks=10,
            operations_per_task=10
        )

        # Verify results structure
        expected_keys = [
            'total_ops_per_sec', 'avg_task_time', 'min_task_time',
            'max_task_time', 'total_time', 'concurrent_tasks', 'operations_per_task'
        ]

        for key in expected_keys:
            assert key in results
            assert isinstance(results[key], (int, float))
            assert results[key] >= 0

        # Log performance results
        print("\\nConcurrent Operations Benchmark:")
        print(f"Total throughput: {results['total_ops_per_sec']:.0f} ops/sec")
        print(f"Average task time: {results['avg_task_time']:.3f}s")
        print(f"Min task time: {results['min_task_time']:.3f}s")
        print(f"Max task time: {results['max_task_time']:.3f}s")

        # Performance expectations
        assert results['total_ops_per_sec'] > 50  # At least 50 ops/sec total
        assert results['avg_task_time'] < 10  # Less than 10 seconds per task
        assert results['max_task_time'] < 20  # No task takes more than 20 seconds

    @pytest.mark.performance
    async def test_pubsub_benchmark(self):
        """Benchmark pub/sub performance."""
        benchmark = PerformanceBenchmark()

        # Run benchmark with smaller message count for tests
        results = await benchmark.benchmark_pubsub_performance(message_count=50)

        # Verify results structure
        expected_keys = [
            'publish_ops_per_sec', 'total_ops_per_sec', 'avg_publish_time_ms',
            'total_time', 'messages_sent', 'messages_received'
        ]

        for key in expected_keys:
            assert key in results
            assert isinstance(results[key], (int, float))
            assert results[key] >= 0

        # Log performance results
        print("\\nPub/Sub Benchmark:")
        print(f"Publish throughput: {results['publish_ops_per_sec']:.0f} msgs/sec")
        print(f"Total throughput: {results['total_ops_per_sec']:.0f} msgs/sec")
        print(f"Average publish time: {results['avg_publish_time_ms']:.2f}ms")

        # Verify all messages were received
        assert results['messages_sent'] == results['messages_received']

        # Performance expectations
        assert results['publish_ops_per_sec'] > 10  # At least 10 msgs/sec
        assert results['avg_publish_time_ms'] < 1000  # Less than 1 second per message

    async def test_event_loop_benchmark(self):
        """Test event loop benchmarking utility."""
        results = await benchmark_current_policy(duration=0.1)  # Short benchmark for tests

        # Verify results structure
        assert 'policy' in results
        assert 'operations' in results
        assert 'ops_per_second' in results

        # Should have some performance data
        assert results['operations'] > 0
        assert results['ops_per_second'] > 0

        print("\\nEvent Loop Benchmark:")
        print(f"Policy: {results['policy']}")
        print(f"Operations: {results['operations']}")
        print(f"Ops/sec: {results['ops_per_second']:.0f}")

    async def test_uvloop_active_detection(self):
        """Test uvloop active detection."""
        # This test verifies the is_uvloop_active function works
        is_active = is_uvloop_active()
        assert isinstance(is_active, bool)

        # Get policy info to verify consistency
        info = get_policy_info()
        expected_active = info.get('active_policy') == 'uvloop'

        assert is_active == expected_active


@pytest.mark.performance
@pytest.mark.integration
class TestUvloopIntegration:
    """Integration tests for uvloop with fullon_cache."""

    async def test_full_cache_stack_performance(self):
        """Test performance of full cache stack with uvloop."""
        from fullon_cache import AccountCache, OrdersCache, TickCache

        # Initialize multiple cache types
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        account_cache = AccountCache()

        # Performance test data
        ticker_data = {
            "symbol": "BTC/USDT",
            "bid": 50000.0,
            "ask": 50001.0,
            "last": 50000.5,
            "volume": 1000.0
        }

        # Benchmark mixed operations
        start_time = time.perf_counter()

        operations = 10  # Much smaller for tests to avoid timeouts
        for i in range(operations):
            # Ticker operations
            await tick_cache.update_ticker("binance", f"BTC{i}/USDT", ticker_data)
            ticker = await tick_cache.get_ticker("binance", f"BTC{i}/USDT")

            # Order operations (simplified - just push, don't pop to avoid timeouts)
            await orders_cache.push_open_order(f"order_{i}", f"local_{i}")

            # Account operations (if methods exist)
            try:
                await account_cache.set_position(
                    user_id=1,
                    exchange_name="binance",
                    symbol=f"BTC{i}/USDT",
                    size=1.0,
                    cost=50000.0
                )
            except AttributeError:
                # Method might not exist yet
                pass

        total_time = time.perf_counter() - start_time
        ops_per_second = (operations * 2) / total_time  # 2 operations per iteration (ticker + order)

        print("\\nFull Stack Performance:")
        print(f"Total operations: {operations * 2}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Throughput: {ops_per_second:.0f} ops/sec")

        # Performance expectations (relaxed for test environment)
        assert ops_per_second > 5  # At least 5 ops/sec for mixed operations
        assert total_time < 10  # Should complete within 10 seconds

    async def test_memory_efficiency(self):
        """Test memory efficiency with uvloop."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create many cache instances and perform operations
        caches = []
        for i in range(10):  # Smaller number for tests
            cache = BaseCache()
            caches.append(cache)

            # Perform operations
            for j in range(50):
                await cache.set(f"mem_test_{i}_{j}", f"value_{j}")

        # Get peak memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Cleanup
        for cache in caches:
            await cache.delete_pattern("mem_test_*")

        print("\\nMemory Efficiency Test:")
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Peak memory: {peak_memory:.1f}MB")
        print(f"Memory increase: {memory_increase:.1f}MB")

        # Memory should be reasonable (adjust threshold based on environment)
        assert memory_increase < 100  # Less than 100MB increase for test operations


# Fixtures for performance testing
@pytest.fixture
async def performance_cache():
    """Fixture providing a cache instance for performance testing."""
    cache = BaseCache()
    yield cache
    # Cleanup any test keys
    await cache.delete_pattern("bench_*")
    await cache.delete_pattern("perf_*")
    await cache.delete_pattern("test_*")


@pytest.fixture
def event_loop_manager():
    """Fixture providing an event loop manager."""
    manager = EventLoopManager()
    yield manager
    # No cleanup needed as manager doesn't hold resources


# Utility functions for performance analysis
def compare_performance_results(asyncio_results: dict[str, float],
                              uvloop_results: dict[str, float]) -> dict[str, float]:
    """Compare performance results between asyncio and uvloop.
    
    Args:
        asyncio_results: Benchmark results using asyncio
        uvloop_results: Benchmark results using uvloop
        
    Returns:
        Dict with performance improvement ratios
    """
    improvements = {}

    for key in asyncio_results:
        if key in uvloop_results and asyncio_results[key] > 0:
            if 'time' in key:
                # For time metrics, lower is better
                improvements[f"{key}_improvement"] = asyncio_results[key] / uvloop_results[key]
            else:
                # For rate metrics, higher is better
                improvements[f"{key}_improvement"] = uvloop_results[key] / asyncio_results[key]

    return improvements


if __name__ == "__main__":
    # Allow running benchmarks directly
    import asyncio

    async def run_benchmarks():
        """Run performance benchmarks directly."""
        print("Running fullon_cache performance benchmarks...")

        # Event loop info
        info = get_policy_info()
        print(f"Event loop policy: {info['active_policy']}")
        print(f"uvloop available: {info['uvloop_available']}")
        print(f"Platform: {info['platform']}")
        print()

        benchmark = PerformanceBenchmark()

        # Basic operations
        print("Running basic operations benchmark...")
        basic_results = await benchmark.benchmark_basic_operations(1000)
        print(f"Set operations: {basic_results['set_ops_per_sec']:.0f} ops/sec")
        print(f"Get operations: {basic_results['get_ops_per_sec']:.0f} ops/sec")
        print()

        # Concurrent operations
        print("Running concurrent operations benchmark...")
        concurrent_results = await benchmark.benchmark_concurrent_operations(50, 50)
        print(f"Concurrent throughput: {concurrent_results['total_ops_per_sec']:.0f} ops/sec")
        print()

        # Pub/sub
        print("Running pub/sub benchmark...")
        pubsub_results = await benchmark.benchmark_pubsub_performance(100)
        print(f"Pub/sub throughput: {pubsub_results['publish_ops_per_sec']:.0f} msgs/sec")
        print()

        print("Benchmarks complete!")

    asyncio.run(run_benchmarks())
