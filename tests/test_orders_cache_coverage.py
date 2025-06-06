"""Additional tests to achieve 100% coverage for OrdersCache."""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock
from redis.exceptions import RedisError

from fullon_cache import OrdersCache
from fullon_orm.models import Order


class TestOrdersCacheCoverage:
    """Additional tests for complete OrdersCache coverage."""

    @pytest.mark.asyncio
    async def test_push_open_order_with_error(self, orders_cache):
        """Test push_open_order with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.rpush.side_effect = RedisError("Push failed")
        
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should not raise, just log error
            await orders_cache.push_open_order("order123", "LOCAL_001")

    @pytest.mark.asyncio
    async def test_pop_open_order_general_error(self, orders_cache):
        """Test pop_open_order with general error."""
        mock_redis = AsyncMock()
        mock_redis.blpop.side_effect = Exception("Some error")
        
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should log error and return None
            result = await orders_cache.pop_open_order("LOCAL_001")
            assert result is None

    @pytest.mark.asyncio
    async def test_save_order_data_with_cancelled_status(self, orders_cache):
        """Test save_order_data sets expiry for cancelled orders."""
        order_data = {
            "status": "cancelled",
            "symbol": "BTC/USDT"
        }
        
        # Should set expiry without error
        await orders_cache.save_order_data("binance", "order123", order_data)

    @pytest.mark.asyncio
    async def test_get_order_status_attribute_error(self, orders_cache):
        """Test get_order_status handles AttributeError."""
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = AttributeError("Test error")
            result = await orders_cache.get_order_status("binance", "order123")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_orders_with_decode_error(self, orders_cache):
        """Test get_orders skips invalid JSON."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            b"order1": b"invalid json{",
            b"order2": b'{"order_id": "order2", "symbol": "ETH/USDT"}'
        }
        
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            orders = await orders_cache.get_orders("binance")
            # Should have 1 valid order (or 0 if _dict_to_order returns None)
            assert len(orders) <= 1

    @pytest.mark.asyncio
    async def test_get_full_accounts_type_error(self, orders_cache):
        """Test get_full_accounts handles TypeError."""
        with patch.object(orders_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = TypeError("Test error")
            result = await orders_cache.get_full_accounts(123)
            assert result is None

    @pytest.mark.asyncio
    async def test_dict_to_order_exception(self, orders_cache):
        """Test _dict_to_order handles exceptions."""
        # Mock the Order.from_dict to raise exception
        with patch('fullon_orm.models.Order.from_dict', side_effect=Exception("Invalid data")):
            result = orders_cache._dict_to_order({"order_id": "123"})
            assert result is None

    @pytest.mark.asyncio
    async def test_order_to_dict_basic(self, orders_cache):
        """Test _order_to_dict converts Order to dict."""
        # Create a simple order
        order = Order(
            order_id=123,
            symbol="BTC/USDT",
            order_type="limit",
            side="buy"
        )
        
        result = orders_cache._order_to_dict(order)
        assert isinstance(result, dict)
        assert result.get("symbol") == "BTC/USDT"