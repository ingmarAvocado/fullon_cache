"""Tests for BotCache functionality."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestBotCache:
    """Test cases for BotCache."""

    async def test_is_blocked_returns_bot_id(self, bot_cache):
        """Test is_blocked returns bot ID when blocked."""
        # Block an exchange/symbol
        await bot_cache.block_exchange("binance", "BTC/USDT", "bot_123")

        # Check if blocked
        result = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert result == "bot_123"

    async def test_is_blocked_returns_empty_string_when_not_blocked(self, bot_cache):
        """Test is_blocked returns empty string when not blocked."""
        result = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert result == ""

    async def test_is_blocked_with_error(self, bot_cache):
        """Test is_blocked handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hget.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.is_blocked("binance", "BTC/USDT")
            assert result == ""

    async def test_get_blocks_empty(self, bot_cache):
        """Test get_blocks returns empty list when no blocks."""
        result = await bot_cache.get_blocks()
        assert result == []

    async def test_get_blocks_with_data(self, bot_cache):
        """Test get_blocks returns all blocked pairs."""
        # Block multiple exchange/symbol pairs
        await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
        await bot_cache.block_exchange("kraken", "ETH/USD", "bot_2")
        await bot_cache.block_exchange("binance", "ETH/USDT", "bot_3")

        result = await bot_cache.get_blocks()
        assert len(result) == 3

        # Check structure
        expected_keys = {"ex_id", "symbol", "bot"}
        for block in result:
            assert set(block.keys()) == expected_keys

        # Verify data
        blocks_dict = {f"{b['ex_id']}:{b['symbol']}": b['bot'] for b in result}
        assert blocks_dict["binance:BTC/USDT"] == "bot_1"
        assert blocks_dict["kraken:ETH/USD"] == "bot_2"
        assert blocks_dict["binance:ETH/USDT"] == "bot_3"

    async def test_get_blocks_with_invalid_format(self, bot_cache):
        """Test get_blocks handles invalid field formats."""
        # Manually insert invalid data
        async with bot_cache._cache._redis_context() as redis_client:
            key = bot_cache._cache._make_key("block_exchange")
            # Field without colon separator
            await redis_client.hset(key, "invalid_field", "bot_1")
            # Valid field
            await redis_client.hset(key, "binance:BTC/USDT", "bot_2")

        result = await bot_cache.get_blocks()
        # Should only return valid entries
        assert len(result) == 1
        assert result[0]["ex_id"] == "binance"
        assert result[0]["symbol"] == "BTC/USDT"

    async def test_get_blocks_with_error(self, bot_cache):
        """Test get_blocks handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hgetall.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.get_blocks()
            assert result == []

    async def test_block_exchange_success(self, bot_cache):
        """Test block_exchange blocks successfully."""
        result = await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
        assert result is True

        # Verify it's blocked
        blocked_by = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert blocked_by == "bot_1"

    async def test_block_exchange_with_int_bot_id(self, bot_cache):
        """Test block_exchange works with integer bot ID."""
        result = await bot_cache.block_exchange("binance", "BTC/USDT", 123)
        assert result is True

        # Verify it's blocked with string conversion
        blocked_by = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert blocked_by == "123"

    async def test_block_exchange_update_existing(self, bot_cache):
        """Test block_exchange updates existing block."""
        # First block
        await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
        # Update with different bot
        result = await bot_cache.block_exchange("binance", "BTC/USDT", "bot_2")
        assert result is True

        # Verify updated
        blocked_by = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert blocked_by == "bot_2"

    async def test_block_exchange_with_error(self, bot_cache):
        """Test block_exchange handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hset.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
            assert result is False

    async def test_unblock_exchange_success(self, bot_cache):
        """Test unblock_exchange removes block."""
        # First block
        await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")

        # Then unblock
        result = await bot_cache.unblock_exchange("binance", "BTC/USDT")
        assert result is True

        # Verify unblocked
        blocked_by = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert blocked_by == ""

    async def test_unblock_exchange_nonexistent(self, bot_cache):
        """Test unblock_exchange on non-existent block."""
        result = await bot_cache.unblock_exchange("binance", "BTC/USDT")
        assert result is False

    async def test_unblock_exchange_with_error(self, bot_cache):
        """Test unblock_exchange handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hdel.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.unblock_exchange("binance", "BTC/USDT")
            assert result is False

    async def test_is_opening_position_true(self, bot_cache):
        """Test is_opening_position returns True when marked."""
        # Mark opening position
        await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")

        result = await bot_cache.is_opening_position("binance", "BTC/USDT")
        assert result is True

    async def test_is_opening_position_false(self, bot_cache):
        """Test is_opening_position returns False when not marked."""
        result = await bot_cache.is_opening_position("binance", "BTC/USDT")
        assert result is False

    async def test_is_opening_position_with_error(self, bot_cache):
        """Test is_opening_position handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hget.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.is_opening_position("binance", "BTC/USDT")
            assert result is False

    async def test_mark_opening_position_success(self, bot_cache):
        """Test mark_opening_position marks successfully."""
        result = await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")
        assert result is True

        # Verify marked
        is_opening = await bot_cache.is_opening_position("binance", "BTC/USDT")
        assert is_opening is True

    async def test_mark_opening_position_with_int_bot_id(self, bot_cache):
        """Test mark_opening_position with integer bot ID."""
        result = await bot_cache.mark_opening_position("binance", "BTC/USDT", 123)
        assert result is True

        # Verify data format
        value = await bot_cache._cache.hget("opening_position", "binance:BTC/USDT")
        assert value is not None
        assert value.startswith("123:")

    async def test_mark_opening_position_update_existing(self, bot_cache):
        """Test mark_opening_position updates existing mark."""
        # First mark
        await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")
        # Update with different bot
        result = await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_2")
        assert result is True

        # Verify updated
        value = await bot_cache._cache.hget("opening_position", "binance:BTC/USDT")
        assert value.startswith("bot_2:")

    async def test_mark_opening_position_with_error(self, bot_cache):
        """Test mark_opening_position handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hset.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")
            assert result is False

    async def test_unmark_opening_position_success(self, bot_cache):
        """Test unmark_opening_position removes mark."""
        # First mark
        await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")

        # Then unmark
        result = await bot_cache.unmark_opening_position("binance", "BTC/USDT")
        assert result is True

        # Verify unmarked
        is_opening = await bot_cache.is_opening_position("binance", "BTC/USDT")
        assert is_opening is False

    async def test_unmark_opening_position_nonexistent(self, bot_cache):
        """Test unmark_opening_position on non-existent mark."""
        result = await bot_cache.unmark_opening_position("binance", "BTC/USDT")
        assert result is False

    async def test_unmark_opening_position_with_error(self, bot_cache):
        """Test unmark_opening_position handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hdel.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.unmark_opening_position("binance", "BTC/USDT")
            assert result is False

    async def test_update_bot_success(self, bot_cache):
        """Test update_bot updates bot status."""
        bot_data = {
            "feed_1": {
                "status": "running",
                "symbols": ["BTC/USDT"],
                "performance": {"pnl": 100.0}
            },
            "feed_2": {
                "status": "paused",
                "symbols": ["ETH/USDT"]
            }
        }

        result = await bot_cache.update_bot("bot_1", bot_data)
        assert result is True

        # Verify stored
        bots = await bot_cache.get_bots()
        assert "bot_1" in bots
        assert "feed_1" in bots["bot_1"]
        assert "feed_2" in bots["bot_1"]
        assert "timestamp" in bots["bot_1"]["feed_1"]
        assert "timestamp" in bots["bot_1"]["feed_2"]

    async def test_update_bot_non_dict_values(self, bot_cache):
        """Test update_bot handles non-dict feed values."""
        bot_data = {
            "feed_1": {"status": "running"},
            "feed_2": "invalid_value",  # Non-dict value
            "feed_3": 123  # Another non-dict
        }

        result = await bot_cache.update_bot("bot_1", bot_data)
        assert result is True

        # Verify stored
        bots = await bot_cache.get_bots()
        assert "bot_1" in bots
        # Dict feed should have timestamp
        assert "timestamp" in bots["bot_1"]["feed_1"]
        # Non-dict feeds should not have timestamp
        assert bots["bot_1"]["feed_2"] == "invalid_value"
        assert bots["bot_1"]["feed_3"] == 123

    async def test_update_bot_with_error(self, bot_cache):
        """Test update_bot handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hset.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.update_bot("bot_1", {"feed_1": {"status": "running"}})
            assert result is False

    async def test_del_bot_success(self, bot_cache):
        """Test del_bot deletes bot status."""
        # First add a bot
        await bot_cache.update_bot("bot_1", {"feed_1": {"status": "running"}})

        # Then delete
        result = await bot_cache.del_bot("bot_1")
        assert result is True

        # Verify deleted
        bots = await bot_cache.get_bots()
        assert "bot_1" not in bots

    async def test_del_bot_nonexistent(self, bot_cache):
        """Test del_bot on non-existent bot."""
        result = await bot_cache.del_bot("bot_999")
        assert result is False

    async def test_del_bot_with_error(self, bot_cache):
        """Test del_bot handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hdel.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.del_bot("bot_1")
            assert result is False

    async def test_del_status_success(self, bot_cache):
        """Test del_status deletes all bot statuses."""
        # Add multiple bots
        await bot_cache.update_bot("bot_1", {"feed_1": {"status": "running"}})
        await bot_cache.update_bot("bot_2", {"feed_2": {"status": "paused"}})
        await bot_cache.update_bot("bot_3", {"feed_3": {"status": "stopped"}})

        # Delete all
        result = await bot_cache.del_status()
        assert result is True

        # Verify all deleted
        bots = await bot_cache.get_bots()
        assert len(bots) == 0

    async def test_del_status_empty(self, bot_cache):
        """Test del_status when no statuses exist."""
        result = await bot_cache.del_status()
        assert result is False

    async def test_del_status_with_error(self, bot_cache):
        """Test del_status handles errors gracefully."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.delete.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            result = await bot_cache.del_status()
            assert result is False

    async def test_get_bots_empty(self, bot_cache):
        """Test get_bots returns empty dict when no bots."""
        result = await bot_cache.get_bots()
        assert result == {}

    async def test_get_bots_with_data(self, bot_cache):
        """Test get_bots returns all bot statuses."""
        # Add multiple bots
        bot1_data = {
            "feed_1": {"status": "running", "symbols": ["BTC/USDT"]},
            "feed_2": {"status": "paused", "symbols": ["ETH/USDT"]}
        }
        bot2_data = {
            "feed_3": {"status": "stopped", "symbols": ["XRP/USDT"]}
        }

        await bot_cache.update_bot("bot_1", bot1_data)
        await bot_cache.update_bot("bot_2", bot2_data)

        result = await bot_cache.get_bots()
        assert len(result) == 2
        assert "bot_1" in result
        assert "bot_2" in result
        assert "feed_1" in result["bot_1"]
        assert "feed_3" in result["bot_2"]

    async def test_get_bots_with_invalid_json(self, bot_cache):
        """Test get_bots handles invalid JSON data."""
        # Manually insert invalid JSON
        async with bot_cache._cache._redis_context() as redis_client:
            key = bot_cache._cache._make_key("bot_status")
            # Valid bot
            await redis_client.hset(key, "bot_1", json.dumps({"feed_1": {"status": "running"}}))
            # Invalid JSON
            await redis_client.hset(key, "bot_2", "invalid{json}")

        result = await bot_cache.get_bots()
        assert len(result) == 2
        assert "bot_1" in result
        assert "bot_2" in result
        assert "feed_1" in result["bot_1"]
        assert result["bot_2"] == {"error": "Invalid JSON"}

    async def test_get_bots_with_error(self, bot_cache):
        """Test get_bots raises on Redis error."""
        with patch.object(bot_cache._cache, '_redis_context') as mock_context:
            mock_redis = AsyncMock()
            mock_redis.hgetall.side_effect = Exception("Redis error")
            mock_context.return_value.__aenter__.return_value = mock_redis

            with pytest.raises(Exception) as exc_info:
                await bot_cache.get_bots()
            assert "Redis error" in str(exc_info.value)

    async def test_bytes_decoding(self, bot_cache):
        """Test proper bytes decoding throughout."""
        # Test with various Unicode characters
        await bot_cache.block_exchange("binance", "BTC/USDT", "bot_🤖")
        await bot_cache.update_bot("bot_émoji", {"feed_1": {"status": "running", "symbol": "BTC/€"}})

        # Verify is_blocked decodes properly
        result = await bot_cache.is_blocked("binance", "BTC/USDT")
        assert result == "bot_🤖"

        # Verify get_blocks decodes properly
        blocks = await bot_cache.get_blocks()
        assert len(blocks) == 1
        assert blocks[0]["bot"] == "bot_🤖"

        # Verify get_bots decodes properly
        bots = await bot_cache.get_bots()
        assert "bot_émoji" in bots
        assert bots["bot_émoji"]["feed_1"]["symbol"] == "BTC/€"

    async def test_timestamp_format(self, bot_cache):
        """Test timestamp format in update_bot."""
        bot_data = {"feed_1": {"status": "running"}}
        await bot_cache.update_bot("bot_1", bot_data)

        bots = await bot_cache.get_bots()
        timestamp = bots["bot_1"]["feed_1"]["timestamp"]

        # Verify it's a valid ISO format timestamp
        # Should be able to parse it
        dt = datetime.fromisoformat(timestamp.replace('+0000', '+00:00'))
        assert dt.tzinfo is not None

    async def test_integration_scenario(self, bot_cache):
        """Test a complete integration scenario."""
        # Bot 1 blocks exchange/symbol
        assert await bot_cache.block_exchange("binance", "BTC/USDT", "bot_1")
        assert await bot_cache.is_blocked("binance", "BTC/USDT") == "bot_1"

        # Bot 1 marks opening position
        assert await bot_cache.mark_opening_position("binance", "BTC/USDT", "bot_1")
        assert await bot_cache.is_opening_position("binance", "BTC/USDT") is True

        # Update bot status
        assert await bot_cache.update_bot("bot_1", {
            "feed_1": {"status": "trading", "symbol": "BTC/USDT"}
        })

        # Bot 2 tries to block same symbol (should succeed but override)
        assert await bot_cache.block_exchange("binance", "BTC/USDT", "bot_2")
        assert await bot_cache.is_blocked("binance", "BTC/USDT") == "bot_2"

        # Get all blocks
        blocks = await bot_cache.get_blocks()
        assert len(blocks) == 1
        assert blocks[0]["bot"] == "bot_2"

        # Unmark position
        assert await bot_cache.unmark_opening_position("binance", "BTC/USDT")
        assert await bot_cache.is_opening_position("binance", "BTC/USDT") is False

        # Unblock exchange
        assert await bot_cache.unblock_exchange("binance", "BTC/USDT")
        assert await bot_cache.is_blocked("binance", "BTC/USDT") == ""

        # Clean up bot
        assert await bot_cache.del_bot("bot_1")
        bots = await bot_cache.get_bots()
        assert "bot_1" not in bots
