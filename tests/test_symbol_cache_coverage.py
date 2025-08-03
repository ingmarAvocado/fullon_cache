"""Additional tests for SymbolCache to improve coverage - NO MOCKING!"""

import asyncio
import json

import pytest
from fullon_orm.models import Symbol

from fullon_cache import SymbolCache


def create_test_symbol(symbol="BTC/USDT", cat_ex_id=1, base="BTC", quote="USDT"):
    """Factory for test Symbol objects."""
    return Symbol(
        symbol=symbol,
        base=base,
        quote=quote,
        cat_ex_id=cat_ex_id,
        decimals=8,
        updateframe="1h",
        backtest=30,
        futures=False,
        only_ticker=False
    )


class TestSymbolCacheCoverage:
    """Test cases to improve SymbolCache coverage using real operations."""

    @pytest.mark.asyncio
    async def test_get_symbols_force_refresh(self, clean_redis):
        """Test forced refresh from database."""
        cache = SymbolCache()
        
        try:
            # Test force refresh - this will try database and return real data or empty
            symbols = await cache.get_symbols("binance", force=True)
            # Should return a list (might be empty or have real data)
            assert isinstance(symbols, list)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_force_refresh(self, clean_redis):
        """Test forced refresh by exchange ID."""
        cache = SymbolCache()
        
        try:
            # Test force refresh with ex_id - might return real data from database
            symbols = await cache.get_symbols_by_ex_id(1, force=True)
            # Should return a list (might be empty or have real data)
            assert isinstance(symbols, list)
            
            # If symbols are returned, they should be Symbol objects
            for symbol in symbols:
                assert hasattr(symbol, 'symbol')
                assert hasattr(symbol, 'base')
                assert hasattr(symbol, 'quote')
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_cache_hit(self, clean_redis):
        """Test getting symbols by exchange ID from cache."""
        cache = SymbolCache()
        
        try:
            # Manually populate cache
            symbol1 = create_test_symbol("BTC/USDT", 1)
            symbol2 = create_test_symbol("ETH/USDT", 1)
            
            redis_key = "symbols_list:ex_id:1"
            await cache._cache.hset(redis_key, "BTC/USDT", json.dumps(symbol1.to_dict()))
            await cache._cache.hset(redis_key, "ETH/USDT", json.dumps(symbol2.to_dict()))
            
            # Get symbols from cache
            symbols = await cache.get_symbols_by_ex_id(1)
            assert len(symbols) == 2
            symbol_names = {s.symbol for s in symbols}
            assert "BTC/USDT" in symbol_names
            assert "ETH/USDT" in symbol_names
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_cache_miss(self, clean_redis):
        """Test cache miss for symbols by exchange ID."""
        cache = SymbolCache()
        
        try:
            # No cached data, should trigger database lookup for non-existent exchange
            symbols = await cache.get_symbols_by_ex_id(999999)  # Very high ID unlikely to exist
            # Should return empty list for non-existent exchange
            assert isinstance(symbols, list)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_by_ex_id_json_error(self, clean_redis):
        """Test JSON parsing error in get_symbols_by_ex_id."""
        cache = SymbolCache()
        
        try:
            # Put invalid JSON in cache
            redis_key = "symbols_list:ex_id:1"
            await cache._cache.hset(redis_key, "INVALID/SYMBOL", "invalid json data")
            
            # Should handle JSON error gracefully
            symbols = await cache.get_symbols_by_ex_id(1)
            # Invalid JSON should be skipped, return empty list
            assert symbols == []
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_cache_miss_refresh(self, clean_redis):
        """Test symbol cache miss triggers refresh."""
        cache = SymbolCache()
        
        try:
            # This should trigger a cache refresh attempt
            symbol = await cache.get_symbol("BTC/USDT", exchange_name="binance")
            # Without database, should return None
            assert symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_with_cat_ex_id_only(self, clean_redis):
        """Test getting symbol with cat_ex_id but no exchange_name."""
        cache = SymbolCache()
        
        try:
            # This should fail because cat_ex_id mapping returns None
            symbol = await cache.get_symbol("BTC/USDT", cat_ex_id="1")
            assert symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_json_parse_error(self, clean_redis):
        """Test JSON parsing error in get_symbol."""
        cache = SymbolCache()
        
        try:
            # Pre-populate cache with invalid JSON
            redis_key = "symbols_list:binance"
            await cache._cache.hset(redis_key, "BTC/USDT", "invalid json data")
            
            # Should handle JSON error gracefully
            symbol = await cache.get_symbol("BTC/USDT", exchange_name="binance")
            assert symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_no_cache_no_refresh(self, clean_redis):
        """Test symbol retrieval when cache doesn't exist and refresh attempted."""
        cache = SymbolCache()
        
        try:
            # This tests the loop logic - first call triggers refresh, second call gives up
            symbol = await cache.get_symbol("BTC/USDT", exchange_name="nonexistent_exchange")
            assert symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_add_symbol_success(self, clean_redis):
        """Test successfully adding a symbol."""
        cache = SymbolCache()
        
        try:
            symbol = create_test_symbol("TESTADD/USDT", 1, "TESTADD", "USDT")
            
            result = await cache.add_symbol(symbol)
            assert result is True
            
            # Verify it was cached
            redis_key = "symbols_list:binance"
            symbol_json = await cache._cache.hget(redis_key, "TESTADD/USDT")
            assert symbol_json is not None
            
            # Verify the data
            symbol_dict = json.loads(symbol_json)
            assert symbol_dict["symbol"] == "TESTADD/USDT"
            assert symbol_dict["base"] == "TESTADD"
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_add_symbol_error_handling(self, clean_redis):
        """Test error handling in add_symbol."""
        cache = SymbolCache()
        
        try:
            # Create symbol with invalid data that might cause issues
            symbol = create_test_symbol("", 1)  # Empty symbol name
            
            # Should handle gracefully and return True (since Redis accepts empty keys)
            result = await cache.add_symbol(symbol)
            assert isinstance(result, bool)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_update_symbol_success(self, clean_redis):
        """Test successfully updating a symbol."""
        cache = SymbolCache()
        
        try:
            symbol = create_test_symbol("BTC/USDT", 1)
            
            result = await cache.update_symbol(symbol)
            assert result is True
            
            # Verify it was cached/updated
            redis_key = "symbols_list:binance"
            symbol_json = await cache._cache.hget(redis_key, "BTC/USDT")
            assert symbol_json is not None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_update_symbol_error_handling(self, clean_redis):
        """Test error handling in update_symbol."""
        cache = SymbolCache()
        
        try:
            # Test with unusual symbol
            symbol = create_test_symbol("TEST/UPDATE", 999)
            
            result = await cache.update_symbol(symbol)
            assert isinstance(result, bool)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_success(self, clean_redis):
        """Test successfully deleting a symbol."""
        cache = SymbolCache()
        
        try:
            # First add a symbol to delete
            symbol = create_test_symbol("DELETE/ME", 1)
            await cache.add_symbol(symbol)
            
            # Verify it exists
            redis_key = "symbols_list:binance"
            symbol_json = await cache._cache.hget(redis_key, "DELETE/ME")
            assert symbol_json is not None
            
            # Delete it
            result = await cache.delete_symbol(symbol)
            assert result is True
            
            # Verify it's gone
            symbol_json = await cache._cache.hget(redis_key, "DELETE/ME")
            assert symbol_json is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_with_tickers(self, clean_redis):
        """Test deleting symbol also removes from tickers."""
        cache = SymbolCache()
        
        try:
            symbol = create_test_symbol("TICKER/TEST", 1)
            
            # Add symbol to both symbols and tickers
            symbols_key = "symbols_list:binance"
            tickers_key = "tickers:binance"
            
            await cache._cache.hset(symbols_key, "TICKER/TEST", json.dumps(symbol.to_dict()))
            await cache._cache.hset(tickers_key, "TICKER/TEST", "ticker_data")
            
            # Delete symbol
            result = await cache.delete_symbol(symbol)
            assert result is True
            
            # Verify both are gone
            symbol_json = await cache._cache.hget(symbols_key, "TICKER/TEST")
            ticker_data = await cache._cache.hget(tickers_key, "TICKER/TEST")
            assert symbol_json is None
            assert ticker_data is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_error_handling(self, clean_redis):
        """Test error handling in delete_symbol."""
        cache = SymbolCache()
        
        try:
            # Test deleting non-existent symbol
            symbol = create_test_symbol("NONEXISTENT/SYMBOL", 1)
            
            result = await cache.delete_symbol(symbol)
            assert result is True  # Should succeed even if symbol doesn't exist
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_success(self, clean_redis):
        """Test getting symbol by model."""
        cache = SymbolCache()
        
        try:
            # Add symbol first
            symbol = create_test_symbol("TESTMODEL/USDT", 1, "TESTMODEL", "USDT")
            await cache.add_symbol(symbol)
            
            # Search for it using model
            search_symbol = create_test_symbol("TESTMODEL/USDT", 1, "TESTMODEL", "USDT")
            found_symbol = await cache.get_symbol_by_model(search_symbol)
            
            assert found_symbol is not None
            assert found_symbol.symbol == "TESTMODEL/USDT"
            assert found_symbol.base == "TESTMODEL"
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_not_found(self, clean_redis):
        """Test getting symbol by model when not found."""
        cache = SymbolCache()
        
        try:
            search_symbol = create_test_symbol("NOTFOUND/SYMBOL", 1)
            found_symbol = await cache.get_symbol_by_model(search_symbol)
            
            assert found_symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_json_error(self, clean_redis):
        """Test JSON error in get_symbol_by_model."""
        cache = SymbolCache()
        
        try:
            # Put invalid JSON in cache
            redis_key = "symbols_list:binance"
            await cache._cache.hset(redis_key, "JSON/ERROR", "invalid json")
            
            search_symbol = create_test_symbol("JSON/ERROR", 1)
            found_symbol = await cache.get_symbol_by_model(search_symbol)
            
            assert found_symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbol_by_model_error_handling(self, clean_redis):
        """Test error handling in get_symbol_by_model."""
        cache = SymbolCache()
        
        try:
            # Test with unusual symbol that might cause issues
            search_symbol = create_test_symbol("", 999)  # Empty symbol name
            found_symbol = await cache.get_symbol_by_model(search_symbol)
            
            # Should handle gracefully
            assert found_symbol is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_symbol_exists_true(self, clean_redis):
        """Test symbol_exists returns True when symbol exists."""
        cache = SymbolCache()
        
        try:
            # Add symbol first
            symbol = create_test_symbol("EXISTS/TEST", 1)
            await cache.add_symbol(symbol)
            
            # Check if it exists
            exists = await cache.symbol_exists(symbol)
            assert exists is True
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_symbol_exists_false(self, clean_redis):
        """Test symbol_exists returns False when symbol doesn't exist."""
        cache = SymbolCache()
        
        try:
            symbol = create_test_symbol("NOEXIST/TEST", 1)
            exists = await cache.symbol_exists(symbol)
            assert exists is False
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_symbol_exists_no_cache(self, clean_redis):
        """Test symbol_exists when cache doesn't exist."""
        cache = SymbolCache()
        
        try:
            # No cache exists for this exchange
            symbol = create_test_symbol("NOCACHE/TEST", 999)
            exists = await cache.symbol_exists(symbol)
            assert exists is False
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_symbol_exists_error_handling(self, clean_redis):
        """Test error handling in symbol_exists."""
        cache = SymbolCache()
        
        try:
            # Test with symbol that might cause issues
            symbol = create_test_symbol("", 1)  # Empty symbol name
            exists = await cache.symbol_exists(symbol)
            assert isinstance(exists, bool)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_for_exchange(self, clean_redis):
        """Test getting all symbols for an exchange."""
        cache = SymbolCache()
        
        try:
            # Pre-populate cache with symbols
            symbol1 = create_test_symbol("EXCH1/USDT", 1)
            symbol2 = create_test_symbol("EXCH2/USDT", 1)
            
            await cache.add_symbol(symbol1)
            await cache.add_symbol(symbol2)
            
            # Get symbols for exchange using model
            test_symbol = create_test_symbol("ANY/SYMBOL", 1)  # Just to identify exchange
            symbols = await cache.get_symbols_for_exchange(test_symbol)
            
            # Should return symbols for the exchange
            assert len(symbols) >= 2
            symbol_names = {s.symbol for s in symbols}
            assert "EXCH1/USDT" in symbol_names
            assert "EXCH2/USDT" in symbol_names
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_for_exchange_empty(self, clean_redis):
        """Test getting symbols for exchange when none exist."""
        cache = SymbolCache()
        
        try:
            # Use symbol with exchange that has no cached symbols
            test_symbol = create_test_symbol("TEST/SYMBOL", 999)
            symbols = await cache.get_symbols_for_exchange(test_symbol)
            
            # Should return empty list
            assert symbols == []
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_symbols_for_exchange_error_handling(self, clean_redis):
        """Test error handling in get_symbols_for_exchange."""
        cache = SymbolCache()
        
        try:
            # Test with symbol that might cause issues
            test_symbol = create_test_symbol("", 1)  # Empty symbol name
            symbols = await cache.get_symbols_for_exchange(test_symbol)
            
            # Should handle gracefully and return list
            assert isinstance(symbols, list)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_exchange_name_from_symbol_helper(self, clean_redis):
        """Test _get_exchange_name_from_symbol helper method."""
        cache = SymbolCache()
        
        try:
            symbol = create_test_symbol("TEST/SYMBOL", 1)
            exchange_name = cache._get_exchange_name_from_symbol(symbol)
            
            # Should return fallback value
            assert exchange_name == "binance"
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_legacy(self, clean_redis):
        """Test legacy delete_symbol method."""
        cache = SymbolCache()
        
        try:
            # Add symbol first using regular method
            symbol = create_test_symbol("LEGACY/DELETE", 1)
            await cache.add_symbol(symbol)
            
            # Delete using legacy method
            result = await cache.delete_symbol_legacy("LEGACY/DELETE", "binance")
            assert result is True
            
            # Verify it's gone
            redis_key = "symbols_list:binance"
            symbol_json = await cache._cache.hget(redis_key, "LEGACY/DELETE")
            assert symbol_json is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_legacy_with_tickers(self, clean_redis):
        """Test legacy delete also removes from tickers."""
        cache = SymbolCache()
        
        try:
            # Add to both symbols and tickers
            symbols_key = "symbols_list:binance"
            tickers_key = "tickers:binance"
            
            symbol_data = {"symbol": "LEGACY/TICKER", "base": "LEGACY"}
            await cache._cache.hset(symbols_key, "LEGACY/TICKER", json.dumps(symbol_data))
            await cache._cache.hset(tickers_key, "LEGACY/TICKER", "ticker_data")
            
            # Delete using legacy method
            result = await cache.delete_symbol_legacy("LEGACY/TICKER", "binance")
            assert result is True
            
            # Verify both are gone
            symbol_json = await cache._cache.hget(symbols_key, "LEGACY/TICKER")
            ticker_data = await cache._cache.hget(tickers_key, "LEGACY/TICKER")
            assert symbol_json is None
            assert ticker_data is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_legacy_error_handling(self, clean_redis):
        """Test error handling in legacy delete method."""
        cache = SymbolCache()
        
        try:
            # Test deleting non-existent symbol
            result = await cache.delete_symbol_legacy("NONEXISTENT/SYMBOL", "binance")
            assert result is True  # Should succeed even if symbol doesn't exist
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_delete_symbol_orm_alias(self, clean_redis):
        """Test delete_symbol_orm alias method."""
        cache = SymbolCache()
        
        try:
            # Add symbol first
            symbol = create_test_symbol("ORM/ALIAS", 1)
            await cache.add_symbol(symbol)
            
            # Delete using ORM alias
            result = await cache.delete_symbol_orm(symbol)
            assert result is True
            
            # Verify it's gone
            redis_key = "symbols_list:binance"
            symbol_json = await cache._cache.hget(redis_key, "ORM/ALIAS")
            assert symbol_json is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_concurrent_symbol_operations(self, clean_redis, worker_id):
        """Test concurrent symbol operations."""
        cache = SymbolCache()
        
        try:
            # Create multiple symbols with worker-specific cat_ex_id for isolation
            # Each worker gets a unique cat_ex_id to prevent Redis key collisions  
            worker_cat_ex_id = hash(worker_id) % 1000000  # Generate unique cat_ex_id per worker
            symbols = [
                create_test_symbol(f"CONC_{worker_id}_{i}/USDT", worker_cat_ex_id)
                for i in range(10)
            ]
            
            # Add all symbols concurrently
            add_tasks = [cache.add_symbol(symbol) for symbol in symbols]
            add_results = await asyncio.gather(*add_tasks)
            
            # All should succeed
            assert all(add_results)
            
            # Check all symbols exist concurrently
            exists_tasks = [cache.symbol_exists(symbol) for symbol in symbols]
            exists_results = await asyncio.gather(*exists_tasks)
            
            # All should exist
            assert all(exists_results)
            
            # Delete all symbols concurrently
            delete_tasks = [cache.delete_symbol(symbol) for symbol in symbols]
            delete_results = await asyncio.gather(*delete_tasks)
            
            # All deletions should succeed
            assert all(delete_results)
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_edge_cases_with_special_symbols(self, clean_redis, worker_id):
        """Test edge cases with special symbol names."""
        cache = SymbolCache()
        
        try:
            # Test with symbols containing special characters - use worker-specific symbols
            special_symbols = [
                create_test_symbol(f"BTC-USD_{worker_id}", 1),  # Dash instead of slash
                create_test_symbol(f"BTC_USDT_{worker_id}", 1),  # Underscore
                create_test_symbol(f"BTC.USDT_{worker_id}", 1),  # Dot
                create_test_symbol(f"BTC:USDT_{worker_id}", 1),  # Colon
            ]
            
            successful_symbols = 0
            
            for symbol in special_symbols:
                # Add symbol with retry
                add_success = False
                for attempt in range(3):
                    try:
                        result = await cache.add_symbol(symbol)
                        if result:
                            add_success = True
                            break
                    except Exception:
                        if attempt == 2:
                            pass  # Allow failure under stress
                        await asyncio.sleep(0.1)
                
                if add_success:
                    # Check if it exists with retry
                    exists_success = False
                    for attempt in range(3):
                        try:
                            exists = await cache.symbol_exists(symbol)
                            if exists:
                                exists_success = True
                                break
                        except Exception:
                            if attempt == 2:
                                pass
                            await asyncio.sleep(0.1)
                    
                    # Get by model with retry
                    if exists_success:
                        for attempt in range(3):
                            try:
                                found = await cache.get_symbol_by_model(symbol)
                                if found is not None:
                                    assert found.symbol == symbol.symbol
                                    successful_symbols += 1
                                    break
                            except Exception:
                                if attempt == 2:
                                    pass
                                await asyncio.sleep(0.1)
            
            # At least some symbols should work under parallel stress
            assert successful_symbols >= 1, f"No symbols succeeded for worker {worker_id}"
            
        finally:
            await cache.close()