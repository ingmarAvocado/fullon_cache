"""Additional tests to achieve 100% coverage for TradesCache."""

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError


class TestTradesCacheCoverage:
    """Additional tests for complete TradesCache coverage."""

    @pytest.mark.asyncio
    async def test_push_trade_list_error_handling(self, trades_cache):
        """Test push_trade_list with Redis error."""
        # Mock the redis context to raise error on rpush
        mock_redis = AsyncMock()
        mock_redis.rpush.side_effect = RedisError("Push failed")

        with patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should log error and return 0
            result = await trades_cache.push_trade_list("BTC/USDT", "binance", {"trade": "data"})
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_all_trade_statuses_with_scan_error(self, trades_cache):
        """Test get_all_trade_statuses when scan fails."""
        # Mock the redis context to raise error
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = RedisError("Scan failed")

        with patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should return empty dict on error
            result = await trades_cache.get_all_trade_statuses()
            assert result == {}

    @pytest.mark.asyncio
    async def test_get_all_trade_statuses_skip_pattern(self, trades_cache):
        """Test get_all_trade_statuses skips non-matching patterns."""
        # Create keys with different patterns
        await trades_cache.update_trade_status("test1")
        await trades_cache._cache.set("OTHER:STATUS:test2", "value")

        # Should only return TRADE:STATUS keys
        result = await trades_cache.get_all_trade_statuses()
        assert all(key.startswith("TRADE:STATUS:") for key in result)

    @pytest.mark.asyncio
    async def test_get_trade_status_keys_with_error(self, trades_cache):
        """Test get_trade_status_keys with scan error."""
        # Mock the redis context to raise error
        mock_redis = AsyncMock()
        mock_redis.scan.side_effect = RedisError("Scan failed")

        with patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should return empty list on error
            keys = await trades_cache.get_trade_status_keys()
            assert keys == []

    @pytest.mark.asyncio
    async def test_push_my_trades_list_with_dict(self, trades_cache):
        """Test push_my_trades_list with dictionary trade data."""
        trade_dict = {
            "trade_id": "TRD123",
            "price": 50000.0,
            "volume": 0.1
        }

        result = await trades_cache.push_my_trades_list("user123", "binance", trade_dict)
        assert result > 0

    @pytest.mark.asyncio
    async def test_pop_my_trade_blocking_with_result(self, trades_cache):
        """Test pop_my_trade with blocking and immediate result."""
        # Push a trade first
        await trades_cache.push_my_trades_list("user123", "binance", {"trade": "data"})

        # Pop with timeout should return immediately
        result = await trades_cache.pop_my_trade("user123", "binance", timeout=5)
        assert result is not None
        assert result["trade"] == "data"

    @pytest.mark.asyncio
    async def test_pop_my_trade_timeout_error_handling(self, trades_cache):
        """Test pop_my_trade handles TimeoutError in error message."""
        with patch.object(trades_cache._cache, 'blpop', side_effect=TimeoutError()):
            # Should return None without logging
            result = await trades_cache.pop_my_trade("user123", "binance", timeout=1)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_trades_list_with_error(self, trades_cache):
        """Test get_trades_list error handling."""
        with patch.object(trades_cache._cache, 'lrange', side_effect=RedisError("Range failed")):
            result = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert result == []

    @pytest.mark.asyncio
    async def test_get_trades_list_delete_error(self, trades_cache):
        """Test get_trades_list when delete fails."""
        # Mock redis context with successful lrange but failed delete
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = [b'{"trade": "data"}']
        mock_redis.delete.side_effect = RedisError("Delete failed")

        with patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_redis
            # Should return empty list on error
            result = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert len(result) == 0
