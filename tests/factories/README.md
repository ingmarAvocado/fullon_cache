# Test Factories

This folder contains factory classes for generating test data with sensible defaults and proper typing.

## Overview

Each factory provides methods to create test data for different cache modules:

- **TickerFactory**: Creates ticker/price data for testing TickCache
- **OrderFactory**: Creates order data for testing OrdersCache
- **ProcessFactory**: Creates process monitoring data for testing ProcessCache
- **SymbolFactory**: Creates trading symbol data for testing SymbolCache
- **TradeFactory**: Creates trade execution data for testing TradesCache
- **OHLCVFactory**: Creates candlestick/OHLCV data for testing OHLCVCache
- **AccountFactory**: Creates account data for testing AccountCache
- **PositionFactory**: Creates position data for testing AccountCache positions
- **BotFactory**: Creates bot configuration data for testing BotCache

## Usage

Import factories in your tests:

```python
from tests.factories import TickerFactory, OrderFactory

def test_ticker_processing():
    factory = TickerFactory()
    
    # Create a single ticker
    ticker = factory.create(
        symbol="BTC/USDT",
        bid=50000.0,
        ask=50001.0
    )
    
    # Create a ticker with specific spread
    ticker = factory.create_spread(
        base_price=50000,
        spread_percent=0.1
    )
    
    # Create multiple tickers
    tickers = factory.create_batch(count=10, exchange="binance")
```

## Factory Methods

### Common Pattern

All factories follow a similar pattern:

1. `create(**kwargs)` - Main method to create data with defaults
2. Specialized creation methods for common scenarios
3. `create_batch()` - Create multiple instances
4. Helper methods for specific test cases

### Examples

#### TickerFactory

```python
factory = TickerFactory()

# Basic ticker
ticker = factory.create()

# Volatile ticker
volatile = factory.create_volatile(volatility=10.0)

# Stale ticker (old timestamp)
stale = factory.create_stale(hours_old=24)
```

#### OrderFactory

```python
factory = OrderFactory()

# Limit order
order = factory.create()

# Market order
market = factory.create_market_order(side="buy")

# Filled order
filled = factory.create_filled_order(fill_percent=50.0)

# Order book snapshot
buy_orders, sell_orders = factory.create_order_book_snapshot(
    symbol="BTC/USDT",
    mid_price=50000,
    depth=5
)
```

#### TradeFactory

```python
factory = TradeFactory()

# Single trade
trade = factory.create()

# Trade history
history = factory.create_trade_history(
    user_id=123,
    days=7,
    trades_per_day=10
)

# Arbitrage trades
arb_trades = factory.create_arbitrage_trades(
    exchanges=["binance", "kraken"],
    price_difference=10.0
)
```

## Best Practices

1. **Use factories in fixtures**: Define pytest fixtures that provide factory instances
2. **Override defaults**: Pass kwargs to override any default values
3. **Use specialized methods**: Use specific creation methods for common test scenarios
4. **Maintain consistency**: Keep test data consistent within a test case

## Adding New Factories

To add a new factory:

1. Create a new file in the `factories/` directory
2. Follow the existing pattern with a class containing:
   - `__init__` to initialize any counters
   - `create(**kwargs)` as the main creation method
   - Specialized methods for common scenarios
   - `create_batch()` for multiple instances
3. Add the import to `__init__.py`
4. Add a fixture in `conftest.py`

## Factory Features

### Realistic Data

Factories generate realistic data with proper relationships:
- Prices have appropriate bid/ask spreads
- Orders have computed fields (remaining, cost)
- Trades calculate fees based on maker/taker status
- Positions track P&L correctly

### Time-based Data

Many factories support time-based scenarios:
- Historical data generation
- Stale/old data for timeout testing
- Time series data (OHLCV bars)

### Stateful Generation

Some factories maintain state:
- SymbolFactory uses a counter for unique IDs
- OrderFactory generates unique order IDs with timestamps
- ProcessFactory tracks component names

### Integration Support

Factories work well together:
- Create orders that match trades
- Generate positions from trades
- Build complete account snapshots