"""OHLCV factory for test data generation."""

from datetime import UTC, datetime, timedelta


class OHLCVFactory:
    """Factory for creating test OHLCV (candlestick) data."""

    def __init__(self):
        self._counter = 0

    def create(self, **kwargs) -> list[float]:
        """Create a single OHLCV bar.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            List of [timestamp, open, high, low, close, volume]
            
        Example:
            factory = OHLCVFactory()
            bar = factory.create(
                open=50000,
                close=50100,
                volume=100.5
            )
        """
        self._counter += 1

        # Default values
        timestamp = kwargs.get('timestamp', datetime.now(UTC).timestamp() * 1000)
        open_price = kwargs.get('open', 50000.0)
        high = kwargs.get('high')
        low = kwargs.get('low')
        close = kwargs.get('close', open_price + 10)
        volume = kwargs.get('volume', 1000.0)

        # Auto-calculate high/low if not provided
        if high is None:
            high = max(open_price, close) * 1.001  # 0.1% above max
        if low is None:
            low = min(open_price, close) * 0.999   # 0.1% below min

        # Ensure high/low bounds are correct
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        return [timestamp, open_price, high, low, close, volume]

    def create_series(self,
                     count: int = 100,
                     timeframe: str = "1h",
                     start_time: datetime | None = None,
                     trend: str = "sideways",
                     volatility: float = 0.02) -> list[list[float]]:
        """Create a series of OHLCV bars.
        
        Args:
            count: Number of bars to create
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            start_time: Starting timestamp
            trend: Market trend (up, down, sideways)
            volatility: Price volatility as percentage
            
        Returns:
            List of OHLCV bars
        """
        if start_time is None:
            start_time = datetime.now(UTC) - timedelta(hours=count)

        # Parse timeframe to minutes
        timeframe_minutes = self._parse_timeframe(timeframe)

        bars = []
        base_price = 50000.0

        for i in range(count):
            # Calculate timestamp
            bar_time = start_time + timedelta(minutes=i * timeframe_minutes)
            timestamp = bar_time.timestamp() * 1000

            # Calculate price based on trend
            if trend == "up":
                trend_factor = 1 + (i / count) * 0.1  # 10% uptrend
            elif trend == "down":
                trend_factor = 1 - (i / count) * 0.1  # 10% downtrend
            else:
                trend_factor = 1.0  # Sideways

            # Add some randomness
            import random
            random_factor = 1 + (random.random() - 0.5) * volatility

            # Calculate OHLC
            open_price = base_price * trend_factor * random_factor

            # Intrabar movement
            high_factor = 1 + random.random() * volatility / 2
            low_factor = 1 - random.random() * volatility / 2
            close_factor = 1 + (random.random() - 0.5) * volatility

            high = open_price * high_factor
            low = open_price * low_factor
            close = open_price * close_factor

            # Ensure bounds
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Volume with some randomness
            volume = 1000 * (1 + random.random())

            bar = [timestamp, open_price, high, low, close, volume]
            bars.append(bar)

            # Use close as next open for continuity
            base_price = close

        return bars

    def create_bullish_bar(self, open_price: float = 50000, gain_percent: float = 2.0) -> list[float]:
        """Create a bullish candlestick.
        
        Args:
            open_price: Opening price
            gain_percent: Percentage gain
            
        Returns:
            Bullish OHLCV bar
        """
        close = open_price * (1 + gain_percent / 100)
        high = close * 1.002  # Small wick
        low = open_price * 0.999  # Small lower shadow

        return self.create(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=2000  # Higher volume on bullish moves
        )

    def create_bearish_bar(self, open_price: float = 50000, loss_percent: float = 2.0) -> list[float]:
        """Create a bearish candlestick.
        
        Args:
            open_price: Opening price
            loss_percent: Percentage loss
            
        Returns:
            Bearish OHLCV bar
        """
        close = open_price * (1 - loss_percent / 100)
        high = open_price * 1.001  # Small upper shadow
        low = close * 0.998  # Small wick

        return self.create(
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=2500  # Higher volume on bearish moves
        )

    def create_doji(self, price: float = 50000) -> list[float]:
        """Create a doji candlestick (open = close).
        
        Args:
            price: Price level
            
        Returns:
            Doji OHLCV bar
        """
        return self.create(
            open=price,
            high=price * 1.005,
            low=price * 0.995,
            close=price,
            volume=500  # Low volume on indecision
        )

    def create_gap_series(self,
                         count: int = 10,
                         gap_percent: float = 1.0,
                         timeframe: str = "1d") -> list[list[float]]:
        """Create OHLCV series with gaps between bars.
        
        Args:
            count: Number of bars
            gap_percent: Gap size as percentage
            timeframe: Timeframe
            
        Returns:
            List of OHLCV bars with gaps
        """
        bars = []
        base_price = 50000.0
        start_time = datetime.now(UTC) - timedelta(days=count)
        timeframe_minutes = self._parse_timeframe(timeframe)

        for i in range(count):
            bar_time = start_time + timedelta(minutes=i * timeframe_minutes)
            timestamp = bar_time.timestamp() * 1000

            # Create gap from previous close
            if i > 0 and i % 3 == 0:  # Gap every 3rd bar
                gap = base_price * (gap_percent / 100)
                open_price = base_price + gap if i % 2 == 0 else base_price - gap
            else:
                open_price = base_price

            # Normal bar movement
            close = open_price * (1 + (0.01 if i % 2 == 0 else -0.01))
            high = max(open_price, close) * 1.002
            low = min(open_price, close) * 0.998

            bar = [timestamp, open_price, high, low, close, 1000.0]
            bars.append(bar)

            base_price = close

        return bars

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to minutes.
        
        Args:
            timeframe: Timeframe string (1m, 5m, 1h, etc.)
            
        Returns:
            Number of minutes
        """
        multipliers = {
            'm': 1,
            'h': 60,
            'd': 1440,
            'w': 10080
        }

        # Extract number and unit
        import re
        match = re.match(r'(\d+)([mhdw])', timeframe.lower())
        if not match:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        number = int(match.group(1))
        unit = match.group(2)

        return number * multipliers.get(unit, 1)
