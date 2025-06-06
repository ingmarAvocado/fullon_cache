"""Ticker factory for test data generation."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any


class TickerFactory:
    """Factory for creating test ticker data."""
    
    def __init__(self):
        self._counter = 0
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create ticker data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with ticker data
            
        Example:
            factory = TickerFactory()
            ticker = factory.create(
                symbol="ETH/USDT",
                bid=3000.0,
                ask=3001.0
            )
        """
        self._counter += 1
        
        defaults = {
            "bid": 50000.0,
            "ask": 50001.0,
            "last": 50000.5,
            "volume": 1234.56,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bid_size": 1.0,
            "ask_size": 1.0,
            "daily_change": 500.0,
            "daily_change_percent": 1.0,
            "high_24h": 51000.0,
            "low_24h": 49000.0,
            "vwap_24h": 50000.0,
        }
        
        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)
        
        return result
    
    def create_spread(self, base_price: float, spread_percent: float = 0.1, **kwargs) -> Dict[str, Any]:
        """Create ticker with specific spread.
        
        Args:
            base_price: Base price for bid/ask
            spread_percent: Spread as percentage (default 0.1%)
            **kwargs: Additional overrides
            
        Returns:
            Ticker data dictionary
        """
        spread = base_price * (spread_percent / 100)
        bid = base_price - (spread / 2)
        ask = base_price + (spread / 2)
        
        return self.create(
            bid=bid,
            ask=ask,
            last=base_price,
            **kwargs
        )
    
    def create_volatile(self, symbol: str = "BTC/USDT", volatility: float = 5.0, **kwargs) -> Dict[str, Any]:
        """Create ticker with high volatility metrics.
        
        Args:
            symbol: Trading symbol
            volatility: Volatility percentage
            **kwargs: Additional overrides
            
        Returns:
            Ticker data dictionary
        """
        base_price = 50000.0
        change = base_price * (volatility / 100)
        
        return self.create(
            symbol=symbol,
            last=base_price,
            bid=base_price - 10,
            ask=base_price + 10,
            daily_change=change,
            daily_change_percent=volatility,
            high_24h=base_price + change,
            low_24h=base_price - change,
            volume=10000.0,  # High volume
            **kwargs
        )
    
    def create_stale(self, hours_old: int = 24, **kwargs) -> Dict[str, Any]:
        """Create ticker with old timestamp.
        
        Args:
            hours_old: How many hours old the ticker should be
            **kwargs: Additional overrides
            
        Returns:
            Ticker data dictionary
        """
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)
        
        return self.create(
            timestamp=old_time.isoformat(),
            **kwargs
        )
    
    def create_batch(self, count: int, exchange: str = "binance", base_symbol: str = "TEST") -> list:
        """Create multiple tickers.
        
        Args:
            count: Number of tickers to create
            exchange: Exchange name
            base_symbol: Base symbol prefix
            
        Returns:
            List of ticker dictionaries
        """
        tickers = []
        for i in range(count):
            ticker = self.create(
                symbol=f"{base_symbol}{i}/USDT",
                bid=50000.0 + (i * 100),
                ask=50001.0 + (i * 100),
                last=50000.5 + (i * 100),
                volume=1000.0 + (i * 10)
            )
            tickers.append(ticker)
        
        return tickers