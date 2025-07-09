"""Comprehensive tests for TickCache using real Redis and objects."""

import pytest
from fullon_orm.models import Tick

from fullon_cache.tick_cache import TickCache


def create_test_tick(symbol="BTC/USDT", exchange="binance", price=50000.0, volume=1234.56):
    """Factory function to create test Tick objects."""
    return Tick(
        symbol=symbol,
        exchange=exchange,
        price=price,
        volume=volume,
        time=1672531200.0,  # 2023-01-01T00:00:00Z
        bid=price - 1.0,
        ask=price + 1.0,
        last=price
    )


class TestTickCache:
    """Test cases for TickCache functionality."""

    @pytest.mark.asyncio
    async def test_init(self, clean_redis):
        """Test TickCache initialization."""
        cache = TickCache()
        assert cache._cache is not None
        await cache._cache.close()

    @pytest.mark.asyncio
    async def test_update_and_get_ticker(self, clean_redis):
        """Test updating and retrieving ticker data."""
        cache = TickCache()
        
        try:
            # Create and update ticker
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            result = await cache.update_ticker("binance", tick)
            assert result is True
            
            # Retrieve ticker
            retrieved_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert retrieved_tick is not None
            assert retrieved_tick.symbol == "BTC/USDT"
            assert retrieved_tick.exchange == "binance"
            assert retrieved_tick.price == 50000.0
            assert retrieved_tick.volume == 1234.56
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_ticker_not_found(self, clean_redis):
        """Test getting non-existent ticker."""
        cache = TickCache()
        
        try:
            # Try to get non-existent ticker
            result = await cache.get_ticker("NONEXISTENT/USDT", "binance")
            assert result is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_price_with_exchange(self, clean_redis):
        """Test get_price with specific exchange."""
        cache = TickCache()
        
        try:
            # Setup - create and store a real ticker
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick)

            # Test
            result = await cache.get_price("BTC/USDT", "binance")
            assert result == 50000.0
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_price_not_found(self, clean_redis):
        """Test get_price when ticker not found."""
        cache = TickCache()
        
        try:
            # Test with non-existent ticker
            result = await cache.get_price("NONEXISTENT/USDT", "binance")
            assert result == 0
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_price_without_exchange(self, clean_redis):
        """Test get_price without specifying exchange (will try database)."""
        cache = TickCache()
        
        try:
            # Test with no data in cache - will try database and return 0
            result = await cache.get_price("BTC/USDT")
            assert result == 0
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_del_exchange_ticker(self, clean_redis):
        """Test deleting exchange ticker data."""
        cache = TickCache()
        
        try:
            # Setup - create and store tickers
            tick1 = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick2 = create_test_tick("ETH/USDT", "binance", 3000.0)
            await cache.update_ticker("binance", tick1)
            await cache.update_ticker("binance", tick2)
            
            # Verify tickers exist
            assert await cache.get_ticker("BTC/USDT", "binance") is not None
            assert await cache.get_ticker("ETH/USDT", "binance") is not None
            
            # Delete exchange tickers
            result = await cache.del_exchange_ticker("binance")
            assert result >= 0  # Should return number of deleted keys
            
            # Verify tickers are gone
            assert await cache.get_ticker("BTC/USDT", "binance") is None
            assert await cache.get_ticker("ETH/USDT", "binance") is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_ticker_any(self, clean_redis):
        """Test get_ticker_any method."""
        cache = TickCache()
        
        try:
            # Setup - create and store ticker
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick)

            # Test get_ticker_any
            result = await cache.get_ticker_any("BTC/USDT")
            assert result == 50000.0
            
            # Test with non-existent ticker
            result = await cache.get_ticker_any("NONEXISTENT/USDT")
            assert result == 0
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_price_tick(self, clean_redis):
        """Test get_price_tick method."""
        cache = TickCache()
        
        try:
            # Setup - create and store ticker
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            await cache.update_ticker("binance", tick)

            # Test get_price_tick
            result = await cache.get_price_tick("BTC/USDT", "binance")
            assert result is not None
            assert result.price == 50000.0
            assert result.symbol == "BTC/USDT"
            
            # Test with non-existent ticker
            result = await cache.get_price_tick("NONEXISTENT/USDT", "binance")
            assert result is None
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_get_tickers(self, clean_redis):
        """Test get_tickers method."""
        cache = TickCache()
        
        try:
            # Setup - create and store multiple tickers
            tick1 = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick2 = create_test_tick("ETH/USDT", "binance", 3000.0)
            await cache.update_ticker("binance", tick1)
            await cache.update_ticker("binance", tick2)

            # Test get_tickers
            result = await cache.get_tickers("binance")
            assert len(result) == 2
            
            # Verify ticker data
            symbols = [ticker.symbol for ticker in result]
            assert "BTC/USDT" in symbols
            assert "ETH/USDT" in symbols
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_multiple_exchanges(self, clean_redis):
        """Test operations with multiple exchanges."""
        cache = TickCache()
        
        try:
            # Setup - create tickers for different exchanges
            tick_binance = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick_kraken = create_test_tick("BTC/USDT", "kraken", 50100.0)
            await cache.update_ticker("binance", tick_binance)
            await cache.update_ticker("kraken", tick_kraken)

            # Test getting specific exchange prices
            binance_price = await cache.get_price("BTC/USDT", "binance")
            kraken_price = await cache.get_price("BTC/USDT", "kraken")
            
            assert binance_price == 50000.0
            assert kraken_price == 50100.0
            
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_tick_properties(self, clean_redis):
        """Test that Tick model properties work correctly."""
        cache = TickCache()
        
        try:
            # Create tick with specific bid/ask
            tick = create_test_tick("BTC/USDT", "binance", 50000.0)
            tick.bid = 49999.0
            tick.ask = 50001.0
            
            await cache.update_ticker("binance", tick)
            
            # Retrieve and verify properties
            retrieved_tick = await cache.get_ticker("BTC/USDT", "binance")
            assert retrieved_tick is not None
            assert retrieved_tick.bid == 49999.0
            assert retrieved_tick.ask == 50001.0
            
            # Test spread calculations if available
            if hasattr(retrieved_tick, 'spread'):
                assert retrieved_tick.spread == 2.0  # ask - bid
                
        finally:
            await cache._cache.close()

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
            await cache._cache.close()

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
            await cache._cache.close()