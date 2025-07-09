"""Trade queue management using Redis.

This module provides trade queue management using Redis lists
for processing trading data.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fullon_orm.models import Trade

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class TradesCache:
    """Cache for trade queue management using Redis.
    
    This cache provides trade queue management using Redis lists for queuing
    and simple status tracking, matching the legacy implementation.
    
    Features:
        - FIFO trade queues using Redis lists
        - Trade status timestamp tracking
        - User trade queues
        - Integration with fullon_orm Trade model
        
    Example:
        cache = TradesCache()
        
        # Push trade to queue
        result = await cache.push_trade_list("BTC/USDT", "binance", trade_data)
        
        # Get all trades from queue (destructive read)
        trades = await cache.get_trades_list("BTC/USDT", "binance")
        
        # Push user trade
        await cache.push_my_trades_list("123", "binance", trade_data)
        
        # Pop user trade
        trade = await cache.pop_my_trade("123", "binance")
    """

    def __init__(self):
        """Initialize the trades cache."""
        self._cache = BaseCache()

    async def push_trade_list(
        self,
        symbol: str,
        exchange: str,
        trade: dict | Trade = {}
    ) -> int:
        """Push trade data to a Redis list.
        
        Args:
            symbol: The trading symbol for the asset pair
            exchange: The name of the exchange where the trade occurred
            trade: The trade data as a dictionary or Trade object
            
        Returns:
            The new length of the list after the push operation
        """
        # Normalize symbol
        normalized_symbol = symbol.replace("/", "")
        redis_key = f"trades:{exchange}:{normalized_symbol}"

        try:
            # Convert Trade object to dict if needed
            if isinstance(trade, Trade):
                trade_data = trade.to_dict()
            else:
                trade_data = trade

            # Push to list
            async with self._cache._redis_context() as redis_client:
                result = await redis_client.rpush(redis_key, json.dumps(trade_data))

            # Update trade status
            if await self.update_trade_status(exchange):
                return result
            return 0
        except Exception as e:
            logger.error(f"Failed to push trade to list: {e}")
            return 0

    async def update_trade_status(self, key: str) -> bool:
        """Update status timestamp for trades.
        
        Args:
            key: The key to update (usually exchange name)
            
        Returns:
            True if successful
        """
        try:
            status_key = f"TRADE:STATUS:{key}"
            timestamp = self._cache._to_redis_timestamp(datetime.now(UTC))

            async with self._cache._redis_context() as redis_client:
                await redis_client.set(status_key, timestamp)
            return True
        except Exception as e:
            logger.error(f"update_trade_status error: {e}")
            return False

    async def get_trade_status(self, key: str) -> datetime | None:
        """Get trade status timestamp.
        
        Args:
            key: The key to retrieve (usually exchange name)
            
        Returns:
            Timestamp as datetime or None
        """
        try:
            status_key = f"TRADE:STATUS:{key}"
            async with self._cache._redis_context() as redis_client:
                value = await redis_client.get(status_key)
            return self._cache._from_redis_timestamp(value) if value else None
        except Exception as e:
            logger.error(f"get_trade_status error: {e}")
            return None

    async def get_all_trade_statuses(
        self,
        prefix: str = "TRADE:STATUS"
    ) -> dict[str, datetime]:
        """Get all trade status timestamps.
        
        Args:
            prefix: The prefix to search for
            
        Returns:
            Dictionary mapping key to timestamp
        """
        try:
            statuses = {}

            # Use raw Redis scan since these are raw keys
            async with self._cache._redis_context() as redis_client:
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(cursor, match=f"{prefix}*", count=100)
                    for key in keys:
                        value = await redis_client.get(key)
                        if value:
                            dt = self._cache._from_redis_timestamp(value)
                            if dt:
                                statuses[key] = dt
                    if cursor == 0:
                        break

            return statuses
        except Exception as e:
            logger.error(f"get_all_trade_statuses error: {e}")
            return {}

    async def get_trade_status_keys(
        self,
        prefix: str = "TRADE:STATUS"
    ) -> list[str]:
        """Get all keys with given prefix.
        
        Args:
            prefix: The prefix to search for
            
        Returns:
            List of matching keys
        """
        try:
            keys = []

            async with self._cache._redis_context() as redis_client:
                cursor = 0
                while True:
                    cursor, found_keys = await redis_client.scan(cursor, match=f"{prefix}*", count=100)
                    keys.extend(found_keys)
                    if cursor == 0:
                        break

            return keys
        except Exception as e:
            logger.error(f"get_trade_status_keys error: {e}")
            return []

    async def update_user_trade_status(
        self,
        key: str,
        timestamp: datetime | None = None
    ) -> bool:
        """Update status timestamp for user trades.
        
        Args:
            key: The key to update
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            True if successful
        """
        try:
            status_key = f"USER_TRADE:STATUS:{key}"
            if timestamp is None:
                timestamp = datetime.now(UTC)

            timestamp_str = self._cache._to_redis_timestamp(timestamp)

            async with self._cache._redis_context() as redis_client:
                await redis_client.set(status_key, timestamp_str)
            return True
        except Exception as e:
            logger.error(f"update_user_trade_status error: {e}")
            return False

    async def delete_user_trade_statuses(self) -> bool:
        """Delete all USER_TRADE:STATUS keys.
        
        Returns:
            True if deletion was successful
        """
        try:
            deleted_count = 0
            pattern = "USER_TRADE:STATUS*"

            async with self._cache._redis_context() as redis_client:
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted_count += await redis_client.delete(*keys)
                    if cursor == 0:
                        break

            logger.debug(f"Deleted {deleted_count} user trade status keys")
            return True
        except Exception as e:
            logger.error(f"delete_user_trade_statuses error: {e}")
            return False

    async def push_my_trades_list(
        self,
        uid: str,
        exchange: str,
        trade: dict | Trade = {}
    ) -> int:
        """Push user trade to Redis list.
        
        Args:
            uid: User ID
            exchange: Exchange name
            trade: Trade data dictionary or Trade object
            
        Returns:
            New length of the list
        """
        try:
            # Convert Trade object to dict if needed
            if isinstance(trade, Trade):
                trade_data = trade.to_dict()
            else:
                trade_data = trade

            redis_key = f"user_trades:{uid}:{exchange}"
            async with self._cache._redis_context() as redis_client:
                return await redis_client.rpush(redis_key, json.dumps(trade_data))
        except Exception as e:
            logger.error(f"Failed to push user trade: {e}")
            return 0

    async def pop_my_trade(
        self,
        uid: str,
        exchange: str,
        timeout: int = 0
    ) -> dict[str, Any] | None:
        """Pop trade from user's trade queue.
        
        Args:
            uid: User ID
            exchange: Exchange name
            timeout: Blocking timeout in seconds
            
        Returns:
            Trade dictionary or None
        """
        try:
            redis_key = f"user_trades:{uid}:{exchange}"

            async with self._cache._redis_context() as redis_client:
                if timeout and timeout > 0:
                    # Blocking pop
                    result = await redis_client.blpop(redis_key, timeout=timeout)
                    if result:
                        _, trade_json = result
                        return json.loads(trade_json)
                else:
                    # Non-blocking pop
                    trade_json = await redis_client.lpop(redis_key)
                    if trade_json:
                        return json.loads(trade_json)

            return None
        except Exception as e:
            if "TimeoutError" not in str(e):
                logger.error(f"Failed to pop user trade: {e}")
            return None

    async def get_trades_list(
        self,
        symbol: str,
        exchange: str
    ) -> list[dict[str, Any]]:
        """Get all trades and clear the list.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            List of trade dictionaries
            
        Note:
            This method gets all trades and then deletes the list.
            Use with caution as it's destructive.
        """
        try:
            # Normalize symbol
            normalized_symbol = symbol.replace("/", "")
            redis_key = f"trades:{exchange}:{normalized_symbol}"

            async with self._cache._redis_context() as redis_client:
                # Get all trades
                trades_json = await redis_client.lrange(redis_key, 0, -1)

                # Delete the list
                await redis_client.delete(redis_key)

            # Parse trades
            trades = []
            for trade_json in trades_json:
                try:
                    trade_dict = json.loads(trade_json)
                    trades.append(trade_dict)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse trade JSON: {trade_json}")
                except Exception as e:
                    logger.warning(f"Failed to parse trade: {e}")

            return trades
        except Exception as e:
            logger.error(f"Failed to get trades list: {e}")
            return []

    async def push_trade(self, exchange: str, trade: Trade) -> bool:
        """Push trade using fullon_orm.Trade model.
        
        Args:
            exchange: Exchange name
            trade: fullon_orm.Trade model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize symbol
            normalized_symbol = trade.symbol.replace("/", "")
            redis_key = f"trades:{exchange}:{normalized_symbol}"
            
            # Convert Trade to dict for Redis storage
            trade_dict = trade.to_dict()
            
            # Push to list
            async with self._cache._redis_context() as redis_client:
                await redis_client.rpush(redis_key, json.dumps(trade_dict))
            
            # Update trade status
            await self.update_trade_status(exchange)
            return True
            
        except Exception as e:
            logger.error(f"Failed to push trade: {e}")
            return False

    async def get_trades(self, symbol: str, exchange: str) -> list[Trade]:
        """Get all trades as fullon_orm.Trade models (destructive read).
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            List of fullon_orm.Trade models
        """
        try:
            # Normalize symbol
            normalized_symbol = symbol.replace("/", "")
            redis_key = f"trades:{exchange}:{normalized_symbol}"

            async with self._cache._redis_context() as redis_client:
                # Get all trades
                trades_json = await redis_client.lrange(redis_key, 0, -1)
                # Delete the list
                await redis_client.delete(redis_key)

            # Parse trades into Trade models
            trades = []
            for trade_json in trades_json:
                try:
                    trade_dict = json.loads(trade_json)
                    trade = Trade.from_dict(trade_dict)
                    trades.append(trade)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse trade: {e}")

            return trades
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    async def push_user_trade(self, uid: str, exchange: str, trade: Trade) -> bool:
        """Push user trade using fullon_orm.Trade model.
        
        Args:
            uid: User ID
            exchange: Exchange name
            trade: fullon_orm.Trade model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert Trade to dict for Redis storage
            trade_dict = trade.to_dict()
            
            redis_key = f"user_trades:{uid}:{exchange}"
            async with self._cache._redis_context() as redis_client:
                await redis_client.rpush(redis_key, json.dumps(trade_dict))
            return True
            
        except Exception as e:
            logger.error(f"Failed to push user trade: {e}")
            return False

    async def pop_user_trade(self, uid: str, exchange: str, timeout: int = 0) -> Trade | None:
        """Pop user trade as fullon_orm.Trade model.
        
        Args:
            uid: User ID
            exchange: Exchange name
            timeout: Blocking timeout in seconds
            
        Returns:
            fullon_orm.Trade model or None if not found
        """
        try:
            redis_key = f"user_trades:{uid}:{exchange}"

            async with self._cache._redis_context() as redis_client:
                if timeout and timeout > 0:
                    # Blocking pop
                    result = await redis_client.blpop(redis_key, timeout=timeout)
                    if result:
                        _, trade_json = result
                        trade_dict = json.loads(trade_json)
                        return Trade.from_dict(trade_dict)
                else:
                    # Non-blocking pop
                    trade_json = await redis_client.lpop(redis_key)
                    if trade_json:
                        trade_dict = json.loads(trade_json)
                        return Trade.from_dict(trade_dict)

            return None
        except (json.JSONDecodeError, Exception) as e:
            if "TimeoutError" not in str(e):
                logger.error(f"Failed to pop user trade: {e}")
            return None

