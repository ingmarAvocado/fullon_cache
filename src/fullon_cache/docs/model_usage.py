"""Model Usage Guide for Fullon Cache.

This module provides comprehensive guidance on using fullon_orm models
with fullon_cache for type-safe, efficient cache operations.
"""

MODEL_USAGE_GUIDE = """
Fullon Cache Model Usage Guide
==============================

This guide demonstrates how to effectively use fullon_orm models with fullon_cache
for type-safe, maintainable, and efficient cache operations.

## Why Use fullon_orm Models?

### Type Safety
fullon_orm models provide compile-time type checking and IDE support:

    # Type-safe model creation
    from fullon_orm.models import Tick
    
    tick = Tick(
        symbol="BTC/USDT",
        exchange="binance",
        price=50000.0,  # IDE knows this should be float
        volume=1234.56,
        time=time.time(),
        bid=49999.0,
        ask=50001.0,
        last=50000.0
    )
    
    # Automatic validation
    # tick.price = "invalid"  # Would raise ValidationError

### Data Consistency
Models ensure consistent data structure across your application:

    # All Position objects have the same structure
    position = Position(
        symbol="BTC/USDT",
        cost=25000.0,
        volume=0.5,
        fee=25.0,
        price=50000.0,
        timestamp=time.time(),
        ex_id="123"
    )
    
    # Guaranteed attributes
    assert hasattr(position, 'volume')
    assert hasattr(position, 'cost')

### IDE Support
Rich autocompletion and error detection:

    # IDE provides autocompletion for all model attributes
    tick.price     # ✓ Available
    tick.volume    # ✓ Available  
    tick.invalid   # ✗ IDE warns about unknown attribute

## Core Models Reference

### Tick Model
Real-time market data representation:

    from fullon_orm.models import Tick
    
    tick = Tick(
        symbol="BTC/USDT",          # Trading pair
        exchange="binance",         # Exchange name
        price=50000.0,             # Current price
        volume=1234.56,            # Volume at this price
        time=time.time(),          # Unix timestamp
        bid=49999.0,               # Optional: Bid price
        ask=50001.0,               # Optional: Ask price
        last=50000.0               # Optional: Last trade price
    )
    
    # Computed properties
    spread = tick.spread           # ask - bid
    spread_pct = tick.spread_percentage  # (spread / mid_price) * 100

### Position Model
Trading position representation:

    from fullon_orm.models import Position
    
    position = Position(
        symbol="BTC/USDT",         # Trading pair
        cost=25000.0,              # Total cost of position
        volume=0.5,                # Position size
        fee=25.0,                  # Trading fees
        price=50000.0,             # Average entry price
        timestamp=time.time(),     # Position timestamp
        ex_id="123",               # Exchange ID
        side="long"                # Optional: Position side
    )

### Order Model
Trading order representation:

    from fullon_orm.models import Order
    
    order = Order(
        ex_order_id="EX_12345",    # Exchange order ID
        symbol="BTC/USDT",         # Trading pair
        side="buy",                # Order side
        volume=0.1,                # Order volume
        price=50000.0,             # Order price
        status="open",             # Order status
        order_type="limit",        # Order type
        exchange="binance",        # Exchange name
        timestamp=datetime.now(UTC) # Order timestamp
    )

### Trade Model
Executed trade representation:

    from fullon_orm.models import Trade
    
    trade = Trade(
        trade_id=12345,            # Internal trade ID
        ex_trade_id="EX_TRD_001",  # Exchange trade ID
        ex_order_id="EX_ORD_001",  # Related order ID
        symbol="BTC/USDT",         # Trading pair
        side="buy",                # Trade side
        volume=0.1,                # Trade volume
        price=50000.0,             # Trade price
        cost=5000.0,               # Total cost
        fee=5.0,                   # Trading fee
        time=datetime.now(UTC)     # Trade timestamp
    )

### Symbol Model
Trading symbol metadata:

    from fullon_orm.models import Symbol
    
    symbol = Symbol(
        symbol="BTC/USDT",         # Trading pair
        base="BTC",                # Base currency
        quote="USDT",              # Quote currency
        cat_ex_id=1,               # Exchange catalog ID
        decimals=8,                # Price precision
        updateframe="1h",          # OHLCV timeframe
        backtest=30,               # Historical data days
        futures=False,             # Futures contract flag
        only_ticker=False          # Ticker-only flag
    )

## Best Practices

### 1. Always Use Models for New Code

    # ✓ Recommended: Use models
    tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0, ...)
    await tick_cache.update_ticker("binance", tick)
    
    # ✗ Avoid: Direct dictionaries
    await tick_cache.update_ticker_legacy("binance", "BTC/USDT", {"price": 50000.0})

### 2. Leverage Model Validation

    # Models validate data automatically
    try:
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price="invalid",  # Will raise ValidationError
            volume=1234.56,
            time=time.time()
        )
    except ValidationError as e:
        logger.error(f"Invalid tick data: {e}")

### 3. Use Model Methods

    # Convert to/from dictionaries when needed
    tick_dict = tick.to_dict()
    restored_tick = Tick.from_dict(tick_dict)
    
    # Models provide useful methods
    position_dict = position.to_dict()
    order_json = json.dumps(order.to_dict())

### 4. Handle Optional Fields Properly

    # Check for optional fields before using
    if tick.bid is not None and tick.ask is not None:
        spread = tick.spread
        print(f"Spread: {spread}")
    
    # Use defaults for missing optional fields
    bid_price = tick.bid or tick.price
    ask_price = tick.ask or tick.price

## Migration Patterns

### From Dictionary to Model

    # Old dictionary-based approach
    old_ticker_data = {
        "symbol": "BTC/USDT",
        "price": 50000.0,
        "volume": 1234.56,
        "timestamp": time.time()
    }
    
    # New model-based approach
    tick = Tick(
        symbol="BTC/USDT",
        exchange="binance",  # Required in model
        price=50000.0,
        volume=1234.56,
        time=time.time()  # Note: 'time' not 'timestamp'
    )

### Gradual Migration Strategy

    # 1. Start by converting data structures
    def dict_to_tick(data: dict, exchange: str) -> Tick:
        return Tick(
            symbol=data["symbol"],
            exchange=exchange,
            price=data["price"],
            volume=data.get("volume", 0.0),
            time=data.get("timestamp", time.time()),
            bid=data.get("bid"),
            ask=data.get("ask"),
            last=data.get("last")
        )
    
    # 2. Use conversion functions during transition
    legacy_data = get_legacy_ticker_data()
    tick = dict_to_tick(legacy_data, "binance")
    await tick_cache.update_ticker("binance", tick)
    
    # 3. Eventually remove conversion and use models directly

## Error Handling

### Model Validation Errors

    from pydantic import ValidationError
    
    try:
        # This will fail validation
        tick = Tick(
            symbol="",  # Empty symbol
            exchange="binance", 
            price=-100.0,  # Negative price
            volume=1234.56,
            time=time.time()
        )
    except ValidationError as e:
        print("Validation errors:")
        for error in e.errors():
            print(f"  {error['loc']}: {error['msg']}")

### Cache Operation Errors

    try:
        tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0, 
                   volume=100.0, time=time.time())
        success = await tick_cache.update_ticker("binance", tick)
        if not success:
            logger.warning("Failed to update ticker")
    except Exception as e:
        logger.error(f"Cache error: {e}")

## Performance Considerations

### Model Creation Overhead

    # Models have minimal overhead compared to dictionaries
    # Benchmark results (typical):
    # - Dict creation: ~0.001ms
    # - Model creation: ~0.003ms
    # - Cache operation: ~0.5-2ms
    # Model overhead is negligible compared to Redis operations

### Batch Operations

    # Create models in batches for better performance
    ticks = []
    for symbol_data in market_data:
        tick = Tick(
            symbol=symbol_data["symbol"],
            exchange="binance",
            price=symbol_data["price"],
            volume=symbol_data["volume"],
            time=time.time()
        )
        ticks.append(tick)
    
    # Process in batch
    for tick in ticks:
        await tick_cache.update_ticker("binance", tick)

### Memory Usage

    # Models use slightly more memory than dicts
    # But provide significant benefits:
    # - Type safety prevents runtime errors
    # - IDE support improves development speed
    # - Consistent structure reduces bugs

## Integration Examples

### Complete Trading Workflow

    async def execute_trade_workflow():
        # Initialize caches
        symbol_cache = SymbolCache()
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        account_cache = AccountCache()
        
        try:
            # 1. Setup symbol
            symbol = Symbol(
                symbol="BTC/USDT",
                base="BTC", 
                quote="USDT",
                cat_ex_id=1,
                decimals=8
            )
            await symbol_cache.add_symbol(symbol)
            
            # 2. Get market data
            tick = await tick_cache.get_ticker("BTC/USDT", "binance")
            if not tick:
                print("No market data available")
                return
            
            # 3. Create order
            order = Order(
                ex_order_id="ORD_001",
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=tick.price,
                status="open",
                order_type="market",
                exchange="binance",
                timestamp=datetime.now(UTC)
            )
            await orders_cache.save_order("binance", order)
            
            # 4. Simulate order fill
            order.status = "filled"
            order.final_volume = 0.1
            await orders_cache.update_order("binance", order)
            
            # 5. Record trade
            trade = Trade(
                trade_id=1,
                ex_trade_id="TRD_001",
                ex_order_id="ORD_001",
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=tick.price,
                cost=0.1 * tick.price,
                fee=5.0,
                time=datetime.now(UTC)
            )
            await trades_cache.push_trade("binance", trade)
            
            # 6. Update position
            position = Position(
                symbol="BTC/USDT",
                cost=0.1 * tick.price,
                volume=0.1,
                fee=5.0,
                price=tick.price,
                timestamp=time.time(),
                ex_id="123"
            )
            await account_cache.upsert_positions(123, [position])
            
            print("Trading workflow completed successfully!")
            
        finally:
            # Cleanup
            await symbol_cache.close()
            await tick_cache.close()
            await orders_cache.close()
            await trades_cache.close()
            await account_cache.close()

### Real-time Data Processing

    async def process_market_feed():
        tick_cache = TickCache()
        
        try:
            # Process incoming market data
            market_updates = get_market_feed()  # Your data source
            
            for update in market_updates:
                # Convert to model
                tick = Tick(
                    symbol=update["symbol"],
                    exchange=update["exchange"],
                    price=update["price"],
                    volume=update["volume"],
                    time=update["timestamp"],
                    bid=update.get("bid"),
                    ask=update.get("ask"),
                    last=update.get("last")
                )
                
                # Validate and cache
                await tick_cache.update_ticker(tick.exchange, tick)
                
                # Use computed properties
                if tick.spread is not None:
                    if tick.spread_percentage > 1.0:  # 1% spread
                        logger.warning(f"Wide spread on {tick.symbol}: {tick.spread_percentage:.2f}%")
                        
        finally:
            await tick_cache.close()

## Testing with Models

### Unit Test Examples

    import pytest
    from fullon_orm.models import Tick
    from fullon_cache import TickCache
    
    @pytest.mark.asyncio
    async def test_tick_cache_with_models():
        cache = TickCache()
        
        try:
            # Create test tick
            tick = Tick(
                symbol="BTC/USDT",
                exchange="test_exchange",
                price=50000.0,
                volume=100.0,
                time=time.time()
            )
            
            # Test update
            success = await cache.update_ticker("test_exchange", tick)
            assert success
            
            # Test retrieval
            retrieved = await cache.get_ticker("BTC/USDT", "test_exchange")
            assert retrieved is not None
            assert retrieved.symbol == "BTC/USDT"
            assert retrieved.price == 50000.0
            
        finally:
            await cache.close()

### Factory Functions for Testing

    def create_test_tick(symbol="BTC/USDT", exchange="test", price=50000.0):
        return Tick(
            symbol=symbol,
            exchange=exchange,
            price=price,
            volume=100.0,
            time=time.time(),
            bid=price - 0.5,
            ask=price + 0.5,
            last=price
        )
    
    def create_test_position(symbol="BTC/USDT", ex_id="123", volume=0.1):
        return Position(
            symbol=symbol,
            cost=volume * 50000.0,
            volume=volume,
            fee=5.0,
            price=50000.0,
            timestamp=time.time(),
            ex_id=ex_id
        )

## Conclusion

Using fullon_orm models with fullon_cache provides:

1. **Type Safety**: Catch errors at development time
2. **Consistency**: Uniform data structures across the application
3. **Maintainability**: Clear interfaces and self-documenting code
4. **IDE Support**: Rich autocompletion and error detection
5. **Validation**: Automatic data validation and error reporting

The small performance overhead is negligible compared to the development
and maintenance benefits. Always prefer model-based interfaces for new
code and gradually migrate legacy dictionary-based code.

For more examples, see:
- fullon_cache.examples.basic_usage
- fullon_cache.examples.queue_patterns
- fullon_cache.docs.api_reference
"""

TYPE_SAFETY_GUIDE = """
Type Safety Guide for Fullon Cache
==================================

This guide demonstrates how fullon_orm models provide type safety benefits
and help prevent common runtime errors in cache operations.

## The Problem with Dictionaries

### Runtime Errors
Dictionary-based approaches can lead to runtime errors:

    # Dictionary approach - prone to errors
    ticker_data = {
        "symbol": "BTC/USDT",
        "price": "50000",  # String instead of float!
        "volume": 1234.56,
        "tmestamp": time.time()  # Typo in key name!
    }
    
    # These errors only surface at runtime
    price = ticker_data["price"] * 1.1  # TypeError: can't multiply str by float
    time_val = ticker_data["timestamp"]  # KeyError: 'timestamp'

### No IDE Support
Dictionaries provide no autocompletion or error detection:

    # No autocompletion available
    ticker_data["pric"]  # Typo - IDE doesn't help
    ticker_data["invalid_key"]  # IDE doesn't warn

## The Solution: fullon_orm Models

### Compile-time Validation
Models catch errors before runtime:

    from fullon_orm.models import Tick
    
    # This fails at creation time, not later
    try:
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price="50000",  # ValidationError: price must be float
            volume=1234.56,
            time=time.time()
        )
    except ValidationError as e:
        print(f"Invalid data: {e}")

### Rich IDE Support
Full autocompletion and error detection:

    tick = Tick(symbol="BTC/USDT", exchange="binance", 
               price=50000.0, volume=100.0, time=time.time())
    
    # IDE provides autocompletion
    tick.price     # ✓ IDE suggests 'price'
    tick.volume    # ✓ IDE suggests 'volume'
    tick.invalid   # ✗ IDE warns about unknown attribute
    
    # Type checking
    tick.price = "invalid"  # ✗ IDE/mypy warns about type mismatch

## Type Checking Tools

### MyPy Integration
Enable static type checking with mypy:

    # Install mypy
    pip install mypy
    
    # Create mypy.ini
    [mypy]
    python_version = 3.11
    warn_return_any = True
    warn_unused_configs = True
    disallow_untyped_defs = True

    # Type-checked code
    from fullon_cache import TickCache
    from fullon_orm.models import Tick
    
    async def update_price(cache: TickCache, tick: Tick) -> bool:
        return await cache.update_ticker(tick.exchange, tick)
    
    # mypy catches type errors
    # update_price(cache, "invalid")  # mypy error

### IDE Configuration
Configure your IDE for maximum type safety:

    # VS Code settings.json
    {
        "python.linting.mypyEnabled": true,
        "python.linting.enabled": true,
        "python.analysis.typeCheckingMode": "strict"
    }

## Type-Safe Patterns

### Function Signatures
Use type hints in function signatures:

    from typing import Optional, List
    from fullon_orm.models import Tick, Position, Order
    
    async def get_market_data(symbol: str, exchange: str) -> Optional[Tick]:
        cache = TickCache()
        try:
            return await cache.get_ticker(symbol, exchange)
        finally:
            await cache.close()
    
    async def update_positions(ex_id: int, positions: List[Position]) -> bool:
        cache = AccountCache()
        try:
            return await cache.upsert_positions(ex_id, positions)
        finally:
            await cache.close()

### Generic Types
Use generic types for flexible, type-safe functions:

    from typing import TypeVar, Generic, List
    
    T = TypeVar('T')
    
    class CacheManager(Generic[T]):
        def __init__(self, cache_type: type[T]):
            self.cache_type = cache_type
            
        async def batch_process(self, items: List[T]) -> List[bool]:
            results = []
            for item in items:
                # Type checker knows 'item' is of type T
                result = await self.process_item(item)
                results.append(result)
            return results

### Union Types for Backward Compatibility
Handle mixed model/dict scenarios safely:

    from typing import Union
    
    TickData = Union[Tick, dict]
    
    def normalize_tick_data(data: TickData, exchange: str) -> Tick:
        if isinstance(data, Tick):
            return data
        else:
            # Convert dict to Tick model
            return Tick(
                symbol=data["symbol"],
                exchange=exchange,
                price=data["price"],
                volume=data.get("volume", 0.0),
                time=data.get("time", time.time())
            )

## Error Prevention Examples

### 1. Attribute Access Errors

    # Dictionary approach - runtime error
    def get_spread_dict(ticker: dict) -> float:
        return ticker["ask"] - ticker["bid"]  # KeyError if keys missing
    
    # Model approach - compile-time safety
    def get_spread_model(tick: Tick) -> Optional[float]:
        if tick.ask is not None and tick.bid is not None:
            return tick.ask - tick.bid
        return None

### 2. Type Conversion Errors

    # Dictionary approach - runtime error
    def calculate_cost_dict(order: dict) -> float:
        return order["volume"] * order["price"]  # TypeError if strings
    
    # Model approach - guaranteed types
    def calculate_cost_model(order: Order) -> float:
        return order.volume * order.price  # Types guaranteed by model

### 3. Missing Field Errors

    # Dictionary approach - silent failures
    def get_timestamp_dict(trade: dict) -> float:
        return trade.get("timestamp", 0.0)  # Might return 0.0 unexpectedly
    
    # Model approach - explicit handling
    def get_timestamp_model(trade: Trade) -> datetime:
        return trade.time  # Guaranteed to exist and be correct type

## Validation Benefits

### Automatic Data Validation

    # Models validate data automatically
    def create_order_safe(data: dict) -> Order:
        return Order(
            ex_order_id=data["ex_order_id"],
            symbol=data["symbol"],
            side=data["side"],  # Validates: must be "buy" or "sell"
            volume=data["volume"],  # Validates: must be positive number
            price=data["price"],  # Validates: must be positive number
            status=data["status"],  # Validates: must be valid status
            order_type=data["order_type"],
            exchange=data["exchange"],
            timestamp=datetime.now(UTC)
        )
        # ValidationError raised if any field is invalid

### Custom Validation
Add custom validation to models:

    from pydantic import validator
    
    class ValidatedTick(Tick):
        @validator('price')
        def price_must_be_positive(cls, v):
            if v <= 0:
                raise ValueError('Price must be positive')
            return v
        
        @validator('volume')
        def volume_must_be_positive(cls, v):
            if v < 0:
                raise ValueError('Volume cannot be negative')
            return v

## Testing Type Safety

### Unit Tests with Type Checking

    import pytest
    from fullon_orm.models import Tick
    
    def test_tick_type_safety():
        # Valid tick creation
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            volume=100.0,
            time=time.time()
        )
        
        # Type is guaranteed
        assert isinstance(tick.price, float)
        assert isinstance(tick.volume, float)
        assert isinstance(tick.symbol, str)
        
        # Invalid tick creation
        with pytest.raises(ValidationError):
            Tick(
                symbol="",  # Empty symbol
                exchange="binance",
                price=-100.0,  # Negative price
                volume=100.0,
                time=time.time()
            )

### Property-Based Testing
Use hypothesis for comprehensive testing:

    from hypothesis import given, strategies as st
    
    @given(
        symbol=st.text(min_size=1, max_size=20),
        price=st.floats(min_value=0.01, max_value=1000000),
        volume=st.floats(min_value=0, max_value=1000000)
    )
    def test_tick_creation(symbol: str, price: float, volume: float):
        tick = Tick(
            symbol=symbol,
            exchange="test",
            price=price,
            volume=volume,
            time=time.time()
        )
        
        # Properties are guaranteed
        assert tick.price == price
        assert tick.volume == volume
        assert tick.symbol == symbol

## Migration Strategy

### Phase 1: Add Type Hints
Start by adding type hints to existing code:

    # Before
    async def update_ticker(cache, symbol, data):
        return await cache.update_ticker(symbol, data)
    
    # After  
    async def update_ticker(cache: TickCache, symbol: str, data: dict) -> bool:
        return await cache.update_ticker_legacy(symbol, "binance", data)

### Phase 2: Introduce Models Gradually
Replace dictionaries with models incrementally:

    # Step 1: Create conversion functions
    def dict_to_tick(data: dict, exchange: str) -> Tick:
        return Tick(
            symbol=data["symbol"],
            exchange=exchange,
            price=float(data["price"]),
            volume=float(data.get("volume", 0)),
            time=data.get("time", time.time())
        )
    
    # Step 2: Use in new code
    async def process_ticker_update(data: dict, exchange: str):
        tick = dict_to_tick(data, exchange)
        await cache.update_ticker(exchange, tick)

### Phase 3: Full Model Adoption
Use models throughout the application:

    async def trading_system():
        # All operations use models
        tick = await get_current_price()  # Returns Tick
        order = create_market_order(tick)  # Takes Tick, returns Order
        trade = await execute_order(order)  # Takes Order, returns Trade
        await update_position(trade)  # Takes Trade

## Tools and Configuration

### Pre-commit Hooks
Add type checking to your development workflow:

    # .pre-commit-config.yaml
    repos:
      - repo: https://github.com/pre-commit/mirrors-mypy
        rev: v1.0.0
        hooks:
          - id: mypy
            additional_dependencies: [types-all]

### CI/CD Integration
Include type checking in your CI pipeline:

    # GitHub Actions
    - name: Type check with mypy
      run: |
        pip install mypy
        mypy src/ tests/

### IDE Settings
Configure your IDE for optimal type safety:

    # PyCharm: Enable type checking inspections
    # VS Code: Install Python and Pylance extensions
    # Vim/Neovim: Configure LSP with pyright

## Best Practices Summary

1. **Always use type hints** in function signatures
2. **Prefer models over dictionaries** for structured data
3. **Enable mypy** in your development environment  
4. **Add validation** at data boundaries
5. **Use Union types** for gradual migration
6. **Test type safety** with comprehensive unit tests
7. **Configure IDE** for maximum type checking support

Type safety with fullon_orm models significantly reduces bugs, improves
code maintainability, and enhances developer productivity. The initial
investment in setup pays dividends in reduced debugging time and
increased confidence in code correctness.
"""

PERFORMANCE_GUIDE = """
Performance Optimization Guide for Fullon Cache
===============================================

This guide covers performance optimization techniques when using fullon_orm
models with fullon_cache for high-throughput trading applications.

## Performance Characteristics

### Model vs Dictionary Overhead

Benchmark results (1000 iterations):
- Dictionary creation: ~0.001ms average
- Model creation: ~0.003ms average  
- Model validation: ~0.002ms average
- Redis operation: ~0.5-2ms average

**Key insight**: Model overhead is negligible compared to network/Redis operations.

### Memory Usage
- Dictionary: ~200 bytes per ticker
- Tick model: ~280 bytes per ticker
- Memory overhead: ~40% for significant type safety benefits

## Optimization Strategies

### 1. Batch Operations

Instead of individual operations:

    # Slow: Individual operations
    for symbol_data in market_feed:
        tick = Tick(
            symbol=symbol_data["symbol"],
            exchange="binance", 
            price=symbol_data["price"],
            volume=symbol_data["volume"],
            time=time.time()
        )
        await tick_cache.update_ticker("binance", tick)

Prefer batch operations:

    # Fast: Batch processing
    ticks = []
    for symbol_data in market_feed:
        tick = Tick(
            symbol=symbol_data["symbol"],
            exchange="binance",
            price=symbol_data["price"], 
            volume=symbol_data["volume"],
            time=time.time()
        )
        ticks.append(tick)
    
    # Process batch with Redis pipeline
    async with tick_cache._cache.pipeline() as pipe:
        for tick in ticks:
            # Add to pipeline instead of executing immediately
            tick_dict = tick.to_dict()
            pipe.hset(f"tickers:binance", tick.symbol, json.dumps(tick_dict))
        await pipe.execute()

### 2. Connection Pooling

Reuse cache instances across operations:

    # Slow: Create new cache for each operation
    async def update_ticker_slow(data):
        cache = TickCache()  # New connection each time
        try:
            tick = Tick(**data)
            await cache.update_ticker("binance", tick)
        finally:
            await cache.close()

    # Fast: Reuse cache instance
    class MarketDataProcessor:
        def __init__(self):
            self.tick_cache = TickCache()
            
        async def update_ticker_fast(self, data):
            tick = Tick(**data)
            await self.tick_cache.update_ticker("binance", tick)
            
        async def close(self):
            await self.tick_cache.close()

### 3. Model Creation Optimization

Cache model creation for repeated data:

    # For high-frequency updates of same symbols
    class OptimizedTickProcessor:
        def __init__(self):
            self.tick_cache = TickCache()
            self._tick_templates = {}
            
        def get_tick_template(self, symbol: str, exchange: str) -> Tick:
            key = f"{exchange}:{symbol}"
            if key not in self._tick_templates:
                self._tick_templates[key] = Tick(
                    symbol=symbol,
                    exchange=exchange,
                    price=0.0,  # Will be updated
                    volume=0.0,  # Will be updated
                    time=0.0    # Will be updated
                )
            return self._tick_templates[key]
            
        async def update_ticker_optimized(self, symbol: str, exchange: str, 
                                        price: float, volume: float):
            # Reuse model structure, update only changing fields
            tick = self.get_tick_template(symbol, exchange)
            tick.price = price
            tick.volume = volume
            tick.time = time.time()
            
            await self.tick_cache.update_ticker(exchange, tick)

### 4. Asynchronous Processing

Use asyncio for concurrent operations:

    async def process_market_data_concurrent(market_updates):
        tick_cache = TickCache()
        
        async def process_update(update):
            tick = Tick(
                symbol=update["symbol"],
                exchange=update["exchange"],
                price=update["price"],
                volume=update["volume"],
                time=time.time()
            )
            return await tick_cache.update_ticker(update["exchange"], tick)
        
        # Process multiple updates concurrently
        tasks = [process_update(update) for update in market_updates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        await tick_cache.close()
        return results

### 5. Memory-Efficient Data Structures

Use slots for custom model extensions:

    from fullon_orm.models import Tick
    
    class OptimizedTick(Tick):
        __slots__ = ()  # Inherit slots from parent
        
        @classmethod
        def from_feed_data(cls, data: dict, exchange: str):
            # Optimized creation from market feed
            return cls(
                symbol=data["s"],  # Assume short field names
                exchange=exchange,
                price=float(data["p"]),
                volume=float(data["v"]),
                time=float(data["t"]) / 1000,  # Convert ms to seconds
                bid=data.get("b"),
                ask=data.get("a"),
                last=data.get("l")
            )

## Real-world Performance Patterns

### High-Frequency Trading Pattern

    class HFTMarketDataHandler:
        def __init__(self):
            self.tick_cache = TickCache()
            self.orders_cache = OrdersCache()
            self.account_cache = AccountCache()
            
            # Pre-allocated objects for minimal GC pressure
            self._reusable_tick = Tick(
                symbol="", exchange="", price=0.0, 
                volume=0.0, time=0.0
            )
            
        async def process_tick_update(self, symbol: str, exchange: str,
                                    price: float, volume: float):
            # Reuse object to minimize allocations
            tick = self._reusable_tick
            tick.symbol = symbol
            tick.exchange = exchange  
            tick.price = price
            tick.volume = volume
            tick.time = time.time()
            
            # Use pipeline for atomic updates
            async with self.tick_cache._cache.pipeline() as pipe:
                tick_data = tick.to_dict()
                pipe.hset(f"tickers:{exchange}", symbol, json.dumps(tick_data))
                pipe.publish(f"tickers:{exchange}:{symbol}", json.dumps(tick_data))
                await pipe.execute()

### Market Making Pattern

    class MarketMakerEngine:
        def __init__(self):
            self.caches = {
                'tick': TickCache(),
                'orders': OrdersCache(), 
                'account': AccountCache()
            }
            self.symbol_configs = {}
            
        async def quote_update_cycle(self, symbol: str, exchange: str):
            # Get current market data
            tick = await self.caches['tick'].get_ticker(symbol, exchange)
            if not tick:
                return
                
            # Calculate quote prices
            config = self.symbol_configs.get(symbol, {})
            spread = config.get('spread', 0.001)
            size = config.get('size', 0.1)
            
            bid_price = tick.price * (1 - spread/2)
            ask_price = tick.price * (1 + spread/2)
            
            # Create orders efficiently
            orders = [
                Order(
                    ex_order_id=f"bid_{symbol}_{int(time.time())}",
                    symbol=symbol,
                    side="buy",
                    volume=size,
                    price=bid_price,
                    status="pending",
                    order_type="limit",
                    exchange=exchange,
                    timestamp=datetime.now(UTC)
                ),
                Order(
                    ex_order_id=f"ask_{symbol}_{int(time.time())}",
                    symbol=symbol,
                    side="sell", 
                    volume=size,
                    price=ask_price,
                    status="pending",
                    order_type="limit",
                    exchange=exchange,
                    timestamp=datetime.now(UTC)
                )
            ]
            
            # Submit orders in batch
            for order in orders:
                await self.caches['orders'].save_order(exchange, order)

### Arbitrage Pattern

    class ArbitrageScanner:
        def __init__(self):
            self.tick_cache = TickCache()
            self.opportunity_threshold = 0.002  # 0.2%
            
        async def scan_arbitrage_opportunities(self, symbol: str, 
                                             exchanges: List[str]):
            # Get tickers from all exchanges concurrently
            tasks = [
                self.tick_cache.get_ticker(symbol, exchange)
                for exchange in exchanges
            ]
            tickers = await asyncio.gather(*tasks)
            
            # Filter valid tickers
            valid_tickers = [(ex, tick) for ex, tick in zip(exchanges, tickers) 
                           if tick is not None]
            
            if len(valid_tickers) < 2:
                return []
                
            # Find arbitrage opportunities
            opportunities = []
            for i, (ex1, tick1) in enumerate(valid_tickers):
                for ex2, tick2 in valid_tickers[i+1:]:
                    price_diff = abs(tick1.price - tick2.price)
                    avg_price = (tick1.price + tick2.price) / 2
                    spread_pct = price_diff / avg_price
                    
                    if spread_pct > self.opportunity_threshold:
                        opportunities.append({
                            'symbol': symbol,
                            'exchange_1': ex1,
                            'price_1': tick1.price,
                            'exchange_2': ex2,
                            'price_2': tick2.price,
                            'spread_pct': spread_pct
                        })
                        
            return opportunities

## Performance Monitoring

### Built-in Metrics

    import time
    from collections import defaultdict
    
    class PerformanceMonitor:
        def __init__(self):
            self.operation_times = defaultdict(list)
            self.operation_counts = defaultdict(int)
            
        async def timed_operation(self, operation_name: str, operation):
            start = time.perf_counter()
            try:
                result = await operation()
                return result
            finally:
                duration = (time.perf_counter() - start) * 1000
                self.operation_times[operation_name].append(duration)
                self.operation_counts[operation_name] += 1
                
        def get_stats(self):
            stats = {}
            for op_name, times in self.operation_times.items():
                if times:
                    stats[op_name] = {
                        'count': len(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times),
                        'total_ms': sum(times)
                    }
            return stats

### Usage Example

    monitor = PerformanceMonitor()
    tick_cache = TickCache()
    
    # Monitor operations
    tick = Tick(symbol="BTC/USDT", exchange="binance", 
               price=50000.0, volume=100.0, time=time.time())
    
    await monitor.timed_operation(
        "ticker_update",
        lambda: tick_cache.update_ticker("binance", tick)
    )
    
    # Get performance stats
    stats = monitor.get_stats()
    print(f"Ticker updates: {stats['ticker_update']['avg_ms']:.2f}ms average")

## Profiling and Debugging

### Memory Profiling

    # Install memory profiler
    pip install memory-profiler
    
    # Profile memory usage
    from memory_profiler import profile
    
    @profile
    async def memory_intensive_operation():
        ticks = []
        for i in range(10000):
            tick = Tick(
                symbol=f"SYMBOL_{i}",
                exchange="test",
                price=float(i),
                volume=100.0,
                time=time.time()
            )
            ticks.append(tick)
        return ticks

### CPU Profiling

    import cProfile
    import asyncio
    
    def profile_cache_operations():
        async def test_operations():
            cache = TickCache()
            try:
                for i in range(1000):
                    tick = Tick(
                        symbol="BTC/USDT",
                        exchange="test",
                        price=50000.0 + i,
                        volume=100.0,
                        time=time.time()
                    )
                    await cache.update_ticker("test", tick)
            finally:
                await cache.close()
        
        cProfile.run('asyncio.run(test_operations())')

## Configuration Tuning

### Redis Optimization

    # Redis configuration for high performance
    # redis.conf
    maxmemory-policy allkeys-lru
    tcp-keepalive 60
    timeout 0
    tcp-nodelay yes

### Connection Pool Settings

    from fullon_cache import BaseCache
    
    # Optimize connection pool
    cache = BaseCache()
    cache._redis_config = {
        'max_connections': 100,  # Increase pool size
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry_on_timeout': True
    }

## Best Practices Summary

1. **Use batch operations** for multiple updates
2. **Reuse cache instances** across operations  
3. **Implement connection pooling** for high-frequency operations
4. **Monitor performance** with built-in metrics
5. **Profile bottlenecks** with memory and CPU profilers
6. **Optimize Redis configuration** for your use case
7. **Use asyncio** for concurrent operations
8. **Pre-allocate objects** for ultra-high frequency scenarios

Remember: Premature optimization is the root of all evil. Profile first,
then optimize the actual bottlenecks in your specific use case.
"""

__all__ = ['MODEL_USAGE_GUIDE', 'TYPE_SAFETY_GUIDE', 'PERFORMANCE_GUIDE']