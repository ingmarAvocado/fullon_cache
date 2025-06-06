"""Order queue management using Redis.

This module provides order queue management using Redis lists and hashes
for processing trading orders.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fullon_orm.models import Order
from fullon_orm import get_async_session
from fullon_orm.repositories import OrderRepository

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class OrdersCache:
    """Cache for order queue management using Redis.
    
    This cache provides order queue management using Redis lists for queuing
    and hashes for order status tracking, matching the legacy implementation.
    
    Features:
        - FIFO order queues using Redis lists
        - Order status tracking with Redis hashes
        - TTL for cancelled orders
        - Integration with fullon_orm Order model
        
    Example:
        cache = OrdersCache()
        
        # Push order ID to queue
        await cache.push_open_order("12345", "LOCAL_001")
        
        # Pop order from queue
        order_id = await cache.pop_open_order("LOCAL_001")
        
        # Save order data
        await cache.save_order_data("binance", "12345", {
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 50000,
            "status": "open"
        })
        
        # Get order status
        order = await cache.get_order_status("binance", "12345")
    """
    
    def __init__(self):
        """Initialize the orders cache."""
        self._cache = BaseCache()
        
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
    
    async def pop_open_order(self, oid: str) -> Optional[str]:
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
                result = await redis_client.blpop(redis_key, timeout=0)
                if result:
                    _, order_id = result
                    return order_id.decode('utf-8') if isinstance(order_id, bytes) else order_id
            return None
        except Exception as e:
            if "TimeoutError" in str(e):
                raise TimeoutError("Not getting any trade")
            logger.error(f"Failed to pop open order: {e}")
            return None
    
    async def save_order_data(
        self,
        ex_id: str,
        oid: str,
        data: Dict = {}
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
                data['timestamp'] = self._cache._to_redis_timestamp(datetime.now(timezone.utc))
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
    ) -> Optional[Order]:
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
    
    async def get_orders(self, ex_id: str) -> List[Order]:
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
    
    async def get_full_accounts(self, ex_id: str) -> Optional[Any]:
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
        except (TypeError, KeyError) as error:
            return None
        except Exception as e:
            logger.error(f"Failed to get full accounts: {e}")
            return None
    
    def _dict_to_order(self, data: Dict[str, Any]) -> Optional[Order]:
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
                
                # Always store as string for ex_order_id
                clean_data['ex_order_id'] = str(data['order_id'])
            
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
                clean_data['timestamp'] = self._cache._from_redis_timestamp(data['timestamp']) or datetime.now(timezone.utc)
            else:
                clean_data['timestamp'] = datetime.now(timezone.utc)
            
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
    
    
    def _order_to_dict(self, order: Order) -> Dict[str, Any]:
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