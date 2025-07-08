"""Tests for TickCache ORM-based interface refactoring."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fullon_orm.models import Tick

from fullon_cache.base_cache import BaseCache
from fullon_cache.tick_cache import TickCache


@pytest.fixture
def mock_base_cache():
    """Mock BaseCache for testing."""
    cache = AsyncMock(spec=BaseCache)
    return cache


@pytest.fixture
def tick_cache(mock_base_cache):
    """Create TickCache instance with mocked BaseCache."""
    cache = TickCache()
    cache._cache = mock_base_cache
    return cache


@pytest.fixture
def sample_tick():
    """Sample Tick model for testing."""
    return Tick(
        symbol="BTC/USDT",
        exchange="binance",
        price=50000.0,
        volume=1234.56,
        time=time.time(),
        bid=49999.0,
        ask=50001.0,
        last=50000.5
    )


@pytest.fixture
def mock_exchanges():
    """Mock exchange objects for testing."""
    class MockExchange:
        def __init__(self, name):
            self.name = name

    return [
        MockExchange("binance"),
        MockExchange("kraken"),
        MockExchange("coinbase")
    ]


class TestTickCacheORM:
    """Test cases for TickCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_update_ticker_with_tick_model(self, tick_cache, mock_base_cache, sample_tick):
        """Test updating ticker with fullon_orm.Tick model."""
        # Setup mocks
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1

        # Test
        result = await tick_cache.update_ticker_orm("binance", sample_tick)

        # Assert
        assert result is True
        
        # Verify hset was called with correct parameters
        mock_base_cache.hset.assert_called_once()
        call_args = mock_base_cache.hset.call_args
        assert call_args[0][0] == "tickers:binance"
        assert call_args[0][1] == sample_tick.symbol
        
        # Verify the data was JSON serialized
        stored_data = json.loads(call_args[0][2])
        assert stored_data["symbol"] == sample_tick.symbol
        assert stored_data["price"] == sample_tick.price
        assert stored_data["volume"] == sample_tick.volume

        # Verify publish was called
        mock_base_cache.publish.assert_called_once()
        pub_args = mock_base_cache.publish.call_args
        assert pub_args[0][0] == f"next_ticker:binance:{sample_tick.symbol}"

    @pytest.mark.asyncio
    async def test_update_ticker_error_handling(self, tick_cache, mock_base_cache, sample_tick):
        """Test update_ticker error handling."""
        # Setup mock to raise exception
        mock_base_cache.hset.side_effect = Exception("Redis error")

        # Test
        result = await tick_cache.update_ticker_orm("binance", sample_tick)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_ticker_returns_tick_model(self, tick_cache, mock_base_cache, sample_tick):
        """Test that get_ticker returns fullon_orm.Tick model."""
        # Setup mock data
        tick_dict = sample_tick.to_dict()
        mock_base_cache.hget.return_value = json.dumps(tick_dict)

        # Test
        result = await tick_cache.get_ticker_orm("BTC/USDT", "binance")

        # Assert
        assert result is not None
        assert isinstance(result, Tick)
        assert result.symbol == sample_tick.symbol
        assert result.exchange == sample_tick.exchange
        assert result.price == sample_tick.price
        assert result.volume == sample_tick.volume
        assert result.bid == sample_tick.bid
        assert result.ask == sample_tick.ask
        assert result.last == sample_tick.last

        # Verify correct Redis key was used
        mock_base_cache.hget.assert_called_once_with("tickers:binance", "BTC/USDT")

    @pytest.mark.asyncio
    async def test_get_ticker_not_found(self, tick_cache, mock_base_cache):
        """Test get_ticker when ticker not found."""
        # Setup mock to return None
        mock_base_cache.hget.return_value = None

        # Test
        result = await tick_cache.get_ticker_orm("NONEXISTENT/USDT", "binance")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_ticker_json_error(self, tick_cache, mock_base_cache):
        """Test get_ticker with invalid JSON data."""
        # Setup mock to return invalid JSON
        mock_base_cache.hget.return_value = "invalid json"

        # Test
        result = await tick_cache.get_ticker_orm("BTC/USDT", "binance")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_ticker_general_error(self, tick_cache, mock_base_cache):
        """Test get_ticker with general error."""
        # Setup mock to raise exception
        mock_base_cache.hget.side_effect = Exception("Redis error")

        # Test
        result = await tick_cache.get_ticker_orm("BTC/USDT", "binance")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_price_tick_with_exchange(self, tick_cache, mock_base_cache, sample_tick):
        """Test get_price_tick with specific exchange."""
        # Setup mock data
        tick_dict = sample_tick.to_dict()
        mock_base_cache.hget.return_value = json.dumps(tick_dict)

        # Test
        result = await tick_cache.get_price_tick_orm("BTC/USDT", "binance")

        # Assert
        assert result is not None
        assert isinstance(result, Tick)
        assert result.price == sample_tick.price
        assert result.volume == sample_tick.volume
        assert result.symbol == sample_tick.symbol
        assert result.exchange == sample_tick.exchange

    @pytest.mark.asyncio
    async def test_get_price_tick_without_exchange(self, tick_cache, mock_exchanges, sample_tick):
        """Test get_price_tick without specifying exchange."""
        with patch('fullon_orm.get_async_session') as mock_session:
            # Setup mock session and repository
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()

            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                tick_dict = sample_tick.to_dict()
                # First exchange returns None, second returns data
                tick_cache._cache.hget.side_effect = [None, json.dumps(tick_dict)]

                # Test
                result = await tick_cache.get_price_tick_orm("BTC/USDT")

                # Assert
                assert result is not None
                assert isinstance(result, Tick)
                assert result.price == sample_tick.price

    @pytest.mark.asyncio
    async def test_get_price_tick_not_found(self, tick_cache, mock_base_cache):
        """Test get_price_tick when ticker not found."""
        mock_base_cache.hget.return_value = None

        result = await tick_cache.get_price_tick_orm("NONEXISTENT/USDT", "binance")

        assert result is None

    @pytest.mark.asyncio
    async def test_backward_compatibility_update_ticker_legacy(self, tick_cache, mock_base_cache):
        """Test backward compatibility with update_ticker_legacy."""
        # Setup mocks
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1

        # Test legacy method
        data = {
            "price": 50000.0,
            "volume": 1234.56,
            "time": time.time(),
            "bid": 49999.0,
            "ask": 50001.0,
            "last": 50000.5
        }
        
        result = await tick_cache.update_ticker_legacy("BTC/USDT", "binance", data)

        # Assert
        assert result == 1
        
        # Verify the underlying ORM method was called
        mock_base_cache.hset.assert_called_once()
        mock_base_cache.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compatibility_update_ticker_legacy_error(self, tick_cache, mock_base_cache):
        """Test update_ticker_legacy error handling."""
        # Setup mock to raise exception
        mock_base_cache.hset.side_effect = Exception("Redis error")

        # Test
        data = {"price": 50000.0, "volume": 1234.56, "time": time.time()}
        result = await tick_cache.update_ticker_legacy("BTC/USDT", "binance", data)

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_backward_compatibility_get_price_legacy(self, tick_cache, mock_base_cache, sample_tick):
        """Test backward compatibility with get_price_legacy."""
        # Setup mock data
        tick_dict = sample_tick.to_dict()
        mock_base_cache.hget.return_value = json.dumps(tick_dict)

        # Test legacy method
        result = await tick_cache.get_price_legacy("BTC/USDT", "binance")

        # Assert
        assert result == sample_tick.price

    @pytest.mark.asyncio
    async def test_backward_compatibility_get_price_legacy_not_found(self, tick_cache, mock_base_cache):
        """Test get_price_legacy when ticker not found."""
        mock_base_cache.hget.return_value = None

        result = await tick_cache.get_price_legacy("NONEXISTENT/USDT", "binance")

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_backward_compatibility_get_price_legacy_without_exchange(self, tick_cache, mock_exchanges, sample_tick):
        """Test get_price_legacy without specifying exchange."""
        with patch('fullon_orm.get_async_session') as mock_session:
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()

            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                tick_dict = sample_tick.to_dict()
                tick_cache._cache.hget.side_effect = [None, json.dumps(tick_dict)]

                result = await tick_cache.get_price_legacy("BTC/USDT")

                assert result == sample_tick.price

    @pytest.mark.asyncio
    async def test_tick_model_properties(self, sample_tick):
        """Test that Tick model has expected properties."""
        # Test basic properties
        assert sample_tick.symbol == "BTC/USDT"
        assert sample_tick.exchange == "binance"
        assert sample_tick.price == 50000.0
        assert sample_tick.volume == 1234.56
        assert sample_tick.bid == 49999.0
        assert sample_tick.ask == 50001.0
        assert sample_tick.last == 50000.5

        # Test spread calculation
        assert sample_tick.spread == 2.0  # ask - bid
        assert sample_tick.spread_percentage == 0.004  # spread / mid_price * 100

    @pytest.mark.asyncio
    async def test_tick_model_to_dict_from_dict(self, sample_tick):
        """Test Tick model serialization and deserialization."""
        # Test to_dict
        tick_dict = sample_tick.to_dict()
        assert isinstance(tick_dict, dict)
        assert tick_dict["symbol"] == sample_tick.symbol
        assert tick_dict["exchange"] == sample_tick.exchange
        assert tick_dict["price"] == sample_tick.price

        # Test from_dict
        reconstructed_tick = Tick.from_dict(tick_dict)
        assert reconstructed_tick.symbol == sample_tick.symbol
        assert reconstructed_tick.exchange == sample_tick.exchange
        assert reconstructed_tick.price == sample_tick.price
        assert reconstructed_tick.volume == sample_tick.volume
        assert reconstructed_tick.bid == sample_tick.bid
        assert reconstructed_tick.ask == sample_tick.ask
        assert reconstructed_tick.last == sample_tick.last

    @pytest.mark.asyncio
    async def test_new_methods_integration(self, tick_cache, mock_base_cache, sample_tick):
        """Test integration of new ORM methods."""
        # Setup mocks
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1

        # Test full workflow: update -> get
        # 1. Update ticker
        update_result = await tick_cache.update_ticker_orm("binance", sample_tick)
        assert update_result is True

        # 2. Mock get_ticker to return the same data
        tick_dict = sample_tick.to_dict()
        mock_base_cache.hget.return_value = json.dumps(tick_dict)

        # 3. Get ticker back
        retrieved_tick = await tick_cache.get_ticker_orm("BTC/USDT", "binance")
        assert retrieved_tick is not None
        assert retrieved_tick.symbol == sample_tick.symbol
        assert retrieved_tick.price == sample_tick.price

        # 4. Get price tick
        price_tick = await tick_cache.get_price_tick_orm("BTC/USDT", "binance")
        assert price_tick is not None
        assert price_tick.price == sample_tick.price

    @pytest.mark.asyncio
    async def test_method_signatures(self, tick_cache):
        """Test that new methods have correct signatures."""
        import inspect
        
        # Test update_ticker signature
        sig = inspect.signature(tick_cache.update_ticker_orm)
        params = list(sig.parameters.keys())
        assert params == ["exchange", "ticker"]
        assert sig.return_annotation == bool

        # Test get_ticker signature  
        sig = inspect.signature(tick_cache.get_ticker_orm)
        params = list(sig.parameters.keys())
        assert params == ["symbol", "exchange"]
        # Note: return annotation should be Tick | None but may show as string

        # Test get_price_tick signature
        sig = inspect.signature(tick_cache.get_price_tick_orm)
        params = list(sig.parameters.keys())
        assert params == ["symbol", "exchange"]

    @pytest.mark.asyncio
    async def test_redis_key_patterns(self, tick_cache, mock_base_cache, sample_tick):
        """Test that Redis key patterns are consistent."""
        # Setup mocks
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1

        # Test update_ticker key pattern
        await tick_cache.update_ticker_orm("binance", sample_tick)
        
        # Verify hset was called with correct key pattern
        hset_call = mock_base_cache.hset.call_args
        assert hset_call[0][0] == "tickers:binance"
        assert hset_call[0][1] == sample_tick.symbol

        # Verify publish was called with correct channel pattern
        publish_call = mock_base_cache.publish.call_args
        assert publish_call[0][0] == f"next_ticker:binance:{sample_tick.symbol}"

    @pytest.mark.asyncio
    async def test_pub_sub_integration(self, tick_cache, mock_base_cache, sample_tick):
        """Test pub/sub integration with ORM methods."""
        # Setup mocks
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1

        # Test that update_ticker publishes to correct channel
        await tick_cache.update_ticker_orm("binance", sample_tick)

        # Verify publish was called with serialized Tick data
        publish_call = mock_base_cache.publish.call_args
        channel = publish_call[0][0]
        message = publish_call[0][1]
        
        assert channel == f"next_ticker:binance:{sample_tick.symbol}"
        
        # Message should be JSON-serialized Tick data
        message_data = json.loads(message)
        assert message_data["symbol"] == sample_tick.symbol
        assert message_data["price"] == sample_tick.price
        assert message_data["exchange"] == sample_tick.exchange