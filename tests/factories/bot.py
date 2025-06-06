"""Bot factory for test data generation."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class BotFactory:
    """Factory for creating test bot data."""
    
    def __init__(self):
        self._counter = 0
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create bot data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with bot data
            
        Example:
            factory = BotFactory()
            bot = factory.create(
                name="arbitrage_bot_1",
                strategy="arbitrage",
                exchanges=["binance", "kraken"]
            )
        """
        self._counter += 1
        
        defaults = {
            "bot_id": self._counter,
            "name": f"test_bot_{self._counter}",
            "user_id": 123,
            "strategy": "grid",
            "status": "running",
            "exchanges": ["binance"],
            "symbols": ["BTC/USDT"],
            "config": {
                "grid_levels": 10,
                "investment": 10000.0,
                "min_price": 45000.0,
                "max_price": 55000.0,
            },
            "performance": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "roi": 0.0,
            },
            "active": True,
            "opening_position": False,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)
        
        return result
    
    def create_grid_bot(self,
                       symbol: str = "BTC/USDT",
                       grid_levels: int = 20,
                       price_range: tuple = (45000, 55000),
                       **kwargs) -> Dict[str, Any]:
        """Create a grid trading bot.
        
        Args:
            symbol: Trading symbol
            grid_levels: Number of grid levels
            price_range: Tuple of (min_price, max_price)
            **kwargs: Additional overrides
            
        Returns:
            Grid bot data
        """
        min_price, max_price = price_range
        
        return self.create(
            strategy="grid",
            symbols=[symbol],
            config={
                "grid_levels": grid_levels,
                "min_price": min_price,
                "max_price": max_price,
                "investment": 10000.0,
                "order_size": 100.0,
                "grid_spacing": (max_price - min_price) / grid_levels,
            },
            **kwargs
        )
    
    def create_arbitrage_bot(self,
                            exchanges: List[str] = None,
                            symbols: List[str] = None,
                            min_profit: float = 0.1,
                            **kwargs) -> Dict[str, Any]:
        """Create an arbitrage bot.
        
        Args:
            exchanges: List of exchanges to monitor
            symbols: List of symbols to trade
            min_profit: Minimum profit percentage
            **kwargs: Additional overrides
            
        Returns:
            Arbitrage bot data
        """
        if exchanges is None:
            exchanges = ["binance", "kraken", "coinbase"]
        if symbols is None:
            symbols = ["BTC/USDT", "ETH/USDT"]
        
        return self.create(
            strategy="arbitrage",
            exchanges=exchanges,
            symbols=symbols,
            config={
                "min_profit_percent": min_profit,
                "max_position_size": 10000.0,
                "slippage_tolerance": 0.05,
                "execution_delay_ms": 100,
            },
            **kwargs
        )
    
    def create_dca_bot(self,
                      symbol: str = "BTC/USDT",
                      interval_hours: int = 24,
                      amount_per_order: float = 100.0,
                      **kwargs) -> Dict[str, Any]:
        """Create a DCA (Dollar Cost Averaging) bot.
        
        Args:
            symbol: Trading symbol
            interval_hours: Hours between purchases
            amount_per_order: Amount to buy each time
            **kwargs: Additional overrides
            
        Returns:
            DCA bot data
        """
        return self.create(
            strategy="dca",
            symbols=[symbol],
            config={
                "interval_hours": interval_hours,
                "amount_per_order": amount_per_order,
                "total_budget": 10000.0,
                "orders_placed": 0,
                "last_order_time": None,
                "average_price": 0.0,
            },
            **kwargs
        )
    
    def create_market_maker_bot(self,
                               symbol: str = "BTC/USDT",
                               spread: float = 0.1,
                               **kwargs) -> Dict[str, Any]:
        """Create a market maker bot.
        
        Args:
            symbol: Trading symbol
            spread: Spread percentage
            **kwargs: Additional overrides
            
        Returns:
            Market maker bot data
        """
        return self.create(
            strategy="market_maker",
            symbols=[symbol],
            config={
                "spread_percent": spread,
                "order_size": 0.1,
                "max_orders_per_side": 5,
                "order_refresh_seconds": 30,
                "inventory_target": 0.5,  # Target 50% of each asset
                "min_spread": 0.05,
                "max_spread": 0.5,
            },
            **kwargs
        )
    
    def create_stopped_bot(self, stop_reason: str = "User stopped", **kwargs) -> Dict[str, Any]:
        """Create a stopped bot.
        
        Args:
            stop_reason: Reason for stopping
            **kwargs: Additional overrides
            
        Returns:
            Stopped bot data
        """
        return self.create(
            status="stopped",
            active=False,
            config={
                "stop_reason": stop_reason,
                "stopped_at": datetime.now(timezone.utc).isoformat(),
            },
            **kwargs
        )
    
    def create_profitable_bot(self,
                             total_trades: int = 100,
                             win_rate: float = 0.65,
                             avg_profit: float = 50.0,
                             **kwargs) -> Dict[str, Any]:
        """Create a bot with profitable performance.
        
        Args:
            total_trades: Total number of trades
            win_rate: Win rate (0-1)
            avg_profit: Average profit per winning trade
            **kwargs: Additional overrides
            
        Returns:
            Profitable bot data
        """
        winning_trades = int(total_trades * win_rate)
        losing_trades = total_trades - winning_trades
        avg_loss = avg_profit * 0.5  # Losses are half the size of wins
        
        total_wins = winning_trades * avg_profit
        total_losses = losing_trades * avg_loss
        total_pnl = total_wins - total_losses
        
        return self.create(
            performance={
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_pnl": total_pnl,
                "roi": (total_pnl / 10000.0) * 100,  # ROI percentage
                "avg_win": avg_profit,
                "avg_loss": avg_loss,
                "win_rate": win_rate,
                "sharpe_ratio": 1.5,
                "max_drawdown": 10.0,
            },
            **kwargs
        )
    
    def create_batch(self,
                    count: int,
                    strategies: List[str] = None,
                    user_id: int = 123) -> List[Dict[str, Any]]:
        """Create multiple bots.
        
        Args:
            count: Number of bots to create
            strategies: List of strategies to cycle through
            user_id: User ID for all bots
            
        Returns:
            List of bot dictionaries
        """
        if strategies is None:
            strategies = ["grid", "arbitrage", "dca", "market_maker"]
        
        bots = []
        
        for i in range(count):
            strategy = strategies[i % len(strategies)]
            
            if strategy == "grid":
                bot = self.create_grid_bot(name=f"grid_bot_{i}", user_id=user_id)
            elif strategy == "arbitrage":
                bot = self.create_arbitrage_bot(name=f"arb_bot_{i}", user_id=user_id)
            elif strategy == "dca":
                bot = self.create_dca_bot(name=f"dca_bot_{i}", user_id=user_id)
            else:
                bot = self.create_market_maker_bot(name=f"mm_bot_{i}", user_id=user_id)
            
            bots.append(bot)
        
        return bots