"""Pytest configuration and fixtures for Fullon Cache tests.

This module provides fixtures and configuration for running tests
with real Redis instances and proper isolation for parallel execution.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Ensure test environment is loaded
load_dotenv('.env.test', override=True)

# Setup logger
logger = logging.getLogger(__name__)

# Import cache modules (will be available after implementation)
from fullon_cache import (
    AccountCache,
    BaseCache,
    BotCache,
    ConnectionPool,
    OHLCVCache,
    OrdersCache,
    ProcessCache,
    TickCache,
    TradesCache,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set the event loop policy for the test session."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy):
    """Create a new event loop for each test function."""
    policy = event_loop_policy
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    try:
        loop.close()
    except RuntimeError:
        pass  # Loop was already closed


@pytest.fixture(scope="function")
def redis_db(worker_id, request) -> int:
    """Allocate unique Redis DB per test file for isolation.
    
    Each test file gets its own Redis database to prevent cross-contamination.
    Tests within the same file share the database and can run sequentially.
    
    Args:
        worker_id: pytest-xdist worker ID
        request: pytest request object to get test file info
        
    Returns:
        Redis database number (1-15, avoiding 0 for production)
    """
    # Map test files to specific Redis databases
    test_file_db_map = {
        "test_base_cache.py": 1,
        "test_process_cache.py": 2,
        "test_exchange_cache.py": 3,
        "test_symbol_cache.py": 4,
        "test_tick_cache.py": 5,
        "test_account_cache.py": 6,
        "test_orders_cache.py": 7,
        "test_bot_cache.py": 8,
        "test_trades_cache.py": 9,
        "test_ohlcv_cache.py": 10,
        "test_imports.py": 11,
    }

    # Get the test file name
    test_file = os.path.basename(request.node.fspath)

    # Get DB number from map, or use hash-based assignment for unknown files
    if test_file in test_file_db_map:
        db_num = test_file_db_map[test_file]
    else:
        # Hash the filename to get a consistent DB number
        db_num = (hash(test_file) % 14) + 1  # 1-14 range

    # If running in parallel with xdist, offset by worker number
    if worker_id != "master":
        try:
            worker_num = int(worker_id[2:])
            # Each worker uses a different DB to avoid conflicts
            # But we keep the file-based separation
            db_num = ((db_num + worker_num * 14) % 15) + 1
        except:
            pass

    # Set environment variable for this test
    os.environ['REDIS_DB'] = str(db_num)
    return db_num


@pytest.fixture(scope="module", autouse=True)
def redis_db_per_file(request):
    """Set Redis DB for each test file - module scoped."""
    # Get test file name and determine DB number
    test_file = os.path.basename(request.node.fspath)
    test_file_db_map = {
        "test_base_cache.py": 1,
        "test_process_cache.py": 2,
        "test_exchange_cache.py": 3,
        "test_symbol_cache.py": 4,
        "test_tick_cache.py": 5,
        "test_account_cache.py": 6,
        "test_orders_cache.py": 7,
        "test_bot_cache.py": 8,
        "test_trades_cache.py": 9,
        "test_ohlcv_cache.py": 10,
        "test_imports.py": 11,
    }

    db_num = test_file_db_map.get(test_file, 1)
    os.environ['REDIS_DB'] = str(db_num)
    print(f"\n[DB SELECT] Using Redis DB {db_num} for test file {test_file}")

    yield db_num

    # Reset after module
    ConnectionPool.reset()


@pytest_asyncio.fixture
async def clean_redis(redis_db) -> AsyncGenerator[None]:
    """Ensure Redis is clean for each test."""
    # Reset connection pool
    await ConnectionPool.reset_async()

    yield

    # Light cleanup after each test
    try:
        await ConnectionPool.reset_async()
    except:
        pass


@pytest_asyncio.fixture
async def base_cache(clean_redis) -> BaseCache:
    """Provide a clean BaseCache instance."""
    return BaseCache()


@pytest_asyncio.fixture
async def process_cache(clean_redis) -> ProcessCache:
    """Provide a clean ProcessCache instance."""
    cache = ProcessCache()

    # Clear any existing process data
    # ProcessCache uses key_prefix="process", so keys are like:
    # process:data:*, process:active:*, process:component:*, process:heartbeat:*
    await cache._cache.delete_pattern("data:*")
    await cache._cache.delete_pattern("active:*")
    await cache._cache.delete_pattern("component:*")
    await cache._cache.delete_pattern("heartbeat:*")

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("data:*")
        await cache._cache.delete_pattern("active:*")
        await cache._cache.delete_pattern("component:*")
        await cache._cache.delete_pattern("heartbeat:*")
    except:
        pass


@pytest_asyncio.fixture
async def tick_cache(clean_redis) -> TickCache:
    """Provide a clean TickCache instance."""
    cache = TickCache()

    # Clear any existing ticker data
    await cache.delete_pattern("ticker:*")
    await cache.delete_pattern("active:*")  # Active exchanges tracking
    await cache.delete_pattern("exchanges")  # Set of exchanges
    await cache.delete_pattern("exchange:*")  # Exchange symbols
    await cache.delete_pattern("prices")  # Price index
    await cache.delete_pattern("tickers:*")  # Legacy patterns
    await cache.delete_pattern("symbols")  # Symbol index
    await cache.delete_pattern("*:BTC*")  # Any BTC related keys
    await cache.delete_pattern("*:ETH*")  # Any ETH related keys

    yield cache

    # Cleanup after test
    try:
        await cache.delete_pattern("ticker:*")
        await cache.delete_pattern("active:*")
        await cache.delete_pattern("exchanges")
        await cache.delete_pattern("exchange:*")
        await cache.delete_pattern("prices")
        await cache.delete_pattern("tickers:*")
    except:
        pass


@pytest_asyncio.fixture
async def orders_cache(clean_redis) -> OrdersCache:
    """Provide a clean OrdersCache instance."""
    cache = OrdersCache()

    # Clear any existing order data
    # Note: OrdersCache uses key_prefix="order"
    await cache._cache.delete_pattern("queue:*")  # Order queues by exchange
    await cache._cache.delete_pattern("status:*")  # Order status
    await cache._cache.delete_pattern("user:*")    # User order indexes
    await cache._cache.delete_pattern("bot:*")     # Bot order indexes
    await cache._cache.delete_pattern("open_orders")  # Legacy patterns
    await cache._cache.delete_pattern("order_status:*")  # Legacy patterns

    # Clear accounts hash used by get_full_accounts (non-prefixed key)
    async with cache._cache._redis_context() as redis_client:
        await redis_client.delete("accounts")

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("queue:*")
        await cache._cache.delete_pattern("status:*")
        await cache._cache.delete_pattern("user:*")
        await cache._cache.delete_pattern("bot:*")
        await cache._cache.delete_pattern("open_orders")
        await cache._cache.delete_pattern("order_status:*")
        # Clean accounts hash
        async with cache._cache._redis_context() as redis_client:
            await redis_client.delete("accounts")
    except:
        pass


@pytest_asyncio.fixture
async def account_cache(clean_redis) -> AccountCache:
    """Provide a clean AccountCache instance."""
    cache = AccountCache()

    # Clear any existing positions and account data
    # Account keys use "account:data:{user_id}:{exchange}" pattern
    await cache._cache.delete_pattern("account:data:*")
    await cache._cache.delete_pattern("account:positions:*")
    await cache._cache.delete_pattern("account:position:*")
    await cache._cache.delete_pattern("account:users:*")
    await cache._cache.delete_pattern("account:global_positions")

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("account:data:*")
        await cache._cache.delete_pattern("account:positions:*")
        await cache._cache.delete_pattern("account:position:*")
        await cache._cache.delete_pattern("account:users:*")
        await cache._cache.delete_pattern("account:global_positions")
    except:
        pass


@pytest_asyncio.fixture
async def bot_cache(clean_redis) -> BotCache:
    """Provide a clean BotCache instance."""
    cache = BotCache()

    # Clear any existing bot data
    await cache._cache.delete_pattern("bot:lock:*")  # Symbol locks
    await cache._cache.delete_pattern("bot:locks:*")  # Bot's active locks list
    await cache._cache.delete_pattern("bot:status:*")
    await cache._cache.delete_pattern("bot:opening:*")
    await cache._cache.delete_pattern("bot:bot_*")  # Legacy patterns
    await cache._cache.delete_pattern("bot:block_*")
    # Clear the specific keys used by simplified implementation
    await cache._cache.delete("block_exchange")
    await cache._cache.delete("opening_position")
    await cache._cache.delete("bot_status")

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("bot:lock:*")
        await cache._cache.delete_pattern("bot:locks:*")
        await cache._cache.delete_pattern("bot:status:*")
        await cache._cache.delete_pattern("bot:opening:*")
        await cache._cache.delete_pattern("bot:bot_*")
        await cache._cache.delete_pattern("bot:block_*")
        # Clear the specific keys used by simplified implementation
        await cache._cache.delete("block_exchange")
        await cache._cache.delete("opening_position")
        await cache._cache.delete("bot_status")
    except:
        pass


@pytest_asyncio.fixture
async def trades_cache(clean_redis) -> TradesCache:
    """Provide a clean TradesCache instance."""
    cache = TradesCache()

    # Clear any existing trades data
    # TradesCache uses key_prefix="trade"
    await cache._cache.delete_pattern("queue:*")     # Trade queues by exchange
    await cache._cache.delete_pattern("status:*")    # Trade status
    await cache._cache.delete_pattern("user:*")      # User trades indexes
    await cache._cache.delete_pattern("bot:*")       # Bot trades indexes
    await cache._cache.delete_pattern("list:*")      # Legacy patterns
    await cache._cache.delete_pattern("trades_list") # Legacy patterns

    # Clear legacy keys that are stored without prefix
    async with cache._cache._redis_context() as redis_client:
        # Scan for user_trades keys and delete them
        async for key in redis_client.scan_iter(match="user_trades:*"):
            await redis_client.delete(key)
        # Scan for legacy trades: pattern keys and delete them
        async for key in redis_client.scan_iter(match="trades:*"):
            await redis_client.delete(key)

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("queue:*")
        await cache._cache.delete_pattern("status:*")
        await cache._cache.delete_pattern("user:*")
        await cache._cache.delete_pattern("bot:*")
        await cache._cache.delete_pattern("list:*")
        await cache._cache.delete_pattern("trades_list")
        # Clean legacy keys
        async with cache._cache._redis_context() as redis_client:
            async for key in redis_client.scan_iter(match="user_trades:*"):
                await redis_client.delete(key)
            async for key in redis_client.scan_iter(match="trades:*"):
                await redis_client.delete(key)
    except:
        pass


@pytest_asyncio.fixture
async def ohlcv_cache(clean_redis) -> OHLCVCache:
    """Provide a clean OHLCVCache instance."""
    cache = OHLCVCache()

    # Clear any existing OHLCV data
    # OHLCV cache keys use pattern: ohlcv:{exchange}:{symbol}:{timeframe}
    # and metadata keys: ohlcv:meta:{exchange}:{symbol}:{timeframe}
    await cache._cache.delete_pattern("*:*:*")  # Clear all OHLCV data keys
    await cache._cache.delete_pattern("meta:*:*:*")  # Clear all metadata keys

    yield cache

    # Cleanup after test
    try:
        await cache._cache.delete_pattern("*:*:*")
        await cache._cache.delete_pattern("meta:*:*:*")
    except:
        pass


@pytest_asyncio.fixture
async def symbol_cache(clean_redis):
    """Provide a clean SymbolCache instance with proper isolation."""
    from fullon_cache import SymbolCache

    # Create a fresh instance
    cache = SymbolCache()

    # Ensure the cache is completely empty before yielding
    # Clear any potential leftover data
    await cache.delete_pattern("symbol:*")
    await cache.delete_pattern("exchange:*")
    await cache.delete_pattern("id:*")
    await cache.delete_pattern("quote:*")
    await cache.delete_pattern("base:*")
    await cache.delete_pattern("active")
    await cache.delete_pattern("symbols_list:*")  # Legacy format
    await cache.delete_pattern("tickers:*")  # Legacy format

    yield cache

    # Post-test cleanup (though clean_redis should handle most of it)
    try:
        # Clear all symbol-related keys again
        await cache._cache.delete_pattern("symbol:*")
        await cache._cache.delete_pattern("exchange:*")
        await cache._cache.delete_pattern("id:*")
        await cache._cache.delete_pattern("quote:*")
        await cache._cache.delete_pattern("base:*")
        await cache._cache.delete_pattern("active")
        await cache._cache.delete_pattern("symbols_list:*")  # Legacy format
        await cache._cache.delete_pattern("tickers:*")  # Legacy format
    except:
        pass  # Ignore cleanup errors


# Import factories from the factories folder
import sys
from pathlib import Path

# Add factories to path
factories_path = Path(__file__).parent / "factories"
sys.path.insert(0, str(factories_path))

from account import AccountFactory, PositionFactory
from bot import BotFactory
from ohlcv import OHLCVFactory
from order import OrderFactory
from process import ProcessFactory
from symbol import SymbolFactory
from ticker import TickerFactory
from trade import TradeFactory


@pytest.fixture
def ticker_factory():
    """Provide ticker factory."""
    return TickerFactory()


@pytest.fixture
def order_factory():
    """Provide order factory."""
    return OrderFactory()


@pytest.fixture
def process_factory():
    """Provide process factory."""
    return ProcessFactory()


@pytest.fixture
def symbol_factory():
    """Provide symbol factory."""
    return SymbolFactory()


@pytest.fixture
def trade_factory():
    """Provide trade factory."""
    return TradeFactory()


@pytest.fixture
def ohlcv_factory():
    """Provide OHLCV factory."""
    return OHLCVFactory()


@pytest.fixture
def account_factory():
    """Provide account factory."""
    return AccountFactory()


@pytest.fixture
def position_factory():
    """Provide position factory."""
    return PositionFactory()


@pytest.fixture
def bot_factory():
    """Provide bot factory."""
    return BotFactory()


@pytest.fixture(autouse=True)
def mock_fullon_orm_repositories():
    """Mock fullon_orm repository calls to prevent database access."""
    with patch('fullon_orm.get_async_session') as mock_session:
        # Create a mock session generator
        async def session_generator():
            yield Mock()
        mock_session.return_value = session_generator()

        # Mock SymbolRepository
        with patch('fullon_orm.repositories.SymbolRepository') as mock_sym_repo_class:
            mock_sym_repo = AsyncMock()

            # Default behavior: return None for not found
            mock_sym_repo.get_by_symbol = AsyncMock(return_value=None)
            mock_sym_repo.get_by_id = AsyncMock(return_value=None)
            mock_sym_repo.get_by_exchange_id = AsyncMock(return_value=[])

            mock_sym_repo_class.return_value = mock_sym_repo

            # Mock ExchangeRepository
            with patch('fullon_orm.repositories.ExchangeRepository') as mock_ex_repo_class:
                mock_ex_repo = AsyncMock()

                # Default behavior
                mock_ex_repo.get_by_id = AsyncMock(return_value=None)
                mock_ex_repo.get_exchange_by_name = AsyncMock(return_value=None)
                mock_ex_repo.get_exchange_by_id = AsyncMock(return_value=None)
                mock_ex_repo.get_all = AsyncMock(return_value=[])

                mock_ex_repo_class.return_value = mock_ex_repo

                yield {
                    'session': mock_session,
                    'symbol_repo': mock_sym_repo,
                    'exchange_repo': mock_ex_repo
                }


# Async utilities for tests

async def wait_for_condition(condition_func, timeout=5, interval=0.1):
    """Wait for a condition to become true.
    
    Args:
        condition_func: Async function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds
        
    Raises:
        TimeoutError: If condition is not met within timeout
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        if await condition_func():
            return

        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Condition not met within {timeout} seconds")

        await asyncio.sleep(interval)


# Performance benchmarking fixtures

@pytest.fixture
def benchmark_async():
    """Async-compatible benchmark fixture."""
    class AsyncBenchmark:
        def __init__(self):
            self.times = []

        async def __call__(self, func, *args, **kwargs):
            import time
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            self.times.append(elapsed)
            return result

        @property
        def stats(self):
            if not self.times:
                return {}
            return {
                'mean': sum(self.times) / len(self.times),
                'min': min(self.times),
                'max': max(self.times),
                'total': sum(self.times),
                'count': len(self.times),
            }

    return AsyncBenchmark()


# Redis health check

@pytest_asyncio.fixture(scope="session")
async def redis_available():
    """Check if Redis is available for testing."""
    try:
        cache = BaseCache()
        await cache.ping()
        return True
    except Exception as e:
        pytest.skip(f"Redis not available for testing: {e}")


# Markers for test organization

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )


# Test environment setup

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment."""
    # Ensure we're not using production Redis DB
    if os.getenv('REDIS_DB', '0') == '0':
        os.environ['REDIS_DB'] = '1'


@pytest_asyncio.fixture
async def full_isolation(clean_redis):
    """Fixture for tests that need extra-strong isolation.
    
    Use this for tests that are particularly sensitive to data contamination.
    This performs more aggressive cleanup than clean_redis alone.
    """
    # Extra pre-test cleanup
    temp_cache = BaseCache()

    # Clear ALL possible patterns that might be used
    patterns = [
        "symbol:*", "exchange:*", "id:*", "quote:*", "base:*",
        "tick:*", "tickers:*", "order:*", "trade:*", "ohlcv:*",
        "bot:*", "lock:*", "account:*", "position:*", "process:*"
    ]

    for pattern in patterns:
        try:
            await temp_cache.delete_pattern(pattern)
        except:
            pass

    await temp_cache.close()

    # Extra delay to ensure everything is cleaned
    await asyncio.sleep(0.02)

    yield

    # Extra post-test cleanup
    cleanup_cache = BaseCache()

    for pattern in patterns:
        try:
            await cleanup_cache.delete_pattern(pattern)
        except:
            pass

    await cleanup_cache.close()

    # Force complete reset
    await ConnectionPool.reset_async()

    import gc
    gc.collect()

    await asyncio.sleep(0.02)

    yield

    # Cleanup is handled by individual test fixtures


# Additional cache fixtures

@pytest.fixture
async def exchange_cache(setup_test_env):
    """Create an exchange cache instance for testing."""
    from fullon_cache import ExchangeCache
    cache = ExchangeCache()
    yield cache
