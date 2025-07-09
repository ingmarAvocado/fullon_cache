"""Symbol information cache.

This module provides caching for trading symbol metadata with automatic
refresh from the database when symbols are not found.
"""

import json
import logging

from fullon_orm import get_async_session
from fullon_orm.models import Symbol
from fullon_orm.repositories import ExchangeRepository, SymbolRepository

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class SymbolCache:
    """Cache for symbol information with auto-refresh.
    
    This cache stores symbol metadata and automatically refreshes from the
    database when a symbol is not found in cache. Returns fullon_orm Symbol
    objects for seamless integration with the ORM layer.
    
    Example:
        cache = SymbolCache()
        
        # Get symbols for an exchange
        symbols = await cache.get_symbols("binance")
        
        # Get specific symbol
        btc_usdt = await cache.get_symbol("BTC/USDT", exchange_name="binance")
        
        # Delete symbol from cache
        await cache.delete_symbol("BTC/USDT", exchange_name="binance")
    """

    def __init__(self):
        """Initialize the symbol cache."""
        self._cache = BaseCache()

    async def close(self):
        """Close the cache connection."""
        await self._cache.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _get_exchange_name_from_cat_ex_id(self, cat_ex_id: str) -> str | None:
        """Get exchange name from cat_ex_id.
        
        Note: This is a simplified implementation.
        In the legacy system this would lookup the exchange name.
        """
        # This would need to be implemented based on your exchange mapping
        # For now, return None to force explicit exchange_name usage
        return None

    async def get_symbols(
        self,
        exchange: str,
        loop: int = 0,
        force: bool = False
    ) -> list[Symbol]:
        """Retrieve symbol information from Redis cache or database.
        
        Args:
            exchange: Exchange name
            loop: Internal counter to prevent infinite recursion
            force: Force database refresh
            
        Returns:
            List of Symbol objects
        """
        redis_key = f"symbols_list:{exchange}"
        symbol_list: list[Symbol] = []

        try:
            if force:
                # Force refresh from database
                async for session in get_async_session():
                    exchange_repo = ExchangeRepository(session)
                    symbol_repo = SymbolRepository(session)

                    # Get exchange by name to find cat_ex_id
                    exchange_obj = await exchange_repo.get_exchange_by_name(exchange)
                    if not exchange_obj:
                        logger.warning(f"Exchange '{exchange}' not found in database")
                        return []

                    # Get symbols for this exchange
                    symbols = await symbol_repo.get_by_exchange_id(exchange_obj.cat_ex_id)
                    if not symbols:
                        return []

                    # Cache each symbol
                    for sym in symbols:
                        sym_dict = sym.to_dict()
                        await self._cache.hset(redis_key, sym.symbol, json.dumps(sym_dict))

                    # Set expiration (24 hours)
                    await self._cache.expire(redis_key, 24 * 60 * 60)
                    return symbols

            # Try to get from cache first
            if await self._cache.exists(redis_key):
                symbols_data = await self._cache.hgetall(redis_key)
                for symbol_name, symbol_json in symbols_data.items():
                    try:
                        symbol_dict = json.loads(symbol_json)
                        symbol_obj = Symbol.from_dict(symbol_dict)
                        symbol_list.append(symbol_obj)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.error(f"Error parsing cached symbol {symbol_name}: {e}")
                        continue
            elif loop == 0:
                # Cache miss, try to refresh from database
                symbol_list = await self.get_symbols(exchange=exchange, loop=1, force=True)

        except Exception as e:
            logger.error(f"Error getting symbols for exchange {exchange}: {e}")

        return symbol_list

    async def get_symbols_by_ex_id(
        self,
        ex_id: int,
        loop: int = 0,
        force: bool = False
    ) -> list[Symbol]:
        """Retrieve symbol information for a specific exchange ID.
        
        Args:
            ex_id: The exchange ID to get symbols for
            loop: Internal counter to prevent infinite recursion
            force: Force database refresh
            
        Returns:
            List of Symbol objects
        """
        redis_key = f"symbols_list:ex_id:{ex_id}"
        symbol_list: list[Symbol] = []

        try:
            if force:
                # Force refresh from database
                async for session in get_async_session():
                    symbol_repo = SymbolRepository(session)
                    symbols = await symbol_repo.get_by_exchange_id(ex_id)
                    if not symbols:
                        return []

                    # Cache each symbol
                    for sym in symbols:
                        sym_dict = sym.to_dict()
                        await self._cache.hset(redis_key, sym.symbol, json.dumps(sym_dict))

                    # Set expiration (24 hours)
                    await self._cache.expire(redis_key, 24 * 60 * 60)
                    return symbols

            # Try to get from cache first
            if await self._cache.exists(redis_key):
                symbols_data = await self._cache.hgetall(redis_key)
                for symbol_name, symbol_json in symbols_data.items():
                    try:
                        symbol_dict = json.loads(symbol_json)
                        symbol_obj = Symbol.from_dict(symbol_dict)
                        symbol_list.append(symbol_obj)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.error(f"Error parsing cached symbol {symbol_name}: {e}")
                        continue
            elif loop == 0:
                # Cache miss, try to refresh from database
                symbol_list = await self.get_symbols_by_ex_id(ex_id=ex_id, loop=1, force=True)

        except Exception as e:
            logger.error(f"Error getting symbols for exchange ID {ex_id}: {e}")

        return symbol_list

    async def get_symbol(
        self,
        symbol: str,
        cat_ex_id: str | None = None,
        exchange_name: str | None = None,
        loop: int = 0
    ) -> Symbol | None:
        """Retrieve symbol information from Redis cache or database.
        
        Args:
            symbol: The symbol to search for
            cat_ex_id: The cat_ex_id (optional)
            exchange_name: The exchange name (optional)
            loop: Internal recursion counter
            
        Returns:
            Symbol object or None if not found
        """
        if not exchange_name and cat_ex_id:
            exchange_name = self._get_exchange_name_from_cat_ex_id(cat_ex_id)

        if not exchange_name:
            logger.error(f"Cannot get symbol {symbol}: exchange_name is required")
            return None

        redis_key = f'symbols_list:{exchange_name}'
        symbol_obj = None

        try:
            while not symbol_obj:
                if await self._cache.exists(redis_key):
                    symbol_json = await self._cache.hget(redis_key, symbol)
                    if symbol_json:
                        try:
                            symbol_dict = json.loads(symbol_json)
                            symbol_obj = Symbol.from_dict(symbol_dict)
                        except (json.JSONDecodeError, Exception) as e:
                            logger.error(f"Error parsing symbol {symbol}: {e}")
                            break
                    elif loop == 0:
                        # Symbol not in cache, refresh from database
                        await self.get_symbols(exchange=exchange_name, force=True)
                        loop = 1
                    else:
                        # Already tried refresh, symbol doesn't exist
                        break
                else:
                    if loop == 0:
                        # Cache doesn't exist, refresh from database
                        await self.get_symbols(exchange=exchange_name, force=True)
                        loop = 1
                    else:
                        # Already tried refresh, cache still doesn't exist
                        break

        except Exception as e:
            logger.error(f"Error getting symbol {symbol} from cache: {e}")

        return symbol_obj

    # New ORM-based methods (Recommended)
    async def add_symbol(self, symbol: Symbol) -> bool:
        """Add symbol using fullon_orm.Symbol model.
        
        Args:
            symbol: fullon_orm.Symbol model instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            redis_key = f"symbols_list:{exchange_name}"
            
            # Convert Symbol to dict for Redis storage
            symbol_dict = symbol.to_dict()
            
            # Store in Redis hash
            await self._cache.hset(redis_key, symbol.symbol, json.dumps(symbol_dict))
            
            # Set expiration (24 hours)
            await self._cache.expire(redis_key, 24 * 60 * 60)
            return True
            
        except Exception as e:
            logger.error(f"Failed to add symbol: {e}")
            return False

    async def update_symbol(self, symbol: Symbol) -> bool:
        """Update symbol using fullon_orm.Symbol model.
        
        Args:
            symbol: fullon_orm.Symbol model instance with updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            redis_key = f"symbols_list:{exchange_name}"
            
            # Convert Symbol to dict for Redis storage
            symbol_dict = symbol.to_dict()
            
            # Update in Redis hash
            await self._cache.hset(redis_key, symbol.symbol, json.dumps(symbol_dict))
            
            # Set expiration (24 hours)
            await self._cache.expire(redis_key, 24 * 60 * 60)
            return True
            
        except Exception as e:
            logger.error(f"Failed to update symbol: {e}")
            return False

    async def delete_symbol_orm(self, symbol: Symbol) -> bool:
        """Delete symbol using fullon_orm.Symbol model.
        
        Args:
            symbol: fullon_orm.Symbol model instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            # Remove from symbols list
            symbols_key = f'symbols_list:{exchange_name}'
            if await self._cache.exists(symbols_key):
                await self._cache.hdel(symbols_key, symbol.symbol)

            # Also remove from tickers if it exists
            tickers_key = f'tickers:{exchange_name}'
            if await self._cache.exists(tickers_key):
                await self._cache.hdel(tickers_key, symbol.symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete symbol: {e}")
            return False

    async def get_symbol_by_model(self, symbol: Symbol) -> Symbol | None:
        """Get symbol using fullon_orm.Symbol model as search criteria.
        
        Args:
            symbol: fullon_orm.Symbol model with search criteria
            
        Returns:
            fullon_orm.Symbol model or None if not found
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            redis_key = f'symbols_list:{exchange_name}'
            
            if await self._cache.exists(redis_key):
                symbol_json = await self._cache.hget(redis_key, symbol.symbol)
                if symbol_json:
                    try:
                        symbol_dict = json.loads(symbol_json)
                        return Symbol.from_dict(symbol_dict)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.error(f"Error parsing symbol {symbol.symbol}: {e}")
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get symbol: {e}")
            return None

    async def symbol_exists(self, symbol: Symbol) -> bool:
        """Check if symbol exists using fullon_orm.Symbol model.
        
        Args:
            symbol: fullon_orm.Symbol model to check
            
        Returns:
            True if symbol exists, False otherwise
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            redis_key = f'symbols_list:{exchange_name}'
            
            if await self._cache.exists(redis_key):
                symbol_json = await self._cache.hget(redis_key, symbol.symbol)
                return symbol_json is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check symbol existence: {e}")
            return False

    async def get_symbols_for_exchange(self, symbol: Symbol) -> list[Symbol]:
        """Get all symbols for the same exchange as the provided symbol.
        
        Args:
            symbol: fullon_orm.Symbol model to identify exchange
            
        Returns:
            List of fullon_orm.Symbol models for the same exchange
        """
        try:
            # Get exchange name from symbol's cat_ex_id
            exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
            if not exchange_name:
                # Fallback to a default mapping - in production this should be proper mapping
                exchange_name = "binance"  # This should be resolved from cat_ex_id
            
            # Use existing get_symbols method
            return await self.get_symbols(exchange_name)
            
        except Exception as e:
            logger.error(f"Failed to get symbols for exchange: {e}")
            return []

    # Legacy methods for backward compatibility
    async def delete_symbol(
        self,
        symbol: str,
        cat_ex_id: str | None = None,
        exchange_name: str | None = None
    ) -> None:
        """Remove a symbol from the Redis cache (legacy method).
        
        Args:
            symbol: The symbol to remove
            cat_ex_id: The cat_ex_id (optional)
            exchange_name: The exchange name (optional)
        """
        if not exchange_name and cat_ex_id:
            exchange_name = self._get_exchange_name_from_cat_ex_id(cat_ex_id)

        if not exchange_name:
            logger.error(f"Cannot delete symbol {symbol}: exchange_name is required")
            return

        try:
            # Remove from symbols list
            redis_key = f'symbols_list:{exchange_name}'
            if await self._cache.exists(redis_key):
                await self._cache.hdel(redis_key, symbol)

            # Also remove from tickers if it exists
            tickers_key = f'tickers:{exchange_name}'
            if await self._cache.exists(tickers_key):
                await self._cache.hdel(tickers_key, symbol)

        except Exception as e:
            logger.error(f"Error deleting symbol {symbol}: {e}")

    def _get_exchange_name_from_symbol(self, symbol: Symbol) -> str:
        """Get exchange name from Symbol model (helper method)."""
        exchange_name = self._get_exchange_name_from_cat_ex_id(str(symbol.cat_ex_id))
        if not exchange_name:
            # Fallback - in production this should be proper mapping
            exchange_name = "binance"
        return exchange_name
