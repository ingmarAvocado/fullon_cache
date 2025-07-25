"""Comprehensive tests for SymbolCache using real Redis and objects."""

import json
import os
import sys

import pytest
from fullon_orm.models import Symbol, Exchange

from fullon_cache.symbol_cache import SymbolCache

sys.path.append(os.path.dirname(__file__))
from factories.symbol import SymbolFactory


def create_test_symbol(symbol="BTC/USDT", cat_ex_id=1):
    """Factory function to create test Symbol objects."""
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


def create_test_exchange(name="binance", ex_id=1, cat_ex_id=1):
    """Factory function to create test Exchange objects."""
    return Exchange(
        name=name,
        ex_id=ex_id,
        cat_ex_id=cat_ex_id,
        active=True,
        paper=False,
        api_url="https://api.binance.com",
        secret_key="test_secret",
        api_key="test_api_key"
    )


class TestSymbolCache:
    """Test cases for SymbolCache functionality."""

    @pytest.mark.asyncio
    async def test_init(self, clean_redis):
        """Test SymbolCache initialization."""
        cache = SymbolCache()
        assert cache._cache is not None
        await cache._cache.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, clean_redis):
        """Test SymbolCache as async context manager."""
        async with SymbolCache() as cache:
            assert cache is not None
            assert hasattr(cache, '_cache')

    @pytest.mark.asyncio
    async def test_get_exchange_name_from_cat_ex_id(self, clean_redis):
        """Test _get_exchange_name_from_cat_ex_id method."""
        cache = SymbolCache()
        try:
            result = cache._get_exchange_name_from_cat_ex_id("some_id")
            assert result is None
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_from_cache(self, clean_redis):
        """Test get_symbols retrieving from cache."""
        cache = SymbolCache()
        
        try:
            exchange = "test_from_cache"  # Use unique exchange name
            
            # Manually populate cache
            symbols = [
                create_test_symbol("BTC/USDT", 1),
                create_test_symbol("ETH/USDT", 1),
                create_test_symbol("ADA/USDT", 1)
            ]
            
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:{exchange}"
                for symbol in symbols:
                    await redis_client.hset(redis_key, symbol.symbol, json.dumps(symbol.to_dict()))
                await redis_client.expire(redis_key, 86400)

            # Get symbols from cache
            result = await cache.get_symbols(exchange)

            assert len(result) == 3
            symbol_names = [s.symbol for s in result]
            assert "BTC/USDT" in symbol_names
            assert "ETH/USDT" in symbol_names
            assert "ADA/USDT" in symbol_names
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_cache_miss(self, clean_redis):
        """Test get_symbols with cache miss (no force refresh)."""
        cache = SymbolCache()
        
        try:
            exchange = "nonexistent"
            
            # Should return empty list when cache doesn't exist and loop=1
            result = await cache.get_symbols(exchange, loop=1)
            assert result == []
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_json_decode_error(self, clean_redis):
        """Test get_symbols handling JSON decode errors."""
        cache = SymbolCache()
        
        try:
            exchange = "test_decode_error"  # Use unique exchange name
            
            # Manually insert valid and invalid data
            valid_symbol = create_test_symbol("ETH/USDT", 1)
            
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:{exchange}"
                await redis_client.hset(redis_key, "BTC/USDT", "invalid_json")
                await redis_client.hset(redis_key, "ETH/USDT", json.dumps(valid_symbol.to_dict()))

            result = await cache.get_symbols(exchange)

            # Should only return the valid symbol
            assert len(result) == 1
            assert result[0].symbol == "ETH/USDT"
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_from_cache(self, clean_redis):
        """Test get_symbols_by_ex_id from cache."""
        cache = SymbolCache()
        
        try:
            ex_id = 1
            
            # Manually populate cache
            symbols = [
                create_test_symbol("BTC/USDT", 1),
                create_test_symbol("ETH/USDT", 1)
            ]
            
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:ex_id:{ex_id}"
                for symbol in symbols:
                    await redis_client.hset(redis_key, symbol.symbol, json.dumps(symbol.to_dict()))

            result = await cache.get_symbols_by_ex_id(ex_id)
            assert len(result) == 2
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_cache_miss(self, clean_redis):
        """Test get_symbols_by_ex_id with cache miss."""
        cache = SymbolCache()
        
        try:
            ex_id = 999
            
            # Should return empty list when cache doesn't exist and loop=1
            result = await cache.get_symbols_by_ex_id(ex_id, loop=1)
            assert result == []
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_success(self, clean_redis):
        """Test get_symbol successful retrieval."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            exchange_name = "binance"
            test_symbol = create_test_symbol(symbol_name, 1)

            # Populate cache
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:{exchange_name}"
                await redis_client.hset(redis_key, symbol_name, json.dumps(test_symbol.to_dict()))

            result = await cache.get_symbol(symbol_name, exchange_name=exchange_name)

            assert result is not None
            assert result.symbol == symbol_name
            assert result.base == "BTC"
            assert result.quote == "USDT"
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_not_found(self, clean_redis):
        """Test get_symbol when symbol not found."""
        cache = SymbolCache()
        
        try:
            symbol_name = "NONEXISTENT/USDT"
            exchange_name = "binance"

            # Try to get non-existent symbol with loop=1 to prevent refresh
            result = await cache.get_symbol(symbol_name, exchange_name=exchange_name, loop=1)
            assert result is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_no_exchange_name(self, clean_redis):
        """Test get_symbol without exchange_name."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            
            result = await cache.get_symbol(symbol_name)
            assert result is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_with_cat_ex_id(self, clean_redis):
        """Test get_symbol with cat_ex_id (but no exchange name mapping)."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            cat_ex_id = "some_id"

            result = await cache.get_symbol(symbol_name, cat_ex_id=cat_ex_id)
            assert result is None  # Because _get_exchange_name_from_cat_ex_id returns None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_json_decode_error(self, clean_redis):
        """Test get_symbol with JSON decode error."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            exchange_name = "binance"

            # Insert invalid JSON
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:{exchange_name}"
                await redis_client.hset(redis_key, symbol_name, "invalid_json")

            result = await cache.get_symbol(symbol_name, exchange_name=exchange_name)
            assert result is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_success(self, clean_redis):
        """Test delete_symbol successful deletion."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            exchange_name = "binance"
            test_symbol = create_test_symbol(symbol_name, 1)

            # Populate cache with symbol and ticker
            async with cache._cache._redis_context() as redis_client:
                symbols_key = f"symbols_list:{exchange_name}"
                tickers_key = f"tickers:{exchange_name}"
                await redis_client.hset(symbols_key, symbol_name, json.dumps(test_symbol.to_dict()))
                await redis_client.hset(tickers_key, symbol_name, json.dumps({"price": 50000.0}))

            # Verify data exists
            async with cache._cache._redis_context() as redis_client:
                symbols_exists = await redis_client.hexists(f"symbols_list:{exchange_name}", symbol_name)
                tickers_exists = await redis_client.hexists(f"tickers:{exchange_name}", symbol_name)
                assert symbols_exists
                assert tickers_exists

            # Delete symbol using ORM object
            await cache.delete_symbol(test_symbol)

            # Verify deletion
            async with cache._cache._redis_context() as redis_client:
                symbols_exists = await redis_client.hexists(f"symbols_list:{exchange_name}", symbol_name)
                tickers_exists = await redis_client.hexists(f"tickers:{exchange_name}", symbol_name)
                assert not symbols_exists
                assert not tickers_exists
                
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_no_exchange_name(self, clean_redis):
        """Test delete_symbol without exchange_name."""
        cache = SymbolCache()
        
        try:
            symbol_name = "BTC/USDT"
            
            # Should not raise any exception
            await cache.delete_symbol(symbol_name)
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_cache_not_exists(self, clean_redis):
        """Test delete_symbol when cache keys don't exist."""
        cache = SymbolCache()
        
        try:
            # Create symbol for deletion test
            symbol = create_test_symbol("BTC/USDT", 1)

            # Delete from non-existent cache (should not raise exception)
            await cache.delete_symbol(symbol)
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_multiple_symbols_workflow(self, clean_redis):
        """Test complete workflow with multiple symbols."""
        cache = SymbolCache()
        
        try:
            exchange = "binance"
            symbols = [
                create_test_symbol("BTC/USDT", 1),
                create_test_symbol("ETH/USDT", 1),
                create_test_symbol("ADA/USDT", 1),
                create_test_symbol("DOT/USDT", 1)
            ]

            # Populate cache
            async with cache._cache._redis_context() as redis_client:
                redis_key = f"symbols_list:{exchange}"
                for symbol in symbols:
                    await redis_client.hset(redis_key, symbol.symbol, json.dumps(symbol.to_dict()))

            # Get all symbols
            all_symbols = await cache.get_symbols(exchange)
            assert len(all_symbols) == 4

            # Get individual symbol
            btc_symbol = await cache.get_symbol("BTC/USDT", exchange_name=exchange)
            assert btc_symbol is not None
            assert btc_symbol.symbol == "BTC/USDT"

            # Delete one symbol
            ada_symbol = create_test_symbol("ADA/USDT", 1)
            await cache.delete_symbol(ada_symbol)

            # Verify deletion
            remaining_symbols = await cache.get_symbols(exchange)
            assert len(remaining_symbols) == 3
            assert not any(s.symbol == "ADA/USDT" for s in remaining_symbols)

            # Try to get deleted symbol
            deleted_symbol = await cache.get_symbol("ADA/USDT", exchange_name=exchange)
            assert deleted_symbol is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_symbol_model_properties(self, clean_redis):
        """Test Symbol model properties."""
        cache = SymbolCache()
        
        try:
            # Create symbol with specific properties that exist on the model
            symbol = create_test_symbol("BTC/USDT", 1)
            # Use actual Symbol model attributes
            assert symbol.decimals == 8
            assert symbol.futures is False
            assert symbol.only_ticker is False
            assert symbol.updateframe == "1h"

            # Store and retrieve
            async with cache._cache._redis_context() as redis_client:
                redis_key = "symbols_list:binance"
                await redis_client.hset(redis_key, symbol.symbol, json.dumps(symbol.to_dict()))

            retrieved = await cache.get_symbol("BTC/USDT", exchange_name="binance")
            assert retrieved is not None
            assert retrieved.decimals == 8
            assert retrieved.futures is False
            assert retrieved.only_ticker is False
            assert retrieved.updateframe == "1h"
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_exchange_specific_symbols(self, clean_redis):
        """Test symbols specific to different exchanges."""
        cache = SymbolCache()
        
        try:
            # Create symbols for different exchanges
            binance_symbols = [
                create_test_symbol("BTC/USDT", 1),
                create_test_symbol("ETH/USDT", 1)
            ]
            
            kraken_symbols = [
                create_test_symbol("BTC/USD", 2),
                create_test_symbol("ETH/EUR", 3)
            ]

            # Populate both exchanges
            async with cache._cache._redis_context() as redis_client:
                for symbol in binance_symbols:
                    await redis_client.hset("symbols_list:binance", symbol.symbol, json.dumps(symbol.to_dict()))
                for symbol in kraken_symbols:
                    await redis_client.hset("symbols_list:kraken", symbol.symbol, json.dumps(symbol.to_dict()))

            # Get symbols for each exchange
            binance_results = await cache.get_symbols("binance")
            kraken_results = await cache.get_symbols("kraken")

            assert len(binance_results) == 2
            assert len(kraken_results) == 2

            # Verify exchange isolation
            binance_pairs = [s.symbol for s in binance_results]
            kraken_pairs = [s.symbol for s in kraken_results]
            
            assert "BTC/USDT" in binance_pairs
            assert "ETH/USDT" in binance_pairs
            assert "BTC/USD" in kraken_pairs
            assert "ETH/EUR" in kraken_pairs
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_symbol_serialization(self, clean_redis):
        """Test Symbol object serialization and deserialization."""
        cache = SymbolCache()
        
        try:
            original_symbol = create_test_symbol("BTC/USDT", 1)
            # Use attributes that actually exist on the Symbol model
            assert original_symbol.decimals == 8
            assert original_symbol.updateframe == "1h"

            # Store and retrieve
            async with cache._cache._redis_context() as redis_client:
                redis_key = "symbols_list:test"
                await redis_client.hset(redis_key, original_symbol.symbol, json.dumps(original_symbol.to_dict()))

            retrieved = await cache.get_symbol("BTC/USDT", exchange_name="test")
            
            # Verify all properties preserved
            assert retrieved is not None
            assert retrieved.symbol == original_symbol.symbol
            assert retrieved.base == original_symbol.base
            assert retrieved.quote == original_symbol.quote
            assert retrieved.decimals == original_symbol.decimals
            assert retrieved.updateframe == original_symbol.updateframe
            assert retrieved.futures == original_symbol.futures
            assert retrieved.only_ticker == original_symbol.only_ticker
            
        finally:
            await cache._cache.close()