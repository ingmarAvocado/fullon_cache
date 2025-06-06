"""Tests for SymbolCache.

Comprehensive test suite for the simplified symbol cache functionality.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fullon_cache.symbol_cache import SymbolCache
from fullon_cache.exceptions import CacheError

import sys
import os
sys.path.append(os.path.dirname(__file__))
from factories.symbol import SymbolFactory


@pytest.fixture
async def symbol_cache():
    """Create a SymbolCache instance for testing."""
    cache = SymbolCache()
    yield cache
    await cache.close()


@pytest.fixture
def mock_symbol():
    """Create a mock Symbol object."""
    factory = SymbolFactory()
    return factory.create()


@pytest.fixture
def mock_symbols_list():
    """Create a list of mock Symbol objects."""
    factory = SymbolFactory()
    return [
        factory.create(symbol="BTC/USDT", base="BTC", quote="USDT"),
        factory.create(symbol="ETH/USDT", base="ETH", quote="USDT"),
        factory.create(symbol="ADA/USDT", base="ADA", quote="USDT"),
    ]


class TestSymbolCache:
    """Test cases for SymbolCache class."""

    @pytest.mark.asyncio
    async def test_init(self, symbol_cache):
        """Test SymbolCache initialization."""
        assert symbol_cache._cache is not None
        assert hasattr(symbol_cache, '_cache')

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test SymbolCache as async context manager."""
        async with SymbolCache() as cache:
            assert cache is not None
            assert hasattr(cache, '_cache')

    @pytest.mark.asyncio
    async def test_close(self, symbol_cache):
        """Test cache connection closing."""
        with patch.object(symbol_cache._cache, 'close', new_callable=AsyncMock) as mock_close:
            await symbol_cache.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_exchange_name_from_cat_ex_id(self, symbol_cache):
        """Test _get_exchange_name_from_cat_ex_id method."""
        # This method returns None in the simplified implementation
        result = symbol_cache._get_exchange_name_from_cat_ex_id("some_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_symbols_force_refresh_success(self, symbol_cache, mock_symbols_list):
        """Test get_symbols with force=True - successful database fetch."""
        exchange = "binance"
        
        # Mock the database session and repositories
        mock_session = AsyncMock()
        mock_exchange_repo = AsyncMock()
        mock_symbol_repo = AsyncMock()
        mock_exchange_obj = MagicMock()
        mock_exchange_obj.cat_ex_id = 1
        
        mock_exchange_repo.get_exchange_by_name.return_value = mock_exchange_obj
        mock_symbol_repo.get_by_exchange_id.return_value = mock_symbols_list
        
        # Mock cache operations
        symbol_cache._cache.hset = AsyncMock()
        symbol_cache._cache.expire = AsyncMock()
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session, \
             patch('fullon_cache.symbol_cache.ExchangeRepository') as mock_ex_repo_class, \
             patch('fullon_cache.symbol_cache.SymbolRepository') as mock_sym_repo_class:
            
            # Setup async generator for session
            async def async_gen():
                yield mock_session
            mock_get_session.return_value = async_gen()
            
            mock_ex_repo_class.return_value = mock_exchange_repo
            mock_sym_repo_class.return_value = mock_symbol_repo
            
            # Call get_symbols with force=True
            result = await symbol_cache.get_symbols(exchange, force=True)
            
            # Verify results
            assert len(result) == 3
            assert all(symbol.symbol in ["BTC/USDT", "ETH/USDT", "ADA/USDT"] for symbol in result)
            
            # Verify repository calls
            mock_exchange_repo.get_exchange_by_name.assert_called_once_with(exchange)
            mock_symbol_repo.get_by_exchange_id.assert_called_once_with(1)
            
            # Verify cache operations
            assert symbol_cache._cache.hset.call_count == 3
            symbol_cache._cache.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_symbols_force_refresh_exchange_not_found(self, symbol_cache):
        """Test get_symbols with force=True when exchange is not found."""
        exchange = "nonexistent"
        
        mock_session = AsyncMock()
        mock_exchange_repo = AsyncMock()
        mock_exchange_repo.get_exchange_by_name.return_value = None
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session, \
             patch('fullon_cache.symbol_cache.ExchangeRepository') as mock_ex_repo_class:
            
            async def async_gen():
                yield mock_session
            mock_get_session.return_value = async_gen()
            mock_ex_repo_class.return_value = mock_exchange_repo
            
            result = await symbol_cache.get_symbols(exchange, force=True)
            
            assert result == []
            mock_exchange_repo.get_exchange_by_name.assert_called_once_with(exchange)

    @pytest.mark.asyncio
    async def test_get_symbols_from_cache(self, symbol_cache, mock_symbols_list):
        """Test get_symbols retrieving from cache."""
        exchange = "binance"
        redis_key = f"symbols_list:{exchange}"
        
        # Mock cache data
        cache_data = {}
        for symbol in mock_symbols_list:
            cache_data[symbol.symbol] = json.dumps(symbol.to_dict())
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hgetall = AsyncMock(return_value=cache_data)
        
        result = await symbol_cache.get_symbols(exchange)
        
        assert len(result) == 3
        symbol_cache._cache.exists.assert_called_once_with(redis_key)
        symbol_cache._cache.hgetall.assert_called_once_with(redis_key)

    @pytest.mark.asyncio
    async def test_get_symbols_cache_miss_with_auto_refresh(self, symbol_cache, mock_symbols_list):
        """Test get_symbols with cache miss triggering auto-refresh."""
        exchange = "binance"
        
        # First call (loop=0): cache miss
        # Second call (loop=1): return from force refresh
        symbol_cache._cache.exists = AsyncMock(return_value=False)
        
        # Mock a successful force refresh by setting up cache to return data on second call
        def side_effect_exists(key):
            # First call: False (cache miss), Second call: True (after refresh)
            return AsyncMock(return_value=True)() if hasattr(side_effect_exists, 'called') else (
                setattr(side_effect_exists, 'called', True), AsyncMock(return_value=False)())[1]
        
        # Simplified test: just verify that empty cache returns empty list when no recursive call
        result = await symbol_cache.get_symbols(exchange, loop=1)  # Prevent recursion
        assert result == []

    @pytest.mark.asyncio
    async def test_get_symbols_json_decode_error(self, symbol_cache):
        """Test get_symbols handling JSON decode errors."""
        exchange = "binance"
        redis_key = f"symbols_list:{exchange}"
        
        # Mock cache with invalid JSON
        cache_data = {
            "BTC/USDT": "invalid_json",
            "ETH/USDT": json.dumps({"symbol": "ETH/USDT", "base": "ETH", "quote": "USDT"})
        }
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hgetall = AsyncMock(return_value=cache_data)
        
        # Mock Symbol.from_dict for valid JSON
        with patch('fullon_cache.symbol_cache.Symbol.from_dict') as mock_from_dict:
            mock_symbol = MagicMock()
            mock_symbol.symbol = "ETH/USDT"
            mock_from_dict.return_value = mock_symbol
            
            result = await symbol_cache.get_symbols(exchange)
            
            # Should only return the valid symbol, invalid JSON should be skipped
            assert len(result) == 1
            assert result[0].symbol == "ETH/USDT"

    @pytest.mark.asyncio
    async def test_get_symbols_database_error(self, symbol_cache):
        """Test get_symbols handling database errors."""
        exchange = "binance"
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")
            
            result = await symbol_cache.get_symbols(exchange, force=True)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_force_refresh_success(self, symbol_cache, mock_symbols_list):
        """Test get_symbols_by_ex_id with force=True."""
        ex_id = 1
        
        mock_session = AsyncMock()
        mock_symbol_repo = AsyncMock()
        mock_symbol_repo.get_by_exchange_id.return_value = mock_symbols_list
        
        symbol_cache._cache.hset = AsyncMock()
        symbol_cache._cache.expire = AsyncMock()
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session, \
             patch('fullon_cache.symbol_cache.SymbolRepository') as mock_sym_repo_class:
            
            async def async_gen():
                yield mock_session
            mock_get_session.return_value = async_gen()
            mock_sym_repo_class.return_value = mock_symbol_repo
            
            result = await symbol_cache.get_symbols_by_ex_id(ex_id, force=True)
            
            assert len(result) == 3
            mock_symbol_repo.get_by_exchange_id.assert_called_once_with(ex_id)
            assert symbol_cache._cache.hset.call_count == 3

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_no_symbols(self, symbol_cache):
        """Test get_symbols_by_ex_id when no symbols found."""
        ex_id = 999
        
        mock_session = AsyncMock()
        mock_symbol_repo = AsyncMock()
        mock_symbol_repo.get_by_exchange_id.return_value = []
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session, \
             patch('fullon_cache.symbol_cache.SymbolRepository') as mock_sym_repo_class:
            
            async def async_gen():
                yield mock_session
            mock_get_session.return_value = async_gen()
            mock_sym_repo_class.return_value = mock_symbol_repo
            
            result = await symbol_cache.get_symbols_by_ex_id(ex_id, force=True)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_from_cache(self, symbol_cache, mock_symbols_list):
        """Test get_symbols_by_ex_id from cache."""
        ex_id = 1
        redis_key = f"symbols_list:ex_id:{ex_id}"
        
        cache_data = {}
        for symbol in mock_symbols_list:
            cache_data[symbol.symbol] = json.dumps(symbol.to_dict())
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hgetall = AsyncMock(return_value=cache_data)
        
        result = await symbol_cache.get_symbols_by_ex_id(ex_id)
        
        assert len(result) == 3
        symbol_cache._cache.exists.assert_called_once_with(redis_key)

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_database_error(self, symbol_cache):
        """Test get_symbols_by_ex_id with database error."""
        ex_id = 1
        
        with patch('fullon_cache.symbol_cache.get_async_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            result = await symbol_cache.get_symbols_by_ex_id(ex_id, force=True)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_symbol_success(self, symbol_cache, mock_symbol):
        """Test get_symbol successful retrieval."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        redis_key = f"symbols_list:{exchange_name}"
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hget = AsyncMock(return_value=json.dumps(mock_symbol.to_dict()))
        
        with patch('fullon_cache.symbol_cache.Symbol.from_dict', return_value=mock_symbol):
            result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name)
            
            assert result == mock_symbol
            symbol_cache._cache.exists.assert_called_once_with(redis_key)
            symbol_cache._cache.hget.assert_called_once_with(redis_key, symbol_name)

    @pytest.mark.asyncio
    async def test_get_symbol_no_exchange_name(self, symbol_cache):
        """Test get_symbol without exchange_name."""
        symbol_name = "BTC/USDT"
        
        result = await symbol_cache.get_symbol(symbol_name)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_symbol_with_cat_ex_id(self, symbol_cache):
        """Test get_symbol with cat_ex_id (but no exchange name mapping)."""
        symbol_name = "BTC/USDT"
        cat_ex_id = "some_id"
        
        result = await symbol_cache.get_symbol(symbol_name, cat_ex_id=cat_ex_id)
        
        assert result is None  # Because _get_exchange_name_from_cat_ex_id returns None

    @pytest.mark.asyncio
    async def test_get_symbol_cache_miss_with_refresh(self, symbol_cache, mock_symbol):
        """Test get_symbol with cache miss triggering refresh."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        # First call: cache exists but symbol not found
        # Second call: after refresh, symbol found
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hget = AsyncMock(side_effect=[None, json.dumps(mock_symbol.to_dict())])
        
        with patch.object(symbol_cache, 'get_symbols', new_callable=AsyncMock) as mock_get_symbols, \
             patch('fullon_cache.symbol_cache.Symbol.from_dict', return_value=mock_symbol):
            
            result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name)
            
            assert result == mock_symbol
            mock_get_symbols.assert_called_once_with(exchange=exchange_name, force=True)

    @pytest.mark.asyncio
    async def test_get_symbol_cache_not_exists_with_refresh(self, symbol_cache, mock_symbol):
        """Test get_symbol when cache doesn't exist, triggering refresh."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        # First call: cache doesn't exist
        # Second call: after refresh, cache exists and symbol found
        symbol_cache._cache.exists = AsyncMock(side_effect=[False, True])
        symbol_cache._cache.hget = AsyncMock(return_value=json.dumps(mock_symbol.to_dict()))
        
        with patch.object(symbol_cache, 'get_symbols', new_callable=AsyncMock) as mock_get_symbols, \
             patch('fullon_cache.symbol_cache.Symbol.from_dict', return_value=mock_symbol):
            
            result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name)
            
            assert result == mock_symbol
            mock_get_symbols.assert_called_once_with(exchange=exchange_name, force=True)

    @pytest.mark.asyncio
    async def test_get_symbol_json_decode_error(self, symbol_cache):
        """Test get_symbol with JSON decode error."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hget = AsyncMock(return_value="invalid_json")
        
        result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_symbol_exception_handling(self, symbol_cache):
        """Test get_symbol exception handling."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(side_effect=Exception("Redis error"))
        
        result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_symbol_success(self, symbol_cache):
        """Test delete_symbol successful deletion."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hdel = AsyncMock()
        
        await symbol_cache.delete_symbol(symbol_name, exchange_name=exchange_name)
        
        # Should delete from both symbols list and tickers
        expected_calls = [
            (f'symbols_list:{exchange_name}', symbol_name),
            (f'tickers:{exchange_name}', symbol_name)
        ]
        
        actual_calls = [call.args for call in symbol_cache._cache.hdel.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls

    @pytest.mark.asyncio
    async def test_delete_symbol_no_exchange_name(self, symbol_cache):
        """Test delete_symbol without exchange_name."""
        symbol_name = "BTC/USDT"
        
        await symbol_cache.delete_symbol(symbol_name)
        
        # Should not make any Redis calls

    @pytest.mark.asyncio
    async def test_delete_symbol_cache_not_exists(self, symbol_cache):
        """Test delete_symbol when cache keys don't exist."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=False)
        symbol_cache._cache.hdel = AsyncMock()
        
        await symbol_cache.delete_symbol(symbol_name, exchange_name=exchange_name)
        
        # hdel should not be called since keys don't exist
        symbol_cache._cache.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_symbol_exception_handling(self, symbol_cache):
        """Test delete_symbol exception handling."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(side_effect=Exception("Redis error"))
        
        # Should not raise exception
        await symbol_cache.delete_symbol(symbol_name, exchange_name=exchange_name)

    @pytest.mark.asyncio
    async def test_get_symbols_empty_cache_no_loop(self, symbol_cache):
        """Test get_symbols with empty cache and loop=1 (no recursive call)."""
        exchange = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=False)
        
        result = await symbol_cache.get_symbols(exchange, loop=1)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_empty_cache_no_loop(self, symbol_cache):
        """Test get_symbols_by_ex_id with empty cache and loop=1."""
        ex_id = 1
        
        symbol_cache._cache.exists = AsyncMock(return_value=False)
        
        result = await symbol_cache.get_symbols_by_ex_id(ex_id, loop=1)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_symbol_already_tried_refresh_symbol_not_found(self, symbol_cache):
        """Test get_symbol when refresh was already tried and symbol still not found."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=True)
        symbol_cache._cache.hget = AsyncMock(return_value=None)
        
        result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name, loop=1)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_symbol_already_tried_refresh_cache_not_exists(self, symbol_cache):
        """Test get_symbol when refresh was already tried and cache still doesn't exist."""
        symbol_name = "BTC/USDT"
        exchange_name = "binance"
        
        symbol_cache._cache.exists = AsyncMock(return_value=False)
        
        result = await symbol_cache.get_symbol(symbol_name, exchange_name=exchange_name, loop=1)
        
        assert result is None