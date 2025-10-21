"""Pytest configuration and fixtures for Fullon Cache tests.

This module provides fixtures and configuration for running tests
with real Redis instances and proper isolation for parallel execution.
"""

import asyncio
from fullon_log import get_component_logger
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Ensure test environment is loaded
load_dotenv('.env.test', override=True)

# Setup logger
logger = get_component_logger("fullon.cache.tests")

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
    # Disable uvloop for tests to avoid conflicts - use the correct env var
    import os
    os.environ['FULLON_CACHE_EVENT_LOOP'] = 'asyncio'
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy):
    """Create a new event loop for each test function with proper cleanup."""
    # Ensure we're using the test policy
    policy = event_loop_policy
    
    # Close any existing loop
    try:
        current_loop = asyncio.get_running_loop()
        if current_loop and not current_loop.is_closed():
            current_loop.close()
    except RuntimeError:
        pass  # No running loop
    
    # Create new loop
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    
    yield loop
    
    # Proper cleanup
    try:
        # Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            if not task.done():
                task.cancel()
        
        # Wait for cancelled tasks to complete
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        # Close the loop
        loop.close()
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        # Ensure no loop is set
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass


@pytest.fixture(scope="function")
def redis_db(worker_id, request) -> int:
    """Allocate completely unique Redis DB per test for maximum isolation.
    
    Each test gets its own database to ensure complete isolation.
    Uses process ID and timestamp to guarantee uniqueness.
    
    Args:
        worker_id: pytest-xdist worker ID (e.g., "gw0", "gw1", etc.)
        request: pytest request object to get test info
        
    Returns:
        Redis database number (1-15, rotating but unique per test)
    """
    import time
    import hashlib
    
    # Get worker number
    if worker_id == "master":
        worker_num = 0
    else:
        try:
            worker_num = int(worker_id[2:])  # Extract number from "gw0", "gw1", etc.
        except (ValueError, IndexError):
            worker_num = 0
    
    # Create unique identifier for this test
    test_file = os.path.basename(request.node.fspath)
    test_name = request.node.name
    timestamp = str(time.time_ns())  # Nanosecond precision
    process_id = str(os.getpid())
    
    # Create hash for unique DB selection
    unique_string = f"{worker_id}_{test_file}_{test_name}_{timestamp}_{process_id}"
    hash_value = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
    
    # Each worker gets a base DB range, but tests cycle through them uniquely
    base_db = (worker_num * 4) + 1  # Worker 0: 1-4, Worker 1: 5-8, Worker 2: 9-12, Worker 3: 13-16
    db_offset = hash_value % 4  # 4 DBs per worker for better isolation
    db_num = base_db + db_offset
    
    # Ensure we stay within Redis DB limits (1-15, extend to 16 for worker 3)
    if db_num > 15:
        db_num = ((db_num - 1) % 15) + 1
    
    # Set environment variable for this test
    os.environ['REDIS_DB'] = str(db_num)
    return db_num


@pytest.fixture(scope="function")
def test_isolation_prefix(worker_id, request) -> str:
    """Generate ultra-unique prefix for test data to prevent cross-test contamination.
    
    This ensures that even within the same Redis DB, different tests and workers
    use completely isolated key spaces with nanosecond precision.
    """
    import time
    import uuid
    import hashlib
    
    # Get worker number
    if worker_id == "master":
        worker_num = 0
    else:
        try:
            worker_num = int(worker_id[2:])
        except (ValueError, IndexError):
            worker_num = 0
    
    # Get test info
    test_file = os.path.basename(request.node.fspath)
    test_name = request.node.name
    
    # Create ultra-unique prefix with maximum separation
    timestamp_ns = time.time_ns()  # Nanosecond precision
    process_id = os.getpid()
    unique_id = uuid.uuid4().hex[:12]  # Longer unique ID
    
    # Create a hash to keep key length reasonable
    full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
    prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:16]
    
    # Final prefix: worker + hash for maximum uniqueness and reasonable length
    prefix = f"w{worker_num}_{prefix_hash}"
    
    return prefix


@pytest.fixture(scope="function")
def test_isolation(worker_id, request):
    """Provide ultra-strong test isolation with unique namespaces and aggressive cleanup.
    
    This fixture ensures each test gets a completely unique namespace with aggressive
    cleanup to prevent any cross-test contamination.
    """
    import time
    import uuid
    import hashlib
    
    # Create an ultra-unique test identifier with nanosecond precision
    test_name = request.node.name
    test_file = os.path.basename(request.node.fspath)
    timestamp_ns = time.time_ns()
    process_id = os.getpid()
    unique_id = uuid.uuid4().hex
    
    # Create hash-based prefix for reasonable key length
    full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
    prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:20]
    test_prefix = f"test_{worker_id}_{prefix_hash}"
    
    # Store the original prefixes for restoration
    original_prefixes = {}
    created_caches = []
    
    def get_isolated_cache(cache_class, **kwargs):
        """Get a cache instance with ultra-isolated key prefix."""
        cache = cache_class(**kwargs)
        created_caches.append(cache)
        
        # Apply isolation to all possible prefix attributes
        if hasattr(cache, '_key_prefix'):
            if cache not in original_prefixes:
                original_prefixes[cache] = getattr(cache, '_key_prefix', '')
            cache._key_prefix = f"{test_prefix}:{cache._key_prefix}" if cache._key_prefix else test_prefix
        
        if hasattr(cache, 'key_prefix'):
            if cache not in original_prefixes:
                original_prefixes[cache] = getattr(cache, 'key_prefix', '')
            cache.key_prefix = f"{test_prefix}:{cache.key_prefix}" if cache.key_prefix else test_prefix
            
        # Also check for nested cache objects
        if hasattr(cache, '_cache'):
            nested_cache = cache._cache
            if hasattr(nested_cache, 'key_prefix'):
                if nested_cache not in original_prefixes:
                    original_prefixes[nested_cache] = getattr(nested_cache, 'key_prefix', '')
                nested_cache.key_prefix = f"{test_prefix}:{nested_cache.key_prefix}" if nested_cache.key_prefix else test_prefix
        
        return cache
    
    # Yield the helper function
    yield get_isolated_cache
    
    # Ultra-aggressive cleanup
    try:
        from fullon_cache import BaseCache
        
        # Multiple cleanup attempts with different patterns
        async def ultra_cleanup():
            cleanup_cache = BaseCache()
            try:
                # Pattern 1: Our specific test prefix
                await cleanup_cache.delete_pattern(f"{test_prefix}:*")
                await cleanup_cache.delete_pattern(f"{test_prefix}")
                
                # Pattern 2: Any keys that might have been created without prefix
                # (for tests that bypass the isolation)
                patterns_to_clean = [
                    f"*{test_name}*",
                    f"*{worker_id}*{timestamp_ns}*",
                    f"bot_*{worker_id}*",
                    f"test_*{worker_id}*",
                ]
                
                for pattern in patterns_to_clean:
                    try:
                        await cleanup_cache.delete_pattern(pattern)
                    except:
                        pass  # Continue cleanup even if one pattern fails
                        
                # Pattern 3: Force flush the entire test database if needed
                try:
                    redis_db = int(os.environ.get('REDIS_DB', '1'))
                    if redis_db > 0:  # Never flush DB 0
                        async with cleanup_cache._redis_context() as redis:
                            # Only flush if we have a reasonable number of keys (safety check)
                            key_count = await redis.dbsize()
                            if key_count < 10000:  # Safety limit
                                await redis.flushdb()
                except:
                    pass  # Ignore flush errors
                    
            except Exception:
                pass  # Ignore all cleanup errors
            finally:
                await cleanup_cache.close()
        
        import asyncio
        asyncio.run(ultra_cleanup())
        
        # Restore original prefixes for all created caches
        for cache, original_prefix in original_prefixes.items():
            try:
                if hasattr(cache, '_key_prefix'):
                    cache._key_prefix = original_prefix
                if hasattr(cache, 'key_prefix'):
                    cache.key_prefix = original_prefix
            except:
                pass  # Ignore restoration errors
                
        # Close all created caches
        for cache in created_caches:
            try:
                if hasattr(cache, 'close'):
                    if asyncio.iscoroutinefunction(cache.close):
                        asyncio.run(cache.close())
                    else:
                        cache.close()
            except:
                pass  # Ignore close errors
                
    except Exception:
        pass  # Ignore all cleanup errors


@pytest.fixture(scope="function")
def sequential_test_lock():
    """Ensure certain high-conflict tests run sequentially.
    
    Use this fixture for tests that are known to have Redis contention issues
    to force them to run one at a time across all workers.
    """
    import fcntl
    import tempfile
    import os
    
    # Create a system-wide lock file
    lock_file_path = os.path.join(tempfile.gettempdir(), "fullon_cache_sequential_test.lock")
    
    try:
        # Open and lock the file
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        
        yield
        
    finally:
        # Release the lock
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
        except:
            pass


@pytest.fixture(scope="module", autouse=True)
def redis_db_per_file(request):
    """Set Redis DB for each test file - module scoped with worker isolation."""
    # Get worker ID from pytest-xdist if available
    worker_id = getattr(request.config, 'worker_id', 'master')
    
    # Get worker number for proper isolation
    if worker_id == "master":
        worker_num = 0
    else:
        try:
            worker_num = int(worker_id[2:])  # Extract number from "gw0", "gw1", etc.
        except (ValueError, IndexError):
            worker_num = 0
    
    # Each worker gets a base DB range to avoid conflicts
    base_db = (worker_num * 5) + 1  # Worker 0: 1, Worker 1: 6, Worker 2: 11
    
    # Get test file name and determine DB offset
    test_file = os.path.basename(request.node.fspath)
    test_file_db_map = {
        "test_base_cache.py": 0,
        "test_process_cache.py": 1,
        "test_tick_cache.py": 4,
        "test_account_cache.py": 0,  # Reuse within worker range is OK
        "test_orders_cache.py": 1,
        "test_bot_cache.py": 2,
        "test_trades_cache.py": 3,
        "test_ohlcv_cache.py": 4,
        "test_imports.py": 0,
        "test_integration_error_handling.py": 1,
        "test_integration_performance.py": 2,
        "test_integration_cross_module.py": 3,
        "test_integration_trading_flow.py": 4,
    }

    # Get DB offset from map, or use hash-based assignment for unknown files
    if test_file in test_file_db_map:
        db_offset = test_file_db_map[test_file]
    else:
        # Hash the filename to get a consistent offset within worker range
        db_offset = hash(test_file) % 5

    # Calculate final DB number within Redis limits (1-15)
    db_num = ((base_db + db_offset - 1) % 15) + 1
    
    os.environ['REDIS_DB'] = str(db_num)
    print(f"\n[DB SELECT] Worker {worker_id} using Redis DB {db_num} for test file {test_file}")

    yield db_num

    # Reset after module
    ConnectionPool.reset()


@pytest_asyncio.fixture
async def clean_redis(redis_db) -> AsyncGenerator[None]:
    """Ensure Redis is ultra-clean for each test with aggressive cleanup."""
    # Reset connection pool and completely flush database before test
    await ConnectionPool.reset_async()
    
    # Clear all data in the test database with multiple attempts
    for attempt in range(3):
        try:
            cache = BaseCache()
            async with cache._redis_context() as redis:
                # Force flush the entire test database
                await redis.flushdb()
                # Verify it's actually empty
                key_count = await redis.dbsize()
                if key_count == 0:
                    break
            await cache.close()
        except Exception:
            if attempt == 2:  # Last attempt
                pass  # Continue anyway
            await asyncio.sleep(0.1)

    # Brief pause to ensure cleanup is complete
    await asyncio.sleep(0.05)

    yield

    # Ultra-aggressive cleanup after each test
    for attempt in range(3):
        try:
            await ConnectionPool.reset_async()
            cache = BaseCache()
            async with cache._redis_context() as redis:
                # Force flush entire database
                await redis.flushdb()
                # Double-check it's clean
                await redis.flushdb()
            await cache.close()
            break
        except Exception:
            if attempt == 2:
                pass  # Give up after 3 attempts
            await asyncio.sleep(0.1)
    
    # Final pause to ensure all cleanup is complete
    await asyncio.sleep(0.05)


@pytest_asyncio.fixture
async def base_cache(clean_redis) -> BaseCache:
    """Provide a clean BaseCache instance."""
    return BaseCache()


@pytest_asyncio.fixture
async def process_cache(clean_redis, worker_id, request) -> ProcessCache:
    """Provide a ProcessCache instance with ultra-strong test isolation."""
    import time
    import uuid
    import hashlib
    
    # Create ultra-unique prefix for this test
    test_name = request.node.name
    test_file = os.path.basename(request.node.fspath)
    timestamp_ns = time.time_ns()
    process_id = os.getpid()
    unique_id = uuid.uuid4().hex
    
    full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
    prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:20]
    test_prefix = f"test_{worker_id}_{prefix_hash}"
    
    cache = ProcessCache()
    original_prefixes = {}
    
    # Apply isolation to all prefix attributes
    if hasattr(cache, '_cache') and hasattr(cache._cache, 'key_prefix'):
        original_prefixes['_cache'] = cache._cache.key_prefix
        cache._cache.key_prefix = f"{test_prefix}:{cache._cache.key_prefix}" if cache._cache.key_prefix else test_prefix
    if hasattr(cache, 'key_prefix'):
        original_prefixes['self'] = cache.key_prefix
        cache.key_prefix = f"{test_prefix}:{cache.key_prefix}" if cache.key_prefix else test_prefix

    yield cache

    # Ultra-aggressive cleanup after test
    try:
        if hasattr(cache, '_cache'):
            await cache._cache.delete_pattern(f"{test_prefix}:*")
            await cache._cache.delete_pattern(f"{test_prefix}")
        # Clean any leaked keys
        cleanup_patterns = [f"*{test_name}*", f"*{worker_id}*{timestamp_ns}*"]
        for pattern in cleanup_patterns:
            try:
                if hasattr(cache, '_cache'):
                    await cache._cache.delete_pattern(pattern)
            except:
                pass
    except:
        pass
    finally:
        # Restore original prefixes
        try:
            if '_cache' in original_prefixes and hasattr(cache, '_cache'):
                cache._cache.key_prefix = original_prefixes['_cache']
            if 'self' in original_prefixes:
                cache.key_prefix = original_prefixes['self']
        except:
            pass


@pytest_asyncio.fixture
async def tick_cache(clean_redis, worker_id, request) -> TickCache:
    """Provide a TickCache instance with ultra-strong test isolation."""
    import time
    import uuid
    import hashlib
    
    # Create ultra-unique prefix for this test
    test_name = request.node.name
    test_file = os.path.basename(request.node.fspath)
    timestamp_ns = time.time_ns()
    process_id = os.getpid()
    unique_id = uuid.uuid4().hex
    
    full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
    prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:20]
    test_prefix = f"test_{worker_id}_{prefix_hash}"
    
    cache = TickCache()
    original_prefixes = {}
    
    # Apply isolation to all prefix attributes
    if hasattr(cache, '_cache') and hasattr(cache._cache, 'key_prefix'):
        original_prefixes['_cache'] = cache._cache.key_prefix
        cache._cache.key_prefix = f"{test_prefix}:{cache._cache.key_prefix}" if cache._cache.key_prefix else test_prefix
    if hasattr(cache, 'key_prefix'):
        original_prefixes['self'] = cache.key_prefix
        cache.key_prefix = f"{test_prefix}:{cache.key_prefix}" if cache.key_prefix else test_prefix

    yield cache

    # Ultra-aggressive cleanup after test
    try:
        if hasattr(cache, '_cache'):
            await cache._cache.delete_pattern(f"{test_prefix}:*")
            await cache._cache.delete_pattern(f"{test_prefix}")
        # Clean any leaked keys including tickers patterns
        cleanup_patterns = [
            f"*{test_name}*", 
            f"*{worker_id}*{timestamp_ns}*",
            f"tickers:*{worker_id}*",
            f"*tick*{worker_id}*"
        ]
        for pattern in cleanup_patterns:
            try:
                if hasattr(cache, '_cache'):
                    await cache._cache.delete_pattern(pattern)
            except:
                pass
    except:
        pass
    finally:
        # Restore original prefixes
        try:
            if '_cache' in original_prefixes and hasattr(cache, '_cache'):
                cache._cache.key_prefix = original_prefixes['_cache']
            if 'self' in original_prefixes:
                cache.key_prefix = original_prefixes['self']
        except:
            pass


@pytest_asyncio.fixture
async def orders_cache(clean_redis, worker_id, request) -> OrdersCache:
    """Provide an OrdersCache instance with ultra-strong test isolation."""
    import time
    import uuid
    import hashlib
    
    # Create ultra-unique prefix for this test
    test_name = request.node.name
    test_file = os.path.basename(request.node.fspath)
    timestamp_ns = time.time_ns()
    process_id = os.getpid()
    unique_id = uuid.uuid4().hex
    
    full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
    prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:20]
    test_prefix = f"test_{worker_id}_{prefix_hash}"
    
    cache = OrdersCache()
    original_prefixes = {}
    
    # Apply isolation to all prefix attributes
    if hasattr(cache, '_cache') and hasattr(cache._cache, 'key_prefix'):
        original_prefixes['_cache'] = cache._cache.key_prefix
        cache._cache.key_prefix = f"{test_prefix}:{cache._cache.key_prefix}" if cache._cache.key_prefix else test_prefix
    if hasattr(cache, 'key_prefix'):
        original_prefixes['self'] = cache.key_prefix
        cache.key_prefix = f"{test_prefix}:{cache.key_prefix}" if cache.key_prefix else test_prefix

    yield cache

    # Ultra-aggressive cleanup after test
    try:
        if hasattr(cache, '_cache'):
            await cache._cache.delete_pattern(f"{test_prefix}:*")
            await cache._cache.delete_pattern(f"{test_prefix}")
        # Clean any leaked keys including order patterns
        cleanup_patterns = [
            f"*{test_name}*", 
            f"*{worker_id}*{timestamp_ns}*",
            f"order*{worker_id}*",
            f"*ORDER*{worker_id}*"
        ]
        for pattern in cleanup_patterns:
            try:
                if hasattr(cache, '_cache'):
                    await cache._cache.delete_pattern(pattern)
            except:
                pass
    except:
        pass
    finally:
        # Restore original prefixes
        try:
            if '_cache' in original_prefixes and hasattr(cache, '_cache'):
                cache._cache.key_prefix = original_prefixes['_cache']
            if 'self' in original_prefixes:
                cache.key_prefix = original_prefixes['self']
        except:
            pass


def create_isolated_cache_fixture(cache_class):
    """Helper to create ultra-isolated cache fixtures with maximum separation."""
    @pytest_asyncio.fixture
    async def cache_fixture(clean_redis, worker_id, request):
        import time
        import uuid
        import hashlib
        
        # Create ultra-unique prefix for this test with nanosecond precision
        test_name = request.node.name
        test_file = os.path.basename(request.node.fspath)
        timestamp_ns = time.time_ns()
        process_id = os.getpid()
        unique_id = uuid.uuid4().hex
        
        # Create hash-based prefix for reasonable key length but maximum uniqueness
        full_identifier = f"{worker_id}_{test_file}_{test_name}_{timestamp_ns}_{process_id}_{unique_id}"
        prefix_hash = hashlib.sha256(full_identifier.encode()).hexdigest()[:20]
        test_prefix = f"test_{worker_id}_{prefix_hash}"
        
        cache = cache_class()
        original_prefixes = {}
        
        # Apply ultra-isolation to all possible prefix locations
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'key_prefix'):
            original_prefixes['_cache_key_prefix'] = cache._cache.key_prefix
            cache._cache.key_prefix = f"{test_prefix}:{cache._cache.key_prefix}" if cache._cache.key_prefix else test_prefix
        
        if hasattr(cache, 'key_prefix'):
            original_prefixes['key_prefix'] = cache.key_prefix
            cache.key_prefix = f"{test_prefix}:{cache.key_prefix}" if cache.key_prefix else test_prefix
            
        if hasattr(cache, '_key_prefix'):
            original_prefixes['_key_prefix'] = cache._key_prefix
            cache._key_prefix = f"{test_prefix}:{cache._key_prefix}" if cache._key_prefix else test_prefix

        yield cache

        # Ultra-aggressive cleanup after test
        try:
            # Pattern 1: Clean our specific prefix
            if hasattr(cache, '_cache'):
                await cache._cache.delete_pattern(f"{test_prefix}:*")
                await cache._cache.delete_pattern(f"{test_prefix}")
            
            # Pattern 2: Clean any leaked keys with test identifiers
            cleanup_patterns = [
                f"*{test_name}*",
                f"*{worker_id}*{timestamp_ns}*",
                f"test_*{worker_id}*",
            ]
            
            for pattern in cleanup_patterns:
                try:
                    if hasattr(cache, '_cache'):
                        await cache._cache.delete_pattern(pattern)
                except:
                    pass
                    
        except Exception:
            pass
        finally:
            # Restore all original prefixes
            try:
                if '_cache_key_prefix' in original_prefixes and hasattr(cache, '_cache'):
                    cache._cache.key_prefix = original_prefixes['_cache_key_prefix']
                if 'key_prefix' in original_prefixes:
                    cache.key_prefix = original_prefixes['key_prefix']
                if '_key_prefix' in original_prefixes:
                    cache._key_prefix = original_prefixes['_key_prefix']
            except:
                pass
    
    return cache_fixture

# Create isolated fixtures for all cache types
account_cache = create_isolated_cache_fixture(AccountCache)
bot_cache = create_isolated_cache_fixture(BotCache)
trades_cache = create_isolated_cache_fixture(TradesCache)
ohlcv_cache = create_isolated_cache_fixture(OHLCVCache)


# Keep the symbol cache simple since it's working



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
def mock_database_connection_only():
    """Mock only database connection for fullon_orm - extreme case mocking.
    
    This is the minimal mocking needed to prevent database connection errors
    while keeping all other behavior real. Only the database session is mocked,
    all other objects are real fullon_orm models and repositories.
    """
    from fullon_orm.models import Exchange, CatExchange
    
    # Create simple mock objects that behave like CatExchange for testing
    class MockCatExchange:
        def __init__(self, name, cat_ex_id):
            self.name = name
            self.cat_ex_id = cat_ex_id
    
    test_exchanges = [
        MockCatExchange("binance", 1),
        MockCatExchange("kraken", 2)
    ]
    
    # Mock DatabaseContext to return real exchange data
    # We need to patch DatabaseContext which is the new API
    with patch('fullon_orm.DatabaseContext') as mock_db_context_class:
        # Create a mock DatabaseContext instance
        mock_db_instance = Mock()

        # Create mock repository
        mock_ex_repo = Mock()

        # Set async methods properly - be very explicit
        async def mock_get_cat_exchanges(all=True):
            return test_exchanges

        async def mock_get_exchange_by_name(name):
            for ex in test_exchanges:
                if ex.name == name:
                    return ex
            return None

        mock_ex_repo.get_cat_exchanges = mock_get_cat_exchanges
        mock_ex_repo.get_exchange_by_name = mock_get_exchange_by_name

        # Set up the exchanges property on the DatabaseContext
        mock_db_instance.exchanges = mock_ex_repo

        # Mock commit, rollback, flush
        async def mock_commit():
            pass
        async def mock_rollback():
            pass
        async def mock_flush():
            pass

        mock_db_instance.commit = mock_commit
        mock_db_instance.rollback = mock_rollback
        mock_db_instance.flush = mock_flush

        # Make DatabaseContext a proper async context manager
        async def mock_aenter(self):
            return mock_db_instance

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            pass

        mock_db_context_class.return_value.__aenter__ = mock_aenter
        mock_db_context_class.return_value.__aexit__ = mock_aexit

        yield


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
