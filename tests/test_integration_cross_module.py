"""Cross-module integration tests for fullon_orm model interfaces.

This module tests interactions between different cache modules to ensure
they work seamlessly together with fullon_orm models.
"""

import json
from datetime import UTC, datetime

import pytest
from fullon_orm.models import Symbol, Tick, Order, Trade, Position

from fullon_cache import (
    TickCache, OrdersCache, TradesCache, AccountCache, BotCache
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


def create_test_order(symbol="BTC/USDT", side="buy", volume=0.1, order_id="ORD_001", exchange="binance", **kwargs):
    """Factory for test Order objects."""
    return Order(
        ex_order_id=order_id,
        ex_id=exchange,
        symbol=symbol,
        side=side,
        order_type=kwargs.get("order_type", "market"),
        volume=volume,
        price=kwargs.get("price", 50000.0),
        uid=kwargs.get("uid", "user_123"),
        status=kwargs.get("status", "open"),
        bot_id=kwargs.get("bot_id", 123),
        cat_ex_id=kwargs.get("cat_ex_id", 1),
        final_volume=kwargs.get("final_volume"),
        timestamp=kwargs.get("timestamp", datetime.now(UTC))
    )



class TestTickOrderIntegration:
    """Test integration between TickCache and OrdersCache."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_price_updates_with_order_management(self, clean_redis):
        """Test price updates alongside order management."""
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        
        try:
            # 1. Set initial price
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await tick_cache.update_ticker("binance", tick)
            
            # 2. Create order at current price
            order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="limit",
                volume=0.1,
                price=50000.0,
                status="open",
                order_id="ORD_001",
                exchange="binance"
            )
            
            await orders_cache.save_order_data("binance", order)
            
            # 3. Update price (simulate market movement)
            new_tick = create_test_tick("BTC/USDT", "binance", 50500.0)
            await tick_cache.update_ticker("binance", new_tick)
            
            # 4. Verify price updated
            current_price = await tick_cache.get_price("BTC/USDT", "binance")
            assert current_price == 50500.0
            
            # 5. Check if order should be filled (price moved favorably)
            order = await orders_cache.get_order_status("binance", "ORD_001")
            assert order is not None
            assert order.price == 50000.0  # Order price unchanged
            
            # 6. Simulate order fill due to price movement
            filled_order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                order_type="limit",
                volume=0.1,
                price=50000.0,
                status="filled",
                order_id="ORD_001",
                exchange="binance"
            )
            await orders_cache.save_order_data("binance", filled_order)
            
            # 7. Verify order is filled
            filled_order = await orders_cache.get_order_status("binance", "ORD_001")
            assert filled_order.status == "filled"
            
        finally:
            await tick_cache._cache.close()
            await orders_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_symbol_price_order_coordination(self, clean_redis):
        """Test price updates and orders across multiple symbols."""
        tick_cache = TickCache()
        orders_cache = OrdersCache()
        
        try:
            symbols_data = [
                ("BTC/USDT", 50000.0),
                ("ETH/USDT", 3000.0),
                ("ADA/USDT", 1.5)
            ]
            
            # 1. Update prices for all symbols
            for symbol, price in symbols_data:
                tick = create_test_tick(symbol, "binance", price)
                await tick_cache.update_ticker("binance", tick)
            
            # 2. Create orders for all symbols
            for i, (symbol, price) in enumerate(symbols_data):
                order = create_test_order(
                    symbol=symbol,
                    side="buy",
                    volume=0.1,
                    price=price,
                    status="open",
                    order_id=f"ORD_{i}",
                    exchange="binance"
                )
                await orders_cache.save_order_data("binance", order)
            
            # 3. Verify all prices are current
            for symbol, expected_price in symbols_data:
                current_price = await tick_cache.get_price(symbol, "binance")
                assert current_price == expected_price
            
            # 4. Verify all orders exist
            all_orders = await orders_cache.get_orders("binance")
            assert len(all_orders) == 3
            
            order_symbols = [order.symbol for order in all_orders]
            for symbol, _ in symbols_data:
                assert symbol in order_symbols
                
        finally:
            await tick_cache._cache.close()
            await orders_cache._cache.close()


class TestOrderTradeAccountIntegration:
    """Test integration between OrdersCache, TradesCache, and AccountCache."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_fill_trade_position_update_flow(self, clean_redis):
        """Test complete flow from order fill to trade recording to position update."""
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        account_cache = AccountCache()
        
        try:
            # 1. Start with empty position
            initial_position = Position(
                symbol="BTC/USDT",
                volume=0.0,
                price=0.0,
                cost=0.0,
                fee=0.0,
                ex_id="1"
            )
            
            await account_cache.upsert_positions(1, [initial_position])
            
            # 2. Create buy order
            buy_order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=50000.0,
                status="open",
                uid="123",
                order_id="ORD_BUY",
                exchange="binance"
            )
            
            await orders_cache.save_order_data("binance", buy_order)
            
            # 3. Fill the order
            filled_buy_order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=50000.0,
                status="filled",
                final_volume=0.1,
                uid="123",
                order_id="ORD_BUY",
                exchange="binance"
            )
            await orders_cache.save_order_data("binance", filled_buy_order)
            
            # 4. Record trade from the fill
            trade_data = {
                "trade_id": "TRD_001",
                "ex_order_id": "ORD_BUY",
                "symbol": "BTC/USDT",
                "side": "buy",
                "volume": 0.1,
                "price": 50000.0,
                "cost": 5000.0,
                "fee": 5.0,
                "uid": "123"
            }
            
            await trades_cache.push_trade_list("BTC/USDT", "binance", trade_data)
            
            # 5. Update position based on trade
            updated_position = Position(
                symbol="BTC/USDT",
                volume=0.1,
                price=50000.0,
                cost=5000.0,
                fee=5.0,
                ex_id="1"
            )
            
            await account_cache.upsert_positions(1, [updated_position])
            
            # 6. Verify entire flow
            # Order should be filled
            final_order = await orders_cache.get_order_status("binance", "ORD_BUY")
            assert final_order.status == "filled"
            assert final_order.final_volume == 0.1
            
            # Trade should be recorded
            trades = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert len(trades) == 1
            assert trades[0]["side"] == "buy"
            assert trades[0]["volume"] == 0.1
            
            # Position should be updated
            positions = await account_cache.get_positions(1)
            assert len(positions) == 1
            assert positions[0].volume == 0.1
            # Note: Position model doesn't have side attribute, it's calculated from volume
            
        finally:
            await orders_cache._cache.close()
            await trades_cache._cache.close()
            await account_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_orders_position_aggregation(self, clean_redis):
        """Test multiple orders affecting the same position."""
        orders_cache = OrdersCache()
        trades_cache = TradesCache()
        account_cache = AccountCache()
        
        try:
            # 1. Start with empty position
            position = Position(
                symbol="ETH/USDT",
                volume=0.0,
                price=0.0,
                cost=0.0,
                fee=0.0,
                ex_id="1"
            )
            
            await account_cache.upsert_positions(1, [position])
            
            # 2. Execute multiple buy orders
            trades = []
            total_volume = 0.0
            total_cost = 0.0
            
            for i in range(3):
                volume = 0.1 * (i + 1)  # 0.1, 0.2, 0.3
                price = 3000.0 + i * 10  # 3000, 3010, 3020
                cost = volume * price
                
                # Create and fill order
                order = create_test_order(
                    symbol="ETH/USDT",
                    side="buy",
                    volume=volume,
                    price=price,
                    status="filled",
                    final_volume=volume,
                    uid="456",
                    order_id=f"ORD_{i}",
                    exchange="kraken"
                )
                
                await orders_cache.save_order_data("kraken", order)
                
                # Record trade
                trade_data = {
                    "trade_id": f"TRD_{i}",
                    "ex_order_id": f"ORD_{i}",
                    "symbol": "ETH/USDT",
                    "side": "buy",
                    "volume": volume,
                    "price": price,
                    "cost": cost,
                    "fee": 1.0,
                    "uid": "456"
                }
                
                await trades_cache.push_trade_list("ETH/USDT", "kraken", trade_data)
                trades.append(trade_data)
                
                total_volume += volume
                total_cost += cost
            
            # 3. Update position with aggregated data
            avg_entry_price = total_cost / total_volume
            final_position = Position(
                symbol="ETH/USDT",
                volume=total_volume,
                price=avg_entry_price,
                cost=total_cost,
                fee=sum(trades[i].get('fee', 0) for i in range(len(trades))),
                ex_id="1"
            )
            
            await account_cache.upsert_positions(1, [final_position])
            
            # 4. Verify aggregation
            # All orders should exist and be filled
            all_orders = await orders_cache.get_orders("kraken")
            filled_orders = [o for o in all_orders if o.status == "filled"]
            assert len(filled_orders) == 3
            
            # All trades should be recorded
            all_trades = await trades_cache.get_trades_list("ETH/USDT", "kraken")
            assert len(all_trades) == 3
            
            # Position should reflect aggregated data
            positions = await account_cache.get_positions(1)
            eth_position = next(p for p in positions if p.symbol == "ETH/USDT")
            assert abs(eth_position.volume - 0.6) < 0.001  # 0.1 + 0.2 + 0.3 (handle floating point precision)
            assert abs(eth_position.price - avg_entry_price) < 0.01
            
        finally:
            await orders_cache._cache.close()
            await trades_cache._cache.close()
            await account_cache._cache.close()


class TestBotCacheIntegration:
    """Test BotCache integration with other modules."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_bot_coordination_with_orders(self, clean_redis):
        """Test bot coordination preventing duplicate orders."""
        bot_cache = BotCache()
        orders_cache = OrdersCache()
        tick_cache = TickCache()
        
        try:
            # 1. Update ticker to establish current price
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await tick_cache.update_ticker("binance", tick)
            
            # 2. Bot 1 blocks the symbol for trading
            result = await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
            assert result is True
            
            # 3. Bot 1 creates an order
            bot_order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=50000.0,
                status="open",
                bot_id="bot_1",
                order_id="BOT1_ORD",
                exchange="binance"
            )
            
            await orders_cache.save_order_data("binance", bot_order)
            
            # 4. Verify bot 1 has control
            blocking_bot = await bot_cache.is_blocked("binance", "BTC/USDT")
            assert blocking_bot == "bot_1"
            
            # 5. Bot 1 marks opening position
            await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")
            is_opening = await bot_cache.is_opening_position("binance", "BTC/USDT")
            assert is_opening is True
            
            # 6. Simulate order completion and cleanup
            filled_bot_order = create_test_order(
                symbol="BTC/USDT",
                side="buy",
                volume=0.1,
                price=50000.0,
                status="filled",
                bot_id="bot_1",
                order_id="BOT1_ORD",
                exchange="binance"
            )
            await orders_cache.save_order_data("binance", filled_bot_order)
            
            # 7. Bot 1 releases control
            await bot_cache.unmark_opening_position("binance", "BTC/USDT")
            await bot_cache.unblock_exchange("binance", "BTC/USDT")
            
            # 8. Verify cleanup
            blocking_bot = await bot_cache.is_blocked("binance", "BTC/USDT")
            assert blocking_bot == ""
            
            is_opening = await bot_cache.is_opening_position("binance", "BTC/USDT")
            assert is_opening is False
            
            # 9. Now bot 2 can take control
            result = await bot_cache.block_exchange("binance", "BTC/USDT", "bot_2")
            assert result is True
            
            blocking_bot = await bot_cache.is_blocked("binance", "BTC/USDT")
            assert blocking_bot == "bot_2"
            
        finally:
            await bot_cache._cache.close()
            await orders_cache._cache.close()
            await tick_cache._cache.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_bot_multi_symbol_coordination(self, clean_redis):
        """Test multiple bots coordinating across multiple symbols."""
        bot_cache = BotCache()
        orders_cache = OrdersCache()
        
        try:
            symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
            bots = ["bot_alpha", "bot_beta", "bot_gamma"]
            
            # 1. Each bot takes control of one symbol
            for i, (bot, symbol) in enumerate(zip(bots, symbols)):
                result = await bot_cache.block_exchange("binance", symbol, bot)
                assert result is True
                
                # Create order for the bot
                order = create_test_order(
                    symbol=symbol,
                    side="buy",
                    volume=0.1,
                    price=1000.0 * (i + 1),  # Different prices
                    status="open",
                    bot_id=bot,
                    order_id=f"{bot}_ORD",
                    exchange="binance"
                )
                
                await orders_cache.save_order_data("binance", order)
            
            # 2. Verify each bot controls its symbol
            for bot, symbol in zip(bots, symbols):
                blocking_bot = await bot_cache.is_blocked("binance", symbol)
                assert blocking_bot == bot
            
            # 3. Get all blocks
            all_blocks = await bot_cache.get_blocks()
            assert len(all_blocks) == 3
            
            block_pairs = [(b["ex_id"], b["symbol"]) for b in all_blocks]
            for symbol in symbols:
                assert ("binance", symbol) in block_pairs
            
            # 4. Verify all orders exist
            all_orders = await orders_cache.get_orders("binance")
            assert len(all_orders) == 3
            
            order_symbols = [o.symbol for o in all_orders]
            for symbol in symbols:
                assert symbol in order_symbols
            
            # 5. Simulate bot operations completing
            for bot, symbol in zip(bots, symbols):
                # Mark opening position
                await bot_cache.mark_opening_position("binance", symbol, bot)
                
                # Fill order
                # Need to find original symbol for this bot
                bot_symbol = symbols[bots.index(bot)]
                bot_price = 1000.0 * (bots.index(bot) + 1)
                
                filled_order = create_test_order(
                    symbol=bot_symbol,
                    side="buy",
                    volume=0.1,
                    price=bot_price,
                    status="filled",
                    bot_id=bot,
                    order_id=f"{bot}_ORD",
                    exchange="binance"
                )
                await orders_cache.save_order_data("binance", filled_order)
                
                # Complete and release
                await bot_cache.unmark_opening_position("binance", symbol)
                await bot_cache.unblock_exchange("binance", symbol)
            
            # 6. Verify all bots released control
            for symbol in symbols:
                blocking_bot = await bot_cache.is_blocked("binance", symbol)
                assert blocking_bot == ""
                
                is_opening = await bot_cache.is_opening_position("binance", symbol)
                assert is_opening is False
            
            # 7. All symbols should be available for new bots
            all_blocks = await bot_cache.get_blocks()
            assert len(all_blocks) == 0
            
        finally:
            await bot_cache._cache.close()
            await orders_cache._cache.close()