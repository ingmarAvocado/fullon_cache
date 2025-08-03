# Fullon Cache System - Documentation

## Project Overview

This is a Redis-based cache library for a cryptocurrency trading system. The cache serves as a high-performance data layer that sits between the trading bots/services and the PostgreSQL database, providing real-time data access and reducing database load.

## Core Features

The fullon_cache system provides a modern, production-ready cache implementation with the following characteristics:

1. **Uses fullon_orm models** for consistent data modeling across the system
2. **Comprehensive testing** without mocking (except for extreme cases like Redis corruption)
3. **Supports parallel testing** with isolated test environments
4. **Follows modern Python best practices** with type hints, async/await, and proper error handling
5. **Maintains backward compatibility** while providing improved architecture
6. **Fully self-documenting** - any LLM can understand and use this library without external documentation:
   - Comprehensive docstrings with examples in every module
   - `docs` module with guides accessible via `from fullon_cache.docs import quickstart`
   - `examples` module with runnable code snippets
   - `help(fullon_cache)` provides a complete overview
   - All public methods have detailed docstrings with usage examples
7. **100% test coverage** with HTML reports:
   - Full coverage of all code paths
   - htmlcov/ folder with coverage reports
   - Coverage integrated into CI/CD pipeline
   - No code merged without proper test coverage
8. All timestamp fields are proper Python datetime objects with timezone-aware UTC timestamps as default.
9. **Uses fullon_log for consistent logging** across all fullon components.

## Architecture Overview

The cache system follows a hierarchical inheritance pattern:

```
BaseCache (Redis connection management)
    ├── ProcessCache (Process monitoring)
    │   └── ExchangeCache (Exchange data caching)
    │       └── SymbolCache (Symbol information)
    │           └── TickCache (Real-time ticker data)
    │               └── AccountCache (User account data)
    │                   ├── OrdersCache (Order management)
    │                   │   └── TradesCache (Trade data)
    │                   └── BotCache (Bot status/blocking)
    │                       └── OHLCVCache (Candlestick data)
```

## Key Components to Implement

### 1. BaseCache (`base_cache.py`)
- **Purpose**: Foundation for all cache operations
- **Key Features**:
  - Redis connection pooling with async support
  - Context manager for proper resource cleanup
  - Global error queue management
  - Configurable decoding based on host
- **Critical Methods**:
  - `test()`: Connection health check
  - `prepare_cache()`: Clear all Redis data
  - `get_keys()`: Pattern-based key retrieval
  - `push_global_error()` / `pop_global_error()`: Error queue

### 2. ProcessCache (`process_cache.py`)
- **Purpose**: Monitor and track various system processes
- **Process Types**: `['tick', 'ohlcv', 'bot', 'account', 'order', 'bot_status_service', 'crawler', 'user_trades_service']`
- **Key Features**:
  - Timestamped process entries
  - Process lifecycle management
  - Time-based filtering

### 3. ExchangeCache (`exchange_cache.py`)
- **Purpose**: Cache exchange metadata from PostgreSQL
- **Key Features**:
  - 24-hour TTL for cached data
  - Integration with fullon_orm ExchangeRepository
  - WebSocket error queue management
- **Data Cached**:
  - Exchange configurations
  - Symbol lists per exchange
  - Catalog exchange data

### 4. SymbolCache (`symbol_cache.py`)
- **Purpose**: Symbol information caching
- **Key Features**:
  - Auto-refresh on cache miss
  - Integration with fullon_orm SymbolRepository
  - Symbol deletion with cascade to tickers

### 5. TickCache (`tick_cache.py`)
- **Purpose**: Real-time ticker data with pub/sub
- **Key Features**:
  - Redis pub/sub for real-time updates
  - Price retrieval with exchange preference
  - Currency-specific rounding logic
  - Tick crawler configuration
- **Critical for**: Real-time price feeds

### 6. AccountCache (`account_cache.py`)
- **Purpose**: User account and position management
- **Key Features**:
  - Position tracking with cost basis
  - Account balance caching
  - Integration with fullon_orm models
- **Data Structure**:
  - Positions: Hash with symbol as key
  - Account data: Full account snapshot

### 7. OrdersCache (`orders_cache.py`)
- **Purpose**: Order queue and status management
- **Key Features**:
  - FIFO order queue using Redis lists
  - Order status tracking with expiration
  - Integration with fullon_orm OrderRepository
- **Queue Operations**:
  - `push_open_order()` / `pop_open_order()`
  - Auto-expiration for cancelled orders (1 hour)

### 8. BotCache (`bot_cache.py`)
- **Purpose**: Bot coordination and exchange blocking
- **Key Features**:
  - Prevent multiple bots trading same symbol
  - Position opening state tracking
  - Bot status updates
- **Critical for**: Multi-bot coordination

### 9. TradesCache (`trades_cache.py`)
- **Purpose**: Trade data queuing and status
- **Key Features**:
  - Trade list management (push/pop)
  - Bulk status operations
  - Integration with fullon_orm TradeRepository

### 10. OHLCVCache (`ohlcv_cache.py`)
- **Purpose**: Candlestick data caching
- **Key Features**:
  - OHLCV bar storage as lists
  - Symbol normalization (remove "/")
  - Efficient bulk operations

## Redis Key Conventions

Use hierarchical key naming:
- Format: `type:identifier:subidentifier`
- Examples:
  - `tickers:kraken:BTCUSD`
  - `order_status:123456`
  - `bot_status:bot_1`
  - `positions:user_123:kraken`

## Data Structures

- **Hashes**: Structured data (accounts, positions, tickers)
- **Lists**: Queues (trades, orders, OHLCV)
- **Strings**: Status values, simple data
- **Sets**: Unique collections (active symbols)
- **Pub/Sub**: Real-time ticker updates

## Testing Requirements

### Test Structure
```
tests/
├── conftest.py          # Pytest fixtures, Redis setup
├── test_base_cache.py   # BaseCache tests
├── test_process_cache.py
├── test_exchange_cache.py
├── test_symbol_cache.py
├── test_tick_cache.py
├── test_account_cache.py
├── test_orders_cache.py
├── test_bot_cache.py
├── test_trades_cache.py
└── test_ohlcv_cache.py
```

### Testing Guidelines
1. **No Mocking**: Use real Redis instance (redis-py-test or Docker)
2. **Parallel Support**: Use unique key prefixes per test
3. **Cleanup**: Ensure each test cleans up its data
4. **Integration Tests**: Test inheritance chain works correctly
5. **Performance Tests**: Verify operations are fast enough
6. **Error Scenarios**: Test connection failures, data corruption

### Example Test Pattern
```python
@pytest.mark.asyncio
async def test_cache_operation(redis_fixture):
    cache = TickCache()
    
    # Setup
    await cache.update_ticker("kraken", "BTC/USD", {...})
    
    # Test
    result = await cache.get_ticker("kraken", "BTC/USD")
    assert result.symbol == "BTC/USD"
    
    # Cleanup handled by fixture
```

## Implementation Status

All cache modules have been successfully implemented:

1. **BaseCache**: Foundation with Redis connection management ✓
2. **ProcessCache, ExchangeCache, SymbolCache**: Core caching layers ✓
3. **TickCache**: Real-time ticker data with pub/sub ✓
4. **AccountCache, OrdersCache**: User and order management ✓
5. **BotCache, TradesCache, OHLCVCache**: Bot coordination and market data ✓

## Performance Considerations

- Use Redis pipelines for bulk operations
- Implement connection pooling properly
- Consider using Redis Cluster for scaling
- Monitor memory usage with large datasets
- Use appropriate expiration times

## Error Handling

- All methods should handle Redis connection errors gracefully
- Use the global error queue for critical errors
- Log errors appropriately (use Python logging)
- Return sensible defaults on cache miss

## ORM Integration

The cache system uses fullon_orm models:
- Uses `UserRepository`, `BotRepository`, etc. from fullon_orm
- Maintains model consistency between cache and database
- Uses Pydantic models for validation where appropriate

### Quick Guide to Understanding fullon_orm

**IMPORTANT**: fullon_orm is already installed in this project. Here's how to quickly understand its structure without wasting time:

```bash
# 1. Quick overview of fullon_orm
poetry run python -c "import fullon_orm; help(fullon_orm)"

# 2. See all available documentation
poetry run python -c "from fullon_orm import docs; print(docs.get_all_docs().keys())"

# 3. Read specific documentation
poetry run python -c "from fullon_orm import docs; print(docs.QUICK_START)"
poetry run python -c "from fullon_orm import docs; print(docs.REPOSITORY_USAGE)"

# 4. See all available examples
poetry run python -c "from fullon_orm import examples; print(examples.get_all_examples().keys())"

# 5. View a specific example
poetry run python -c "from fullon_orm import examples; print(examples.BASIC_USAGE)"

# 6. Explore available models
poetry run python -c "import fullon_orm.models; help(fullon_orm.models)"

# 7. Explore available repositories
poetry run python -c "import fullon_orm.repositories; help(fullon_orm.repositories)"
```

### Key Points About fullon_orm Self-Documentation

1. **Everything is in the package**: All docs and examples are Python string constants, not external files
2. **docs module**: Contains constants like `QUICK_START`, `API_REFERENCE`, etc. Access via `from fullon_orm.docs import QUICK_START`
3. **examples module**: Contains runnable code examples as string constants
4. **get_all_docs()** and **get_all_examples()**: Functions that return all documentation/examples as dictionaries
5. **No external files needed**: An LLM can understand the entire library just by importing it

### Pattern to Replicate for fullon_cache

We must follow the exact same pattern:
- Store all documentation as string constants in `docs/__init__.py`
- Store all examples as string constants in `examples/__init__.py`
- Use triple quotes for docs, triple single quotes for code examples
- Provide aggregator functions (`get_all_docs()`, `get_all_examples()`)
- Make everything discoverable through imports and `help()`

## Self-Documenting Structure

The library MUST be structured to be fully discoverable by LLMs:

```python
# Users should be able to discover everything through Python:
import fullon_cache
help(fullon_cache)  # Complete overview

# Documentation module
from fullon_cache.docs import quickstart, api_reference, caching_guide
print(quickstart.GUIDE)
print(api_reference.TICK_CACHE)

# Examples module with runnable code
from fullon_cache.examples import basic_usage, advanced_patterns
import asyncio
asyncio.run(basic_usage.main())

# Every class should have comprehensive docstrings
from fullon_cache import TickCache
help(TickCache)  # Shows complete usage with examples
```

### Documentation Module Structure
```
src/fullon_cache/docs/
├── __init__.py       # Exports all guides
├── quickstart.py     # QUICK_START constant with getting started guide
├── api_reference.py  # Detailed API documentation for each cache
├── caching_guide.py  # Best practices and patterns
├── testing_guide.py  # How to test with this library
└── migration.py      # Migrating from old cache system
```

### Examples Module Structure
```
src/fullon_cache/examples/
├── __init__.py           # Exports all examples
├── basic_usage.py        # Simple cache operations
├── pubsub_example.py     # Ticker pub/sub patterns
├── queue_patterns.py     # Order/trade queue examples
├── bot_coordination.py   # Multi-bot exchange blocking
└── performance_test.py   # Benchmarking cache operations
```

## Testing & Coverage Requirements

### Coverage Goals
- **100% code coverage** is MANDATORY
- Every method, every branch, every edge case
- Use `# pragma: no cover` ONLY for impossible-to-test code (like Redis corruption handlers)

### Coverage Commands
```bash
# Run tests with coverage
poetry run pytest --cov=fullon_cache --cov-report=html --cov-report=term-missing

# View coverage report in browser
open htmlcov/index.html

# Run with coverage thresholds
poetry run pytest --cov=fullon_cache --cov-fail-under=100

# Coverage with branch coverage
poetry run pytest --cov=fullon_cache --cov-branch --cov-report=html
```

### Test Coverage Structure
The `htmlcov/` folder MUST be generated and should show:
- 100% line coverage
- 100% branch coverage  
- Clear indication of which lines are covered
- No untested code paths

### Coverage Configuration
Add to pyproject.toml:
```toml
[tool.coverage.run]
source = ["fullon_cache"]
branch = true
omit = ["*/tests/*", "*/examples/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
show_missing = true
skip_covered = false
```

## Development Commands

```bash
# Install dependencies
poetry install

# Run tests with coverage
poetry run pytest --cov=fullon_cache --cov-report=html --cov-report=term-missing -xvs

# Run specific test file with coverage
poetry run pytest tests/test_tick_cache.py --cov=fullon_cache --cov-report=html -xvs

# Run tests in parallel with coverage
poetry run pytest -n auto --cov=fullon_cache --cov-report=html

# View coverage report
open htmlcov/index.html

# Lint code
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/

# Type checking
poetry run mypy src/ tests/

# Run all checks (add this as a pre-commit hook)
poetry run pytest --cov=fullon_cache --cov-fail-under=100 && poetry run ruff check && poetry run mypy src/
```

## Success Criteria

1. All cache modules implemented with async/await
2. **100% test coverage** - NO EXCEPTIONS:
   - Line coverage: 100%
   - Branch coverage: 100%
   - `htmlcov/` folder must be generated with full reports
   - Coverage badge in README showing 100%
3. Tests run in parallel without conflicts
4. Performance: <1ms for cache hits
5. Proper error handling and logging
6. Clean integration with fullon_orm
7. Backward compatible where possible
8. **Fully self-documenting**:
   - `help(fullon_cache)` provides complete overview
   - `from fullon_cache.docs import quickstart` works
   - `from fullon_cache.examples import basic_usage` provides runnable examples
   - Every public method has docstring with examples
   - An LLM can understand and use the library without any external docs

## Logging with Fullon Log

This project uses fullon-log for consistent, beautiful logging across all fullon components.

### Installation
fullon-log is already included as a dependency in pyproject.toml:
```toml
dependencies = [
    "fullon-log @ git+ssh://git@github.com/ingmarAvocado/fullon_log.git"
]
```

### Basic Usage
All cache modules use component-specific loggers:
```python
from fullon_log import get_component_logger

class TickCache:
    def __init__(self):
        self.logger = get_component_logger("fullon.cache.tick")
    
    def update_ticker(self, exchange: str, symbol: str):
        self.logger.info("Ticker updated", exchange=exchange, symbol=symbol)
```

### Component Logger Names
- `fullon.cache.base` - BaseCache operations
- `fullon.cache.process` - Process monitoring
- `fullon.cache.exchange` - Exchange data caching
- `fullon.cache.tick` - Ticker data operations
- `fullon.cache.orders` - Order management
- `fullon.cache.account` - Account data
- `fullon.cache.bot` - Bot coordination
- `fullon.cache.trades` - Trade data
- `fullon.cache.ohlcv` - OHLCV data
- `fullon.cache.connection` - Redis connections
- `fullon.cache.examples.*` - Example code loggers

### Environment Configuration
Configure logging via .env variables:
```bash
# .env file
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=beautiful              # beautiful, minimal, development, detailed, trading, json
LOG_CONSOLE=true                  # Enable console output
LOG_COLORS=true                   # Enable colored output

# Fullon Cache specific log directory
FULLON_CACHE_LOG_DIR=/tmp/fullon_log  # Default: /tmp/fullon_log/
                                      # Logs saved to: {LOG_DIR}/fullon_cache.log
                                      # Automatic rotation: 10 MB
                                      # Retention: 7 days
```

### Default Log File Location
By default, fullon_cache logs are saved to:
- **File**: `/tmp/fullon_log/fullon_cache.log`
- **Rotation**: 10 MB per file
- **Retention**: 7 days
- **Console**: Also displays on console with beautiful formatting

You can override the log directory:
```bash
# Custom log directory
FULLON_CACHE_LOG_DIR=/var/log/fullon
```

### Structured Logging
Use structured logging with key-value pairs:
```python
logger.info("Cache operation completed", 
           operation="set_ticker", 
           exchange="binance", 
           symbol="BTC/USDT",
           latency_ms=1.2,
           cache_hit=True)
```

## Configuration

This library uses `.env` files for configuration (NOT settings.py or config modules). All configuration is done through environment variables loaded from `.env` files using `python-dotenv`.

### .env File Structure

Create a `.env` file in your project root:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # Optional

# Connection Pool Settings
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Cache TTL Settings (in seconds)
CACHE_TTL_EXCHANGE=86400  # 24 hours
CACHE_TTL_SYMBOL=86400    # 24 hours
CACHE_TTL_ORDER=3600      # 1 hour for cancelled orders

# Redis Cluster Mode (optional)
REDIS_CLUSTER_MODE=false
REDIS_CLUSTER_NODES=localhost:7000,localhost:7001,localhost:7002
```

### Loading Configuration

The library should automatically load `.env` files:

```python
# In base_cache.py
from dotenv import load_dotenv
import os

# Load .env file automatically
load_dotenv()

class BaseCache:
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD')
        # ... etc
```

### Testing with Different Configurations

For testing, use separate `.env.test` files:

```bash
# Run tests with test configuration
DOTENV_FILE=.env.test poetry run pytest

# Or set inline for CI/CD
REDIS_HOST=localhost REDIS_PORT=6380 poetry run pytest
```

### Important Notes on Configuration

- **NO settings.py**: We use `.env` files exclusively
- **Auto-loading**: The library should load `.env` automatically when imported
- **Test isolation**: Tests should use different Redis DB numbers to avoid conflicts
- **Defaults**: Always provide sensible defaults when env vars are missing

## Technical Details

- Fully async implementation using aioredis
- Redis Streams can be used for queue operations where appropriate
- Circuit breakers for Redis failures can be implemented
- Monitoring hooks available for production use
