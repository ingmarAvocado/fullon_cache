"""Exchange information cache with fullon_orm integration.

This module provides comprehensive exchange data caching with automatic
refresh from the database when exchanges are not found. Uses fullon_orm
models for type safety and consistency.
"""

import json
import logging
from typing import Any

from fullon_orm import get_async_session
from fullon_orm.models import Exchange, CatExchange
from fullon_orm.repositories import ExchangeRepository

from .process_cache import ProcessCache

logger = logging.getLogger(__name__)


class ExchangeCache(ProcessCache):
    """Cache for exchange data with fullon_orm integration.
    
    This cache provides comprehensive exchange data management with automatic
    database refresh when data is not found in cache. Returns fullon_orm
    Exchange and CatExchange objects for seamless integration with the ORM layer.
    
    Features:
        - Exchange account caching with TTL (24 hours)
        - CatExchange (exchange type) caching  
        - WebSocket error queue management
        - Integration with fullon_orm models and repositories
        - Automatic cache refresh on miss
    
    Example:
        cache = ExchangeCache()
        
        # Get user exchange accounts
        exchanges = await cache.get_exchanges(user_id=123)
        
        # Get specific exchange
        exchange = await cache.get_exchange(ex_id=456)
        
        # Get catalog exchanges
        cat_exchanges = await cache.get_cat_exchanges()
        
        # WebSocket error management
        await cache.push_ws_error("connection timeout", "binance_1")
        error = await cache.pop_ws_error("binance_1", timeout=5)
    """

    def __init__(self):
        """Initialize the exchange cache."""
        super().__init__()
        self._key_prefix = "exchange"
        self._cache_ttl = 24 * 60 * 60  # 24 hours

    async def get_exchange(self, ex_id: int) -> Exchange | None:
        """Get exchange by ID from cache or database.
        
        Args:
            ex_id: Exchange account ID
            
        Returns:
            Exchange object or None if not found
        """
        redis_key = f"exchange:{ex_id}"
        
        try:
            # Try cache first
            cached_data = await self._cache.get(redis_key)
            if cached_data:
                try:
                    exchange_dict = json.loads(cached_data)
                    return Exchange.from_dict(exchange_dict)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse cached exchange {ex_id}: {e}")
            
            # Cache miss - fetch from database
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                exchange = await repo.get_by_id(ex_id)
                if exchange:
                    # Cache the result
                    exchange_dict = exchange.to_dict()
                    await self._cache.set(redis_key, json.dumps(exchange_dict), ttl=self._cache_ttl)
                    return exchange
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting exchange {ex_id}: {e}")
            return None

    async def get_exchanges(self, user_id: int) -> list[Exchange]:
        """Get all exchanges for a user from cache or database.
        
        Args:
            user_id: User ID
            
        Returns:
            List of Exchange objects
        """
        redis_key = f"user_exchanges:{user_id}"
        
        try:
            # Try cache first
            cached_data = await self._cache.get(redis_key)
            if cached_data:
                try:
                    exchanges_data = json.loads(cached_data)
                    return [Exchange.from_dict(ex_dict) for ex_dict in exchanges_data]
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse cached exchanges for user {user_id}: {e}")
            
            # Cache miss - fetch from database
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                exchanges_data = await repo.get_user_exchanges(user_id)
                
                # Convert dict results to Exchange objects
                exchanges = []
                for ex_dict in exchanges_data:
                    try:
                        exchange = Exchange.from_dict(ex_dict)
                        exchanges.append(exchange)
                    except Exception as e:
                        logger.warning(f"Failed to create Exchange from dict: {e}")
                        continue
                
                # Cache the results
                if exchanges:
                    cache_data = [ex.to_dict() for ex in exchanges]
                    await self._cache.set(redis_key, json.dumps(cache_data), ttl=self._cache_ttl)
                
                return exchanges
            
        except Exception as e:
            logger.error(f"Error getting exchanges for user {user_id}: {e}")
            return []

    async def get_cat_exchanges(self, exchange_name: str = "", all: bool = False) -> list[CatExchange]:
        """Get catalog exchanges from cache or database.
        
        Args:
            exchange_name: Filter by exchange name (optional)
            all: Return all exchanges without pagination
            
        Returns:
            List of CatExchange objects
        """
        redis_key = f"cat_exchanges:{exchange_name}:{all}"
        
        try:
            # Try cache first
            cached_data = await self._cache.get(redis_key)
            if cached_data:
                try:
                    cat_exchanges_data = json.loads(cached_data)
                    return [CatExchange.from_dict(cat_ex_dict) for cat_ex_dict in cat_exchanges_data]
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse cached cat exchanges: {e}")
            
            # Cache miss - fetch from database
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                cat_exchanges = await repo.get_cat_exchanges(exchange=exchange_name, all=all)
                
                # Cache the results
                if cat_exchanges:
                    cache_data = [cat_ex.to_dict() for cat_ex in cat_exchanges]
                    await self._cache.set(redis_key, json.dumps(cache_data), ttl=self._cache_ttl)
                
                return cat_exchanges
            
        except Exception as e:
            logger.error(f"Error getting cat exchanges: {e}")
            return []

    async def add_exchange(self, exchange: Exchange) -> bool:
        """Add exchange to database and cache.
        
        Args:
            exchange: Exchange object to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                
                # Add to database
                exchange_dict = exchange.to_dict()
                ex_id = await repo.add_user_exchange(exchange_dict)
                
                if ex_id:
                    # Update the exchange with the new ID
                    exchange.ex_id = ex_id
                    
                    # Cache the new exchange
                    redis_key = f"exchange:{ex_id}"
                    await self._cache.set(redis_key, json.dumps(exchange.to_dict()), ttl=self._cache_ttl)
                    
                    # Invalidate user exchanges cache
                    if hasattr(exchange, 'uid') and exchange.uid:
                        await self._cache.delete(f"user_exchanges:{exchange.uid}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error adding exchange: {e}")
            
        return False

    async def update_exchange(self, exchange: Exchange) -> bool:
        """Update exchange in database and cache.
        
        Args:
            exchange: Exchange object with updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not exchange.ex_id:
                logger.error("Exchange ID is required for updates")
                return False
                
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                
                # Get existing exchange to preserve data
                existing = await repo.get_by_id(exchange.ex_id)
                if not existing:
                    logger.error(f"Exchange {exchange.ex_id} not found")
                    return False
                
                # Update fields that are provided
                for field, value in exchange.to_dict().items():
                    if value is not None:
                        setattr(existing, field, value)
                
                # Commit changes
                await repo.commit()
                
                # Update cache
                redis_key = f"exchange:{exchange.ex_id}"
                await self._cache.set(redis_key, json.dumps(existing.to_dict()), ttl=self._cache_ttl)
                
                # Invalidate user exchanges cache
                if hasattr(existing, 'uid') and existing.uid:
                    await self._cache.delete(f"user_exchanges:{existing.uid}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating exchange: {e}")
            
        return False

    async def delete_exchange(self, ex_id: int) -> bool:
        """Delete exchange from database and cache.
        
        Args:
            ex_id: Exchange ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async for session in get_async_session():
                repo = ExchangeRepository(session)
                
                # Get exchange to find user_id for cache invalidation
                exchange = await repo.get_by_id(ex_id)
                if not exchange:
                    logger.warning(f"Exchange {ex_id} not found for deletion")
                    return False
                
                # Delete from database
                success = await repo.remove_user_exchange(ex_id)
                
                if success:
                    # Remove from cache
                    await self._cache.delete(f"exchange:{ex_id}")
                    
                    # Invalidate user exchanges cache
                    if hasattr(exchange, 'uid') and exchange.uid:
                        await self._cache.delete(f"user_exchanges:{exchange.uid}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error deleting exchange: {e}")
            
        return False

    async def get_exchange_by_name(self, exchange_name: str) -> CatExchange | None:
        """Get catalog exchange by name.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            CatExchange object or None if not found
        """
        cat_exchanges = await self.get_cat_exchanges(exchange_name=exchange_name, all=True)
        for cat_ex in cat_exchanges:
            if cat_ex.name == exchange_name:
                return cat_ex
        return None

    async def invalidate_cache(self, ex_id: int | None = None, user_id: int | None = None) -> None:
        """Invalidate cache entries.
        
        Args:
            ex_id: Exchange ID to invalidate (optional)
            user_id: User ID to invalidate user exchanges (optional)
            
        If neither ex_id nor user_id is provided, invalidates all cache entries.
        """
        try:
            if ex_id:
                await self._cache.delete(f"exchange:{ex_id}")
            
            if user_id:
                await self._cache.delete(f"user_exchanges:{user_id}")
            
            # Only invalidate all cat_exchanges entries if neither ex_id nor user_id is provided
            if ex_id is None and user_id is None:
                pattern = "cat_exchanges:*"
                keys = []
                async for key in self._cache.scan_keys(pattern):
                    keys.append(key)
                if keys:
                    await self._cache.delete(*keys)
                
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")

    # WebSocket error management methods
    async def push_ws_error(self, error: str, ex_id: str) -> None:
        """Push WebSocket error to queue.
        
        Args:
            error: Error message
            ex_id: Exchange ID
            
        Example:
            await cache.push_ws_error("Connection lost", "binance_1")
        """
        redis_key = f"ws_error:{ex_id}"
        await self._cache.rpush(redis_key, error)

    async def pop_ws_error(self, ex_id: str, timeout: int = 0) -> str | None:
        """Pop WebSocket error from queue (blocking).
        
        Args:
            ex_id: Exchange ID
            timeout: Blocking timeout in seconds (0 = no timeout)
            
        Returns:
            Error message or None if timeout
            
        Example:
            # Block until error available
            error = await cache.pop_ws_error("binance_1")
            
            # With timeout
            error = await cache.pop_ws_error("binance_1", timeout=5)
        """
        redis_key = f"ws_error:{ex_id}"

        try:
            result = await self._cache.blpop([redis_key], timeout=timeout)
            if result:
                # blpop returns (key, value) tuple
                return result[1]
        except Exception as e:
            logger.error(f"Failed to pop WebSocket error: {e}")

        return None
