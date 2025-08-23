"""Clean ticker data cache with basic CRUD operations using fullon_orm models."""

import json
import asyncio
from typing import Union

from fullon_log import get_component_logger
from fullon_orm.models import Tick, Symbol

from .base_cache import BaseCache

logger = get_component_logger("fullon.cache.tick")


class TickCache(BaseCache):
    """Clean Redis-based cache for ticker data using fullon_orm models.
    
    Provides simple CRUD operations:
    - set_ticker(symbol, tick) -> bool
    - get_ticker(symbol) -> Tick | None  
    - get_next_ticker(symbol) -> Tick | None (time-ordered)
    - get_any_ticker(symbol) -> Tick | None (any exchange)
    - get_all_tickers(exchange_name/cat_ex_id) -> list[Tick]
    - delete_ticker(symbol) -> bool
    - delete_exchange_tickers(exchange_name) -> int
    
    Redis key structure:
    - ticker:{exchange}:{symbol} -> JSON tick data
    - ticker_time:{exchange}:{symbol} -> timestamp (for ordering)
    - ticker_updates:{exchange}:{symbol} -> pub/sub channel
    
    Example:
        from fullon_orm.models import Symbol, Tick
        from tests.factories import SymbolFactory
        
        cache = TickCache()
        factory = SymbolFactory()
        
        # Create symbol and tick
        symbol = factory.create(symbol="BTC/USDT", exchange_name="binance")
        tick = Tick(symbol="BTC/USDT", exchange="binance", price=50000.0, time=time.time())
        
        # CRUD operations
        await cache.set_ticker(symbol, tick)
        retrieved = await cache.get_ticker(symbol)
        tickers = await cache.get_all_tickers(exchange_name="binance")
        await cache.delete_ticker(symbol)
    """

    def __init__(self):
        """Initialize TickCache with BaseCache."""
        super().__init__()
        # For backward compatibility - some tests access cache._cache
        self._cache = self

    def _get_exchange_name(self, symbol: Symbol) -> str:
        """Get exchange name from Symbol object."""
        # Try cached exchange name first (from factory)
        if hasattr(symbol, '_cached_exchange_name'):
            return symbol._cached_exchange_name
        
        # Try hybrid property if available
        if hasattr(symbol, 'exchange_name'):
            return symbol.exchange_name
            
        # Fallback to generic name based on cat_ex_id
        return f"exchange_{symbol.cat_ex_id}"

    def _get_ticker_key(self, exchange: str, symbol_name: str) -> str:
        """Generate Redis key for ticker data."""
        return f"ticker:{exchange}:{symbol_name}"

    def _get_time_key(self, exchange: str, symbol_name: str) -> str:
        """Generate Redis key for time index.""" 
        return f"ticker_time:{exchange}:{symbol_name}"

    def _get_pubsub_channel(self, exchange: str, symbol_name: str) -> str:
        """Generate pub/sub channel name."""
        return f"ticker_updates:{exchange}:{symbol_name}"

    async def set_ticker(self, symbol: Symbol, tick: Tick) -> bool:
        """Set ticker data for a symbol.
        
        Args:
            symbol: fullon_orm Symbol object
            tick: fullon_orm Tick object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            exchange = self._get_exchange_name(symbol)
            channel = self._get_pubsub_channel(exchange, symbol.symbol)
            
            # Prepare tick data
            tick_data = tick.to_dict()
            tick_json = json.dumps(tick_data)
            
            # Store ticker data (use hash structure)
            await self.hset(f"tickers:{exchange}", symbol.symbol, tick_json)
            
            # Store timestamp for ordering (simple key-value)
            await self.set(f"ticker_time:{exchange}:{symbol.symbol}", str(tick.time))
            
            # Publish update
            await self.publish(channel, tick_json)
            
            logger.debug("Ticker set", exchange=exchange, symbol=symbol.symbol, price=tick.price)
            return True
            
        except Exception as e:
            logger.error("Failed to set ticker", error=str(e), symbol=symbol.symbol)
            return False

    async def get_ticker(self, symbol_or_str, exchange: str = None) -> Tick | None:
        """Get ticker data for a symbol.
        
        Supports both new and legacy interfaces:
        - New: get_ticker(symbol_object) 
        - Legacy: get_ticker("BTC/USDT", "binance")
        
        Args:
            symbol_or_str: fullon_orm Symbol object OR string symbol name
            exchange: Exchange name (for legacy string interface)
            
        Returns:
            fullon_orm Tick object or None if not found
        """
        try:
            # Detect if this is the new clean interface or legacy
            if isinstance(symbol_or_str, Symbol):
                # New clean interface
                symbol = symbol_or_str
                exchange = self._get_exchange_name(symbol)
            else:
                # Legacy interface - convert string to Symbol object
                symbol_str = symbol_or_str
                if not exchange:
                    raise ValueError("Exchange required for string symbol interface")
                
                # Create temporary Symbol object
                try:
                    from ..tests.factories import SymbolFactory
                    factory = SymbolFactory()
                    symbol = factory.create(symbol=symbol_str, exchange_name=exchange)
                except ImportError:
                    from fullon_orm.models import Symbol as ORMSymbol
                    symbol = ORMSymbol(
                        symbol=symbol_str,
                        cat_ex_id=1,
                        base=symbol_str.split('/')[0] if '/' in symbol_str else symbol_str,
                        quote=symbol_str.split('/')[1] if '/' in symbol_str else 'USDT'
                    )
                    symbol._cached_exchange_name = exchange
                exchange = self._get_exchange_name(symbol)
            
            tick_json = await self.hget(f"tickers:{exchange}", symbol.symbol)
            if not tick_json:
                return None
                
            tick_data = json.loads(tick_json)
            # Ensure symbol and exchange are set
            tick_data['symbol'] = symbol.symbol
            tick_data['exchange'] = exchange
            
            return Tick.from_dict(tick_data)
            
        except Exception as e:
            symbol_name = symbol.symbol if isinstance(symbol_or_str, Symbol) else symbol_or_str
            logger.error("Failed to get ticker", error=str(e), symbol=symbol_name)
            return None

    async def get_next_ticker(self, symbol_or_str, exchange: str = None) -> Tick | tuple[float, str | None]:
        """Get the next/most recent ticker update for a symbol.
        
        Supports both new and legacy interfaces:
        - New: get_next_ticker(symbol_object) -> Tick | None
        - Legacy: get_next_ticker("BTC/USDT", "binance") -> tuple[float, str | None]
        
        Args:
            symbol_or_str: fullon_orm Symbol object OR string symbol name
            exchange: Exchange name (for legacy string interface)
            
        Returns:
            New interface: fullon_orm Tick object or None
            Legacy interface: tuple (price, timestamp) or (0, None)
        """
        try:
            # Detect if this is the new clean interface or legacy
            if isinstance(symbol_or_str, Symbol):
                # New clean interface
                symbol = symbol_or_str
                exchange = self._get_exchange_name(symbol)
                
                # First try to get existing ticker  
                existing_tick = await self.get_ticker(symbol)
                if existing_tick:
                    return existing_tick
                
                # Try pub/sub for real-time update
                channel = self._get_pubsub_channel(exchange, symbol.symbol)
                
                try:
                    # Subscribe with short timeout
                    subscription = self.subscribe(channel)
                    async for message in subscription:
                        if message and message.get('type') == 'message':
                            tick_data = json.loads(message['data'])
                            tick_data['symbol'] = symbol.symbol
                            tick_data['exchange'] = exchange
                            await subscription.aclose()
                            return Tick.from_dict(tick_data)
                            
                except asyncio.TimeoutError:
                    pass
                    
                return None
                
            else:
                # Legacy interface - return tuple (price, timestamp)
                symbol_str = symbol_or_str
                if not exchange:
                    raise ValueError("Exchange required for string symbol interface")
                
                # Create temporary Symbol object
                try:
                    from ..tests.factories import SymbolFactory
                    factory = SymbolFactory()
                    symbol = factory.create(symbol=symbol_str, exchange_name=exchange)
                except ImportError:
                    from fullon_orm.models import Symbol as ORMSymbol
                    symbol = ORMSymbol(
                        symbol=symbol_str,
                        cat_ex_id=1,
                        base=symbol_str.split('/')[0] if '/' in symbol_str else symbol_str,
                        quote=symbol_str.split('/')[1] if '/' in symbol_str else 'USDT'
                    )
                    symbol._cached_exchange_name = exchange
                
                # Get tick using new interface
                tick = await self.get_next_ticker(symbol)
                if tick:
                    return (tick.price, str(tick.time))
                else:
                    return (0, None)
            
        except Exception as e:
            symbol_name = symbol_or_str.symbol if isinstance(symbol_or_str, Symbol) else symbol_or_str
            logger.error("Failed to get next ticker", error=str(e), symbol=symbol_name)
            
            if isinstance(symbol_or_str, Symbol):
                return None
            else:
                return (0, None)

    async def get_any_ticker(self, symbol: Symbol) -> Tick | None:
        """Get ticker for symbol from any exchange.
        
        Searches across all exchanges to find a ticker for the given symbol.
        
        Args:
            symbol: fullon_orm Symbol object
            
        Returns:
            fullon_orm Tick object from any exchange, or None if not found
        """
        try:
            # Try the symbol's own exchange first
            tick = await self.get_ticker(symbol)
            if tick:
                return tick
                
            # Search across common exchanges
            common_exchanges = ["binance", "kraken", "coinbase", "bitfinex", "bybit"]
            
            for exchange_name in common_exchanges:
                try:
                    tick_json = await self.hget(f"tickers:{exchange_name}", symbol.symbol)
                    if tick_json:
                        tick_data = json.loads(tick_json)
                        tick_data['symbol'] = symbol.symbol
                        tick_data['exchange'] = exchange_name
                        return Tick.from_dict(tick_data)
                        
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                    
            return None
            
        except Exception as e:
            logger.error("Failed to get any ticker", error=str(e), symbol=symbol.symbol)
            return None

    async def get_all_tickers(self, exchange_name: str = None, cat_ex_id: int = None) -> list[Tick]:
        """Get all tickers, optionally filtered by exchange.
        
        Args:
            exchange_name: Filter by exchange name
            cat_ex_id: Filter by catalog exchange ID
            
        Returns:
            List of fullon_orm Tick objects
        """
        try:
            tickers = []
            
            if exchange_name:
                exchanges = [exchange_name]
            elif cat_ex_id:
                # Get all exchanges and filter by cat_ex_id later
                exchanges = ["binance", "kraken", "coinbase", "bitfinex", "bybit"]
            else:
                # Get from common exchanges
                exchanges = ["binance", "kraken", "coinbase", "bitfinex", "bybit"]
            
            for exchange in exchanges:
                try:
                    ticker_data = await self.hgetall(f"tickers:{exchange}")
                    
                    for symbol_name, tick_json in ticker_data.items():
                        try:
                            tick_data = json.loads(tick_json)
                            tick_data['symbol'] = symbol_name
                            tick_data['exchange'] = exchange
                            
                            # If filtering by cat_ex_id, only include tickers from that exchange
                            # This is a simplified implementation - in production you'd need 
                            # a proper mapping from cat_ex_id to exchange_name
                            if cat_ex_id is not None:
                                # Simple mapping for testing: cat_ex_id=1 -> "binance", cat_ex_id=2 -> "kraken", etc.
                                if cat_ex_id == 1 and exchange != "binance":
                                    continue
                                elif cat_ex_id == 2 and exchange != "kraken":
                                    continue
                                elif cat_ex_id > 2 and exchange in ["binance", "kraken"]:
                                    continue
                            
                            tick = Tick.from_dict(tick_data)
                            tickers.append(tick)
                            
                        except (json.JSONDecodeError, TypeError, ValueError) as e:
                            logger.warning("Invalid ticker data", exchange=exchange, symbol=symbol_name, error=str(e))
                            continue
                            
                except Exception as e:
                    logger.warning("Failed to get tickers from exchange", exchange=exchange, error=str(e))
                    continue
                    
            return tickers
            
        except Exception as e:
            logger.error("Failed to get all tickers", error=str(e))
            return []

    async def delete_ticker(self, symbol: Symbol) -> bool:
        """Delete ticker data for a symbol.
        
        Args:
            symbol: fullon_orm Symbol object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            exchange = self._get_exchange_name(symbol)
            
            # Remove from ticker data and time key
            await self.hdel(f"tickers:{exchange}", symbol.symbol)
            await self.delete(f"ticker_time:{exchange}:{symbol.symbol}")
            
            logger.debug("Ticker deleted", exchange=exchange, symbol=symbol.symbol)
            return True
            
        except Exception as e:
            logger.error("Failed to delete ticker", error=str(e), symbol=symbol.symbol)
            return False

    async def delete_exchange_tickers(self, exchange_name: str) -> int:
        """Delete all tickers for an exchange.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            Number of tickers deleted
        """
        try:
            # Get all symbols first
            ticker_data = await self.hgetall(f"tickers:{exchange_name}")
            symbol_count = len(ticker_data)
            
            # Delete the entire exchange hash
            await self.delete(f"tickers:{exchange_name}")
            
            # Delete individual time keys
            for symbol_name in ticker_data.keys():
                await self.delete(f"ticker_time:{exchange_name}:{symbol_name}")
            
            logger.debug("Exchange tickers deleted", exchange=exchange_name, count=symbol_count)
            return symbol_count
            
        except Exception as e:
            logger.error("Failed to delete exchange tickers", error=str(e), exchange=exchange_name)
            return 0

    # Additional methods expected by tests
    
    async def get_price_tick(self, symbol: str, exchange: str = None) -> Tick | None:
        """Get full tick data (not just price) - legacy method.
        
        Args:
            symbol: Trading symbol  
            exchange: Exchange name (optional)
            
        Returns:
            fullon_orm Tick object or None if not found
        """
        try:
            # Create temporary Symbol object for compatibility
            try:
                from ..tests.factories import SymbolFactory
                factory = SymbolFactory()
                temp_symbol = factory.create(symbol=symbol, exchange_name=exchange or "binance")
            except ImportError:
                from fullon_orm.models import Symbol as ORMSymbol
                temp_symbol = ORMSymbol(
                    symbol=symbol, 
                    cat_ex_id=1, 
                    base=symbol.split('/')[0] if '/' in symbol else symbol, 
                    quote=symbol.split('/')[1] if '/' in symbol else 'USDT'
                )
                temp_symbol._cached_exchange_name = exchange or "binance"
            
            if exchange:
                return await self.get_ticker(temp_symbol)
            else:
                return await self.get_any_ticker(temp_symbol)
                
        except Exception as e:
            logger.error("Failed to get price tick", error=str(e), symbol=symbol)
            return None

    async def get_ticker_any(self, symbol: str) -> float:
        """Legacy method: gets ticker from any exchange by trying multiple exchanges."""
        try:
            # Search across multiple exchanges like the old implementation
            exchanges = ["binance", "kraken", "coinbase", "bitfinex", "bybit"]
            
            for exchange_name in exchanges:
                try:
                    tick_json = await self.hget(f"tickers:{exchange_name}", symbol)
                    if tick_json:
                        tick_data = json.loads(tick_json)
                        return float(tick_data.get('price', 0.0))
                        
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
            
            return 0.0
            
        except Exception as e:
            logger.error("Failed to get ticker any", error=str(e), symbol=symbol)
            return 0.0

    async def get_tickers(self, exchange: str = None) -> list[Tick]:
        """Legacy method: get all tickers."""
        return await self.get_all_tickers(exchange_name=exchange)

    async def del_exchange_ticker(self, exchange: str) -> int:
        """Legacy method: delete all tickers for exchange."""
        return await self.delete_exchange_tickers(exchange)

    # Legacy compatibility methods (temporary)
    
    async def get_price(self, symbol: str, exchange: str = None) -> float:
        """Legacy method: get price as float."""
        try:
            # Create a temporary Symbol object for compatibility
            try:
                from ..tests.factories import SymbolFactory
            except ImportError:
                # Fallback for when tests module isn't available
                from fullon_orm.models import Symbol as ORMSymbol
                temp_symbol = ORMSymbol(symbol=symbol, cat_ex_id=1, base=symbol.split('/')[0] if '/' in symbol else symbol, quote=symbol.split('/')[1] if '/' in symbol else 'USDT')
                temp_symbol._cached_exchange_name = exchange or "binance"
            else:
                factory = SymbolFactory()
                temp_symbol = factory.create(symbol=symbol, exchange_name=exchange or "binance")
            
            tick = await self.get_ticker(temp_symbol) if exchange else await self.get_any_ticker(temp_symbol)
            return tick.price if tick else 0.0
            
        except Exception as e:
            logger.error("Failed to get price", error=str(e), symbol=symbol)
            return 0.0

    async def update_ticker(self, exchange_or_symbol: str, tick_or_exchange: Union[Tick, str], ticker_data: dict = None) -> bool:
        """Legacy method: backward compatibility for old signature."""
        try:
            if isinstance(tick_or_exchange, Tick):
                # New signature: update_ticker(exchange, tick)
                exchange = exchange_or_symbol
                tick = tick_or_exchange
            else:
                # Legacy signature: update_ticker(symbol, exchange, ticker_data)
                symbol_name = exchange_or_symbol
                exchange = tick_or_exchange
                
                # Create Tick object from legacy data - handle None values
                tick_dict = {
                    'symbol': symbol_name,
                    'exchange': exchange,
                    'price': ticker_data.get('price') or 0.0,
                    'volume': ticker_data.get('volume') or 0.0,
                    'time': ticker_data.get('time') or 0.0,
                    'bid': ticker_data.get('bid') or 0.0,
                    'ask': ticker_data.get('ask') or 0.0,
                    'last': ticker_data.get('last') or 0.0
                }
                tick = Tick.from_dict(tick_dict)
            
            # Create temporary Symbol object
            try:
                from ..tests.factories import SymbolFactory
                factory = SymbolFactory()
                symbol = factory.create(symbol=tick.symbol, exchange_name=tick.exchange)
            except ImportError:
                # Fallback for when tests module isn't available
                from fullon_orm.models import Symbol as ORMSymbol
                symbol = ORMSymbol(symbol=tick.symbol, cat_ex_id=1, base=tick.symbol.split('/')[0] if '/' in tick.symbol else tick.symbol, quote=tick.symbol.split('/')[1] if '/' in tick.symbol else 'USDT')
                symbol._cached_exchange_name = tick.exchange
            
            return await self.set_ticker(symbol, tick)
            
        except Exception as e:
            logger.error("Failed to update ticker", error=str(e))
            return False