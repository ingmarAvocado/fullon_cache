"""Order factory for test data generation."""

from datetime import UTC, datetime
from typing import Any


class OrderFactory:
    """Factory for creating test order data."""

    def __init__(self):
        self._counter = 0

    def create(self, **kwargs) -> dict[str, Any]:
        """Create order data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with order data
            
        Example:
            factory = OrderFactory()
            order = factory.create(
                symbol="ETH/USDT",
                amount=1.0,
                price=3000.0
            )
        """
        self._counter += 1
        timestamp = datetime.now(UTC)

        defaults = {
            "order_id": f"ORD{timestamp.strftime('%Y%m%d%H%M%S')}{self._counter:06d}",
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "order_type": "limit",
            "volume": 0.1,
            "price": 50000.0,
            "status": "pending",
            "uid": 123,
            "bot_id": 1,
            "ex_id": 1,
            "cat_ex_id": 1,
            "final_volume": 0.0,
            "command": None,
            "reason": "",
            "futures": False,
            "leverage": None,
            "tick": None,
            "plimit": None,
            "timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        }

        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)

        return result

    def create_market_order(self, side: str = "buy", **kwargs) -> dict[str, Any]:
        """Create a market order.
        
        Args:
            side: Order side (buy/sell)
            **kwargs: Additional overrides
            
        Returns:
            Market order data
        """
        return self.create(
            order_type="market",
            side=side,
            price=None,  # Market orders don't have price
            **kwargs
        )

    def create_stop_order(self, stop_price: float, **kwargs) -> dict[str, Any]:
        """Create a stop order.
        
        Args:
            stop_price: Stop trigger price
            **kwargs: Additional overrides
            
        Returns:
            Stop order data
        """
        return self.create(
            order_type="stop",
            plimit=stop_price,
            **kwargs
        )

    def create_filled_order(self, fill_percent: float = 100.0, **kwargs) -> dict[str, Any]:
        """Create a partially or fully filled order.
        
        Args:
            fill_percent: Percentage filled (0-100)
            **kwargs: Additional overrides
            
        Returns:
            Filled order data
        """
        order = self.create(**kwargs)

        filled_volume = order["volume"] * (fill_percent / 100)
        order["final_volume"] = filled_volume

        if fill_percent >= 100:
            order["status"] = "filled"
        elif fill_percent > 0:
            order["status"] = "partially_filled"

        return order

    def create_cancelled_order(self, reason: str = "User cancelled", **kwargs) -> dict[str, Any]:
        """Create a cancelled order.
        
        Args:
            reason: Cancellation reason
            **kwargs: Additional overrides
            
        Returns:
            Cancelled order data
        """
        return self.create(
            status="cancelled",
            reason=reason,
            **kwargs
        )

    def create_batch(self,
                    count: int,
                    exchange: str = "binance",
                    symbol: str = "BTC/USDT",
                    side_alternating: bool = True) -> list:
        """Create multiple orders.
        
        Args:
            count: Number of orders to create
            exchange: Exchange name
            symbol: Trading symbol
            side_alternating: Alternate between buy/sell
            
        Returns:
            List of order dictionaries
        """
        orders = []

        for i in range(count):
            side = "buy" if (i % 2 == 0 or not side_alternating) else "sell"

            order = self.create(
                exchange=exchange,
                symbol=symbol,
                side=side,
                volume=0.1 * (i + 1),
                price=50000.0 + (i * 10),
                uid=100 + (i % 10),
                bot_id=1 + (i % 5)
            )
            orders.append(order)

        return orders

    def create_order_book_snapshot(self,
                                  symbol: str = "BTC/USDT",
                                  mid_price: float = 50000.0,
                                  depth: int = 5,
                                  spread: float = 10.0) -> tuple:
        """Create matching buy and sell orders for order book.
        
        Args:
            symbol: Trading symbol
            mid_price: Middle price
            depth: Number of orders on each side
            spread: Price spread between orders
            
        Returns:
            Tuple of (buy_orders, sell_orders)
        """
        buy_orders = []
        sell_orders = []

        for i in range(depth):
            # Buy orders below mid price
            buy_order = self.create(
                symbol=symbol,
                side="buy",
                price=mid_price - (i + 1) * spread,
                volume=0.5 * (i + 1)
            )
            buy_orders.append(buy_order)

            # Sell orders above mid price
            sell_order = self.create(
                symbol=symbol,
                side="sell",
                price=mid_price + (i + 1) * spread,
                volume=0.5 * (i + 1)
            )
            sell_orders.append(sell_order)

        return buy_orders, sell_orders
