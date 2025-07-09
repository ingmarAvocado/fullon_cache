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
def mock_base_cache():
    """Mock BaseCache for testing."""
    cache = AsyncMock(spec=BaseCache)
    # Mock the _to_redis_timestamp and _from_redis_timestamp methods
    cache._to_redis_timestamp.return_value = "2023-01-01T00:00:00Z"
    cache._from_redis_timestamp.return_value = datetime.now(UTC)
    return cache


@pytest.fixture
def orders_cache(mock_base_cache):
    """Create OrdersCache instance with mocked BaseCache."""
    cache = OrdersCache()
    cache._cache = mock_base_cache
    return cache


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


@pytest.fixture
def mock_redis_context():
    """Mock redis context manager."""
    mock_redis = AsyncMock()
    
    @pytest.fixture
    def context_manager():
        return mock_redis
    
    return context_manager


class TestOrdersCacheORM:
    """Test cases for OrdersCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_save_order_with_order_model(self, orders_cache, mock_base_cache, sample_order):
        """Test saving order with fullon_orm.Order model."""
        # Setup mock redis context
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test
        result = await orders_cache.save_order("binance", sample_order)

        # Assert
        assert result is True
        
        # Verify hset was called
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "order_status:binance"
        assert call_args[0][1] == "EX_12345"  # ex_order_id used as key
        
        # Verify the data was JSON serialized
        stored_data = json.loads(call_args[0][2])
        assert stored_data["symbol"] == sample_order.symbol
        assert stored_data["side"] == sample_order.side
        assert stored_data["volume"] == sample_order.volume

    @pytest.mark.asyncio
    async def test_save_order_error_handling(self, orders_cache, mock_base_cache, sample_order):
        """Test save_order error handling."""
        # Setup mock to raise exception
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.side_effect = Exception("Redis error")

        # Test
        result = await orders_cache.save_order("binance", sample_order)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_save_order_cancelled_sets_ttl(self, orders_cache, mock_base_cache, sample_order):
        """Test that cancelled orders get TTL set."""
        # Setup cancelled order
        sample_order.status = "canceled"
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test
        result = await orders_cache.save_order("binance", sample_order)

        # Assert
        assert result is True
        mock_redis.expire.assert_called_once_with("order_status:binance", 3600)  # 1 hour

    @pytest.mark.asyncio
    async def test_update_order_merges_data(self, orders_cache, mock_base_cache, sample_order):
        """Test that update_order merges with existing data."""
        # Setup existing data
        existing_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "open"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(existing_data)
        mock_redis.hset.return_value = True

        # Create update order with new status
        update_order = Order(
            ex_order_id="EX_12345",
            status="filled",
            final_volume=0.095
        )

        # Test
        result = await orders_cache.update_order("binance", update_order)

        # Assert
        assert result is True
        
        # Verify merge occurred
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        merged_data = json.loads(call_args[0][2])
        
        assert merged_data["status"] == "filled"  # Updated
        assert merged_data["final_volume"] == 0.095  # New field
        assert merged_data["symbol"] == "BTC/USDT"  # Preserved
        assert merged_data["volume"] == 0.1  # Preserved

    @pytest.mark.asyncio
    async def test_update_order_no_existing_data(self, orders_cache, mock_base_cache, sample_order):
        """Test update_order when no existing data exists."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = None  # No existing data
        mock_redis.hset.return_value = True

        # Test
        result = await orders_cache.update_order("binance", sample_order)

        # Assert - should behave like save_order
        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_order_returns_order_model(self, orders_cache, mock_base_cache, sample_order):
        """Test that get_order returns fullon_orm.Order model."""
        # Setup mock data
        order_dict = {
            "order_id": "EX_12345",
            "ex_order_id": "EX_12345",
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "open",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(order_dict)

        # Test
        result = await orders_cache.get_order("binance", "EX_12345")

        # Assert
        assert result is not None
        assert isinstance(result, Order)
        assert result.ex_order_id == "EX_12345"
        assert result.symbol == "BTC/USDT"
        assert result.side == "buy"
        assert result.volume == 0.1

        # Verify correct Redis key was used
        mock_redis.hget.assert_called_once_with("order_status:binance", "EX_12345")

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, orders_cache, mock_base_cache):
        """Test get_order when order not found."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = None

        # Test
        result = await orders_cache.get_order("binance", "NONEXISTENT")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_json_error(self, orders_cache, mock_base_cache):
        """Test get_order with invalid JSON data."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = "invalid json"

        # Test
        result = await orders_cache.get_order("binance", "EX_12345")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_general_error(self, orders_cache, mock_base_cache):
        """Test get_order with general error."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.side_effect = Exception("Redis error")

        # Test
        result = await orders_cache.get_order("binance", "EX_12345")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_orders_returns_order_list(self, orders_cache, mock_base_cache):
        """Test that get_orders returns list of Order models."""
        # Setup multiple orders
        orders_data = {
            "EX_001": json.dumps({
                "order_id": "EX_001",
                "ex_order_id": "EX_001",
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "volume": 0.1,
                "status": "open"
            }),
            "EX_002": json.dumps({
                "order_id": "EX_002", 
                "ex_order_id": "EX_002",
                "exchange": "binance",
                "symbol": "ETH/USDT",
                "side": "sell",
                "volume": 1.0,
                "status": "filled"
            })
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hgetall.return_value = orders_data

        # Test
        result = await orders_cache.get_orders("binance")

        # Assert
        assert len(result) == 2
        assert all(isinstance(order, Order) for order in result)
        
        # Check specific order data
        btc_order = next(o for o in result if o.symbol == "BTC/USDT")
        assert btc_order.ex_order_id == "EX_001"
        assert btc_order.side == "buy"

    @pytest.mark.asyncio
    async def test_backward_compatibility_save_order_data_legacy(self, orders_cache, mock_base_cache):
        """Test backward compatibility with save_order_data_legacy."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = None  # No existing data
        mock_redis.hset.return_value = True

        # Test legacy method
        data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "open"
        }
        
        # Should not raise exception
        await orders_cache.save_order_data_legacy("binance", "EX_12345", data)
        
        # Verify the underlying ORM method was called
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compatibility_save_order_data_legacy_error(self, orders_cache, mock_base_cache):
        """Test save_order_data_legacy error handling."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.side_effect = Exception("Redis error")

        # Test
        data = {"symbol": "BTC/USDT", "side": "buy"}
        
        with pytest.raises(Exception, match="Error saving order status to Redis"):
            await orders_cache.save_order_data_legacy("binance", "EX_12345", data)

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
    async def test_redis_key_patterns(self, orders_cache, mock_base_cache, sample_order):
        """Test that Redis key patterns are consistent."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test save_order key pattern
        await orders_cache.save_order("binance", sample_order)
        
        # Verify hset was called with correct key pattern
        hset_call = mock_redis.hset.call_args
        assert hset_call[0][0] == "order_status:binance"
        assert hset_call[0][1] == sample_order.ex_order_id

    @pytest.mark.asyncio
    async def test_order_id_handling(self, orders_cache, mock_base_cache):
        """Test handling of both order_id and ex_order_id."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test with ex_order_id
        order_with_ex_id = Order(ex_order_id="EX_123", symbol="BTC/USDT", side="buy", volume=0.1)
        await orders_cache.save_order("binance", order_with_ex_id)
        
        hset_call = mock_redis.hset.call_args
        assert hset_call[0][1] == "EX_123"

        # Test with order_id when ex_order_id is None
        order_with_id = Order(order_id=456, symbol="ETH/USDT", side="sell", volume=1.0)
        await orders_cache.save_order("binance", order_with_id)
        
        hset_call = mock_redis.hset.call_args
        assert hset_call[0][1] == "456"

    @pytest.mark.asyncio
    async def test_integration_save_and_retrieve(self, orders_cache, mock_base_cache, sample_order):
        """Test integration of save and retrieve operations."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test save operation
        save_result = await orders_cache.save_order("binance", sample_order)
        assert save_result is True

        # Mock the retrieval
        order_dict = sample_order.to_dict()
        mock_redis.hget.return_value = json.dumps(order_dict)

        # Test retrieve operation
        retrieved_order = await orders_cache.get_order("binance", sample_order.ex_order_id)
        assert retrieved_order is not None
        assert retrieved_order.symbol == sample_order.symbol
        assert retrieved_order.side == sample_order.side

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
    async def test_partial_order_updates(self, orders_cache, mock_base_cache):
        """Test updating orders with partial data."""
        # Setup existing order
        existing_data = {
            "order_id": "123",
            "ex_order_id": "EX_123",
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "status": "open"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(existing_data)
        mock_redis.hset.return_value = True

        # Create partial update (only status and final_volume)
        partial_order = Order(
            ex_order_id="EX_123",
            status="filled",
            final_volume=0.098
        )

        # Test update
        result = await orders_cache.update_order("binance", partial_order)
        assert result is True

        # Verify merge
        call_args = mock_redis.hset.call_args
        merged_data = json.loads(call_args[0][2])
        
        assert merged_data["status"] == "filled"  # Updated
        assert merged_data["final_volume"] == 0.098  # New
        assert merged_data["symbol"] == "BTC/USDT"  # Preserved
        assert merged_data["price"] == 50000.0  # Preserved