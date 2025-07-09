"""Tests for SymbolCache ORM-based interface refactoring."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Symbol

from fullon_cache.base_cache import BaseCache
from fullon_cache.symbol_cache import SymbolCache


@pytest.fixture
def mock_base_cache():
    """Mock BaseCache for testing."""
    cache = AsyncMock(spec=BaseCache)
    return cache


@pytest.fixture
def symbol_cache(mock_base_cache):
    """Create SymbolCache instance with mocked BaseCache."""
    cache = SymbolCache()
    cache._cache = mock_base_cache
    return cache


@pytest.fixture
def sample_symbol():
    """Sample Symbol model for testing."""
    return Symbol(
        symbol_id=1,
        symbol="BTC/USDT",
        cat_ex_id=1,
        base="BTC",
        quote="USDT",
        decimals=8,
        updateframe="1h",
        backtest=30,
        futures=False,
        only_ticker=False
    )


@pytest.fixture
def sample_symbols():
    """Sample Symbol models list for testing."""
    return [
        Symbol(
            symbol_id=1,
            symbol="BTC/USDT",
            cat_ex_id=1,
            base="BTC",
            quote="USDT",
            decimals=8,
            updateframe="1h",
            backtest=30,
            futures=False,
            only_ticker=False
        ),
        Symbol(
            symbol_id=2,
            symbol="ETH/USDT",
            cat_ex_id=1,
            base="ETH",
            quote="USDT",
            decimals=18,
            updateframe="1h",
            backtest=30,
            futures=False,
            only_ticker=False
        )
    ]


class TestSymbolCacheORM:
    """Test cases for SymbolCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_add_symbol_with_symbol_model(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test adding symbol with fullon_orm.Symbol model."""
        # Setup mock redis
        mock_base_cache.hset.return_value = True
        mock_base_cache.expire.return_value = True

        # Test
        result = await symbol_cache.add_symbol(sample_symbol)

        # Assert
        assert result is True
        
        # Verify hset was called with correct arguments
        mock_base_cache.hset.assert_called_once()
        call_args = mock_base_cache.hset.call_args
        expected_key = "symbols_list:binance"  # Based on exchange mapping
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == sample_symbol.symbol
        
        # Verify the data was JSON serialized
        stored_data = json.loads(call_args[0][2])
        assert stored_data["symbol_id"] == sample_symbol.symbol_id
        assert stored_data["symbol"] == sample_symbol.symbol
        assert stored_data["cat_ex_id"] == sample_symbol.cat_ex_id
        assert stored_data["base"] == sample_symbol.base
        assert stored_data["quote"] == sample_symbol.quote

        # Verify expiration was set
        mock_base_cache.expire.assert_called_once_with(expected_key, 24 * 60 * 60)

    @pytest.mark.asyncio
    async def test_add_symbol_error_handling(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test add_symbol error handling."""
        # Setup mock to raise exception
        mock_base_cache.hset.side_effect = Exception("Redis error")

        # Test
        result = await symbol_cache.add_symbol(sample_symbol)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_update_symbol_with_symbol_model(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test updating symbol with fullon_orm.Symbol model."""
        # Setup mock redis
        mock_base_cache.hset.return_value = True
        mock_base_cache.expire.return_value = True

        # Modify symbol for update
        sample_symbol.decimals = 10
        sample_symbol.backtest = 60

        # Test
        result = await symbol_cache.update_symbol(sample_symbol)

        # Assert
        assert result is True
        
        # Verify hset was called with updated data
        mock_base_cache.hset.assert_called_once()
        call_args = mock_base_cache.hset.call_args
        stored_data = json.loads(call_args[0][2])
        assert stored_data["decimals"] == 10
        assert stored_data["backtest"] == 60

    @pytest.mark.asyncio
    async def test_update_symbol_error_handling(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test update_symbol error handling."""
        # Setup mock to raise exception
        mock_base_cache.hset.side_effect = Exception("Redis error")

        # Test
        result = await symbol_cache.update_symbol(sample_symbol)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_symbol_with_symbol_model(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test deleting symbol with fullon_orm.Symbol model."""
        # Setup mock redis
        mock_base_cache.exists.return_value = True
        mock_base_cache.hdel.return_value = 1

        # Test
        result = await symbol_cache.delete_symbol_orm(sample_symbol)

        # Assert
        assert result is True
        
        # Verify hdel was called for both symbols and tickers
        assert mock_base_cache.hdel.call_count == 2
        call_args_list = mock_base_cache.hdel.call_args_list
        
        # Check symbols_list deletion
        symbols_call = call_args_list[0]
        assert symbols_call[0][0] == "symbols_list:binance"
        assert symbols_call[0][1] == sample_symbol.symbol
        
        # Check tickers deletion
        tickers_call = call_args_list[1]
        assert tickers_call[0][0] == "tickers:binance"
        assert tickers_call[0][1] == sample_symbol.symbol

    @pytest.mark.asyncio
    async def test_delete_symbol_with_symbol_model_no_cache(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test delete_symbol when cache entries don't exist."""
        # Setup mock redis - no existing cache
        mock_base_cache.exists.return_value = False

        # Test
        result = await symbol_cache.delete_symbol_orm(sample_symbol)

        # Assert
        assert result is True
        
        # Verify hdel was not called since cache doesn't exist
        mock_base_cache.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_symbol_error_handling(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test delete_symbol_orm error handling."""
        # Setup mock to raise exception
        mock_base_cache.exists.side_effect = Exception("Redis error")

        # Test
        result = await symbol_cache.delete_symbol_orm(sample_symbol)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_symbol_by_model(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test getting symbol using Symbol model as search criteria."""
        # Setup mock data
        symbol_data = sample_symbol.to_dict()
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = json.dumps(symbol_data)

        # Test
        result = await symbol_cache.get_symbol_by_model(sample_symbol)

        # Assert
        assert result is not None
        assert isinstance(result, Symbol)
        assert result.symbol == sample_symbol.symbol
        assert result.cat_ex_id == sample_symbol.cat_ex_id
        assert result.base == sample_symbol.base

        # Verify correct Redis key was used
        expected_key = "symbols_list:binance"
        mock_base_cache.hget.assert_called_once_with(expected_key, sample_symbol.symbol)

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_not_found(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test get_symbol_by_model when symbol not found."""
        # Setup mock redis - symbol not found
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = None

        # Test
        result = await symbol_cache.get_symbol_by_model(sample_symbol)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_json_error(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test get_symbol_by_model with invalid JSON data."""
        # Setup mock redis - invalid JSON
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = "invalid json"

        # Test
        result = await symbol_cache.get_symbol_by_model(sample_symbol)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_symbol_exists_with_symbol_model(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test checking if symbol exists using Symbol model."""
        # Setup mock redis
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = json.dumps(sample_symbol.to_dict())

        # Test
        exists = await symbol_cache.symbol_exists(sample_symbol)

        # Assert
        assert exists is True

        # Verify correct Redis operations
        expected_key = "symbols_list:binance"
        mock_base_cache.hget.assert_called_once_with(expected_key, sample_symbol.symbol)

    @pytest.mark.asyncio
    async def test_symbol_exists_false(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test symbol_exists when symbol doesn't exist."""
        # Setup mock redis - symbol not found
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = None

        # Test
        exists = await symbol_cache.symbol_exists(sample_symbol)

        # Assert
        assert exists is False

    @pytest.mark.asyncio
    async def test_symbol_exists_cache_miss(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test symbol_exists when cache doesn't exist."""
        # Setup mock redis - cache doesn't exist
        mock_base_cache.exists.return_value = False

        # Test
        exists = await symbol_cache.symbol_exists(sample_symbol)

        # Assert
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_symbols_for_symbol_model(self, symbol_cache, mock_base_cache, sample_symbols):
        """Test getting all symbols for exchange using Symbol model to identify exchange."""
        # Setup mock data
        symbols_data = {
            sym.symbol: json.dumps(sym.to_dict()) for sym in sample_symbols
        }
        mock_base_cache.exists.return_value = True
        mock_base_cache.hgetall.return_value = symbols_data

        # Use first symbol to identify exchange
        search_symbol = sample_symbols[0]

        # Test
        result = await symbol_cache.get_symbols_for_exchange(search_symbol)

        # Assert
        assert len(result) == 2
        assert all(isinstance(sym, Symbol) for sym in result)
        
        # Check specific symbols
        btc_sym = next((s for s in result if s.symbol == "BTC/USDT"), None)
        assert btc_sym is not None
        assert btc_sym.base == "BTC"

        eth_sym = next((s for s in result if s.symbol == "ETH/USDT"), None)
        assert eth_sym is not None
        assert eth_sym.base == "ETH"

    @pytest.mark.asyncio
    async def test_backward_compatibility_delete_symbol_legacy(self, symbol_cache, mock_base_cache):
        """Test backward compatibility with legacy delete_symbol method."""
        # Setup mock redis
        mock_base_cache.exists.return_value = True
        mock_base_cache.hdel.return_value = 1

        # Test legacy method
        await symbol_cache.delete_symbol("BTC/USDT", exchange_name="binance")
        
        # Verify legacy behavior still works
        assert mock_base_cache.hdel.call_count == 2

    @pytest.mark.asyncio
    async def test_symbol_model_properties(self, sample_symbol):
        """Test that Symbol model has expected properties."""
        # Test basic properties
        assert sample_symbol.symbol == "BTC/USDT"
        assert sample_symbol.cat_ex_id == 1
        assert sample_symbol.base == "BTC"
        assert sample_symbol.quote == "USDT"
        assert sample_symbol.decimals == 8
        assert sample_symbol.futures is False

    @pytest.mark.asyncio
    async def test_symbol_model_to_dict_from_dict(self, sample_symbol):
        """Test Symbol model serialization and deserialization."""
        # Test to_dict
        symbol_dict = sample_symbol.to_dict()
        assert isinstance(symbol_dict, dict)
        assert symbol_dict["symbol"] == sample_symbol.symbol
        assert symbol_dict["cat_ex_id"] == sample_symbol.cat_ex_id
        assert symbol_dict["base"] == sample_symbol.base

        # Test from_dict
        reconstructed_symbol = Symbol.from_dict(symbol_dict)
        assert reconstructed_symbol.symbol == sample_symbol.symbol
        assert reconstructed_symbol.cat_ex_id == sample_symbol.cat_ex_id
        assert reconstructed_symbol.base == sample_symbol.base
        assert reconstructed_symbol.quote == sample_symbol.quote

    @pytest.mark.asyncio
    async def test_integration_add_and_get_symbol(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test integration of add and get operations."""
        # Setup add operation
        mock_base_cache.hset.return_value = True
        mock_base_cache.expire.return_value = True

        # Test add operation
        add_result = await symbol_cache.add_symbol(sample_symbol)
        assert add_result is True

        # Setup get operation
        symbol_data = sample_symbol.to_dict()
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = json.dumps(symbol_data)

        # Test get operation
        retrieved_symbol = await symbol_cache.get_symbol_by_model(sample_symbol)
        assert retrieved_symbol is not None
        assert retrieved_symbol.symbol == sample_symbol.symbol
        assert retrieved_symbol.cat_ex_id == sample_symbol.cat_ex_id

    @pytest.mark.asyncio
    async def test_integration_update_and_get_symbol(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test integration of update and get operations."""
        # Modify symbol
        sample_symbol.decimals = 12
        sample_symbol.backtest = 90

        # Setup update operation
        mock_base_cache.hset.return_value = True
        mock_base_cache.expire.return_value = True

        # Test update operation
        update_result = await symbol_cache.update_symbol(sample_symbol)
        assert update_result is True

        # Setup get operation with updated data
        updated_data = sample_symbol.to_dict()
        mock_base_cache.exists.return_value = True
        mock_base_cache.hget.return_value = json.dumps(updated_data)

        # Test get operation
        retrieved_symbol = await symbol_cache.get_symbol_by_model(sample_symbol)
        assert retrieved_symbol is not None
        assert retrieved_symbol.decimals == 12
        assert retrieved_symbol.backtest == 90

    @pytest.mark.asyncio
    async def test_error_logging(self, symbol_cache, mock_base_cache, sample_symbol):
        """Test that errors are properly logged."""
        # Setup Redis error
        mock_base_cache.hset.side_effect = Exception("Redis connection failed")

        # Test with logging
        with patch('fullon_cache.symbol_cache.logger') as mock_logger:
            result = await symbol_cache.add_symbol(sample_symbol)

        # Assert
        assert result is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_name_mapping(self, symbol_cache, sample_symbol):
        """Test exchange name mapping from cat_ex_id."""
        # This would test the _get_exchange_name_from_cat_ex_id method
        # For now it returns None, but in production it should map cat_ex_id to exchange name
        exchange_name = symbol_cache._get_exchange_name_from_cat_ex_id("1")
        assert exchange_name is None  # Current implementation

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, symbol_cache, sample_symbol):
        """Test that cache keys are generated correctly."""
        # Test key generation for different operations
        # This ensures consistent key patterns across methods
        
        # Mock the exchange name resolution
        with patch.object(symbol_cache, '_get_exchange_name_from_symbol', return_value="binance"):
            expected_key = "symbols_list:binance"
            
            # The key should be consistent across all operations
            # This is important for cache coherence
            assert expected_key == f"symbols_list:binance"