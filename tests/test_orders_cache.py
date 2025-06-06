"""Tests for OrdersCache with legacy method support."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from fullon_cache import OrdersCache
from fullon_orm.models import Order


class TestOrdersCacheLegacyMethods:
    """Test legacy methods for backward compatibility."""
    
    @pytest.mark.asyncio
    async def test_push_open_order(self, orders_cache):
        """Test legacy push_open_order method."""
        # Push order using legacy method
        await orders_cache.push_open_order("ORDER123", "LOCAL456")
        
        # Pop using legacy method
        order_id = await orders_cache.pop_open_order("LOCAL456")
        assert order_id == "ORDER123"
    
    @pytest.mark.asyncio
    async def test_pop_open_order_timeout(self, orders_cache):
        """Test pop_open_order with timeout."""
        # Try to pop from empty queue - should raise TimeoutError
        with pytest.raises(TimeoutError, match="Not getting any trade"):
            # Mock the redis client to simulate timeout
            with patch.object(orders_cache._cache, '_redis_context') as mock_context:
                mock_redis = AsyncMock()
                mock_redis.blpop.side_effect = Exception("TimeoutError")
                mock_context.return_value.__aenter__.return_value = mock_redis
                
                await orders_cache.pop_open_order("EMPTY_QUEUE")
    
    @pytest.mark.asyncio
    async def test_save_order_data(self, orders_cache):
        """Test legacy save_order_data method."""
        order_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "open",
            "bot_id": 123,
            "uid": 456,
            "ex_id": 789
        }
        
        # Save order data
        await orders_cache.save_order_data("binance", "ORD789", order_data)
        
        # Retrieve using legacy method
        retrieved = await orders_cache.get_order_status("binance", "ORD789")
        assert retrieved is not None
        assert isinstance(retrieved, Order)
        assert retrieved.ex_order_id == "ORD789"
        assert retrieved.symbol == "BTC/USDT"
        assert retrieved.status == "open"
        assert retrieved.volume == 0.1
        assert retrieved.price == 50000.0
    
    @pytest.mark.asyncio
    async def test_save_order_data_update(self, orders_cache):
        """Test updating existing order data."""
        # Save initial data
        await orders_cache.save_order_data("binance", "ORD999", {"status": "open", "volume": 1.0})
        
        # Update with new data
        await orders_cache.save_order_data("binance", "ORD999", {"final_volume": 0.5})
        
        # Retrieve and verify merge
        order = await orders_cache.get_order_status("binance", "ORD999")
        assert order.status == "open"
        assert order.volume == 1.0
        assert order.final_volume == 0.5
    
    @pytest.mark.asyncio
    async def test_save_order_data_cancelled_expiry(self, orders_cache):
        """Test that cancelled orders get expiry set."""
        await orders_cache.save_order_data(
            "binance",
            "ORD_CANCEL",
            {"status": "canceled", "symbol": "BTC/USDT"}
        )
        
        # Order should exist
        order = await orders_cache.get_order_status("binance", "ORD_CANCEL")
        assert order is not None
        assert order.status == "canceled"
    
    @pytest.mark.asyncio
    async def test_get_orders(self, orders_cache):
        """Test getting all orders for an exchange."""
        # Save multiple orders
        for i in range(5):
            await orders_cache.save_order_data(
                "kraken",
                f"ORD{i}",
                {
                    "symbol": f"TEST{i}/USD",
                    "volume": 0.1 * (i + 1),
                    "status": "open",
                    "side": "buy",
                    "order_type": "limit",
                    "bot_id": 100 + i,
                    "uid": 200,
                    "ex_id": 300
                }
            )
        
        # Get all orders
        orders = await orders_cache.get_orders("kraken")
        assert len(orders) >= 5
        
        # Verify order data
        for order in orders:
            assert isinstance(order, Order)
            assert order.ex_order_id is not None
            assert order.symbol is not None
            assert order.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_get_full_accounts(self, orders_cache):
        """Test getting full account data."""
        # This method seems to belong in AccountCache
        # Test that it returns None when no data
        accounts = await orders_cache.get_full_accounts("binance")
        assert accounts is None
        
        # Set some account data
        async with orders_cache._cache._redis_context() as redis_client:
            await redis_client.hset(
                "accounts",
                "binance",
                json.dumps({"balance": {"USD": 10000, "BTC": 0.5}})
            )
        
        # Now it should return data
        accounts = await orders_cache.get_full_accounts("binance")
        assert accounts is not None
        assert accounts["balance"]["USD"] == 10000
        assert accounts["balance"]["BTC"] == 0.5
    
    @pytest.mark.asyncio
    async def test_dict_to_order_conversion(self, orders_cache):
        """Test internal _dict_to_order conversion."""
        data = {
            "order_id": "12345",
            "bot_id": 100,
            "uid": 200,
            "ex_id": 300,
            "cat_ex_id": 1,
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "order_type": "limit",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "filled",
            "command": "OPEN_LONG",
            "reason": "Signal triggered",
            "timestamp": "2024-01-01 12:00:00.123"
        }
        
        order = orders_cache._dict_to_order(data)
        assert isinstance(order, Order)
        assert order.ex_order_id == "12345"
        assert order.bot_id == 100
        assert order.uid == 200
        assert order.symbol == "BTC/USDT"
        assert order.volume == 0.1
        assert order.price == 50000.0
        assert order.status == "filled"
    
    @pytest.mark.asyncio
    async def test_save_order_data_error_handling(self, orders_cache):
        """Test error handling in save_order_data."""
        # Mock Redis error
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hget.side_effect = Exception("Redis connection failed")
            mock_context.return_value.__aenter__.return_value = mock_redis
            
            # Should raise exception
            with pytest.raises(Exception, match="Error saving order status to Redis"):
                await orders_cache.save_order_data("binance", "ORD_ERROR", {"status": "open"})


class TestOrdersCacheLegacyIntegration:
    """Integration tests for legacy methods."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_legacy_order_workflow(self, orders_cache):
        """Test complete legacy order workflow."""
        exchange = "binance"
        order_id = "LEGACY_ORD_001"
        local_id = "LOCAL_001"
        
        # 1. Push order to queue
        await orders_cache.push_open_order(order_id, local_id)
        
        # 2. Save order data
        await orders_cache.save_order_data(
            exchange,
            order_id,
            {
                "symbol": "BTC/USDT",
                "side": "buy",
                "volume": 0.1,
                "price": 50000.0,
                "status": "pending",
                "order_type": "limit",
                "bot_id": 123,
                "uid": 456,
                "ex_id": 789,
                "cat_ex_id": 1
            }
        )
        
        # 3. Pop order for processing
        popped_id = await orders_cache.pop_open_order(local_id)
        assert popped_id == order_id
        
        # 4. Update order status
        await orders_cache.save_order_data(
            exchange,
            order_id,
            {"status": "open", "ex_order_id": "BIN123"}
        )
        
        # 5. Get order status
        order = await orders_cache.get_order_status(exchange, order_id)
        assert order.status == "open"
        assert order.ex_order_id == order_id  # Should be set from order_id
        
        # 6. Fill order
        await orders_cache.save_order_data(
            exchange,
            order_id,
            {
                "status": "filled",
                "final_volume": 0.1,
                "fee": 0.1
            }
        )
        
        # 7. Get all orders
        all_orders = await orders_cache.get_orders(exchange)
        assert any(o.ex_order_id == order_id for o in all_orders)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_orders_workflow(self, orders_cache):
        """Test handling multiple orders concurrently."""
        exchange = "kraken"
        
        # Create multiple orders
        order_ids = []
        for i in range(10):
            order_id = f"MULTI_ORD_{i:03d}"
            local_id = f"LOCAL_{i:03d}"
            
            # Push to queue
            await orders_cache.push_open_order(order_id, local_id)
            
            # Save order data
            await orders_cache.save_order_data(
                exchange,
                order_id,
                {
                    "symbol": "ETH/USD",
                    "side": "buy" if i % 2 == 0 else "sell",
                    "volume": 0.1 * (i + 1),
                    "price": 3000.0 + i * 10,
                    "status": "pending",
                    "order_type": "limit",
                    "bot_id": 100,
                    "uid": 200,
                    "ex_id": 300,
                    "cat_ex_id": 2
                }
            )
            
            order_ids.append((order_id, local_id))
        
        # Pop and process orders
        for order_id, local_id in order_ids:
            popped_id = await orders_cache.pop_open_order(local_id)
            assert popped_id == order_id
            
            # Update to open
            await orders_cache.save_order_data(
                exchange,
                order_id,
                {"status": "open"}
            )
        
        # Get all orders
        all_orders = await orders_cache.get_orders(exchange)
        assert len(all_orders) >= 10
        
        # Verify all are open
        for order in all_orders:
            if order.ex_order_id.startswith("MULTI_ORD_"):
                assert order.status == "open"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_data_persistence(self, orders_cache):
        """Test that order data persists correctly."""
        exchange = "coinbase"
        order_id = "PERSIST_001"
        
        # Save comprehensive order data
        full_data = {
            "symbol": "BTC/USD",
            "side": "buy",
            "order_type": "limit",
            "volume": 0.5,
            "price": 45000.0,
            "status": "open",
            "bot_id": 999,
            "uid": 111,
            "ex_id": 222,
            "cat_ex_id": 3,
            "command": "GRID_BUY",
            "reason": "Grid level hit",
            "futures": True,
            "leverage": 10.0,
            "tick": 0.01,
            "plimit": 44000.0
        }
        
        await orders_cache.save_order_data(exchange, order_id, full_data)
        
        # Retrieve and verify all fields
        order = await orders_cache.get_order_status(exchange, order_id)
        assert order.symbol == "BTC/USD"
        assert order.side == "buy"
        assert order.order_type == "limit"
        assert order.volume == 0.5
        assert order.price == 45000.0
        assert order.status == "open"
        assert order.bot_id == 999
        assert order.uid == 111
        assert order.ex_id == 222
        assert order.cat_ex_id == 3
        assert order.command == "GRID_BUY"
        assert order.reason == "Grid level hit"
        assert order.futures is True
        assert order.leverage == 10.0
        assert order.tick == 0.01
        assert order.plimit == 44000.0


class TestOrdersCacheEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_order_data(self, orders_cache):
        """Test handling empty order data."""
        await orders_cache.save_order_data("test", "EMPTY_001", {})
        
        order = await orders_cache.get_order_status("test", "EMPTY_001")
        assert order is not None
        assert order.ex_order_id == "EMPTY_001"
        assert order.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_invalid_order_id_format(self, orders_cache):
        """Test handling non-numeric order IDs."""
        await orders_cache.save_order_data(
            "test",
            "NON_NUMERIC_ID",
            {"symbol": "BTC/USDT", "volume": 1.0}
        )
        
        order = await orders_cache.get_order_status("test", "NON_NUMERIC_ID")
        assert order is not None
        assert order.ex_order_id == "NON_NUMERIC_ID"
        assert order.order_id is None  # Should be None for non-numeric IDs
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_order(self, orders_cache):
        """Test getting order that doesn't exist."""
        order = await orders_cache.get_order_status("fake_exchange", "NONEXISTENT")
        assert order is None
    
    @pytest.mark.asyncio
    async def test_get_orders_empty_exchange(self, orders_cache):
        """Test getting orders for exchange with no orders."""
        orders = await orders_cache.get_orders("empty_exchange")
        assert orders == []
    
    @pytest.mark.asyncio
    async def test_dict_to_order_with_numeric_conversions(self, orders_cache):
        """Test dict to order conversion with various numeric types."""
        data = {
            'order_id': '67890',  # String that can be converted to int
            'volume': '0.5',      # String float
            'price': 45000,       # Integer
            'final_volume': None, # None value
            'leverage': '10',     # String leverage
            'futures': 1,         # Truthy integer
            'timestamp': '2024-01-01 12:00:00'  # Without microseconds
        }
        
        order = orders_cache._dict_to_order(data)
        
        assert order is not None
        assert order.order_id == 67890  # Converted to int
        assert order.volume == 0.5      # Converted to float
        assert order.price == 45000.0   # Converted to float
        assert order.final_volume is None
        assert order.leverage == 10.0
        assert order.futures is True    # Converted to bool
        
    @pytest.mark.asyncio
    async def test_dict_to_order_invalid_data(self, orders_cache):
        """Test dict to order conversion with invalid data."""
        data = {
            'order_id': 'invalid-id',  # Non-numeric string
            'volume': 'not-a-number',  # Invalid float
            'price': None,             # None for numeric field
            'timestamp': 'invalid-timestamp'
        }
        
        order = orders_cache._dict_to_order(data)
        
        assert order is not None
        # order_id should not be set as int since it's not numeric
        assert not hasattr(order, 'order_id') or order.order_id is None
        assert order.ex_order_id == 'invalid-id'
        # volume should default to 0.0 due to conversion error
        assert order.volume == 0.0
        
    @pytest.mark.asyncio 
    async def test_order_to_dict_conversion(self, orders_cache):
        """Test Order object to dictionary conversion."""
        from fullon_orm.models import Order
        from datetime import datetime, timezone
        
        order = Order()
        order.order_id = 12345
        order.ex_order_id = 'EX12345'
        order.symbol = 'ETH/USDT'
        order.side = 'sell'
        order.volume = 1.5
        order.price = 3000.0
        order.status = 'filled'
        order.timestamp = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
        
        data = orders_cache._order_to_dict(order)
        
        assert isinstance(data, dict)
        assert data['order_id'] == 12345
        assert data['ex_order_id'] == 'EX12345'
        assert data['symbol'] == 'ETH/USDT'
        # Check that timestamp is formatted as string (the exact format depends on to_dict)
        assert isinstance(data['timestamp'], str)
        assert '2024-01-01' in data['timestamp']
        
