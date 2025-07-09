"""Tests for TradesCache ORM-based interface refactoring."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Trade

from fullon_cache.base_cache import BaseCache
from fullon_cache.trades_cache import TradesCache


@pytest.fixture
def mock_base_cache():
    """Mock BaseCache for testing."""
    cache = AsyncMock(spec=BaseCache)
    # Mock the _to_redis_timestamp and _from_redis_timestamp methods
    cache._to_redis_timestamp.return_value = "2023-01-01T00:00:00Z"
    cache._from_redis_timestamp.return_value = datetime.now(UTC)
    return cache


@pytest.fixture
def trades_cache(mock_base_cache):
    """Create TradesCache instance with mocked BaseCache."""
    cache = TradesCache()
    cache._cache = mock_base_cache
    return cache


@pytest.fixture
def sample_trade():
    """Sample Trade model for testing."""
    return Trade(
        trade_id=12345,
        ex_trade_id="EX_TRD_001",
        ex_order_id="EX_ORD_001",
        uid=1,
        ex_id=1,
        symbol="BTC/USDT",
        order_type="limit",
        side="buy",
        volume=0.1,
        price=50000.0,
        cost=5000.0,
        fee=5.0,
        cur_volume=0.1,
        cur_avg_price=50000.0,
        cur_avg_cost=5000.0,
        cur_fee=5.0,
        roi=0.0,
        roi_pct=0.0,
        total_fee=5.0,
        leverage=1.0,
        time=datetime.now(UTC)
    )


@pytest.fixture
def sample_trades():
    """Sample Trade models list for testing."""
    return [
        Trade(
            trade_id=1,
            ex_trade_id="EX_TRD_001",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            time=datetime.now(UTC)
        ),
        Trade(
            trade_id=2,
            ex_trade_id="EX_TRD_002",
            symbol="BTC/USDT",
            side="sell",
            volume=0.05,
            price=51000.0,
            cost=2550.0,
            fee=2.5,
            time=datetime.now(UTC)
        )
    ]


class TestTradesCacheORM:
    """Test cases for TradesCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_push_trade_with_trade_model(self, trades_cache, mock_base_cache, sample_trade):
        """Test pushing trade with fullon_orm.Trade model."""
        # Setup mock redis context
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1
        mock_redis.set.return_value = True  # For update_trade_status

        # Test
        result = await trades_cache.push_trade("binance", sample_trade)

        # Assert
        assert result is True
        
        # Verify rpush was called with correct arguments
        mock_redis.rpush.assert_called_once()
        call_args = mock_redis.rpush.call_args
        expected_key = "trades:binance:BTCUSDT"  # Symbol normalized
        assert call_args[0][0] == expected_key
        
        # Verify the data was JSON serialized
        stored_data = json.loads(call_args[0][1])
        assert stored_data["trade_id"] == sample_trade.trade_id
        assert stored_data["symbol"] == sample_trade.symbol
        assert stored_data["side"] == sample_trade.side
        assert stored_data["volume"] == sample_trade.volume

    @pytest.mark.asyncio
    async def test_push_trade_error_handling(self, trades_cache, mock_base_cache, sample_trade):
        """Test push_trade error handling."""
        # Setup mock to raise exception
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.side_effect = Exception("Redis error")

        # Test
        result = await trades_cache.push_trade("binance", sample_trade)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_trades_returns_trade_list(self, trades_cache, mock_base_cache):
        """Test that get_trades returns list of Trade models."""
        # Setup mock data
        trade_data_1 = {
            "trade_id": 1,
            "ex_trade_id": "EX_TRD_001",
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "cost": 5000.0,
            "fee": 5.0,
            "time": "2023-01-01T00:00:00Z"
        }
        trade_data_2 = {
            "trade_id": 2,
            "ex_trade_id": "EX_TRD_002",
            "symbol": "BTC/USDT",
            "side": "sell",
            "volume": 0.05,
            "price": 51000.0,
            "cost": 2550.0,
            "fee": 2.5,
            "time": "2023-01-01T01:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lrange.return_value = [json.dumps(trade_data_1), json.dumps(trade_data_2)]
        mock_redis.delete.return_value = 1

        # Test
        result = await trades_cache.get_trades("BTC/USDT", "binance")

        # Assert
        assert len(result) == 2
        assert all(isinstance(trade, Trade) for trade in result)
        
        # Check specific trade data
        assert result[0].trade_id == 1
        assert result[0].symbol == "BTC/USDT"
        assert result[0].side == "buy"
        assert result[1].trade_id == 2
        assert result[1].side == "sell"

        # Verify correct Redis operations
        mock_redis.lrange.assert_called_once_with("trades:binance:BTCUSDT", 0, -1)
        mock_redis.delete.assert_called_once_with("trades:binance:BTCUSDT")

    @pytest.mark.asyncio
    async def test_get_trades_empty_list(self, trades_cache, mock_base_cache):
        """Test get_trades with empty list."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lrange.return_value = []
        mock_redis.delete.return_value = 0

        # Test
        result = await trades_cache.get_trades("BTC/USDT", "binance")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_trades_json_parse_error(self, trades_cache, mock_base_cache):
        """Test get_trades with JSON parsing errors."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        # Include invalid JSON
        mock_redis.lrange.return_value = ["invalid json", json.dumps({
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        })]
        mock_redis.delete.return_value = 1

        # Test
        result = await trades_cache.get_trades("BTC/USDT", "binance")

        # Assert - Should only get the valid trade
        assert len(result) == 1
        assert result[0].trade_id == 1

    @pytest.mark.asyncio
    async def test_get_trades_error_handling(self, trades_cache, mock_base_cache):
        """Test get_trades error handling."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lrange.side_effect = Exception("Redis error")

        # Test
        result = await trades_cache.get_trades("BTC/USDT", "binance")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_push_user_trade_with_trade_model(self, trades_cache, mock_base_cache, sample_trade):
        """Test pushing user trade with fullon_orm.Trade model."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1

        # Test
        result = await trades_cache.push_user_trade("123", "binance", sample_trade)

        # Assert
        assert result is True
        
        # Verify rpush was called with correct key
        mock_redis.rpush.assert_called_once()
        call_args = mock_redis.rpush.call_args
        assert call_args[0][0] == "user_trades:123:binance"
        
        # Verify trade data was serialized
        stored_data = json.loads(call_args[0][1])
        assert stored_data["trade_id"] == sample_trade.trade_id
        assert stored_data["symbol"] == sample_trade.symbol

    @pytest.mark.asyncio
    async def test_push_user_trade_error_handling(self, trades_cache, mock_base_cache, sample_trade):
        """Test push_user_trade error handling."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.side_effect = Exception("Redis error")

        # Test
        result = await trades_cache.push_user_trade("123", "binance", sample_trade)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_pop_user_trade_returns_trade_model(self, trades_cache, mock_base_cache):
        """Test that pop_user_trade returns fullon_orm.Trade model."""
        # Setup mock data
        trade_data = {
            "trade_id": 1,
            "ex_trade_id": "EX_TRD_001",
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0,
            "cost": 5000.0,
            "fee": 5.0,
            "time": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lpop.return_value = json.dumps(trade_data)

        # Test
        result = await trades_cache.pop_user_trade("123", "binance")

        # Assert
        assert result is not None
        assert isinstance(result, Trade)
        assert result.trade_id == 1
        assert result.symbol == "BTC/USDT"
        assert result.side == "buy"

        # Verify correct Redis operation
        mock_redis.lpop.assert_called_once_with("user_trades:123:binance")

    @pytest.mark.asyncio
    async def test_pop_user_trade_blocking(self, trades_cache, mock_base_cache):
        """Test pop_user_trade with blocking timeout."""
        trade_data = {
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.blpop.return_value = ("user_trades:123:binance", json.dumps(trade_data))

        # Test
        result = await trades_cache.pop_user_trade("123", "binance", timeout=5)

        # Assert
        assert result is not None
        assert isinstance(result, Trade)
        assert result.trade_id == 1

        # Verify blocking pop was used
        mock_redis.blpop.assert_called_once_with("user_trades:123:binance", timeout=5)

    @pytest.mark.asyncio
    async def test_pop_user_trade_not_found(self, trades_cache, mock_base_cache):
        """Test pop_user_trade when no trade available."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lpop.return_value = None

        # Test
        result = await trades_cache.pop_user_trade("123", "binance")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_pop_user_trade_json_error(self, trades_cache, mock_base_cache):
        """Test pop_user_trade with invalid JSON data."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lpop.return_value = "invalid json"

        # Test
        result = await trades_cache.pop_user_trade("123", "binance")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_pop_user_trade_timeout_error(self, trades_cache, mock_base_cache):
        """Test pop_user_trade with timeout."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.blpop.return_value = None  # Timeout

        # Test
        result = await trades_cache.pop_user_trade("123", "binance", timeout=1)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_backward_compatibility_push_trade_list_legacy(self, trades_cache, mock_base_cache):
        """Test backward compatibility with push_trade_list using dict."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1
        mock_redis.set.return_value = True  # For update_trade_status

        # Test legacy method with dict
        trade_dict = {
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        }
        
        result = await trades_cache.push_trade_list_legacy("BTC/USDT", "binance", trade_dict)
        
        # Assert
        assert result > 0
        mock_redis.rpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compatibility_push_my_trades_list_legacy(self, trades_cache, mock_base_cache):
        """Test backward compatibility with push_my_trades_list using dict."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1

        # Test legacy method with dict
        trade_dict = {
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        }
        
        result = await trades_cache.push_my_trades_list_legacy("123", "binance", trade_dict)
        
        # Assert
        assert result > 0
        mock_redis.rpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compatibility_get_trades_list_legacy(self, trades_cache, mock_base_cache):
        """Test backward compatibility with get_trades_list returning dicts."""
        trade_data = {
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lrange.return_value = [json.dumps(trade_data)]
        mock_redis.delete.return_value = 1

        # Test
        result = await trades_cache.get_trades_list_legacy("BTC/USDT", "binance")

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["trade_id"] == 1

    @pytest.mark.asyncio
    async def test_backward_compatibility_pop_my_trade_legacy(self, trades_cache, mock_base_cache):
        """Test backward compatibility with pop_my_trade returning dict."""
        trade_data = {
            "trade_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000.0
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.lpop.return_value = json.dumps(trade_data)

        # Test
        result = await trades_cache.pop_my_trade_legacy("123", "binance")

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result["trade_id"] == 1

    @pytest.mark.asyncio
    async def test_trade_model_properties(self, sample_trade):
        """Test that Trade model has expected properties."""
        # Test basic properties
        assert sample_trade.trade_id == 12345
        assert sample_trade.ex_trade_id == "EX_TRD_001"
        assert sample_trade.symbol == "BTC/USDT"
        assert sample_trade.side == "buy"
        assert sample_trade.volume == 0.1
        assert sample_trade.price == 50000.0

    @pytest.mark.asyncio
    async def test_trade_model_to_dict_from_dict(self, sample_trade):
        """Test Trade model serialization and deserialization."""
        # Test to_dict
        trade_dict = sample_trade.to_dict()
        assert isinstance(trade_dict, dict)
        assert trade_dict["trade_id"] == sample_trade.trade_id
        assert trade_dict["symbol"] == sample_trade.symbol
        assert trade_dict["side"] == sample_trade.side

        # Test from_dict
        reconstructed_trade = Trade.from_dict(trade_dict)
        assert reconstructed_trade.trade_id == sample_trade.trade_id
        assert reconstructed_trade.symbol == sample_trade.symbol
        assert reconstructed_trade.side == sample_trade.side
        assert reconstructed_trade.volume == sample_trade.volume

    @pytest.mark.asyncio
    async def test_integration_push_and_get_trades(self, trades_cache, mock_base_cache, sample_trades):
        """Test integration of push and get operations."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1
        mock_redis.set.return_value = True  # For update_trade_status

        # Test push operations
        for trade in sample_trades:
            result = await trades_cache.push_trade("binance", trade)
            assert result is True

        # Mock the retrieval
        trade_dicts = [trade.to_dict() for trade in sample_trades]
        mock_redis.lrange.return_value = [json.dumps(td) for td in trade_dicts]
        mock_redis.delete.return_value = 1

        # Test retrieve operation
        retrieved_trades = await trades_cache.get_trades("BTC/USDT", "binance")
        assert len(retrieved_trades) == 2
        assert all(isinstance(trade, Trade) for trade in retrieved_trades)

    @pytest.mark.asyncio
    async def test_integration_push_and_pop_user_trades(self, trades_cache, mock_base_cache, sample_trade):
        """Test integration of user trade push and pop operations."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1

        # Test push operation
        push_result = await trades_cache.push_user_trade("123", "binance", sample_trade)
        assert push_result is True

        # Mock the pop
        trade_dict = sample_trade.to_dict()
        mock_redis.lpop.return_value = json.dumps(trade_dict)

        # Test pop operation
        popped_trade = await trades_cache.pop_user_trade("123", "binance")
        assert popped_trade is not None
        assert popped_trade.trade_id == sample_trade.trade_id
        assert popped_trade.symbol == sample_trade.symbol

    @pytest.mark.asyncio
    async def test_symbol_normalization(self, trades_cache, mock_base_cache, sample_trade):
        """Test that symbols are properly normalized (/ removed)."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.return_value = 1
        mock_redis.set.return_value = True

        # Test with symbol containing /
        result = await trades_cache.push_trade("binance", sample_trade)
        assert result is True

        # Verify the key was normalized
        call_args = mock_redis.rpush.call_args
        expected_key = "trades:binance:BTCUSDT"  # / removed
        assert call_args[0][0] == expected_key

    @pytest.mark.asyncio
    async def test_error_logging(self, trades_cache, mock_base_cache, sample_trade):
        """Test that errors are properly logged."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.rpush.side_effect = Exception("Redis connection failed")

        # Test with logging
        with patch('fullon_cache.trades_cache.logger') as mock_logger:
            result = await trades_cache.push_trade("binance", sample_trade)

        # Assert
        assert result is False
        mock_logger.error.assert_called_once()