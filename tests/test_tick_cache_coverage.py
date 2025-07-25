"""Additional tests to achieve 100% coverage for TickCache."""

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError

from fullon_cache import TickCache


class TestTickCacheCoverage:
    """Additional tests for complete coverage."""

    # NOTE: The Ticker class tests have been removed as the Ticker class
    # no longer exists in the current implementation. The TickCache now
    # works with dictionaries and Tick ORM models instead.

    @pytest.mark.asyncio
    async def test_tick_cache_error_handling(self):
        """Test error handling in TickCache methods."""
        cache = TickCache()

        # Mock Redis errors
        with patch.object(cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hget.side_effect = RedisError("Connection failed")
            mock_context.return_value.__aenter__.return_value = mock_redis

            # Test get_ticker with Redis error
            result = await cache.get_ticker("BTC/USDT", "binance")
            assert result is None

    @pytest.mark.asyncio
    async def test_update_ticker_edge_cases(self):
        """Test update_ticker with edge cases."""
        cache = TickCache()

        # Test with empty values dict
        result = await cache.update_ticker("BTC/USDT", "binance", {})
        assert result == 1  # Should still succeed

        # Test with None values
        result = await cache.update_ticker("BTC/USDT", "binance", {
            "price": None,
            "volume": None,
            "time": None
        })
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_all_tickers_error_handling(self):
        """Test get_tickers with Redis errors."""
        cache = TickCache()

        with patch.object(cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hgetall.side_effect = RedisError("Connection failed")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await cache.get_tickers()
            assert result == []

    @pytest.mark.asyncio
    async def test_subscribe_get_next_ticker_timeout(self):
        """Test get_next_ticker with timeout."""
        cache = TickCache()

        # Mock the subscribe method to return an empty async generator
        async def empty_generator():
            # Don't yield anything to simulate timeout
            if False:
                yield

        with patch.object(cache._cache, 'subscribe', return_value=empty_generator()):
            # This should return (0, None) since no messages are yielded
            result = await cache.get_next_ticker("BTC/USDT", "binance")
            assert result == (0, None)
