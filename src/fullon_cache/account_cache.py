"""Simplified account and position cache matching legacy interface."""

import json
import logging
from datetime import UTC, datetime

from fullon_orm.models import Position

from .base_cache import BaseCache
from .exceptions import CacheError, ConnectionError

logger = logging.getLogger(__name__)


class AccountCache:
    """Cache for user accounts and positions.
    
    Provides simple storage and retrieval of account balances and positions
    without complex calculations or analytics.
    """

    def __init__(self):
        """Initialize account cache with BaseCache composition."""
        self._cache = BaseCache()

    async def upsert_positions(
        self,
        ex_id: int,
        positions: dict[str, dict[str, float]],
        update_date: bool = False
    ) -> bool:
        """Upserts positions into the cache.

        Args:
            ex_id: Exchange ID.
            positions: Positions to upsert. Expected format:
                {symbol: {'cost': float, 'volume': float, 'fee': float, 'price': float, 'timestamp': str}}
            update_date: If True, only update the timestamp for existing positions.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Convert ex_id to string for Redis key
            str_ex_id = str(ex_id)
            key = "account_positions"

            async with self._cache._redis_context() as redis:
                if update_date:
                    # Only update timestamp if positions exist
                    existing = await redis.hget(key, str_ex_id)
                    if existing:
                        existing_positions = json.loads(existing)
                        existing_positions['timestamp'] = self._cache._to_redis_timestamp(datetime.now(UTC))
                        await redis.hset(key, str_ex_id, json.dumps(existing_positions))
                        return True
                    return False

                if positions == {}:
                    # Delete if empty
                    result = await redis.hdel(key, str_ex_id)
                    return bool(result)

                if not self._check_position_dict(positions):
                    # Invalid positions dict
                    return False

                # Add timestamp to positions data
                positions_with_timestamp = positions.copy()
                positions_with_timestamp['timestamp'] = self._cache._to_redis_timestamp(datetime.now(UTC))

                await redis.hset(key, str_ex_id, json.dumps(positions_with_timestamp))
                return True

        except (AttributeError, ConnectionError) as error:
            logger.error(f"Error in upsert_positions: {error}")
            return False

    async def upsert_user_account(
        self,
        ex_id: int,
        account: dict = {},
        update_date: str = ""
    ) -> bool:
        """Upserts user account. If update_date is provided, only updates the date field.

        Args:
            ex_id: Exchange ID.
            account: Account information.
            update_date: If provided as string, only update the date for existing accounts.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Convert ex_id to string for Redis key
            str_ex_id = str(ex_id)
            key = "accounts"

            async with self._cache._redis_context() as redis:
                if isinstance(update_date, str) and update_date:
                    # Only update date if account exists
                    existing = await redis.hget(key, str_ex_id)
                    if existing:
                        existing_account = json.loads(existing)
                        existing_account['date'] = update_date
                        await redis.hset(key, str_ex_id, json.dumps(existing_account))
                        return True
                    return False
                else:
                    # Full upsert
                    account['date'] = self._cache._to_redis_timestamp(datetime.now(UTC))
                    await redis.hset(key, str_ex_id, json.dumps(account))
                    return True

        except (AttributeError, TypeError, ConnectionError) as error:
            logger.error(f"Error in upsert_user_account: {error}")
            return False

    async def clean_positions(self) -> int:
        """Removes all positions from redis.
        
        Returns:
            int: Number of keys deleted (0, 1, or 2).
        """
        try:
            async with self._cache._redis_context() as redis:
                deleted1 = await redis.delete("account_positions")
                deleted2 = await redis.delete("accounts")
                return deleted1 + deleted2
        except ConnectionError as error:
            logger.error(f"Error in clean_positions: {error}")
            return 0

    async def get_all_positions(self) -> list[Position]:
        """Get all positions from cache.
        
        Returns:
            List[Position]: List of fullon_orm Position objects.
        """
        positions = []
        try:
            async with self._cache._redis_context() as redis:
                datas = await redis.hgetall("account_positions")
                if not datas:
                    return positions

                for key, value in datas.items():
                    try:
                        account_data = json.loads(value)
                        # Get the root timestamp if it exists
                        root_timestamp_str = account_data.get('timestamp')
                        root_timestamp = None
                        if root_timestamp_str:
                            dt = self._cache._from_redis_timestamp(root_timestamp_str)
                            if dt:
                                root_timestamp = dt.timestamp()
                        ex_id = key.decode('utf-8') if isinstance(key, bytes) else key

                        for symbol, data in account_data.items():
                            if symbol != 'timestamp':
                                # Map to fullon_orm Position fields
                                position_dict = {
                                    'symbol': symbol,
                                    'cost': data.get('cost', 0.0),
                                    'volume': data.get('volume', 0.0),
                                    'fee': data.get('fee', 0.0),
                                    'price': data.get('price', 0.0),
                                    'timestamp': data.get('timestamp', root_timestamp or datetime.now(UTC).timestamp()),
                                    'ex_id': ex_id
                                }
                                position = Position.from_dict(position_dict)
                                positions.append(position)

                    except (json.JSONDecodeError, KeyError, TypeError) as error:
                        logger.error(f"Error parsing position data: {error}")
                        continue

        except (ConnectionError, CacheError) as error:
            logger.error(f"Error getting all positions: {error}")

        return positions

    @staticmethod
    def _check_position_dict(pos: dict) -> bool:
        """Check if all items in the input dictionary have the same set of subkeys.

        Args:
            pos: A dictionary containing pairs as keys and dictionaries with subkeys as values.

        Returns:
            bool: True if all items have the same set of subkeys, False otherwise.
        """
        subkeys = {'cost', 'volume', 'fee', 'price', 'timestamp'}
        for pair_data in pos.values():
            if not isinstance(pair_data, dict):
                return False
            if set(pair_data.keys()) != subkeys:
                return False
        return True

    async def get_position(
        self,
        symbol: str,
        ex_id: str,
        latest: bool = False,
        cur_timestamp: float | None = None
    ) -> Position:
        """Returns position from account by symbol.

        Args:
            symbol: Trading symbol.
            ex_id: Exchange ID.
            latest: Whether to wait for latest position (simplified - ignored).
            cur_timestamp: Current timestamp (simplified - ignored).

        Returns:
            Position: Position data or empty Position if not found.
        """
        try:
            if not ex_id:
                return Position(symbol=symbol)

            async with self._cache._redis_context() as redis:
                datas = await redis.hget("account_positions", str(ex_id))
                if not datas:
                    return Position(symbol=symbol)

                positions_data = json.loads(datas)
                if symbol not in positions_data:
                    return Position(symbol=symbol)

                data = positions_data[symbol]
                # Map to fullon_orm Position
                position_dict = {
                    'symbol': symbol,
                    'cost': data.get('cost', 0.0),
                    'volume': data.get('volume', 0.0),
                    'fee': data.get('fee', 0.0),
                    'price': data.get('price', 0.0),
                    'timestamp': data.get('timestamp', datetime.now(UTC).timestamp()),
                    'ex_id': str(ex_id)
                }

                return Position.from_dict(position_dict)

        except (KeyError, TypeError, json.JSONDecodeError, ConnectionError) as error:
            logger.debug(f"Error getting position: {error}")
            return Position(symbol=symbol)

    async def get_full_account(self, exchange: int, currency: str) -> dict:
        """Returns account data for specific currency.

        Args:
            exchange: Exchange ID.
            currency: Base currency.

        Returns:
            dict: Account data for the currency or empty dict.
        """
        try:
            async with self._cache._redis_context() as redis:
                key = str(exchange)
                data = await redis.hget("accounts", key)
                if data:
                    account_data = json.loads(data)
                    return account_data.get(currency, {})
                return {}

        except (TypeError, KeyError, json.JSONDecodeError, ConnectionError) as error:
            logger.error(f"Error in get_full_account: {error}")
            return {}

    async def get_all_accounts(self) -> dict:
        """Returns all accounts, decoded from JSON.
        
        Returns:
            dict: All account data.
        """
        try:
            async with self._cache._redis_context() as redis:
                raw_data = await redis.hgetall("accounts")
                decoded_data = {}

                for key, value in raw_data.items():
                    try:
                        # Decode bytes to string if necessary
                        if isinstance(key, bytes):
                            key = key.decode('utf-8')
                        if isinstance(value, bytes):
                            value = value.decode('utf-8')
                        # Parse JSON
                        decoded_data[key] = json.loads(value)
                    except json.JSONDecodeError as json_error:
                        logger.warning(f"Failed to decode JSON for key {key}: {json_error}")
                        decoded_data[key] = value  # Store original value if JSON parsing fails

                return decoded_data

        except (TypeError, KeyError, ConnectionError) as error:
            logger.error(f"Error retrieving accounts: {error}")
            return {}
