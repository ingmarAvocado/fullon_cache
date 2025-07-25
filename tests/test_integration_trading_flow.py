"""End-to-end trading flow integration tests using fullon_orm models.

This module tests complete trading workflows to ensure all cache modules
work seamlessly together with fullon_orm models in real-world scenarios.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from fullon_orm.models import Symbol, Tick, Order, Trade, Position

from fullon_cache import (
    SymbolCache, TickCache, OrdersCache, TradesCache, AccountCache
)


def create_test_symbol(symbol="BTC/USDT", cat_ex_id=1):
    """Factory for test Symbol objects."""
    return Symbol(
        symbol=symbol,
        base=symbol.split("/")[0],
        quote=symbol.split("/")[1],
        cat_ex_id=cat_ex_id,
        decimals=8,
        updateframe="1h",
        backtest=30,
        futures=False,
        only_ticker=False
    )


def create_test_tick(symbol="BTC/USDT", exchange="binance", price=50000.0):
    """Factory for test Tick objects."""
    return Tick(
        symbol=symbol,
        exchange=exchange,
        price=price,
        volume=1234.56,
        time=datetime.now(UTC).timestamp(),
        bid=price - 1.0,
        ask=price + 1.0,
        last=price
    )


def create_test_order(symbol="BTC/USDT", ex_id="binance", side="buy", volume=0.1):
    """Factory for test Order data (as dict)."""
    return {
        "ex_order_id": "ORD_67890",
        "ex_id": ex_id,
        "symbol": symbol,
        "side": side,
        "order_type": "market",
        "volume": volume,
        "price": 50000.0,
        "cost": 5000.0,
        "fee": 5.0,
        "uid": "user_123",
        "status": "open"
    }


def create_test_trade(symbol="BTC/USDT", ex_id="binance", volume=0.1):
    """Factory for test Trade data (as dict)."""
    return {
        "trade_id": "TRD_12345",
        "ex_order_id": "ORD_67890", 
        "ex_id": ex_id,
        "symbol": symbol,
        "side": "buy",
        "order_type": "market",
        "volume": volume,
        "price": 50000.0,
        "cost": 5000.0,
        "fee": 5.0,
        "uid": "user_123"
    }


def create_test_position(symbol="BTC/USDT", ex_id="1", volume=0.1):
    """Factory for test Position objects."""
    return Position(
        symbol=symbol,
        cost=volume * 50000.0,  # cost = volume * price
        volume=volume,
        fee=5.0,
        price=50000.0,
        timestamp=datetime.now(UTC).timestamp(),
        ex_id=str(ex_id)
    )


class TestEndToEndTradingFlow:
    """Test complete trading workflows using fullon_orm models."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_trading_workflow(self, clean_redis):
        """Test complete end-to-end trading workflow with all cache modules."""
        # Initialize all cache modules
        symbol_cache = SymbolCache()
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        account_cache = AccountCache()
        
        try:
            # 1. SETUP: Add trading symbol to cache
            symbol = create_test_symbol("BTC/USDT", 1)
            
            # Manually add symbol to cache (normally from database)
            import json
            async with symbol_cache._cache._redis_context() as redis_client:
                key = "symbols_list:binance"
                await redis_client.hset(key, symbol.symbol, json.dumps(symbol.to_dict()))
            
            # Verify symbol exists
            cached_symbol = await symbol_cache.get_symbol("BTC/USDT", exchange_name="binance")
            assert cached_symbol is not None
            assert cached_symbol.symbol == "BTC/USDT"
            
            # 2. MARKET DATA: Update ticker information
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            
            result = await tick_cache.update_ticker("binance", tick)
            assert result is True
            
            # Verify ticker data
            cached_tick = await tick_cache.get_ticker("BTC/USDT", "binance")
            assert cached_tick is not None
            assert cached_tick.price == 50000.0
            
            # 3. ORDER MANAGEMENT: Create and process order
            order = create_test_order("BTC/USDT", "binance", "buy", 0.1)
            
            # Push order to queue
            await orders_cache.push_open_order(order["ex_order_id"], "LOCAL_123")
            
            # Save order data
            await orders_cache.save_order_data("binance", order["ex_order_id"], order)
            
            # Pop order from queue
            order_id = await orders_cache.pop_open_order("LOCAL_123")
            assert order_id == order["ex_order_id"]
            
            # Verify order status
            cached_order = await orders_cache.get_order_status("binance", order["ex_order_id"])
            assert cached_order is not None
            assert cached_order.symbol == "BTC/USDT"
            assert cached_order.side == "buy"
            
            # 4. TRADE EXECUTION: Record trade
            trade = create_test_trade("BTC/USDT", "binance", 0.1)
            
            # Push trade to list
            length = await trades_cache.push_trade_list("BTC/USDT", "binance", trade)
            assert length > 0
            
            # Update trade status
            success = await trades_cache.update_trade_status("binance")
            assert success is True
            
            # Get trades
            trades = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert len(trades) == 1
            assert trades[0]["symbol"] == "BTC/USDT"
            
            # 5. POSITION UPDATE: Update account positions
            position = create_test_position("BTC/USDT", ex_id=1, volume=0.1)
            positions = [position]
            
            result = await account_cache.upsert_positions(1, positions)
            assert result is True
            
            # Verify position
            cached_positions = await account_cache.get_all_positions()
            assert len(cached_positions) >= 1
            btc_position = next(p for p in cached_positions if p.symbol == "BTC/USDT")
            assert btc_position.symbol == "BTC/USDT"
            assert btc_position.volume == 0.1
            
            # 6. PRICE UPDATE VERIFICATION: Ensure all modules reflect current price
            current_price = await tick_cache.get_price("BTC/USDT", "binance")
            assert current_price == 50000.0
            
            # Price should be available across modules
            price_tick = await tick_cache.get_price_tick("BTC/USDT", "binance")
            assert price_tick is not None
            assert price_tick.price == 50000.0
            
        finally:
            # Cleanup
            await symbol_cache._cache.close()
            await tick_cache._cache.close()
            await orders_cache._cache.close()
            await trades_cache._cache.close()
            await account_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_symbol_trading_flow(self, clean_redis):
        """Test trading workflow with multiple symbols."""
        symbol_cache = SymbolCache()
        tick_cache = TickCache()
        account_cache = AccountCache()
        
        try:
            symbols = [
                ("BTC/USDT", 50000.0),
                ("ETH/USDT", 3000.0),
                ("ADA/USDT", 1.5)
            ]
            
            positions = []
            
            for symbol_pair, price in symbols:
                # 1. Add symbol
                symbol = create_test_symbol(symbol_pair, "binance")
                import json
                async with symbol_cache._cache._redis_context() as redis_client:
                    key = "symbols_list:binance"
                    await redis_client.hset(key, symbol.symbol, json.dumps(symbol.to_dict()))
                
                # 2. Update ticker
                tick = create_test_tick(symbol_pair, "binance", price)
                await tick_cache.update_ticker("binance", tick)
                
                # 3. Create position
                position = create_test_position(symbol_pair, ex_id=1, volume=0.1)
                positions.append(position)
            
            # 4. Update all positions at once
            result = await account_cache.upsert_positions(1, positions)
            assert result is True
            
            # 5. Verify all positions exist
            cached_positions = await account_cache.get_all_positions()
            assert len(cached_positions) >= 3
            
            position_symbols = [p.symbol for p in cached_positions]
            assert "BTC/USDT" in position_symbols
            assert "ETH/USDT" in position_symbols
            assert "ADA/USDT" in position_symbols
            
            # 6. Verify prices are available for all symbols
            for symbol_pair, expected_price in symbols:
                price = await tick_cache.get_price(symbol_pair, "binance")
                assert price == expected_price
                
        finally:
            await symbol_cache._cache.close()
            await tick_cache._cache.close()
            await account_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_lifecycle_integration(self, clean_redis):
        """Test complete order lifecycle across multiple cache modules."""
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        account_cache = AccountCache()
        
        try:
            # 1. Create initial position
            initial_position = create_test_position("BTC/USDT", ex_id=1, volume=0.0)
            await account_cache.upsert_positions(1, [initial_position])
            
            # 2. Create and submit order
            order = create_test_order("BTC/USDT", "binance", "buy", 0.1)
            
            await orders_cache.push_open_order(order["ex_order_id"], "LOCAL_ORDER")
            await orders_cache.save_order_data("binance", order["ex_order_id"], order)
            
            # 3. Process order (simulate exchange processing)
            order_id = await orders_cache.pop_open_order("LOCAL_ORDER")
            assert order_id == order["ex_order_id"]
            
            # 4. Order gets filled - update status
            await orders_cache.save_order_data(
                "binance", 
                order["ex_order_id"], 
                {"status": "filled", "final_volume": 0.1}
            )
            
            # 5. Record trade from fill
            trade = create_test_trade("BTC/USDT", "binance", 0.1)
            await trades_cache.push_trade_list("BTC/USDT", "binance", trade)
            
            # 6. Update position based on trade
            updated_position = create_test_position("BTC/USDT", ex_id=1, volume=0.1)
            await account_cache.upsert_positions(1, [updated_position])
            
            # 7. Verify final state
            # Order should be filled
            final_order = await orders_cache.get_order_status("binance", order["ex_order_id"])
            assert final_order.status == "filled"
            assert final_order.final_volume == 0.1
            
            # Trade should be recorded
            trades = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert len(trades) == 1
            assert trades[0]["volume"] == 0.1
            
            # Position should be updated
            positions = await account_cache.get_all_positions()
            assert len(positions) >= 1
            btc_position = next(p for p in positions if p.symbol == "BTC/USDT")
            assert btc_position.volume == 0.1
            
        finally:
            await orders_cache._cache.close()
            await trades_cache._cache.close()
            await account_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_operations_integration(self, clean_redis):
        """Test concurrent operations across multiple cache modules."""
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        
        try:
            # Simulate concurrent market activity
            async def update_tickers():
                """Simulate real-time ticker updates."""
                for i in range(10):
                    tick = create_test_tick("BTC/USDT", "binance", 50000.0 + i)
                    await tick_cache.update_ticker("binance", tick)
                    await asyncio.sleep(0.01)  # Small delay to simulate real-time
            
            async def process_orders():
                """Simulate order processing."""
                for i in range(5):
                    order = create_test_order("BTC/USDT", "binance", "buy", 0.1)
                    order["ex_order_id"] = f"ORD_{i}"
                    
                    await orders_cache.push_open_order(order["ex_order_id"], f"LOCAL_{i}")
                    await orders_cache.save_order_data("binance", order["ex_order_id"], order)
                    await asyncio.sleep(0.02)
            
            async def record_trades():
                """Simulate trade recording."""
                for i in range(3):
                    trade = create_test_trade("BTC/USDT", "binance", 0.1)
                    await trades_cache.push_trade_list("BTC/USDT", "binance", trade)
                    await asyncio.sleep(0.03)
            
            # Run all operations concurrently
            await asyncio.gather(
                update_tickers(),
                process_orders(),
                record_trades()
            )
            
            # Verify all operations completed successfully
            # Check final ticker price
            final_price = await tick_cache.get_price("BTC/USDT", "binance")
            assert final_price == 50009.0  # Last price from update_tickers
            
            # Check orders were created
            all_orders = await orders_cache.get_orders("binance")
            assert len(all_orders) >= 5
            
            # Check trades were recorded
            trades = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert len(trades) >= 3
            
        finally:
            await tick_cache._cache.close()
            await orders_cache._cache.close()
            await trades_cache._cache.close()


class TestTradingFlowErrorHandling:
    """Test error handling in trading workflows."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_model_data_handling(self, clean_redis):
        """Test handling of invalid fullon_orm model data."""
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        
        try:
            # Test invalid order data
            invalid_order_data = {
                "symbol": "",  # Invalid empty symbol
                "side": "invalid_side",  # Invalid side
                "volume": -1.0,  # Invalid negative volume
            }
            
            # Should handle gracefully
            await orders_cache.save_order_data("binance", "INVALID_ORDER", invalid_order_data)
            
            # Order should still be retrievable (cache doesn't validate)
            order = await orders_cache.get_order_status("binance", "INVALID_ORDER")
            assert order is not None
            
            # Test invalid trade data
            invalid_trade_data = {
                "symbol": None,  # Invalid None symbol
                "volume": "not_a_number",  # Invalid volume type
            }
            
            # Should handle gracefully
            length = await trades_cache.push_trade_list("BTC/USDT", "binance", invalid_trade_data)
            assert length > 0
            
        finally:
            await orders_cache._cache.close()
            await trades_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_partial_failure_recovery(self, clean_redis):
        """Test recovery from partial failures in trading flow."""
        symbol_cache = SymbolCache()
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        
        try:
            # 1. Successfully add symbol
            symbol = create_test_symbol("BTC/USDT", "binance")
            import json
            async with symbol_cache._cache._redis_context() as redis_client:
                key = "symbols_list:binance"
                await redis_client.hset(key, symbol.symbol, json.dumps(symbol.to_dict()))
            
            # 2. Successfully update ticker
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            result = await tick_cache.update_ticker("binance", tick)
            assert result is True
            
            # 3. Attempt to create order (this should work)
            order = create_test_order("BTC/USDT", "binance", "buy", 0.1)
            await orders_cache.save_order_data("binance", order["ex_order_id"], order)
            
            # 4. Verify partial state is consistent
            # Symbol should exist
            cached_symbol = await symbol_cache.get_symbol("BTC/USDT", exchange_name="binance")
            assert cached_symbol is not None
            
            # Ticker should exist
            cached_tick = await tick_cache.get_ticker("BTC/USDT", "binance")
            assert cached_tick is not None
            
            # Order should exist
            cached_order = await orders_cache.get_order_status("binance", order["ex_order_id"])
            assert cached_order is not None
            
            # System should still be functional for new operations
            new_tick = create_test_tick("BTC/USDT", "binance", 51000.0)
            result = await tick_cache.update_ticker("binance", new_tick)
            assert result is True
            
            updated_price = await tick_cache.get_price("BTC/USDT", "binance")
            assert updated_price == 51000.0
            
        finally:
            await symbol_cache._cache.close()
            await tick_cache._cache.close()
            await orders_cache._cache.close()