"""Testing guide for Fullon Cache."""

GUIDE = """
Fullon Cache - Testing Guide
============================

This guide covers testing strategies, fixtures, and best practices for
achieving 100% test coverage.

Testing Philosophy
------------------

1. **No Mocking**: Use real Redis instances for authentic testing
2. **Parallel Support**: Tests must run in parallel without conflicts
3. **100% Coverage**: Every line, every branch must be tested
4. **Fast Execution**: Tests should complete quickly

Test Environment Setup
----------------------

1. **Redis Configuration for Tests**

   Create `.env.test`:
       REDIS_HOST=localhost
       REDIS_PORT=6379
       REDIS_DB=1  # Don't use DB 0 (production)
       REDIS_MAX_CONNECTIONS=10
       
   Load test environment:
       # In conftest.py
       from dotenv import load_dotenv
       load_dotenv('.env.test')

2. **Parallel Test Isolation**

   Each test worker gets its own Redis DB:
       
       @pytest.fixture
       async def redis_db(worker_id):
           '''Allocate unique Redis DB per test worker'''
           if worker_id == "master":
               db_num = 1
           else:
               # worker_id is like "gw0", "gw1", etc.
               db_num = int(worker_id[2:]) + 2
               
           # Ensure DB number is within Redis limit (1-15)
           db_num = (db_num % 15) + 1
           
           return db_num

3. **Auto-cleanup Fixture**

       @pytest.fixture
       async def cache(redis_db):
           '''Provide clean cache instance for each test'''
           # Set environment for this test
           os.environ['REDIS_DB'] = str(redis_db)
           
           # Create cache instance
           cache = TickCache()
           
           # Ensure clean state
           await cache.flushdb()
           
           yield cache
           
           # Cleanup after test
           await cache.flushdb()

Writing Effective Tests
-----------------------

1. **Test Structure** (Arrange-Act-Assert)

       async def test_ticker_update_and_retrieve(cache):
           # Arrange
           exchange = "binance"
           symbol = "BTC/USDT"
           ticker_data = {
               "bid": 50000.0,
               "ask": 50001.0,
               "last": 50000.5,
               "timestamp": "2024-01-01T00:00:00Z"
           }
           
           # Act
           await cache.update_ticker(exchange, symbol, ticker_data)
           result = await cache.get_ticker(exchange, symbol)
           
           # Assert
           assert result is not None
           assert result.last == 50000.5
           assert result.symbol == symbol

2. **Edge Cases and Error Conditions**

       async def test_ticker_not_found(cache):
           '''Test cache miss behavior'''
           result = await cache.get_ticker("unknown", "XXX/YYY")
           assert result is None
           
       async def test_invalid_data_handling(cache):
           '''Test serialization errors'''
           with pytest.raises(SerializationError):
               await cache.set_json("key", object())  # Non-serializable
               
       async def test_connection_failure():
           '''Test Redis connection errors'''
           os.environ['REDIS_PORT'] = '99999'  # Invalid port
           
           with pytest.raises(ConnectionError):
               cache = BaseCache()
               await cache.ping()

3. **Concurrency Testing**

       async def test_concurrent_updates(cache):
           '''Test race conditions'''
           async def update_ticker(n):
               await cache.update_ticker(
                   "binance", 
                   "BTC/USDT",
                   {"last": n}
               )
               
           # Run 100 concurrent updates
           await asyncio.gather(*[update_ticker(i) for i in range(100)])
           
           # Verify last update wins
           ticker = await cache.get_ticker("binance", "BTC/USDT")
           assert ticker.last in range(100)

4. **Pub/Sub Testing**

       async def test_ticker_subscription(cache):
           '''Test real-time updates'''
           received = []
           
           async def subscriber():
               async for ticker in cache.ticker_stream("binance", "BTC/USDT"):
                   received.append(ticker)
                   if len(received) >= 3:
                       break
                       
           # Start subscriber
           sub_task = asyncio.create_task(subscriber())
           
           # Give subscriber time to connect
           await asyncio.sleep(0.1)
           
           # Publish updates
           for i in range(3):
               await cache.update_ticker(
                   "binance", 
                   "BTC/USDT", 
                   {"last": 50000 + i}
               )
               
           # Wait for subscriber
           await sub_task
           
           assert len(received) == 3
           assert [t.last for t in received] == [50000, 50001, 50002]

5. **Stream Testing**

       async def test_order_queue_fifo(cache):
           '''Test queue order preservation'''
           orders = [
               {"order_id": f"ORD{i}", "price": i}
               for i in range(10)
           ]
           
           # Push orders
           for order in orders:
               await cache.push_order(order)
               
           # Pop and verify order
           popped = []
           while order := await cache.pop_order("binance", timeout=1):
               popped.append(order)
               
           assert len(popped) == 10
           assert [o.order_id for o in popped] == [f"ORD{i}" for i in range(10)]

Coverage Techniques
-------------------

1. **Branch Coverage**

   Test all code paths:
       
       # Function to test
       async def get_price(self, exchange, symbol, default=None):
           ticker = await self.get_ticker(exchange, symbol)
           if ticker:
               return ticker.last
           return default
           
       # Tests covering all branches
       async def test_get_price_exists(cache):
           await cache.update_ticker("binance", "BTC/USDT", {"last": 50000})
           price = await cache.get_price("binance", "BTC/USDT")
           assert price == 50000
           
       async def test_get_price_not_exists(cache):
           price = await cache.get_price("binance", "XXX/YYY", default=0)
           assert price == 0

2. **Exception Coverage**

   Test error handling:
       
       async def test_redis_errors(cache, monkeypatch):
           # Simulate Redis error
           async def mock_get(*args):
               raise redis.RedisError("Connection lost")
               
           monkeypatch.setattr(cache._redis, "get", mock_get)
           
           with pytest.raises(CacheError):
               await cache.get("key")

3. **Parametrized Tests**

   Test multiple scenarios efficiently:
       
       @pytest.mark.parametrize("exchange,symbol,expected", [
           ("binance", "BTC/USDT", True),
           ("kraken", "ETH/USD", True),
           ("", "BTC/USDT", False),  # Invalid exchange
           ("binance", "", False),    # Invalid symbol
           (None, None, False),       # None values
       ])
       async def test_ticker_validation(cache, exchange, symbol, expected):
           if expected:
               await cache.update_ticker(exchange, symbol, {"last": 100})
               assert await cache.get_ticker(exchange, symbol) is not None
           else:
               with pytest.raises(ValueError):
                   await cache.update_ticker(exchange, symbol, {"last": 100})

Performance Testing
-------------------

Ensure operations meet performance requirements:

    async def test_ticker_performance(cache, benchmark):
        '''Verify <1ms cache hits'''
        # Prepare data
        await cache.update_ticker("binance", "BTC/USDT", {"last": 50000})
        
        # Benchmark get operation
        result = await benchmark(cache.get_ticker, "binance", "BTC/USDT")
        
        assert result.last == 50000
        assert benchmark.stats['mean'] < 0.001  # <1ms average

Integration Testing
-------------------

Test complete workflows:

    async def test_trading_workflow(tick_cache, orders_cache, account_cache):
        '''Test realistic trading scenario'''
        user_id = 123
        exchange = "binance"
        symbol = "BTC/USDT"
        
        # 1. Update market data
        await tick_cache.update_ticker(exchange, symbol, {
            "bid": 49900,
            "ask": 50100,
            "last": 50000
        })
        
        # 2. Check account
        await account_cache.update_account(user_id, exchange, {
            "balance": {"USDT": 10000, "BTC": 0}
        })
        
        # 3. Place order
        order = {
            "order_id": "ORD123",
            "user_id": user_id,
            "symbol": symbol,
            "side": "buy",
            "amount": 0.1,
            "price": 49900
        }
        await orders_cache.push_order(order)
        
        # 4. Process order
        popped = await orders_cache.pop_order(exchange)
        assert popped.order_id == "ORD123"
        
        # 5. Update position
        await account_cache.upsert_position(user_id, exchange, symbol, {
            "side": "long",
            "amount": 0.1,
            "entry_price": 49900
        })
        
        # Verify final state
        position = await account_cache.get_position(user_id, exchange, symbol)
        assert position.amount == 0.1

Test Utilities
--------------

Create test data factories:

    class TickerFactory:
        @staticmethod
        def create(**kwargs):
            defaults = {
                "bid": 50000.0,
                "ask": 50001.0,
                "last": 50000.5,
                "volume": 1234.56,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return {**defaults, **kwargs}
            
    class OrderFactory:
        @staticmethod
        def create(**kwargs):
            defaults = {
                "order_id": f"ORD{random.randint(1000, 9999)}",
                "symbol": "BTC/USDT",
                "side": "buy",
                "amount": 0.1,
                "price": 50000,
                "type": "limit"
            }
            return {**defaults, **kwargs}

Running Tests
-------------

    # Run all tests with coverage
    pytest --cov=fullon_cache --cov-report=html --cov-report=term-missing
    
    # Run specific test file
    pytest tests/test_tick_cache.py -v
    
    # Run in parallel
    pytest -n auto
    
    # Run with specific Redis DB
    REDIS_DB=5 pytest
    
    # Generate coverage badge
    pytest --cov=fullon_cache --cov-report=json
    coverage-badge -o coverage.svg

Debugging Failed Tests
----------------------

1. **Enable Redis Monitor**
   
       redis-cli MONITOR  # In separate terminal

2. **Add Logging**
   
       from fullon_log import get_component_logger
       logger = get_component_logger("fullon.cache.tests", level="DEBUG")

3. **Use pytest-asyncio markers**
   
       @pytest.mark.asyncio
       @pytest.mark.timeout(5)  # Prevent hanging
       async def test_something():
           pass

4. **Inspect Redis State**
   
       async def test_debug(cache):
           await cache.set("key", "value")
           
           # Inspect Redis directly
           keys = [k async for k in cache.scan_keys("*")]
           print(f"Keys in Redis: {keys}")
           
           info = await cache.info()
           print(f"Redis info: {info}")

Common Testing Pitfalls
-----------------------

1. **State Leakage**: Always clean up after tests
2. **Timing Issues**: Use proper waits for async operations
3. **Resource Exhaustion**: Limit connection pools in tests
4. **Flaky Tests**: Avoid time-dependent assertions
5. **Missing Cleanup**: Ensure fixtures clean up properly

Coverage Reports
----------------

Achieve and maintain 100% coverage:

1. Check coverage regularly:
   
       coverage report --show-missing

2. Find untested code:
   
       coverage html
       open htmlcov/index.html

3. Exclude untestable code sparingly:
   
       if TYPE_CHECKING:  # pragma: no cover
           from typing import ...

4. Test edge cases and errors:
   - Connection failures
   - Serialization errors  
   - Concurrent access
   - Resource exhaustion
   - Invalid inputs
"""
