"""OHLCV (candlestick) data cache.

This module provides simplified storage and retrieval of OHLCV data
for trading symbols and timeframes.
"""

import json

from fullon_log import get_component_logger

from .base_cache import BaseCache

logger = get_component_logger("fullon.cache.ohlcv")


class OHLCVCache(BaseCache):
    """Cache for OHLCV candlestick data.
    
    This cache provides simplified storage and retrieval of historical
    price data for technical analysis.
    
    Features:
        - Store OHLCV bars for symbols and timeframes
        - Retrieve recent bars
        
    Example:
        cache = OHLCVCache()
        
        # Store OHLCV data
        bars = [
            [1234567890, 50000, 50100, 49900, 50050, 1234.56],
            [1234567950, 50050, 50150, 50000, 50100, 2345.67],
        ]
        await cache.update_ohlcv_bars("BTCUSD", "1h", bars)
        
        # Get recent bars
        recent = await cache.get_latest_ohlcv_bars("BTCUSD", "1h", 100)
    """

    def __init__(self):
        """Initialize the OHLCV cache."""
        super().__init__()

    async def update_ohlcv_bars(self, symbol: str, timeframe: str, bars: list[list[float]]) -> None:
        """Store OHLCV bars for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSD")
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")
            bars: List of OHLCV bars in format [timestamp, open, high, low, close, volume]
            
        Example:
            bars = [
                [1234567890, 50000, 50100, 49900, 50050, 1234.56],
                [1234567950, 50050, 50150, 50000, 50100, 2345.67],
            ]
            await cache.update_ohlcv_bars("BTCUSD", "1h", bars)
        """
        if not bars:
            return

        try:
            # Create key without slashes
            key = f"ohlcv:{symbol}:{timeframe}"

            # Convert bars to JSON strings
            bar_strings = []
            for bar in bars:
                if isinstance(bar, list) and len(bar) >= 6:
                    bar_strings.append(json.dumps(bar))

            if not bar_strings:
                return

            # Store bars (append to list)
            await self.rpush(key, *bar_strings)

            # Keep only the most recent 10000 bars
            await self.ltrim(key, -10000, -1)

        except Exception as e:
            logger.error(f"Error updating OHLCV bars: {e}")

    async def get_latest_ohlcv_bars(self, symbol: str, timeframe: str, count: int) -> list[list[float]]:
        """Get the most recent N OHLCV bars.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSD")
            timeframe: Timeframe (e.g., "1m", "5m", "1h", "1d")
            count: Number of bars to retrieve
            
        Returns:
            List of OHLCV bars (oldest to newest)
            
        Example:
            bars = await cache.get_latest_ohlcv_bars("BTCUSD", "1h", 24)
            # Returns last 24 hourly bars
        """
        try:
            # Create key without slashes
            key = f"ohlcv:{symbol}:{timeframe}"

            # Get recent bars from end of list
            bar_strings = await self.lrange(key, -count, -1)

            bars = []
            for bar_str in bar_strings:
                try:
                    bar = json.loads(bar_str)
                    if isinstance(bar, list) and len(bar) >= 6:
                        bars.append(bar)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse OHLCV bar: {bar_str}")

            return bars

        except Exception as e:
            logger.error(f"Error getting OHLCV bars: {e}")
            return []
