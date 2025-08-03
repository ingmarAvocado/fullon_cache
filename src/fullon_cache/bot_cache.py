"""Bot coordination and exchange blocking cache.

This module provides simplified bot coordination for trading systems,
managing exchange/symbol blocking and bot status tracking.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fullon_log import get_component_logger

from .base_cache import BaseCache

logger = get_component_logger("fullon.cache.bot")


class BotCache:
    """Cache for bot coordination and exchange blocking.
    
    This cache provides mechanisms for coordinating multiple trading bots,
    preventing them from interfering with each other when trading the same
    symbols on the same exchanges.
    
    Features:
        - Exchange/symbol blocking to prevent conflicts
        - Bot status tracking with feed structure
        - Position opening state management
        
    Example:
        cache = BotCache()
        
        # Block an exchange/symbol for a bot
        await cache.block_exchange("binance", "BTC/USDT", "bot_1")
        
        # Check if blocked
        bot_id = await cache.is_blocked("binance", "BTC/USDT")
        if bot_id:
            print(f"Blocked by bot {bot_id}")
        
        # Update bot status
        await cache.update_bot("bot_1", {
            "feed_1": {"status": "running", "symbols": ["BTC/USDT"]},
            "feed_2": {"status": "paused", "symbols": ["ETH/USDT"]}
        })
    """

    def __init__(self):
        """Initialize the bot cache."""
        self._cache = BaseCache()

    async def is_blocked(self, ex_id: str, symbol: str) -> str:
        """Check if exchange/symbol is blocked.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            
        Returns:
            Bot ID if blocked, empty string otherwise
        """
        try:
            field = f"{ex_id}:{symbol}"
            value = await self._cache.hget("block_exchange", field)
            return value if value else ""
        except Exception as e:
            logger.error(f"Error checking if blocked: {e}")
            return ""

    async def get_blocks(self) -> list[dict[str, str]]:
        """Get all blocked exchange/symbol pairs.
        
        Returns:
            List of dicts with ex_id, symbol, and bot info
        """
        blocks = []
        try:
            data = await self._cache.hgetall("block_exchange")

            for field, value in data.items():
                # Parse field
                if ":" in field:
                    ex_id, symbol = field.split(":", 1)
                    blocks.append({
                        "ex_id": ex_id,
                        "symbol": symbol,
                        "bot": value
                    })
        except Exception as e:
            logger.error(f"Error getting blocks: {e}")

        return blocks

    async def block_exchange(self, ex_id: str, symbol: str, bot_id: str | int) -> bool:
        """Block exchange/symbol pair.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            bot_id: Bot ID to assign the block
            
        Returns:
            True if blocked successfully
        """
        try:
            field = f"{ex_id}:{symbol}"
            value = str(bot_id)
            # Set in hash (returns 1 if new, 0 if updated)
            result = await self._cache.hset("block_exchange", field, value)
            return True  # Success regardless of new or update
        except Exception as e:
            logger.error(f"Error blocking exchange: {e}")
            return False

    async def unblock_exchange(self, ex_id: str, symbol: str) -> bool:
        """Unblock exchange/symbol pair.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            
        Returns:
            True if unblocked successfully
        """
        try:
            field = f"{ex_id}:{symbol}"
            # Delete from hash
            deleted = await self._cache.hdel("block_exchange", field)
            return deleted > 0
        except Exception as e:
            logger.error(f"Error unblocking exchange: {e}")
            return False

    async def is_opening_position(self, ex_id: str, symbol: str) -> bool:
        """Check if position is being opened on exchange/symbol.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            
        Returns:
            True if position is being opened
        """
        try:
            field = f"{ex_id}:{symbol}"
            # Check if field exists in hash
            value = await self._cache.hget("opening_position", field)
            return value is not None
        except Exception as e:
            logger.error(f"Error checking opening position: {e}")
            return False

    async def mark_opening_position(self, ex_id: str, symbol: str, bot_id: str | int) -> bool:
        """Mark position as opening on exchange/symbol.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            bot_id: Bot ID opening the position
            
        Returns:
            True if marked successfully
        """
        try:
            field = f"{ex_id}:{symbol}"
            value = f"{bot_id}:{datetime.now(UTC).isoformat()}"
            # Set in hash
            result = await self._cache.hset("opening_position", field, value)
            return True  # Success regardless of new or update
        except Exception as e:
            logger.error(f"Error marking opening position: {e}")
            return False

    async def unmark_opening_position(self, ex_id: str, symbol: str) -> bool:
        """Unmark position opening on exchange/symbol.
        
        Args:
            ex_id: Exchange ID
            symbol: Trading symbol
            
        Returns:
            True if unmarked successfully
        """
        try:
            field = f"{ex_id}:{symbol}"
            # Delete from hash
            deleted = await self._cache.hdel("opening_position", field)
            return deleted > 0
        except Exception as e:
            logger.error(f"Error unmarking opening position: {e}")
            return False

    async def update_bot(self, bot_id: str, bot: dict[str, str | int | float]) -> bool:
        """Update bot status with feed structure.
        
        Args:
            bot_id: Bot ID
            bot: Dictionary containing bot's feed statuses
            
        Returns:
            True if updated successfully
            
        Example:
            await cache.update_bot("bot_1", {
                "feed_1": {
                    "status": "running",
                    "symbols": ["BTC/USDT"],
                    "performance": {"pnl": 100.0}
                },
                "feed_2": {
                    "status": "paused",
                    "symbols": ["ETH/USDT"]
                }
            })
        """
        try:
            # Add timestamp to each feed
            timestamp = datetime.now(UTC).isoformat()
            for feed_status in bot.values():
                if isinstance(feed_status, dict):
                    feed_status["timestamp"] = timestamp

            field = str(bot_id)
            value = json.dumps(bot)
            # Save to hash
            result = await self._cache.hset("bot_status", field, value)
            return True  # Success regardless of new or update
        except Exception as e:
            logger.error(f"Error updating bot: {e}")
            return False

    async def del_bot(self, bot_id: str) -> bool:
        """Delete bot status.
        
        Args:
            bot_id: Bot ID
            
        Returns:
            True if deleted successfully
        """
        try:
            field = str(bot_id)
            # Delete from hash
            deleted = await self._cache.hdel("bot_status", field)
            return deleted > 0
        except Exception as e:
            logger.error(f"Error deleting bot: {e}")
            return False

    async def del_status(self) -> bool:
        """Delete all bot statuses.
        
        WARNING: This removes ALL bot status data.
        
        Returns:
            True if deleted successfully
        """
        try:
            # Delete entire key
            deleted = await self._cache.delete("bot_status")
            return deleted > 0
        except Exception as e:
            logger.error(f"Error deleting all statuses: {e}")
            return False

    async def get_bots(self) -> dict[str, dict[str, Any]]:
        """Get all bots and their statuses.
        
        Returns:
            Dictionary mapping bot_id to bot status with feeds
            
        Example:
            bots = await cache.get_bots()
            # Returns: {
            #     "bot_1": {
            #         "feed_1": {"status": "running", "timestamp": "..."},
            #         "feed_2": {"status": "paused", "timestamp": "..."}
            #     }
            # }
        """
        bots = {}
        try:
            # Get all hash entries
            data = await self._cache.hgetall("bot_status")

            for bot_id, bot_status in data.items():
                try:
                    # Parse JSON
                    bots[bot_id] = json.loads(bot_status)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse bot status for {bot_id}")
                    # Return error in same format as legacy
                    bots[bot_id] = {"error": "Invalid JSON"}
        except Exception as e:
            logger.error(f"Failed to get bot statuses from Redis: {e}")
            raise

        return bots
