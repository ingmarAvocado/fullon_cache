"""Tests for TickCache ORM-based interface using real Redis and objects."""

import json
import time

import pytest
from fullon_orm.models import Tick, Exchange

from fullon_cache.tick_cache import TickCache


def create_test_tick(symbol="BTC/USDT", exchange="binance", price=50000.0, volume=1234.56):
    """Factory function to create test Tick objects."""
    return Tick(
        symbol=symbol,
        exchange=exchange,
        price=price,
        volume=volume,
        time=time.time(),
        bid=price - 1.0,
        ask=price + 1.0,
        last=price + 0.5
    )


def create_test_exchange(name="binance", ex_id=1, cat_ex_id=1):
    """Factory function to create test Exchange objects."""
    return Exchange(
        name=name,
        ex_id=ex_id,
        cat_ex_id=cat_ex_id,
        active=True,
        paper=False,
        api_url=f"https://api.{name}.com",
        secret_key="test_secret",
        api_key="test_api_key"
    )


class TestTickCacheORM:
    """Test cases for TickCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_update_ticker_with_tick_model(self, clean_redis):
        """Test updating ticker with fullon_orm.Tick model."""
        cache = TickCache()
        
        try:
            # Create test tick
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            
            # Test update_ticker
            result = await cache.update_ticker("binance", tick)
            assert result is True
            
            # Verify the tick was stored
            stored_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert stored_tick is not None
            assert stored_tick.symbol == tick.symbol
            assert stored_tick.price == tick.price
            assert stored_tick.volume == tick.volume
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_ticker_returns_tick_model(self, clean_redis):
        """Test that get_ticker returns fullon_orm.Tick model."""
        cache = TickCache()
        
        try:
            # Create and store a tick
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick)

            # Get the tick back
            result = await cache.get_ticker("BTC/USDT", "binance")

            # Verify it's a proper Tick model
            assert result is not None
            assert isinstance(result, Tick)
            assert result.symbol == tick.symbol
            assert result.exchange == tick.exchange
            assert result.price == tick.price
            assert result.volume == tick.volume
            assert result.bid == tick.bid
            assert result.ask == tick.ask
            assert result.last == tick.last
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_ticker_not_found(self, clean_redis):
        """Test get_ticker when ticker not found."""
        cache = TickCache()
        
        try:
            result = await cache.get_ticker("NONEXISTENT/USDT", "binance")
            assert result is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_price_tick_with_exchange(self, clean_redis):
        """Test get_price_tick with specific exchange."""
        cache = TickCache()
        
        try:
            # Create and store a tick
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick)

            # Get price tick
            result = await cache.get_price_tick("BTC/USDT", "binance")

            assert result is not None
            assert isinstance(result, Tick)
            assert result.price == tick.price
            assert result.volume == tick.volume
            assert result.symbol == tick.symbol
            assert result.exchange == tick.exchange
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_get_price_tick_not_found(self, clean_redis):
        """Test get_price_tick when ticker not found."""
        cache = TickCache()
        
        try:
            result = await cache.get_price_tick("NONEXISTENT/USDT", "binance")
            assert result is None
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_tick_model_properties(self, clean_redis):
        """Test that Tick model has expected properties."""
        tick = create_test_tick("BTC/USDT", "binance", 50000.0, 1234.56)
        
        # Test basic properties
        assert tick.symbol == "BTC/USDT"
        assert tick.exchange == "binance"
        assert tick.price == 50000.0
        assert tick.volume == 1234.56
        assert tick.bid == 49999.0
        assert tick.ask == 50001.0
        assert tick.last == 50000.5

        # Test spread calculation
        assert tick.spread == 2.0  # ask - bid
        assert tick.spread_percentage == 0.004  # spread / mid_price * 100

    @pytest.mark.asyncio
    async def test_tick_model_to_dict_from_dict(self, clean_redis):
        """Test Tick model serialization and deserialization."""
        tick = create_test_tick("BTC/USDT", "binance", 50000.0, 1234.56)
        
        # Test to_dict
        tick_dict = tick.to_dict()
        assert isinstance(tick_dict, dict)
        assert tick_dict["symbol"] == tick.symbol
        assert tick_dict["exchange"] == tick.exchange
        assert tick_dict["price"] == tick.price

        # Test from_dict
        reconstructed_tick = Tick.from_dict(tick_dict)
        assert reconstructed_tick.symbol == tick.symbol
        assert reconstructed_tick.exchange == tick.exchange
        assert reconstructed_tick.price == tick.price
        assert reconstructed_tick.volume == tick.volume
        assert reconstructed_tick.bid == tick.bid
        assert reconstructed_tick.ask == tick.ask
        assert reconstructed_tick.last == tick.last

    @pytest.mark.asyncio
    async def test_new_methods_integration(self, clean_redis):
        """Test integration of ORM methods."""
        cache = TickCache()
        
        try:
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            
            # Test full workflow: update -> get
            # 1. Update ticker
            update_result = await cache.update_ticker("binance", tick)
            assert update_result is True

            # 2. Get ticker back
            retrieved_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert retrieved_tick is not None
            assert retrieved_tick.symbol == tick.symbol
            assert retrieved_tick.price == tick.price

            # 3. Get price tick
            price_tick = await cache.get_price_tick("BTC/USDT", "binance")
            assert price_tick is not None
            assert price_tick.price == tick.price
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_redis_key_patterns(self, clean_redis):
        """Test that Redis key patterns are consistent."""
        cache = TickCache()
        
        try:
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            
            # Update ticker
            await cache.update_ticker("binance", tick)
            
            # Verify the data exists in expected Redis key
            async with cache._cache._redis_context() as redis_client:
                key = "tickers:binance"
                stored_data = await redis_client.hget(key, tick.symbol)
                assert stored_data is not None
                
                # Verify it's JSON and has expected data
                parsed_data = json.loads(stored_data)
                assert parsed_data["symbol"] == tick.symbol
                assert parsed_data["price"] == tick.price
                assert parsed_data["exchange"] == tick.exchange
                
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_multiple_exchanges(self, clean_redis):
        """Test tickers for multiple exchanges."""
        cache = TickCache()
        
        try:
            # Create tickers for different exchanges
            binance_tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            kraken_tick = create_test_tick("BTC/USDT", "kraken", 50100.0)
            
            # Store both
            await cache.update_ticker("binance", binance_tick)
            await cache.update_ticker("kraken", kraken_tick)
            
            # Retrieve both
            binance_result = await cache.get_ticker("BTC/USDT", "binance")
            kraken_result = await cache.get_ticker("BTC/USDT", "kraken")
            
            assert binance_result is not None
            assert kraken_result is not None
            assert binance_result.price == 50000.0
            assert kraken_result.price == 50100.0
            assert binance_result.exchange == "binance"
            assert kraken_result.exchange == "kraken"
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_overwrite_ticker(self, clean_redis):
        """Test overwriting existing ticker data."""
        cache = TickCache()
        
        try:
            # Create and store initial ticker
            tick1 = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick1)
            
            # Verify initial data
            result = await cache.get_price("BTC/USDT", "binance")
            assert result == 50000.0
            
            # Overwrite with new ticker
            tick2 = create_test_tick("BTC/USDT", "binance", 51000.0)
            await cache.update_ticker("binance", tick2)
            
            # Verify updated data
            result = await cache.get_price("BTC/USDT", "binance")
            assert result == 51000.0
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_timestamp_handling(self, clean_redis):
        """Test timestamp handling in tickers."""
        cache = TickCache()
        
        try:
            # Create tick with specific timestamp
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick.time = 1672531200.0  # 2023-01-01T00:00:00Z
            
            await cache.update_ticker("binance", tick)
            
            # Retrieve and verify timestamp
            retrieved_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert retrieved_tick is not None
            assert retrieved_tick.time == 1672531200.0
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_various_symbols(self, clean_redis):
        """Test various symbol formats."""
        cache = TickCache()
        
        try:
            symbols = [
                ("BTC/USDT", "Bitcoin to USDT"),
                ("ETH/EUR", "Ethereum to Euro"),
                ("ADA/BTC", "Cardano to Bitcoin"),
                ("XRP/USD", "Ripple to USD")
            ]
            
            # Store tickers for all symbols
            for symbol, description in symbols:
                tick = create_test_tick(symbol, "binance", 1000.0)
                await cache.update_ticker("binance", tick)
            
            # Retrieve and verify all
            for symbol, description in symbols:
                result = await cache.get_ticker(symbol, "binance")
                assert result is not None
                assert result.symbol == symbol
                assert result.price == 1000.0
                
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_bid_ask_spread_calculations(self, clean_redis):
        """Test bid/ask spread calculations."""
        cache = TickCache()
        
        try:
            # Create tick with specific bid/ask
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick.bid = 49995.0
            tick.ask = 50005.0
            
            await cache.update_ticker("binance", tick)
            
            # Retrieve and verify spread
            retrieved_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert retrieved_tick is not None
            assert retrieved_tick.bid == 49995.0
            assert retrieved_tick.ask == 50005.0
            assert retrieved_tick.spread == 10.0  # ask - bid
            
        finally:
            await cache.close()

    @pytest.mark.asyncio
    async def test_exchange_objects(self, clean_redis):
        """Test using Exchange objects alongside tickers."""
        # Create exchanges
        binance = create_test_exchange("binance", 1, 1)
        kraken = create_test_exchange("kraken", 2, 2)
        
        # Verify exchange properties
        assert binance.name == "binance"
        assert binance.ex_id == 1
        assert binance.cat_ex_id == 1
        assert binance.active is True
        assert binance.api_url == "https://api.binance.com"
        
        assert kraken.name == "kraken"
        assert kraken.ex_id == 2
        assert kraken.cat_ex_id == 2