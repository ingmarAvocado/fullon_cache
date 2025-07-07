"""Tests for OHLCVCache functionality."""

import json
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
class TestOHLCVCache:
    """Test cases for OHLCVCache."""

    async def test_update_ohlcv_bars_success(self, ohlcv_cache):
        """Test updating OHLCV bars successfully."""
        bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
            [1234568010, 50100, 50200, 50050, 50150, 3456.78],
        ]

        # Should not raise any exception
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars)

        # Verify bars were stored
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 3)
        assert len(retrieved) == 3
        assert retrieved[0] == bars[0]
        assert retrieved[1] == bars[1]
        assert retrieved[2] == bars[2]

    async def test_update_ohlcv_bars_empty_list(self, ohlcv_cache):
        """Test updating with empty bar list."""
        # Should not raise exception
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", [])

        # Should have no bars
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 10)
        assert len(retrieved) == 0

    async def test_update_ohlcv_bars_invalid_format(self, ohlcv_cache):
        """Test updating with invalid bar format."""
        bars = [
            [1234567890, 50000, 50100],  # Too short
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],  # Valid
            "not a list",  # Invalid type
            [1234568010, 50100, 50200, 50050, 50150, 3456.78],  # Valid
        ]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars)

        # Only valid bars should be stored
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 10)
        assert len(retrieved) == 2
        assert retrieved[0] == [1234567950, 50050, 50150, 50000, 50100, 2345.67]
        assert retrieved[1] == [1234568010, 50100, 50200, 50050, 50150, 3456.78]

    async def test_update_ohlcv_bars_with_error(self, ohlcv_cache):
        """Test update_ohlcv_bars handles errors gracefully."""
        bars = [[1234567890, 50000, 50100, 49900, 50050, 1234.56]]

        with patch.object(ohlcv_cache._cache, 'rpush') as mock_rpush:
            mock_rpush.side_effect = Exception("Redis error")

            # Should not raise exception
            await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars)

    async def test_update_ohlcv_bars_max_limit(self, ohlcv_cache):
        """Test that only 10000 most recent bars are kept."""
        # Create more than 10000 bars
        bars = []
        for i in range(100):  # Add in batches to test trimming
            batch = []
            for j in range(110):
                timestamp = 1234567890 + (i * 110 + j) * 60
                batch.append([timestamp, 50000, 50100, 49900, 50050, 1000])
            await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", batch)

        # Should only keep 10000 most recent
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 11000)
        assert len(retrieved) == 10000

        # Verify we have the most recent bars
        first_timestamp = retrieved[0][0]
        last_timestamp = retrieved[-1][0]
        assert last_timestamp > first_timestamp

    async def test_get_latest_ohlcv_bars_success(self, ohlcv_cache):
        """Test getting latest OHLCV bars."""
        bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
            [1234568010, 50100, 50200, 50050, 50150, 3456.78],
            [1234568070, 50150, 50250, 50100, 50200, 4567.89],
            [1234568130, 50200, 50300, 50150, 50250, 5678.90],
        ]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", bars)

        # Get last 3 bars
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 3)
        assert len(retrieved) == 3
        assert retrieved[0] == bars[2]  # Third bar
        assert retrieved[1] == bars[3]  # Fourth bar
        assert retrieved[2] == bars[4]  # Fifth bar (most recent)

    async def test_get_latest_ohlcv_bars_more_than_exist(self, ohlcv_cache):
        """Test getting more bars than exist."""
        bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
        ]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "5m", bars)

        # Request 10 but only 2 exist
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "5m", 10)
        assert len(retrieved) == 2
        assert retrieved[0] == bars[0]
        assert retrieved[1] == bars[1]

    async def test_get_latest_ohlcv_bars_nonexistent_symbol(self, ohlcv_cache):
        """Test getting bars for non-existent symbol."""
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("NONEXISTENT", "1h", 10)
        assert len(retrieved) == 0

    async def test_get_latest_ohlcv_bars_with_invalid_json(self, ohlcv_cache):
        """Test getting bars when Redis contains invalid JSON."""
        # Manually insert invalid JSON
        key = "ohlcv:BTCUSD:1h"
        await ohlcv_cache._cache.rpush(key, "invalid{json}", '{"also": "invalid"')

        # Also add a valid bar
        valid_bar = [1234567890, 50000, 50100, 49900, 50050, 1234.56]
        await ohlcv_cache._cache.rpush(key, json.dumps(valid_bar))

        # Should only return valid bars
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 10)
        assert len(retrieved) == 1
        assert retrieved[0] == valid_bar

    async def test_get_latest_ohlcv_bars_with_error(self, ohlcv_cache):
        """Test get_latest_ohlcv_bars handles errors gracefully."""
        with patch.object(ohlcv_cache._cache, 'lrange') as mock_lrange:
            mock_lrange.side_effect = Exception("Redis error")

            retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 10)
            assert retrieved == []

    async def test_different_timeframes(self, ohlcv_cache):
        """Test storing bars for different timeframes."""
        bars_1m = [[1234567890, 50000, 50100, 49900, 50050, 100]]
        bars_5m = [[1234567890, 50000, 50200, 49800, 50150, 500]]
        bars_1h = [[1234567890, 50000, 50500, 49500, 50400, 6000]]
        bars_1d = [[1234567890, 50000, 51000, 49000, 50800, 144000]]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", bars_1m)
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "5m", bars_5m)
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars_1h)
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1d", bars_1d)

        # Each timeframe should have its own data
        retrieved_1m = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 1)
        retrieved_5m = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "5m", 1)
        retrieved_1h = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 1)
        retrieved_1d = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1d", 1)

        assert retrieved_1m[0] == bars_1m[0]
        assert retrieved_5m[0] == bars_5m[0]
        assert retrieved_1h[0] == bars_1h[0]
        assert retrieved_1d[0] == bars_1d[0]

    async def test_different_symbols(self, ohlcv_cache):
        """Test storing bars for different symbols."""
        bars_btc = [[1234567890, 50000, 50100, 49900, 50050, 1234.56]]
        bars_eth = [[1234567890, 3000, 3010, 2990, 3005, 234.56]]
        bars_bnb = [[1234567890, 400, 401, 399, 400.5, 34.56]]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars_btc)
        await ohlcv_cache.update_ohlcv_bars("ETHUSD", "1h", bars_eth)
        await ohlcv_cache.update_ohlcv_bars("BNBUSD", "1h", bars_bnb)

        # Each symbol should have its own data
        retrieved_btc = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 1)
        retrieved_eth = await ohlcv_cache.get_latest_ohlcv_bars("ETHUSD", "1h", 1)
        retrieved_bnb = await ohlcv_cache.get_latest_ohlcv_bars("BNBUSD", "1h", 1)

        assert retrieved_btc[0] == bars_btc[0]
        assert retrieved_eth[0] == bars_eth[0]
        assert retrieved_bnb[0] == bars_bnb[0]

    async def test_symbol_without_slash(self, ohlcv_cache):
        """Test handling symbols without slashes."""
        bars = [[1234567890, 50000, 50100, 49900, 50050, 1234.56]]

        # These symbols don't have slashes
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", bars)
        await ohlcv_cache.update_ohlcv_bars("ETHUSD", "1h", bars)

        retrieved_btc = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 1)
        retrieved_eth = await ohlcv_cache.get_latest_ohlcv_bars("ETHUSD", "1h", 1)

        assert len(retrieved_btc) == 1
        assert len(retrieved_eth) == 1

    async def test_append_order_preservation(self, ohlcv_cache):
        """Test that bar order is preserved."""
        # Add bars in multiple batches
        batch1 = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
        ]
        batch2 = [
            [1234568010, 50100, 50200, 50050, 50150, 3456.78],
            [1234568070, 50150, 50250, 50100, 50200, 4567.89],
        ]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", batch1)
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", batch2)

        # Get all bars
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 4)

        # Should be in chronological order
        assert len(retrieved) == 4
        assert retrieved[0] == batch1[0]
        assert retrieved[1] == batch1[1]
        assert retrieved[2] == batch2[0]
        assert retrieved[3] == batch2[1]

    async def test_numeric_types(self, ohlcv_cache):
        """Test handling different numeric types."""
        bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],  # All floats
            [1234567950, 50050.5, 50150.5, 50000.5, 50100.5, 2345.67],  # Decimals
            [1234568010, "50100", "50200", "50050", "50150", "3456.78"],  # Strings are accepted in simplified version
        ]

        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", bars)

        # All bars should be stored (simplified version doesn't validate types)
        retrieved = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 3)
        assert len(retrieved) == 3

    async def test_integration_scenario(self, ohlcv_cache):
        """Test a complete usage scenario."""
        # 1. Initial bars
        initial_bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
            [1234568010, 50100, 50200, 50050, 50150, 3456.78],
        ]
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", initial_bars)

        # 2. Add more bars
        new_bars = [
            [1234568070, 50150, 50250, 50100, 50200, 4567.89],
            [1234568130, 50200, 50300, 50150, 50250, 5678.90],
        ]
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1m", new_bars)

        # 3. Get recent bars
        recent = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 3)
        assert len(recent) == 3
        assert recent[0] == initial_bars[2]  # Third initial bar
        assert recent[1] == new_bars[0]      # First new bar
        assert recent[2] == new_bars[1]      # Second new bar

        # 4. Different timeframe for same symbol
        hourly_bar = [[1234567890, 50000, 50300, 49900, 50250, 15000]]
        await ohlcv_cache.update_ohlcv_bars("BTCUSD", "1h", hourly_bar)

        hourly = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1h", 1)
        assert len(hourly) == 1
        assert hourly[0] == hourly_bar[0]

        # 5. Verify 1m data still intact
        minute_bars = await ohlcv_cache.get_latest_ohlcv_bars("BTCUSD", "1m", 5)
        assert len(minute_bars) == 5
