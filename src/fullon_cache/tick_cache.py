"""Simplified ticker data cache with essential operations only.

This module provides basic caching for cryptocurrency ticker data
with real-time updates via Redis pub/sub.
"""

import asyncio
import json
import logging
from typing import Any

from fullon_orm.models import Tick
from fullon_orm.repositories import ExchangeRepository

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class TickCache:
    """Simplified cache for ticker data with essential operations only.
    
    Provides basic ticker CRUD operations and pub/sub functionality
    following the legacy interface while using modern async patterns.
    
    Example:
        cache = TickCache()
        
        # Update ticker
        result = await cache.update_ticker("BTC/USDT", "binance", {
            "price": 50000.0,
            "volume": 1234.56,
            "time": "2023-01-01T00:00:00Z"
        })
        
        # Get ticker
        price, timestamp = await cache.get_ticker("BTC/USDT", "binance")
        
        # Subscribe to updates
        price, timestamp = await cache.get_next_ticker("BTC/USDT", "binance")
    """

    def __init__(self):
        """Initialize tick cache with BaseCache composition."""
        self._cache = BaseCache()

    async def get_price(self, symbol: str, exchange: str | None = None) -> float:
        """Get the price for a symbol, optionally using a specific exchange.

        Args:
            symbol: The trading symbol to get the price for
            exchange: The exchange to use. If None, uses any exchange

        Returns:
            The price of the symbol, or 0 if not found
        """
        try:
            if exchange:
                price, _ = await self.get_ticker(symbol=symbol, exchange=exchange)
                return price if price is not None else 0
            else:
                return await self.get_ticker_any(symbol=symbol)
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0

    async def update_ticker(self, symbol: str, exchange: str, data: dict[str, Any]) -> int:
        """Update the ticker data for a symbol on a specific exchange and notify subscribers.

        Args:
            symbol: The trading symbol to update the ticker for
            exchange: The exchange to update the ticker on
            data: The new ticker data

        Returns:
            1 if the ticker was updated successfully, 0 otherwise
        """
        try:
            # Store ticker data in Redis hash
            await self._cache.hset(f"tickers:{exchange}", symbol, json.dumps(data))

            # Publish message to subscribers
            channel = f'next_ticker:{exchange}:{symbol}'
            await self._cache.publish(channel, json.dumps(data))

            return 1
        except Exception as e:
            logger.error(f"Can't save ticker {symbol}:{data} - {str(e)}")
            return 0

    async def del_exchange_ticker(self, exchange: str) -> int:
        """Delete all tickers for a specific exchange.

        Args:
            exchange: The exchange to delete tickers for

        Returns:
            Number of keys deleted
        """
        try:
            return await self._cache.delete(f"tickers:{exchange}")
        except Exception as e:
            logger.error(f"Error deleting exchange ticker {exchange}: {e}")
            return 0

    async def get_next_ticker(self, symbol: str, exchange: str) -> tuple[float, str | None]:
        """Subscribe to a ticker update channel and return the price and timestamp once a message is received.
        
        Args:
            symbol: The trading symbol for which ticker updates are being listened
            exchange: The exchange that the symbol belongs to

        Returns:
            Tuple containing the updated price as a float and the timestamp as a string.
            If an error occurs, (0, None) is returned.
        """
        try:
            channel = f'next_ticker:{exchange}:{symbol}'

            async for message in self._cache.subscribe(channel):
                if message and message.get('type') == 'message':
                    ticker = json.loads(message['data'])
                    return (float(ticker['price']), ticker['time'])

            return (0, None)
        except TimeoutError:
            logger.warning(f"No ticker ({exchange}:{symbol}) data received, trying again...")
            await asyncio.sleep(0.1)
            return await self.get_next_ticker(symbol=symbol, exchange=exchange)
        except Exception as e:
            logger.error(f"Error in get_next_ticker: {e}")
            return (0, None)

    async def get_ticker_any(self, symbol: str) -> float:
        """Gets ticker from any exchange given the symbol.

        Args:
            symbol: the symbol to look for (e.g. BTC/USD)

        Returns:
            the ticker price or 0 if not found
        """
        try:
            # Get available exchanges from fullon_orm
            from fullon_orm import get_async_session
            async with get_async_session() as session:
                exchange_repo = ExchangeRepository(session)
                exchanges = await exchange_repo.get_cat_exchanges(all=True)

            for exchange_obj in exchanges:
                try:
                    ticker_data = await self._cache.hget(f"tickers:{exchange_obj.name}", symbol)
                    if ticker_data:
                        ticker = json.loads(ticker_data)
                        return float(ticker['price'])
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
            return 0
        except Exception as e:
            logger.error(f"Error in get_ticker_any: {e}")
            return 0

    async def get_ticker(self, symbol: str, exchange: str | None = None) -> tuple[float | None, str | None]:
        """Gets ticker from the database for a symbol, optionally from a specific exchange.

        Args:
            symbol: The symbol to look for (e.g. BTC/USD)
            exchange: The exchange name. If None, will return first matching ticker from any exchange.

        Returns:
            tuple: A tuple containing the ticker price (float) and timestamp (str), or (0, None) if not found.
        """
        try:
            if exchange:
                ticker_data = await self._cache.hget(f"tickers:{exchange}", symbol)
                if ticker_data:
                    ticker = json.loads(ticker_data)
                    return (float(ticker['price']), ticker['time'])
            else:
                # Search across all exchanges
                from fullon_orm import get_async_session
                async with get_async_session() as session:
                    exchange_repo = ExchangeRepository(session)
                    exchanges = await exchange_repo.get_cat_exchanges(all=True)

                for exchange_obj in exchanges:
                    ticker_data = await self._cache.hget(f"tickers:{exchange_obj.name}", symbol)
                    if ticker_data:
                        ticker = json.loads(ticker_data)
                        return (float(ticker['price']), ticker['time'])

            return (0, None)
        except (TypeError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Error getting ticker {symbol}: {e}")
            return (0, None)

    async def get_tickers(self, exchange: str | None = "") -> list[Tick]:
        """Gets all tickers from the database, from the specified exchange or all exchanges.

        Args:
            exchange: The exchange to use. If empty, returns from all exchanges.

        Returns:
            List of Tick objects
        """
        try:
            rows = []

            if exchange:
                exchanges = [exchange]
            else:
                # Get all exchanges from fullon_orm
                from fullon_orm import get_async_session
                async with get_async_session() as session:
                    exchange_repo = ExchangeRepository(session)
                    exchange_objs = await exchange_repo.get_cat_exchanges(all=True)
                    exchanges = [ex.name for ex in exchange_objs]

            for exch in exchanges:
                ticker_data = await self._cache.hgetall(f"tickers:{exch}")
                for symbol, value in ticker_data.items():
                    try:
                        values = json.loads(value)
                        values['exchange'] = exch
                        values['symbol'] = symbol

                        # Convert to fullon_orm Tick using from_dict
                        tick = Tick.from_dict(values)
                        rows.append(tick)
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        logger.warning(f"Failed to parse ticker data for {exch}:{symbol}: {e}")
                        continue

            return rows
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
            return []

    async def get_tick_crawlers(self) -> dict[str, Any]:
        """Get all tick crawlers that are supposed to be running.

        Returns:
            A dictionary of tick crawlers, where keys are crawler names
            and values are their respective configurations.

        Raises:
            ValueError: If there's an issue processing the Redis data.
        """
        try:
            raw_data = await self._cache.hgetall('tick')
            if not raw_data:
                return {}

            result = {}
            for key, value in raw_data.items():
                try:
                    crawler_data = json.loads(value)
                    result[key] = crawler_data
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to process data for {key}: {e}")
                    continue

            return result
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise ValueError("Failed to process tick crawlers data") from e

    async def round_down(self, symbol: str, exchange: str, sizes: list[float], futures: bool) -> tuple[float, float, float]:
        """Rounds down the sizes for a symbol on a specific exchange.

        Args:
            symbol: The trading symbol to round down
            exchange: The exchange to use
            sizes: A list of sizes (free, used, and total)
            futures: Whether to use futures or not

        Returns:
            The rounded down sizes
        """
        try:
            if sizes[0] == 0 and sizes[1] == 0 and sizes[2] == 0:
                return 0, 0, 0

            if '/' in symbol:
                currency = symbol.split('/')[0]
                if currency == 'BTC' or futures:
                    return tuple(sizes)
            else:
                return tuple(sizes)

            price, _ = await self.get_ticker(exchange=exchange, symbol=symbol)
            if not price:
                return 0, 0, 0

            base_currency = symbol.split('/')[1]
            # Use USDT as stable coin default
            stable_coin = "USDT"
            tsymbol = f"{base_currency}/{stable_coin}"

            for count, value in enumerate(sizes):
                base = value * price
                if 'USD' in base_currency:
                    sizes[count] = base
                else:
                    # Get conversion rate to stable coin
                    conversion_price = await self.get_price(tsymbol)
                    sizes[count] = base * conversion_price if conversion_price else 0

            if sizes[0] < 2:  # less than 2 usd in value
                return 0, 0, 0

            return tuple(sizes)
        except Exception as e:
            logger.error(f"Error in round_down for {symbol}: {e}")
            return 0, 0, 0
