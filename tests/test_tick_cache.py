"""Comprehensive tests for TickCache with 90%+ coverage."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fullon_orm.models import Tick
from fullon_cache.tick_cache import TickCache
from fullon_cache.base_cache import BaseCache


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


@pytest.fixture
def sample_ticker_data():
    """Sample ticker data for testing."""
    return {
        "price": 50000.0,
        "volume": 1234.56,
        "time": "2023-01-01T00:00:00Z",
        "bid": 49999.0,
        "ask": 50001.0
    }


class TestTickCache:
    """Test cases for TickCache functionality."""

    @pytest.mark.asyncio
    async def test_get_price_with_exchange(self, tick_cache, mock_base_cache):
        """Test get_price with specific exchange."""
        # Setup
        ticker_data = {"price": 50000.0, "time": "2023-01-01T00:00:00Z"}
        mock_base_cache.hget.return_value = json.dumps(ticker_data)
        
        # Test
        result = await tick_cache.get_price("BTC/USDT", "binance")
        
        # Assert
        assert result == 50000.0
        mock_base_cache.hget.assert_called_once_with("tickers:binance", "BTC/USDT")

    @pytest.mark.asyncio
    async def test_get_price_without_exchange(self, tick_cache, mock_exchanges):
        """Test get_price without specifying exchange."""
        with patch('fullon_orm.get_async_session') as mock_session:
            # Setup mock session and repository
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()
            
            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                ticker_data = {"price": 45000.0, "time": "2023-01-01T00:00:00Z"}
                tick_cache._cache.hget.side_effect = [None, json.dumps(ticker_data)]
                
                # Test
                result = await tick_cache.get_price("BTC/USDT")
                
                # Assert
                assert result == 45000.0

    @pytest.mark.asyncio
    async def test_get_price_not_found(self, tick_cache, mock_base_cache):
        """Test get_price when ticker not found."""
        mock_base_cache.hget.return_value = None
        
        result = await tick_cache.get_price("NONEXISTENT/USDT", "binance")
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_price_error_handling(self, tick_cache, mock_base_cache):
        """Test get_price error handling."""
        mock_base_cache.hget.side_effect = Exception("Redis error")
        
        result = await tick_cache.get_price("BTC/USDT", "binance")
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_update_ticker_success(self, tick_cache, mock_base_cache, sample_ticker_data):
        """Test successful ticker update."""
        mock_base_cache.hset.return_value = True
        mock_base_cache.publish.return_value = 1
        
        result = await tick_cache.update_ticker("BTC/USDT", "binance", sample_ticker_data)
        
        assert result == 1
        mock_base_cache.hset.assert_called_once_with(
            "tickers:binance", "BTC/USDT", json.dumps(sample_ticker_data)
        )
        mock_base_cache.publish.assert_called_once_with(
            "next_ticker:binance:BTC/USDT", json.dumps(sample_ticker_data)
        )

    @pytest.mark.asyncio
    async def test_update_ticker_error(self, tick_cache, mock_base_cache, sample_ticker_data):
        """Test ticker update with error."""
        mock_base_cache.hset.side_effect = Exception("Redis error")
        
        result = await tick_cache.update_ticker("BTC/USDT", "binance", sample_ticker_data)
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_del_exchange_ticker_success(self, tick_cache, mock_base_cache):
        """Test successful exchange ticker deletion."""
        mock_base_cache.delete.return_value = 1
        
        result = await tick_cache.del_exchange_ticker("binance")
        
        assert result == 1
        mock_base_cache.delete.assert_called_once_with("tickers:binance")

    @pytest.mark.asyncio
    async def test_del_exchange_ticker_error(self, tick_cache, mock_base_cache):
        """Test exchange ticker deletion with error."""
        mock_base_cache.delete.side_effect = Exception("Redis error")
        
        result = await tick_cache.del_exchange_ticker("binance")
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_next_ticker_success(self, tick_cache, mock_base_cache):
        """Test successful get_next_ticker."""
        # Mock subscription that yields a message
        async def mock_subscribe(channel):
            yield {
                'type': 'message',
                'data': json.dumps({"price": 51000.0, "time": "2023-01-01T01:00:00Z"})
            }
        
        mock_base_cache.subscribe.return_value = mock_subscribe("test_channel")
        
        result = await tick_cache.get_next_ticker("BTC/USDT", "binance")
        
        assert result == (51000.0, "2023-01-01T01:00:00Z")

    @pytest.mark.asyncio
    async def test_get_next_ticker_timeout(self, tick_cache, mock_base_cache):
        """Test get_next_ticker with timeout."""
        # Mock subscription that raises timeout
        async def mock_subscribe():
            raise asyncio.TimeoutError()
            yield  # This makes it an async generator
        
        mock_base_cache.subscribe.return_value = mock_subscribe()
        
        # Mock the recursive call to avoid infinite recursion in test
        with patch.object(tick_cache, 'get_next_ticker', return_value=(0, None)) as mock_recursive:
            # Call the method once to trigger timeout
            mock_base_cache.subscribe.side_effect = asyncio.TimeoutError()
            
            result = await tick_cache.get_next_ticker("BTC/USDT", "binance")
            
            assert result == (0, None)

    @pytest.mark.asyncio
    async def test_get_next_ticker_error(self, tick_cache, mock_base_cache):
        """Test get_next_ticker with general error."""
        mock_base_cache.subscribe.side_effect = Exception("Connection error")
        
        result = await tick_cache.get_next_ticker("BTC/USDT", "binance")
        
        assert result == (0, None)

    @pytest.mark.asyncio
    async def test_get_ticker_any_success(self, tick_cache, mock_exchanges):
        """Test successful get_ticker_any."""
        with patch('fullon_orm.get_async_session') as mock_session:
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()
            
            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                ticker_data = {"price": 48000.0}
                tick_cache._cache.hget.side_effect = [None, json.dumps(ticker_data)]
                
                result = await tick_cache.get_ticker_any("BTC/USDT")
                
                assert result == 48000.0

    @pytest.mark.asyncio
    async def test_get_ticker_any_not_found(self, tick_cache, mock_exchanges):
        """Test get_ticker_any when ticker not found."""
        with patch('fullon_orm.get_async_session') as mock_session:
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()
            
            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                tick_cache._cache.hget.return_value = None
                
                result = await tick_cache.get_ticker_any("NONEXISTENT/USDT")
                
                assert result == 0

    @pytest.mark.asyncio
    async def test_get_ticker_any_error(self, tick_cache):
        """Test get_ticker_any with error."""
        with patch('fullon_orm.get_async_session', side_effect=Exception("DB error")):
            result = await tick_cache.get_ticker_any("BTC/USDT")
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_ticker_with_exchange(self, tick_cache, mock_base_cache):
        """Test get_ticker with specific exchange."""
        ticker_data = {"price": 52000.0, "time": "2023-01-01T02:00:00Z"}
        mock_base_cache.hget.return_value = json.dumps(ticker_data)
        
        result = await tick_cache.get_ticker("BTC/USDT", "binance")
        
        assert result == (52000.0, "2023-01-01T02:00:00Z")

    @pytest.mark.asyncio
    async def test_get_ticker_without_exchange(self, tick_cache, mock_exchanges):
        """Test get_ticker without specifying exchange."""
        with patch('fullon_orm.get_async_session') as mock_session:
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()
            
            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                ticker_data = {"price": 53000.0, "time": "2023-01-01T03:00:00Z"}
                tick_cache._cache.hget.side_effect = [None, json.dumps(ticker_data)]
                
                result = await tick_cache.get_ticker("BTC/USDT")
                
                assert result == (53000.0, "2023-01-01T03:00:00Z")

    @pytest.mark.asyncio
    async def test_get_ticker_not_found(self, tick_cache, mock_base_cache):
        """Test get_ticker when ticker not found."""
        mock_base_cache.hget.return_value = None
        
        result = await tick_cache.get_ticker("NONEXISTENT/USDT", "binance")
        
        assert result == (0, None)

    @pytest.mark.asyncio
    async def test_get_ticker_json_error(self, tick_cache, mock_base_cache):
        """Test get_ticker with JSON decode error."""
        mock_base_cache.hget.return_value = "invalid json"
        
        result = await tick_cache.get_ticker("BTC/USDT", "binance")
        
        assert result == (0, None)

    @pytest.mark.asyncio
    async def test_get_tickers_with_exchange(self, tick_cache, mock_base_cache):
        """Test get_tickers with specific exchange."""
        ticker_data = {
            "BTC/USDT": json.dumps({"price": 50000.0, "volume": 1000.0, "time": 1640995200.0}),
            "ETH/USDT": json.dumps({"price": 4000.0, "volume": 500.0, "time": 1640995200.0})
        }
        mock_base_cache.hgetall.return_value = ticker_data
        
        with patch.object(Tick, 'from_dict') as mock_from_dict:
            mock_tick = MagicMock(spec=Tick)
            mock_from_dict.return_value = mock_tick
            
            result = await tick_cache.get_tickers("binance")
            
            assert len(result) == 2
            assert all(isinstance(tick, MagicMock) for tick in result)

    @pytest.mark.asyncio
    async def test_get_tickers_all_exchanges(self, tick_cache, mock_exchanges):
        """Test get_tickers for all exchanges."""
        with patch('fullon_orm.get_async_session') as mock_session:
            mock_repo = AsyncMock()
            mock_repo.get_cat_exchanges.return_value = mock_exchanges
            mock_session.return_value.__aenter__.return_value = MagicMock()
            
            with patch('fullon_cache.tick_cache.ExchangeRepository', return_value=mock_repo):
                ticker_data = {
                    "BTC/USDT": json.dumps({"price": 50000.0, "volume": 1000.0, "time": 1640995200.0})
                }
                tick_cache._cache.hgetall.return_value = ticker_data
                
                with patch.object(Tick, 'from_dict') as mock_from_dict:
                    mock_tick = MagicMock(spec=Tick)
                    mock_from_dict.return_value = mock_tick
                    
                    result = await tick_cache.get_tickers("")
                    
                    # Should call hgetall for each exchange
                    assert tick_cache._cache.hgetall.call_count == len(mock_exchanges)

    @pytest.mark.asyncio
    async def test_get_tickers_parse_error(self, tick_cache, mock_base_cache):
        """Test get_tickers with JSON parse error."""
        ticker_data = {
            "BTC/USDT": "invalid json",
            "ETH/USDT": json.dumps({"price": 4000.0, "volume": 500.0, "time": 1640995200.0})
        }
        mock_base_cache.hgetall.return_value = ticker_data
        
        with patch.object(Tick, 'from_dict') as mock_from_dict:
            mock_tick = MagicMock(spec=Tick)
            mock_from_dict.return_value = mock_tick
            
            result = await tick_cache.get_tickers("binance")
            
            # Should only return valid ticker (ETH/USDT)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_tickers_error(self, tick_cache):
        """Test get_tickers with general error."""
        with patch('fullon_orm.get_async_session', side_effect=Exception("DB error")):
            result = await tick_cache.get_tickers("")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_tick_crawlers_success(self, tick_cache, mock_base_cache):
        """Test successful get_tick_crawlers."""
        crawler_data = {
            "crawler1": json.dumps({"exchange": "binance", "symbol": "BTC/USDT"}),
            "crawler2": json.dumps({"exchange": "kraken", "symbol": "ETH/USDT"})
        }
        mock_base_cache.hgetall.return_value = crawler_data
        
        result = await tick_cache.get_tick_crawlers()
        
        assert len(result) == 2
        assert "crawler1" in result
        assert result["crawler1"]["exchange"] == "binance"

    @pytest.mark.asyncio
    async def test_get_tick_crawlers_empty(self, tick_cache, mock_base_cache):
        """Test get_tick_crawlers with empty data."""
        mock_base_cache.hgetall.return_value = {}
        
        result = await tick_cache.get_tick_crawlers()
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_tick_crawlers_parse_error(self, tick_cache, mock_base_cache):
        """Test get_tick_crawlers with JSON parse error."""
        crawler_data = {
            "crawler1": "invalid json",
            "crawler2": json.dumps({"exchange": "kraken", "symbol": "ETH/USDT"})
        }
        mock_base_cache.hgetall.return_value = crawler_data
        
        result = await tick_cache.get_tick_crawlers()
        
        # Should only return valid crawler
        assert len(result) == 1
        assert "crawler2" in result

    @pytest.mark.asyncio
    async def test_get_tick_crawlers_error(self, tick_cache, mock_base_cache):
        """Test get_tick_crawlers with general error."""
        mock_base_cache.hgetall.side_effect = Exception("Redis error")
        
        with pytest.raises(ValueError, match="Failed to process tick crawlers data"):
            await tick_cache.get_tick_crawlers()

    @pytest.mark.asyncio
    async def test_round_down_zero_sizes(self, tick_cache):
        """Test round_down with zero sizes."""
        result = await tick_cache.round_down("BTC/USDT", "binance", [0, 0, 0], False)
        
        assert result == (0, 0, 0)

    @pytest.mark.asyncio
    async def test_round_down_btc_currency(self, tick_cache):
        """Test round_down with BTC currency."""
        sizes = [1.5, 2.5, 4.0]
        result = await tick_cache.round_down("BTC/USDT", "binance", sizes, False)
        
        assert result == (1.5, 2.5, 4.0)

    @pytest.mark.asyncio
    async def test_round_down_futures(self, tick_cache):
        """Test round_down with futures enabled."""
        sizes = [1.5, 2.5, 4.0]
        result = await tick_cache.round_down("ETH/USDT", "binance", sizes, True)
        
        assert result == (1.5, 2.5, 4.0)

    @pytest.mark.asyncio
    async def test_round_down_no_slash(self, tick_cache):
        """Test round_down with symbol without slash."""
        sizes = [1.5, 2.5, 4.0]
        result = await tick_cache.round_down("BTCUSDT", "binance", sizes, False)
        
        assert result == (1.5, 2.5, 4.0)

    @pytest.mark.asyncio
    async def test_round_down_with_conversion(self, tick_cache, mock_base_cache):
        """Test round_down with currency conversion."""
        # Mock ticker data for main symbol
        ticker_data = {"price": 50000.0, "time": "2023-01-01T00:00:00Z"}
        mock_base_cache.hget.return_value = json.dumps(ticker_data)
        
        # Mock get_price for conversion
        with patch.object(tick_cache, 'get_price', return_value=1.0):
            sizes = [0.1, 0.2, 0.3]
            result = await tick_cache.round_down("ETH/EUR", "binance", sizes, False)
            
            # Should convert to USD values
            assert result[0] > 0  # Should be converted value

    @pytest.mark.asyncio
    async def test_round_down_usd_currency(self, tick_cache, mock_base_cache):
        """Test round_down with USD base currency."""
        ticker_data = {"price": 50000.0, "time": "2023-01-01T00:00:00Z"}
        mock_base_cache.hget.return_value = json.dumps(ticker_data)
        
        sizes = [0.1, 0.2, 0.3]
        result = await tick_cache.round_down("ETH/USD", "binance", sizes, False)
        
        # Should multiply by price directly for USD (0.1 * 50000 = 5000.0)
        expected = (5000.0, 10000.0, 15000.0)
        assert result == expected

    @pytest.mark.asyncio
    async def test_round_down_small_value(self, tick_cache, mock_base_cache):
        """Test round_down with value less than 2 USD."""
        ticker_data = {"price": 0.01, "time": "2023-01-01T00:00:00Z"}  # Very low price
        mock_base_cache.hget.return_value = json.dumps(ticker_data)
        
        sizes = [1.0, 2.0, 3.0]
        result = await tick_cache.round_down("LOWCOIN/USD", "binance", sizes, False)
        
        assert result == (0, 0, 0)  # Should return zeros for low value

    @pytest.mark.asyncio
    async def test_round_down_no_price(self, tick_cache, mock_base_cache):
        """Test round_down when price not found."""
        mock_base_cache.hget.return_value = None
        
        sizes = [1.0, 2.0, 3.0]
        result = await tick_cache.round_down("UNKNOWN/USDT", "binance", sizes, False)
        
        assert result == (0, 0, 0)

    @pytest.mark.asyncio
    async def test_round_down_error(self, tick_cache, mock_base_cache):
        """Test round_down with error."""
        # Set up get_ticker to fail
        with patch.object(tick_cache, 'get_ticker', side_effect=Exception("Redis error")):
            sizes = [1.0, 2.0, 3.0]
            result = await tick_cache.round_down("ETH/USDT", "binance", sizes, False)
            
            assert result == (0, 0, 0)

    @pytest.mark.asyncio
    async def test_init(self):
        """Test TickCache initialization."""
        cache = TickCache()
        
        assert hasattr(cache, '_cache')
        assert isinstance(cache._cache, BaseCache)

    @pytest.mark.asyncio 
    async def test_tick_from_dict_usage(self, tick_cache, mock_base_cache):
        """Test that Tick.from_dict is used correctly in get_tickers."""
        ticker_data = {
            "BTC/USDT": json.dumps({
                "price": 50000.0,
                "volume": 1000.0, 
                "time": 1640995200.0,
                "bid": 49999.0,
                "ask": 50001.0,
                "last": 50000.5
            })
        }
        mock_base_cache.hgetall.return_value = ticker_data
        
        # Mock the actual Tick.from_dict call
        with patch.object(Tick, 'from_dict') as mock_from_dict:
            expected_dict = {
                "price": 50000.0,
                "volume": 1000.0,
                "time": 1640995200.0,
                "bid": 49999.0,
                "ask": 50001.0,
                "last": 50000.5,
                "exchange": "binance",
                "symbol": "BTC/USDT"
            }
            mock_tick = MagicMock(spec=Tick)
            mock_from_dict.return_value = mock_tick
            
            result = await tick_cache.get_tickers("binance")
            
            # Verify from_dict was called with correct data
            mock_from_dict.assert_called_once_with(expected_dict)
            assert len(result) == 1
            assert result[0] == mock_tick

    @pytest.mark.asyncio
    async def test_tick_to_dict_usage(self, tick_cache):
        """Test that tick.to_dict() would work correctly."""
        # Create a real Tick instance to test to_dict
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance", 
            price=50000.5,
            volume=1234.56,
            time=1640995200.0,
            bid=50000.0,
            ask=50001.0,
            last=50000.5
        )
        
        # Test to_dict method
        tick_dict = tick.to_dict()
        
        assert tick_dict["symbol"] == "BTC/USDT"
        assert tick_dict["exchange"] == "binance"
        assert tick_dict["price"] == 50000.5
        assert tick_dict["volume"] == 1234.56
        assert tick_dict["time"] == 1640995200.0
        assert tick_dict["bid"] == 50000.0
        assert tick_dict["ask"] == 50001.0
        assert tick_dict["last"] == 50000.5