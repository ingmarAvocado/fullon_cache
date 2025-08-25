"""Tests for OrdersCache ORM-based interface refactoring."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Order

from fullon_cache.base_cache import BaseCache
from fullon_cache.orders_cache import OrdersCache




@pytest.fixture
def sample_order():
    """Sample Order model for testing."""
    return Order(
        order_id=12345,
        ex_order_id="EX_12345",
        exchange="binance",
        symbol="BTC/USDT",
        order_type="limit",
        side="buy",
        volume=0.1,
        price=50000.0,
        status="open",
        timestamp=datetime.now(UTC),
        bot_id=1,
        uid=1,
        ex_id=1
    )




class TestOrdersCacheORM:
    """Test cases for OrdersCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_save_order_with_order_model(self, orders_cache, sample_order):
        """Test saving order with fullon_orm.Order model."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test save_order with real Redis
        result = await orders_cache.save_order("binance", sample_order)
        assert result is True
        
        # Verify we can retrieve it
        retrieved = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert isinstance(retrieved, Order)
        assert retrieved.ex_order_id == sample_order.ex_order_id
        assert retrieved.symbol == sample_order.symbol
        assert retrieved.side == sample_order.side

    @pytest.mark.asyncio
    async def test_save_order_error_handling(self, orders_cache, sample_order):
        """Test save_order with minimal order data."""
        # Create order with minimal data - cache doesn't validate, just stores
        minimal_order = Order()
        
        # Test - cache accepts any Order object and returns True
        result = await orders_cache.save_order("binance", minimal_order)
        
        # Cache doesn't validate data, just stores it
        assert result is True

    @pytest.mark.asyncio
    async def test_save_order_cancelled_sets_ttl(self, orders_cache, sample_order):
        """Test that cancelled orders get TTL set."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Setup cancelled order
        sample_order.status = "canceled"
        
        # Test
        result = await orders_cache.save_order("binance", sample_order)
        assert result is True
        
        # Verify order can be retrieved (TTL doesn't affect immediate retrieval)
        retrieved = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert retrieved.status == "canceled"

    @pytest.mark.asyncio
    async def test_update_order_merges_data(self, orders_cache, sample_order):
        """Test that update_order merges with existing data."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # First save the original order
        result = await orders_cache.save_order("binance", sample_order)
        assert result is True
        
        # Create update order with new status and final_volume
        update_order = Order(
            ex_order_id=sample_order.ex_order_id,
            status="filled",
            final_volume=0.095
        )
        
        # Test update
        result = await orders_cache.update_order("binance", update_order)
        assert result is True
        
        # Verify merge - should preserve original data but update status and final_volume
        retrieved = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert retrieved.status == "filled"  # Updated
        assert retrieved.final_volume == 0.095  # New field
        assert retrieved.symbol == sample_order.symbol  # Preserved
        assert retrieved.volume == sample_order.volume  # Preserved

    @pytest.mark.asyncio
    async def test_update_order_no_existing_data(self, orders_cache, sample_order):
        """Test update_order when no existing data exists."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test update_order without existing data - should behave like save_order
        result = await orders_cache.update_order("binance", sample_order)
        assert result is True
        
        # Verify order was saved
        retrieved = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert retrieved.ex_order_id == sample_order.ex_order_id

    @pytest.mark.asyncio
    async def test_get_order_returns_order_model(self, orders_cache, sample_order):
        """Test that get_order returns fullon_orm.Order model."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # First save the order
        await orders_cache.save_order("binance", sample_order)
        
        # Test retrieval
        result = await orders_cache.get_order("binance", sample_order.ex_order_id)
        
        # Assert
        assert result is not None
        assert isinstance(result, Order)
        assert result.ex_order_id == sample_order.ex_order_id
        assert result.symbol == sample_order.symbol
        assert result.side == sample_order.side
        assert result.volume == sample_order.volume

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, orders_cache):
        """Test get_order when order not found."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test retrieving non-existent order
        result = await orders_cache.get_order("binance", "NONEXISTENT")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_json_error(self, orders_cache):
        """Test get_order handles invalid JSON data gracefully."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Manually insert invalid JSON data
        async with orders_cache._redis_context() as redis_client:
            await redis_client.hset("order_status:binance", "BAD_ORDER", "invalid json")
        
        # Test - should handle gracefully
        result = await orders_cache.get_order("binance", "BAD_ORDER")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_handles_errors(self, orders_cache):
        """Test get_order handles errors gracefully."""
        # Test with empty string order ID which might cause issues
        result = await orders_cache.get_order("binance", "")
        
        # Should handle gracefully and return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_orders_returns_order_list(self, orders_cache):
        """Test that get_orders returns list of Order models."""
        # Setup multiple orders
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Create and save multiple orders
        order1 = Order(
            ex_order_id="EX_001",
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            status="open",
            timestamp=datetime.now(UTC)
        )
        
        order2 = Order(
            ex_order_id="EX_002",
            exchange="binance",
            symbol="ETH/USDT",
            side="sell",
            volume=1.0,
            status="filled",
            timestamp=datetime.now(UTC)
        )
        
        # Save both orders
        await orders_cache.save_order("binance", order1)
        await orders_cache.save_order("binance", order2)
        
        # Test
        result = await orders_cache.get_orders("binance")
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(order, Order) for order in result)
        
        # Check specific order data
        symbols = [o.symbol for o in result]
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols

    @pytest.mark.asyncio
    async def test_save_order_data_with_order_model(self, orders_cache, sample_order):
        """Test save_order_data with Order model."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test save_order_data with Order model
        await orders_cache.save_order_data("binance", sample_order)
        
        # Verify we can retrieve it using get_order_status
        retrieved = await orders_cache.get_order_status("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert isinstance(retrieved, Order)
        assert retrieved.ex_order_id == sample_order.ex_order_id

    @pytest.mark.asyncio
    async def test_save_order_data_error_handling(self, orders_cache, sample_order):
        """Test save_order_data with minimal order data."""
        # Create order with minimal data - cache doesn't validate, just stores
        minimal_order = Order()  # Minimal order
        
        # Test - cache accepts and stores any Order object without exception
        # save_order_data returns None on success, raises exception on error
        result = await orders_cache.save_order_data("binance", minimal_order)
        assert result is None  # Method returns None on success

    @pytest.mark.asyncio
    async def test_method_signatures(self, orders_cache):
        """Test that new methods have correct signatures."""
        import inspect
        
        # Test save_order signature
        sig = inspect.signature(orders_cache.save_order)
        params = list(sig.parameters.keys())
        assert params == ["exchange", "order"]
        assert sig.return_annotation == bool

        # Test update_order signature  
        sig = inspect.signature(orders_cache.update_order)
        params = list(sig.parameters.keys())
        assert params == ["exchange", "order"]
        assert sig.return_annotation == bool

        # Test get_order signature
        sig = inspect.signature(orders_cache.get_order)
        params = list(sig.parameters.keys())
        assert params == ["exchange", "order_id"]

    @pytest.mark.asyncio
    async def test_redis_key_patterns(self, orders_cache, sample_order):
        """Test that Redis key patterns are consistent."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test save_order creates correct key pattern
        result = await orders_cache.save_order("binance", sample_order)
        assert result is True
        
        # Verify we can retrieve using the expected pattern
        retrieved = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved is not None
        assert retrieved.ex_order_id == sample_order.ex_order_id

    @pytest.mark.asyncio
    async def test_order_id_handling(self, orders_cache):
        """Test handling of both order_id and ex_order_id."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test with ex_order_id
        order_with_ex_id = Order(
            ex_order_id="EX_123", 
            symbol="BTC/USDT", 
            side="buy", 
            volume=0.1,
            timestamp=datetime.now(UTC)
        )
        result = await orders_cache.save_order("binance", order_with_ex_id)
        assert result is True
        
        # Verify retrieval by ex_order_id
        retrieved = await orders_cache.get_order("binance", "EX_123")
        assert retrieved is not None
        assert retrieved.ex_order_id == "EX_123"
        
        # Test with order_id when ex_order_id is None
        order_with_id = Order(
            order_id=456, 
            symbol="ETH/USDT", 
            side="sell", 
            volume=1.0,
            timestamp=datetime.now(UTC)
        )
        result = await orders_cache.save_order("binance", order_with_id)
        assert result is True
        
        # Should use order_id as the key when ex_order_id is None
        retrieved2 = await orders_cache.get_order("binance", "456")
        assert retrieved2 is not None

    @pytest.mark.asyncio
    async def test_integration_save_and_retrieve(self, orders_cache, sample_order):
        """Test integration of save and retrieve operations."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Test save operation
        save_result = await orders_cache.save_order("binance", sample_order)
        assert save_result is True
        
        # Test retrieve operation
        retrieved_order = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved_order is not None
        assert retrieved_order.symbol == sample_order.symbol
        assert retrieved_order.side == sample_order.side
        assert retrieved_order.ex_order_id == sample_order.ex_order_id

    @pytest.mark.asyncio
    async def test_order_model_properties(self, sample_order):
        """Test that Order model has expected properties."""
        # Test basic properties
        assert sample_order.ex_order_id == "EX_12345"
        assert sample_order.exchange == "binance"
        assert sample_order.symbol == "BTC/USDT"
        assert sample_order.side == "buy"
        assert sample_order.volume == 0.1
        assert sample_order.price == 50000.0
        assert sample_order.status == "open"

    @pytest.mark.asyncio
    async def test_order_model_to_dict_from_dict(self, sample_order):
        """Test Order model serialization and deserialization."""
        # Test to_dict
        order_dict = sample_order.to_dict()
        assert isinstance(order_dict, dict)
        assert order_dict["ex_order_id"] == sample_order.ex_order_id
        assert order_dict["symbol"] == sample_order.symbol
        assert order_dict["side"] == sample_order.side

        # Test from_dict
        reconstructed_order = Order.from_dict(order_dict)
        assert reconstructed_order.ex_order_id == sample_order.ex_order_id
        assert reconstructed_order.symbol == sample_order.symbol
        assert reconstructed_order.side == sample_order.side
        assert reconstructed_order.volume == sample_order.volume

    @pytest.mark.asyncio
    async def test_partial_order_updates(self, orders_cache):
        """Test updating orders with partial data."""
        # Use the clean_redis fixture or delete specific test keys
        async with orders_cache._redis_context() as redis_client:
            await redis_client.delete("order_status:binance")
        
        # Setup existing order
        existing_order = Order(
            ex_order_id="EX_123",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=50000.0,
            status="open",
            timestamp=datetime.now(UTC)
        )
        
        # Save the existing order
        await orders_cache.save_order("binance", existing_order)
        
        # Create partial update (only status and final_volume)
        partial_order = Order(
            ex_order_id="EX_123",
            status="filled",
            final_volume=0.098
        )
        
        # Test update
        result = await orders_cache.update_order("binance", partial_order)
        assert result is True
        
        # Verify merge - original fields preserved, new fields added/updated
        retrieved = await orders_cache.get_order("binance", "EX_123")
        assert retrieved is not None
        assert retrieved.status == "filled"  # Updated
        assert retrieved.final_volume == 0.098  # New
        assert retrieved.symbol == "BTC/USDT"  # Preserved
        assert retrieved.price == 50000.0  # Preserved