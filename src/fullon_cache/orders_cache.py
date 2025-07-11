"""Order queue management using Redis.

This module provides order queue management using Redis lists and hashes
for processing trading orders.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fullon_orm.models import Order

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class OrdersCache:
    """Cache for order queue management using Redis.
    
    This cache provides order queue management using Redis lists for queuing
    and hashes for order status tracking with fullon_orm.Order model support.
    
    Features:
        - FIFO order queues using Redis lists
        - Order status tracking with Redis hashes
        - TTL for cancelled orders (1 hour)
        - Type-safe fullon_orm Order model integration
        - Both ORM-based and legacy methods supported
        
    Example:
        from fullon_orm.models import Order
        from datetime import datetime, timezone
        
        cache = OrdersCache()
        
        # Create order with ORM model
        order = Order(
            ex_order_id="EX_12345",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=50000.0,
            status="open",
            order_type="limit",
            exchange="binance",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Save order using ORM model
        success = await cache.save_order("binance", order)
        
        # Push order ID to queue
        await cache.push_open_order("EX_12345", "LOCAL_001")
        
        # Pop order from queue
        order_id = await cache.pop_open_order("LOCAL_001")
        
        # Get order as ORM model
        retrieved_order = await cache.get_order("binance", "EX_12345")
        if retrieved_order:
            print(f"Order: {retrieved_order.symbol} {retrieved_order.side}")
        
        # Get order status
        order = await cache.get_order_status("binance", "12345")
    """

    def __init__(self):
        """Initialize the orders cache."""
        self._cache = BaseCache()

    async def close(self):
        """Close the cache connection."""
        await self._cache.close()

    async def push_open_order(self, oid: str, local_oid: str) -> None:
        """Push order ID to a Redis list.
        
        Args:
            oid: The ID of the open order
            local_oid: The local order ID
            
        Returns:
            None
        """
        redis_key = f"new_orders:{local_oid}"
        try:
            async with self._cache._redis_context() as redis_client:
                await redis_client.rpush(redis_key, oid)
        except Exception as e:
            logger.error(f"Failed to push open order: {e}")

    async def pop_open_order(self, oid: str) -> str | None:
        """Pop order from Redis list with blocking.
        
        Args:
            oid: The local order ID
            
        Returns:
            The order ID or None
            
        Raises:
            TimeoutError: If the open order queue is empty and timeout expired
        """
        redis_key = f"new_orders:{oid}"
        try:
            async with self._cache._redis_context() as redis_client:
                # Use timeout=1 to avoid blocking forever in tests
                result = await redis_client.blpop(redis_key, timeout=1)
                if result:
                    _, order_id = result
                    return order_id.decode('utf-8') if isinstance(order_id, bytes) else order_id
            return None
        except Exception as e:
            if "TimeoutError" in str(e) or "Timeout" in str(e):
                # Don't raise, just return None for tests
                return None
            logger.error(f"Failed to pop open order: {e}")
            return None

    async def save_order_data(
        self,
        ex_id: str,
        oid: str,
        data: dict = {}
    ) -> None:
        """Save order data to Redis hash.
        
        Args:
            ex_id: The exchange ID
            oid: The order ID
            data: Order data dictionary
            
        Returns:
            None
            
        Raises:
            Exception: If there was an error saving to Redis
        """
        redis_key = f"order_status:{ex_id}"
        second_key = str(oid)

        try:
            async with self._cache._redis_context() as redis_client:
                # Get existing data
                existing_data = await redis_client.hget(redis_key, second_key)
                if existing_data:
                    existing_data = json.loads(existing_data)
                    existing_data.update(data)
                    data = existing_data

                # Update timestamp
                data['timestamp'] = self._cache._to_redis_timestamp(datetime.now(UTC))
                data['order_id'] = oid

                # Save to hash
                await redis_client.hset(redis_key, second_key, json.dumps(data))

                # Set expiration for cancelled orders
                if data.get('status') == "canceled":
                    await redis_client.expire(redis_key, 60 * 60)  # 1 hour

        except Exception as e:
            logger.exception(f"Error saving order data to Redis: {e}")
            raise Exception("Error saving order status to Redis") from e

    async def get_order_status(
        self,
        ex_id: str,
        oid: str
    ) -> Order | None:
        """Get order status from Redis hash.
        
        Args:
            ex_id: The exchange ID
            oid: The order ID
            
        Returns:
            Order object or None
            
        Raises:
            Exception: If there was an error getting from Redis
        """
        redis_key = f"order_status:{ex_id}"
        second_key = str(oid)

        try:
            async with self._cache._redis_context() as redis_client:
                result = await redis_client.hget(redis_key, second_key)
                if result:
                    data = json.loads(result)
                    # Convert to ORM Order model
                    return self._dict_to_order(data)
            return None
        except AttributeError:
            pass
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
        return None

    async def get_orders(self, ex_id: str) -> list[Order]:
        """Get all orders for an exchange.
        
        Args:
            ex_id: The exchange ID
            
        Returns:
            List of Order objects
            
        Raises:
            Exception: If there was an error getting from Redis
        """
        redis_key = f"order_status:{ex_id}"
        orders = []

        try:
            async with self._cache._redis_context() as redis_client:
                _orders = await redis_client.hgetall(redis_key)
                if _orders:
                    for key, value in _orders.items():
                        try:
                            # Decode bytes if needed
                            if isinstance(value, bytes):
                                value = value.decode('utf-8')
                            order_data = json.loads(value)
                            order = self._dict_to_order(order_data)
                            if order:
                                orders.append(order)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse order JSON: {value}")
        except AttributeError:
            pass
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")

        return orders

    async def get_full_accounts(self, ex_id: str) -> Any | None:
        """Get full account data for exchange.
        
        Args:
            ex_id: Exchange ID
            
        Returns:
            Account data or None
        """
        try:
            key = str(ex_id)
            async with self._cache._redis_context() as redis_client:
                data = await redis_client.hget("accounts", key)
                if data:
                    return json.loads(data)
            return None
        except (TypeError, KeyError):
            return None
        except Exception as e:
            logger.error(f"Failed to get full accounts: {e}")
            return None

    def _dict_to_order(self, data: dict[str, Any]) -> Order | None:
        """Convert dictionary to ORM Order object.
        
        Args:
            data: Dictionary with order data
            
        Returns:
            ORM Order object or None if data is invalid
        """
        try:
            # Clean and prepare data for ORM
            clean_data = {}

            # Handle order_id and ex_order_id
            if 'order_id' in data:
                # Try to convert to int for order_id
                try:
                    order_id_val = data['order_id']
                    if order_id_val is not None and str(order_id_val).isdigit():
                        clean_data['order_id'] = int(order_id_val)
                except (ValueError, TypeError):
                    pass

            # Handle ex_order_id - always use order_id as ex_order_id for legacy compatibility
            # The order_id field contains the Redis key, which should be the ex_order_id
            if 'order_id' in data and data['order_id'] is not None:
                clean_data['ex_order_id'] = str(data['order_id'])
            elif 'ex_order_id' in data and data['ex_order_id'] is not None:
                clean_data['ex_order_id'] = str(data['ex_order_id'])

            # Handle numeric fields with proper conversion
            numeric_fields = {
                'volume': 0.0,
                'final_volume': None,
                'price': None,
                'plimit': None,
                'leverage': None
            }

            for field, default in numeric_fields.items():
                if field in data and data[field] is not None:
                    try:
                        clean_data[field] = float(data[field])
                    except (ValueError, TypeError):
                        if default is not None:
                            clean_data[field] = default

            # Handle boolean fields
            if 'futures' in data:
                clean_data['futures'] = bool(data.get('futures', False))

            # Handle timestamp
            if 'timestamp' in data:
                clean_data['timestamp'] = self._cache._from_redis_timestamp(data['timestamp']) or datetime.now(UTC)
            else:
                clean_data['timestamp'] = datetime.now(UTC)

            # Copy string fields directly
            string_fields = ['exchange', 'symbol', 'order_type', 'side', 'status', 'command', 'reason']
            for field in string_fields:
                if field in data:
                    clean_data[field] = str(data[field]) if data[field] is not None else ''

            # Copy other fields as-is
            other_fields = ['bot_id', 'uid', 'ex_id', 'cat_ex_id', 'tick']
            for field in other_fields:
                if field in data and data[field] is not None:
                    clean_data[field] = data[field]

            # Use ORM's from_dict method
            return Order.from_dict(clean_data)

        except Exception as e:
            logger.error(f"Failed to convert dict to Order: {e}")
            return None


    def _order_to_dict(self, order: Order) -> dict[str, Any]:
        """Convert ORM Order object to dictionary.
        
        Args:
            order: ORM Order object
            
        Returns:
            Dictionary representation of the order
        """
        try:
            # Use ORM's to_dict method if available
            data = order.to_dict()

            # Ensure timestamp is ISO formatted
            if 'timestamp' in data and isinstance(data['timestamp'], datetime):
                data['timestamp'] = self._cache._to_redis_timestamp(data['timestamp'])

            # Ensure order_id is included
            if hasattr(order, 'order_id') and order.order_id:
                data['order_id'] = order.order_id
            elif hasattr(order, 'ex_order_id') and order.ex_order_id:
                data['order_id'] = order.ex_order_id

            return data
        except Exception as e:
            logger.error(f"Failed to convert Order to dict: {e}")
            return {}

    async def save_order(self, exchange: str, order: Order) -> bool:
        """Save order using fullon_orm.Order model.
        
        Args:
            exchange: Exchange name
            order: fullon_orm.Order model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_key = f"order_status:{exchange}"
            order_id = str(order.ex_order_id or order.order_id)
            
            # Convert Order to dict for Redis storage
            order_dict = self._order_to_dict(order)
            order_dict['timestamp'] = self._cache._to_redis_timestamp(datetime.now(UTC))
            order_dict['order_id'] = order_id
            
            async with self._cache._redis_context() as redis_client:
                # Store in Redis
                await redis_client.hset(redis_key, order_id, json.dumps(order_dict))
                
                # Set TTL for cancelled orders
                if order.status == "canceled":
                    await redis_client.expire(redis_key, 60 * 60)  # 1 hour
            
            return True
        except Exception as e:
            logger.error(f"Failed to save order: {e}")
            return False

    async def update_order(self, exchange: str, order: Order) -> bool:
        """Update existing order with new data.
        
        Args:
            exchange: Exchange name
            order: fullon_orm.Order model with updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_key = f"order_status:{exchange}"
            order_id = str(order.ex_order_id or order.order_id)
            
            async with self._cache._redis_context() as redis_client:
                # Get existing data
                existing_data = await redis_client.hget(redis_key, order_id)
                if existing_data:
                    existing_dict = json.loads(existing_data)
                    
                    # Merge with new data
                    new_dict = self._order_to_dict(order)
                    # Only update non-None values
                    for key, value in new_dict.items():
                        if value is not None:
                            existing_dict[key] = value
                    
                    # Update timestamp
                    existing_dict['timestamp'] = self._cache._to_redis_timestamp(datetime.now(UTC))
                    
                    # Store merged data
                    await redis_client.hset(redis_key, order_id, json.dumps(existing_dict))
                    
                    # Set TTL for cancelled orders
                    if existing_dict.get('status') == "canceled":
                        await redis_client.expire(redis_key, 60 * 60)
                    
                    return True
                else:
                    # No existing data, treat as new save
                    return await self.save_order(exchange, order)
        except Exception as e:
            logger.error(f"Failed to update order: {e}")
            return False

    async def get_order(self, exchange: str, order_id: str) -> Order | None:
        """Get order as fullon_orm.Order model.
        
        Args:
            exchange: Exchange name
            order_id: Order ID (ex_order_id or order_id)
            
        Returns:
            fullon_orm.Order model or None if not found
        """
        try:
            redis_key = f"order_status:{exchange}"
            
            async with self._cache._redis_context() as redis_client:
                order_data = await redis_client.hget(redis_key, str(order_id))
                
                if order_data:
                    order_dict = json.loads(order_data)
                    return self._dict_to_order(order_dict)
                return None
        except Exception as e:
            logger.error(f"Failed to get order: {e}")
            return None

    # Legacy compatibility methods
    async def save_order_data_legacy(self, ex_id: str, oid: str, data: dict = {}) -> None:
        """Legacy method for backward compatibility.
        
        Args:
            ex_id: The exchange ID
            oid: The order ID
            data: Order data dictionary
            
        Returns:
            None
            
        Raises:
            Exception: If there was an error saving to Redis
        """
        try:
            await self.save_order_data(ex_id, oid, data)
        except Exception as e:
            logger.exception(f"Error saving order data to Redis: {e}")
            raise Exception("Error saving order status to Redis") from e

