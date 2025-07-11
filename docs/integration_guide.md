# fullon_cache Integration Guide

This guide demonstrates how to use multiple fullon_cache modules together with fullon_orm models for real-world trading scenarios.

## Table of Contents

1. [Overview](#overview)
2. [End-to-End Trading Flow](#end-to-end-trading-flow)
3. [Cross-Module Patterns](#cross-module-patterns)
4. [Performance Considerations](#performance-considerations)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

## Overview

The fullon_cache system is designed for seamless integration between modules using fullon_orm models as the primary interface. This ensures type safety, consistency, and maintainability across your trading application.

### Key Integration Points

- **SymbolCache + TickCache**: Symbol metadata with real-time price data
- **TickCache + OrdersCache**: Price updates triggering order management
- **OrdersCache + TradesCache**: Order fills generating trade records
- **TradesCache + AccountCache**: Trade execution updating positions
- **BotCache + All Modules**: Bot coordination across trading operations

## End-to-End Trading Flow

Here's a complete example of a trading workflow using multiple cache modules:

```python
import asyncio
from datetime import UTC, datetime
from fullon_orm.models import Symbol, Tick, Order, Trade, Position
from fullon_cache import (
    SymbolCache, TickCache, OrdersCache, TradesCache, AccountCache
)

async def complete_trading_workflow():
    """Demonstrate a complete trading workflow."""
    # Initialize cache modules
    symbol_cache = SymbolCache()
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    trades_cache = TradesCache()
    account_cache = AccountCache()
    
    try:
        # 1. Setup trading symbol
        symbol = Symbol(
            symbol="BTC/USDT",
            base="BTC",
            quote="USDT", 
            exchange="binance",
            precision=8,
            margin=True,
            leverage=10.0,
            contract_size=1.0,
            tick_size=0.01,
            description="Bitcoin to USDT trading pair"
        )
        
        # Store symbol metadata (normally from database)
        import json
        async with symbol_cache._cache._redis_context() as redis_client:
            key = "symbols_list:binance"
            await redis_client.hset(key, symbol.symbol, json.dumps(symbol.to_dict()))
        
        # 2. Update market data
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance", 
            price=50000.0,
            volume=1234.56,
            time=datetime.now(UTC).timestamp(),
            bid=49999.0,
            ask=50001.0,
            last=50000.0
        )
        
        await tick_cache.update_ticker("binance", tick)
        print(f"Updated ticker: {tick.symbol} @ ${tick.price}")
        
        # 3. Create and manage order
        order = Order(
            trade_id="TRD_001",
            ex_order_id="ORD_001",
            ex_id="binance",
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            uid="user_123",
            status="open"
        )
        
        # Queue order
        await orders_cache.push_open_order(order.ex_order_id, "LOCAL_001")
        await orders_cache.save_order_data("binance", order.ex_order_id, order.to_dict())
        
        # Process order
        order_id = await orders_cache.pop_open_order("LOCAL_001")
        print(f"Processing order: {order_id}")
        
        # 4. Simulate order fill
        await orders_cache.save_order_data(
            "binance",
            order.ex_order_id,
            {"status": "filled", "final_volume": 0.1, "fill_price": 50000.0}
        )
        
        # 5. Record trade
        trade = Trade(
            trade_id="TRD_001",
            ex_order_id="ORD_001",
            ex_id="binance",
            symbol="BTC/USDT",
            side="buy",
            order_type="market", 
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            uid="user_123"
        )
        
        await trades_cache.push_trade_list("BTC/USDT", "binance", trade.to_dict())
        print(f"Recorded trade: {trade.volume} {trade.symbol}")
        
        # 6. Update position
        position = Position(
            user_id=123,
            ex_id=1,
            symbol="BTC/USDT", 
            size=0.1,
            entry_price=50000.0,
            side="long",
            unrealized_pnl=0.0,
            cost_basis=5000.0
        )
        
        await account_cache.upsert_positions(1, [position])
        print(f"Updated position: {position.size} {position.symbol}")
        
        # 7. Verify complete workflow
        final_order = await orders_cache.get_order_status("binance", "ORD_001")
        trades = await trades_cache.get_trades_list("BTC/USDT", "binance") 
        positions = await account_cache.get_positions(1)
        current_price = await tick_cache.get_price("BTC/USDT", "binance")
        
        print(f"Workflow complete:")
        print(f"  Order status: {final_order.status}")
        print(f"  Trades recorded: {len(trades)}")
        print(f"  Positions: {len(positions)}")
        print(f"  Current price: ${current_price}")
        
    finally:
        # Cleanup
        await symbol_cache.close()
        await tick_cache.close()
        await orders_cache.close()
        await trades_cache.close()
        await account_cache.close()

# Run the example
asyncio.run(complete_trading_workflow())
```

## Cross-Module Patterns

### Symbol + Ticker Integration

Combine symbol metadata with real-time price data:

```python
async def symbol_ticker_integration():
    """Integrate symbol metadata with ticker data."""
    symbol_cache = SymbolCache()
    tick_cache = TickCache()
    
    try:
        # Get symbol metadata
        symbol = await symbol_cache.get_symbol("BTC/USDT", exchange_name="binance")
        
        # Get current ticker
        tick = await tick_cache.get_ticker("BTC/USDT", "binance")
        
        if symbol and tick:
            # Validate price precision against symbol metadata
            price = tick.price
            tick_size = symbol.tick_size
            
            # Ensure price aligns with symbol's tick size
            aligned_price = round(price / tick_size) * tick_size
            
            if price != aligned_price:
                print(f"Price {price} not aligned with tick size {tick_size}")
                
            # Use symbol precision for display
            formatted_price = f"{price:.{symbol.precision}f}"
            print(f"{symbol.symbol}: ${formatted_price}")
            
    finally:
        await symbol_cache.close()
        await tick_cache.close()
```

### Order + Trade + Position Flow

Coordinate order fills, trade recording, and position updates:

```python
async def order_trade_position_flow():
    """Coordinate order fills with trade and position updates."""
    orders_cache = OrdersCache()
    trades_cache = TradesCache()
    account_cache = AccountCache()
    
    try:
        # Monitor order status
        order = await orders_cache.get_order_status("binance", "ORD_123")
        
        if order and order.status == "filled":
            # Record the trade
            trade_data = {
                "trade_id": f"TRD_{order.ex_order_id}",
                "ex_order_id": order.ex_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "volume": order.final_volume,
                "price": order.fill_price,
                "cost": order.final_volume * order.fill_price,
                "fee": order.fee,
                "uid": order.uid
            }
            
            await trades_cache.push_trade_list(order.symbol, "binance", trade_data)
            
            # Update position
            current_positions = await account_cache.get_positions(int(order.uid))
            
            # Find existing position for this symbol
            existing_position = next(
                (p for p in current_positions if p.symbol == order.symbol),
                None
            )
            
            if existing_position:
                # Update existing position
                if order.side == "buy":
                    new_size = existing_position.size + order.final_volume
                else:  # sell
                    new_size = existing_position.size - order.final_volume
                
                # Calculate new average entry price
                if new_size != 0:
                    total_cost = (existing_position.size * existing_position.entry_price + 
                                order.final_volume * order.fill_price)
                    new_entry_price = total_cost / abs(new_size)
                else:
                    new_entry_price = 0.0
                
                updated_position = Position(
                    user_id=existing_position.user_id,
                    ex_id=existing_position.ex_id,
                    symbol=existing_position.symbol,
                    size=new_size,
                    entry_price=new_entry_price,
                    side="long" if new_size > 0 else "short" if new_size < 0 else "neutral",
                    unrealized_pnl=existing_position.unrealized_pnl,
                    cost_basis=abs(new_size) * new_entry_price
                )
                
                await account_cache.upsert_positions(existing_position.ex_id, [updated_position])
                print(f"Updated position: {updated_position.size} {updated_position.symbol}")
            
    finally:
        await orders_cache.close()
        await trades_cache.close()
        await account_cache.close()
```

### Bot Coordination Pattern

Use BotCache to coordinate multiple bots:

```python
async def bot_coordination_example():
    """Demonstrate bot coordination across trading operations."""
    bot_cache = BotCache()
    orders_cache = OrdersCache()
    tick_cache = TickCache()
    
    try:
        symbol = "BTC/USDT"
        exchange = "binance"
        bot_id = "arbitrage_bot_1"
        
        # 1. Check if symbol is available
        blocking_bot = await bot_cache.is_blocked(exchange, symbol)
        if blocking_bot:
            print(f"Symbol {symbol} blocked by {blocking_bot}")
            return
        
        # 2. Block symbol for this bot
        success = await bot_cache.block_exchange(exchange, symbol, bot_id)
        if not success:
            print(f"Failed to block {symbol}")
            return
        
        try:
            # 3. Get current price
            current_price = await tick_cache.get_price(symbol, exchange)
            
            # 4. Mark that we're opening a position
            await bot_cache.mark_opening_position(exchange, symbol, bot_id)
            
            # 5. Create order
            order_data = {
                "symbol": symbol,
                "side": "buy",
                "volume": 0.1,
                "price": current_price,
                "status": "open",
                "bot_id": bot_id
            }
            
            await orders_cache.save_order_data(exchange, f"{bot_id}_ORD", order_data)
            print(f"Bot {bot_id} created order for {symbol}")
            
            # 6. Simulate order processing
            await asyncio.sleep(1)  # Simulate time for order to fill
            
            # 7. Update order status
            await orders_cache.save_order_data(
                exchange,
                f"{bot_id}_ORD",
                {"status": "filled", "final_volume": 0.1}
            )
            
        finally:
            # 8. Always cleanup bot coordination
            await bot_cache.unmark_opening_position(exchange, symbol)
            await bot_cache.unblock_exchange(exchange, symbol)
            print(f"Bot {bot_id} released control of {symbol}")
            
    finally:
        await bot_cache.close()
        await orders_cache.close()
        await tick_cache.close()
```

## Performance Considerations

### Batch Operations

When possible, batch operations for better performance:

```python
async def batch_operations_example():
    """Demonstrate efficient batch operations."""
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    
    try:
        # Batch ticker updates
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        
        # Update all tickers efficiently
        for symbol in symbols:
            tick = Tick(
                symbol=symbol,
                exchange="binance",
                price=1000.0,
                volume=100.0,
                time=datetime.now(UTC).timestamp(),
                bid=999.0,
                ask=1001.0,
                last=1000.0
            )
            await tick_cache.update_ticker("binance", tick)
        
        # Batch order creation
        order_ids = []
        for i, symbol in enumerate(symbols):
            order_id = f"BATCH_ORD_{i}"
            order_data = {
                "symbol": symbol,
                "side": "buy",
                "volume": 0.1,
                "price": 1000.0,
                "status": "open"
            }
            
            await orders_cache.save_order_data("binance", order_id, order_data)
            order_ids.append(order_id)
        
        # Verify all operations completed
        all_orders = await orders_cache.get_orders("binance")
        batch_orders = [o for o in all_orders if o.ex_order_id.startswith("BATCH_ORD_")]
        
        print(f"Batch operations completed:")
        print(f"  Tickers updated: {len(symbols)}")
        print(f"  Orders created: {len(batch_orders)}")
        
    finally:
        await tick_cache.close()
        await orders_cache.close()
```

### Connection Pooling

Reuse cache instances when possible:

```python
class TradingEngine:
    """Example trading engine with efficient cache usage."""
    
    def __init__(self):
        self.tick_cache = TickCache()
        self.orders_cache = OrdersCache()
        self.account_cache = AccountCache()
        
    async def process_market_data(self, ticks):
        """Process multiple tickers efficiently."""
        for tick in ticks:
            await self.tick_cache.update_ticker(tick.exchange, tick)
    
    async def process_orders(self, orders):
        """Process multiple orders efficiently."""
        for order in orders:
            await self.orders_cache.save_order_data(
                order.ex_id, 
                order.ex_order_id, 
                order.to_dict()
            )
    
    async def close(self):
        """Cleanup all cache connections."""
        await self.tick_cache.close()
        await self.orders_cache.close()
        await self.account_cache.close()
```

## Error Handling

### Graceful Degradation

Handle errors gracefully to maintain system stability:

```python
async def robust_trading_operation():
    """Demonstrate robust error handling."""
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    trades_cache = TradesCache()
    
    try:
        # Core operation with error handling
        symbol = "BTC/USDT"
        exchange = "binance"
        
        # 1. Try to get current price
        try:
            current_price = await tick_cache.get_price(symbol, exchange)
            if current_price == 0:
                print(f"Warning: No price data for {symbol}")
                return
        except Exception as e:
            print(f"Error getting price: {e}")
            return
        
        # 2. Try to create order
        order_data = {
            "symbol": symbol,
            "side": "buy",
            "volume": 0.1,
            "price": current_price,
            "status": "open"
        }
        
        try:
            await orders_cache.save_order_data(exchange, "ROBUST_ORD", order_data)
            print("Order created successfully")
        except Exception as e:
            print(f"Error creating order: {e}")
            # Continue with other operations
        
        # 3. Try to record trade (even if order failed)
        try:
            trade_data = {
                "trade_id": "ROBUST_TRD",
                "symbol": symbol,
                "side": "buy",
                "volume": 0.1,
                "price": current_price
            }
            
            await trades_cache.push_trade_list(symbol, exchange, trade_data)
            print("Trade recorded successfully")
        except Exception as e:
            print(f"Error recording trade: {e}")
            # System continues to function
        
        print("Robust operation completed with graceful error handling")
        
    except Exception as e:
        print(f"Critical error: {e}")
        # Log error and potentially retry or alert
        
    finally:
        await tick_cache.close()
        await orders_cache.close()
        await trades_cache.close()
```

### Circuit Breaker Pattern

Implement circuit breakers for external dependencies:

```python
class CircuitBreaker:
    """Simple circuit breaker for cache operations."""
    
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def should_allow_request(self):
        """Check if request should be allowed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

async def circuit_breaker_example():
    """Use circuit breaker with cache operations."""
    tick_cache = TickCache()
    circuit_breaker = CircuitBreaker()
    
    try:
        symbol = "BTC/USDT"
        exchange = "binance"
        
        # Check circuit breaker before operation
        if not circuit_breaker.should_allow_request():
            print("Circuit breaker is OPEN, skipping operation")
            return
        
        try:
            # Attempt cache operation
            tick = Tick(
                symbol=symbol,
                exchange=exchange,
                price=50000.0,
                volume=100.0,
                time=datetime.now(UTC).timestamp(),
                bid=49999.0,
                ask=50001.0,
                last=50000.0
            )
            
            await tick_cache.update_ticker(exchange, tick)
            circuit_breaker.record_success()
            print("Operation successful")
            
        except Exception as e:
            circuit_breaker.record_failure()
            print(f"Operation failed: {e}")
            raise
            
    finally:
        await tick_cache.close()
```

## Best Practices

### 1. Use Type Hints and Models

Always use fullon_orm models for type safety:

```python
from fullon_orm.models import Tick, Order
from fullon_cache import TickCache, OrdersCache

async def type_safe_operations():
    """Use proper typing for cache operations."""
    tick_cache = TickCache()
    orders_cache = OrdersCache()
    
    try:
        # Type-safe ticker creation
        tick: Tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            volume=100.0,
            time=datetime.now(UTC).timestamp(),
            bid=49999.0,
            ask=50001.0,
            last=50000.0
        )
        
        # Type-safe operations
        result: bool = await tick_cache.update_ticker("binance", tick)
        retrieved_tick: Tick | None = await tick_cache.get_ticker("BTC/USDT", "binance")
        
        if retrieved_tick:
            print(f"Price: {retrieved_tick.price}")
            
    finally:
        await tick_cache.close()
        await orders_cache.close()
```

### 2. Proper Resource Management

Always use context managers or proper cleanup:

```python
async def proper_resource_management():
    """Demonstrate proper resource management."""
    
    # Option 1: Context manager
    async with TickCache() as tick_cache:
        tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0, 
                   volume=100.0, time=datetime.now(UTC).timestamp(),
                   bid=49999.0, ask=50001.0, last=50000.0)
        await tick_cache.update_ticker("binance", tick)
    
    # Option 2: Try/finally
    orders_cache = OrdersCache()
    try:
        order_data = {"symbol": "BTC/USDT", "side": "buy", "volume": 0.1}
        await orders_cache.save_order_data("binance", "ORD_001", order_data)
    finally:
        await orders_cache.close()
```

### 3. Monitor and Log Operations

Add comprehensive logging and monitoring:

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def monitored_trading_operation():
    """Add monitoring and logging to operations."""
    tick_cache = TickCache()
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting trading operation at {start_time}")
        
        # Operation with timing
        operation_start = datetime.now()
        tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0,
                   volume=100.0, time=datetime.now(UTC).timestamp(),
                   bid=49999.0, ask=50001.0, last=50000.0)
        result = await tick_cache.update_ticker("binance", tick)
        operation_duration = (datetime.now() - operation_start).total_seconds()
        
        logger.info(f"Ticker update completed in {operation_duration:.3f}s")
        
        if not result:
            logger.warning("Ticker update returned False")
        
        # Performance monitoring
        if operation_duration > 0.1:  # 100ms threshold
            logger.warning(f"Slow operation: {operation_duration:.3f}s")
            
    except Exception as e:
        logger.error(f"Trading operation failed: {e}", exc_info=True)
        raise
    finally:
        await tick_cache.close()
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Trading operation completed in {total_duration:.3f}s")
```

### 4. Configuration Management

Use environment variables for configuration:

```python
import os
from fullon_cache import TickCache

def create_configured_cache():
    """Create cache with environment-based configuration."""
    
    # Configuration from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_DB', 0))
    
    # Create cache with configuration
    cache = TickCache()
    
    return cache

async def environment_based_setup():
    """Use environment-based configuration."""
    cache = create_configured_cache()
    
    try:
        # Use cache normally
        tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0,
                   volume=100.0, time=datetime.now(UTC).timestamp(),
                   bid=49999.0, ask=50001.0, last=50000.0)
        await cache.update_ticker("binance", tick)
        
    finally:
        await cache.close()
```

This integration guide provides comprehensive examples of how to use fullon_cache modules together effectively with fullon_orm models. The patterns shown here ensure type safety, performance, and robust error handling in production trading applications.