"""Trade factory for test data generation."""

from datetime import UTC, datetime
from typing import Any

from fullon_orm.models import Trade


# Trade status and type constants
class TradeStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class TradeType:
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"


class TradeFactory:
    """Factory for creating test trade data."""

    def __init__(self):
        self._counter = 0

    def create(self, as_orm: bool = False, **kwargs) -> dict[str, Any] | Trade:
        """Create trade data with defaults.
        
        Args:
            as_orm: If True, return ORM Trade object instead of dict
            **kwargs: Override any default values
            
        Returns:
            Dictionary with trade data or Trade object
            
        Example:
            factory = TradeFactory()
            
            # Get as dictionary
            trade_dict = factory.create(
                symbol="ETH/USDT",
                amount=1.0,
                price=3000.0
            )
            
            # Get as ORM object
            trade_obj = factory.create(
                as_orm=True,
                symbol="ETH/USDT",
                amount=1.0,
                price=3000.0
            )
        """
        self._counter += 1
        timestamp = datetime.now(UTC)

        defaults = {
            "trade_id": f"TRD{timestamp.strftime('%Y%m%d%H%M%S')}{self._counter:06d}",
            "order_id": f"ORD{timestamp.strftime('%Y%m%d%H%M%S')}{self._counter:06d}",
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "trade_type": TradeType.SPOT.value,
            "amount": 0.1,
            "price": 50000.0,
            "cost": None,  # Will be computed
            "fee": None,
            "fee_currency": "USDT",
            "user_id": 123,
            "bot_id": 1,
            "timestamp": timestamp.isoformat(),
            "exchange_trade_id": f"EX{self._counter}",
            "is_maker": False,
            "metadata": {}
        }

        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)

        # Compute derived fields if not provided
        if result["cost"] is None:
            result["cost"] = result["amount"] * result["price"]

        if result["fee"] is None:
            # Default 0.1% taker fee
            result["fee"] = result["cost"] * 0.001

        # Return as ORM object if requested
        if as_orm:
            return Trade.from_dict(result)

        return result

    def create_sell_trade(self, as_orm: bool = False, **kwargs) -> dict[str, Any] | Trade:
        """Create a sell trade.
        
        Args:
            as_orm: If True, return ORM Trade object
            **kwargs: Additional overrides
            
        Returns:
            Sell trade data or Trade object
        """
        return self.create(
            as_orm=as_orm,
            side="sell",
            **kwargs
        )

    def create_futures_trade(self, **kwargs) -> dict[str, Any]:
        """Create a futures trade.
        
        Args:
            **kwargs: Additional overrides
            
        Returns:
            Futures trade data
        """
        return self.create(
            trade_type=TradeType.FUTURES.value,
            symbol=kwargs.pop("symbol", "BTC-PERP"),
            fee_currency="USD",
            **kwargs
        )

    def create_maker_trade(self, **kwargs) -> dict[str, Any]:
        """Create a maker trade with lower fees.
        
        Args:
            **kwargs: Additional overrides
            
        Returns:
            Maker trade data
        """
        trade = self.create(
            is_maker=True,
            **kwargs
        )

        # Maker fee is typically lower
        if "fee" not in kwargs:
            trade["fee"] = trade["cost"] * 0.0005  # 0.05% maker fee

        return trade

    def create_batch_trades(self,
                           count: int,
                           symbol: str = "BTC/USDT",
                           user_id: int = 123,
                           price_range: tuple = (49000, 51000),
                           **kwargs) -> list:
        """Create multiple trades for analysis.
        
        Args:
            count: Number of trades to create
            symbol: Trading symbol
            user_id: User ID
            price_range: Tuple of (min_price, max_price)
            **kwargs: Additional overrides
            
        Returns:
            List of trade dictionaries
        """
        trades = []
        min_price, max_price = price_range
        price_step = (max_price - min_price) / count if count > 1 else 0

        for i in range(count):
            side = "buy" if i % 2 == 0 else "sell"
            price = min_price + (i * price_step)

            trade = self.create(
                symbol=symbol,
                side=side,
                user_id=user_id,
                price=price,
                amount=0.1 + (i * 0.01),
                **kwargs
            )
            trades.append(trade)

        return trades

    def create_trade_history(self,
                            user_id: int,
                            symbol: str = "BTC/USDT",
                            days: int = 7,
                            trades_per_day: int = 10) -> list:
        """Create historical trades for a user.
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            days: Number of days of history
            trades_per_day: Average trades per day
            
        Returns:
            List of historical trade dictionaries
        """
        from datetime import timedelta
        trades = []

        for day in range(days):
            day_timestamp = datetime.now(UTC) - timedelta(days=day)

            for i in range(trades_per_day):
                # Add some randomness to timestamps
                trade_time = day_timestamp + timedelta(
                    hours=i * (24 / trades_per_day),
                    minutes=(i * 17) % 60  # Some pseudo-randomness
                )

                # Vary price throughout the day
                base_price = 50000 + (day * 100)  # Trend over days
                daily_variation = (i - trades_per_day/2) * 10  # Daily variation
                price = base_price + daily_variation

                trade = self.create(
                    user_id=user_id,
                    symbol=symbol,
                    timestamp=trade_time.isoformat(),
                    price=price,
                    amount=0.1 + (i % 5) * 0.05,
                    side="buy" if i % 3 != 0 else "sell"
                )
                trades.append(trade)

        return trades

    def create_arbitrage_trades(self,
                               symbol: str = "BTC/USDT",
                               exchanges: list = None,
                               price_difference: float = 10.0) -> list:
        """Create trades for arbitrage testing.
        
        Args:
            symbol: Trading symbol
            exchanges: List of exchanges
            price_difference: Price difference between exchanges
            
        Returns:
            List of trades showing arbitrage opportunity
        """
        if exchanges is None:
            exchanges = ["binance", "kraken"]

        if len(exchanges) < 2:
            raise ValueError("Need at least 2 exchanges for arbitrage")

        base_price = 50000.0
        trades = []

        # Buy on first exchange (lower price)
        buy_trade = self.create(
            exchange=exchanges[0],
            symbol=symbol,
            side="buy",
            price=base_price - price_difference/2,
            amount=1.0
        )
        trades.append(buy_trade)

        # Sell on second exchange (higher price)
        sell_trade = self.create(
            exchange=exchanges[1],
            symbol=symbol,
            side="sell",
            price=base_price + price_difference/2,
            amount=1.0,
            timestamp=buy_trade["timestamp"]  # Same time
        )
        trades.append(sell_trade)

        return trades
