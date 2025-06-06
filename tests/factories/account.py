"""Account and Position factories for test data generation."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class PositionFactory:
    """Factory for creating test position data."""
    
    def __init__(self):
        self._counter = 0
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create position data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with position data
        """
        self._counter += 1
        
        defaults = {
            "symbol": "BTC/USDT",
            "amount": 1.0,
            "cost": 50000.0,
            "price": 50000.0,
            "pl": 0.0,
            "pl_pct": 0.0,
            "side": "long",
            "leverage": 1.0,
            "margin": 0.0,
            "unrealized_pl": 0.0,
            "realized_pl": 0.0,
            "maintenance_margin": 0.0,
            "initial_margin": 0.0,
            "liquidation_price": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)
        
        # Calculate derived fields if not provided
        if result["cost"] == 0 and result["amount"] != 0 and result["price"] != 0:
            result["cost"] = result["amount"] * result["price"]
        
        return result
    
    def create_profitable_position(self, 
                                  symbol: str = "BTC/USDT",
                                  profit_percent: float = 10.0,
                                  **kwargs) -> Dict[str, Any]:
        """Create a profitable position.
        
        Args:
            symbol: Trading symbol
            profit_percent: Profit percentage
            **kwargs: Additional overrides
            
        Returns:
            Profitable position data
        """
        entry_price = 50000.0
        current_price = entry_price * (1 + profit_percent / 100)
        amount = kwargs.pop("amount", 1.0)
        
        return self.create(
            symbol=symbol,
            amount=amount,
            price=entry_price,
            cost=entry_price * amount,
            pl=(current_price - entry_price) * amount,
            pl_pct=profit_percent,
            unrealized_pl=(current_price - entry_price) * amount,
            **kwargs
        )
    
    def create_losing_position(self,
                              symbol: str = "BTC/USDT", 
                              loss_percent: float = 5.0,
                              **kwargs) -> Dict[str, Any]:
        """Create a losing position.
        
        Args:
            symbol: Trading symbol
            loss_percent: Loss percentage
            **kwargs: Additional overrides
            
        Returns:
            Losing position data
        """
        entry_price = 50000.0
        current_price = entry_price * (1 - loss_percent / 100)
        amount = kwargs.pop("amount", 1.0)
        
        return self.create(
            symbol=symbol,
            amount=amount,
            price=entry_price,
            cost=entry_price * amount,
            pl=(current_price - entry_price) * amount,
            pl_pct=-loss_percent,
            unrealized_pl=(current_price - entry_price) * amount,
            **kwargs
        )
    
    def create_leveraged_position(self,
                                 leverage: float = 10.0,
                                 **kwargs) -> Dict[str, Any]:
        """Create a leveraged position.
        
        Args:
            leverage: Leverage multiplier
            **kwargs: Additional overrides
            
        Returns:
            Leveraged position data
        """
        amount = 10.0  # 10 BTC worth
        price = 50000.0
        notional = amount * price
        margin = notional / leverage
        
        # Calculate liquidation price (simplified)
        liquidation_price = price * (1 - 0.8 / leverage)
        
        return self.create(
            amount=amount,
            price=price,
            cost=notional,
            leverage=leverage,
            margin=margin,
            initial_margin=margin,
            maintenance_margin=margin * 0.5,  # 50% of initial
            liquidation_price=liquidation_price,
            side="long",
            **kwargs
        )


class AccountFactory:
    """Factory for creating test account data."""
    
    def __init__(self):
        self._counter = 0
        self.position_factory = PositionFactory()
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create account data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with account data
            
        Example:
            factory = AccountFactory()
            account = factory.create(
                user_id=123,
                exchange="binance",
                total_value=100000
            )
        """
        self._counter += 1
        
        defaults = {
            "account_id": f"ACC{self._counter:06d}",
            "user_id": 123,
            "exchange": "binance",
            "balances": {
                "USDT": {
                    "free": 10000.0,
                    "used": 0.0,
                    "total": 10000.0
                },
                "BTC": {
                    "free": 0.1,
                    "used": 0.0,
                    "total": 0.1
                }
            },
            "positions": {},
            "total_value": None,  # Will be calculated
            "margin_level": None,
            "free_margin": None,
            "used_margin": 0.0,
            "equity": None,
            "pnl": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)
        
        # Calculate total value if not provided
        if result["total_value"] is None:
            total = 0.0
            for balance_data in result["balances"].values():
                if isinstance(balance_data, dict):
                    total += balance_data.get("total", 0) * self._get_usd_price(balance_data)
            result["total_value"] = total
        
        # Set equity to total_value if not provided
        if result["equity"] is None:
            result["equity"] = result["total_value"]
        
        # Set free margin
        if result["free_margin"] is None:
            result["free_margin"] = result["equity"] - result["used_margin"]
        
        return result
    
    def create_with_positions(self,
                             positions: List[Dict[str, Any]] = None,
                             **kwargs) -> Dict[str, Any]:
        """Create account with positions.
        
        Args:
            positions: List of position dictionaries
            **kwargs: Additional account overrides
            
        Returns:
            Account data with positions
        """
        if positions is None:
            # Create some default positions
            positions = [
                self.position_factory.create_profitable_position(
                    symbol="BTC/USDT",
                    amount=0.5,
                    profit_percent=5.0
                ),
                self.position_factory.create_losing_position(
                    symbol="ETH/USDT",
                    amount=10.0,
                    loss_percent=2.0
                )
            ]
        
        # Convert positions list to dict keyed by symbol
        positions_dict = {pos["symbol"]: pos for pos in positions}
        
        # Calculate total PnL
        total_pnl = sum(pos.get("pl", 0) for pos in positions)
        
        # Calculate used margin
        used_margin = sum(pos.get("margin", 0) for pos in positions)
        
        return self.create(
            positions=positions_dict,
            pnl=total_pnl,
            used_margin=used_margin,
            **kwargs
        )
    
    def create_margin_account(self,
                             leverage: float = 5.0,
                             margin_level: float = 150.0,
                             **kwargs) -> Dict[str, Any]:
        """Create a margin trading account.
        
        Args:
            leverage: Account leverage
            margin_level: Margin level percentage
            **kwargs: Additional overrides
            
        Returns:
            Margin account data
        """
        equity = 50000.0
        used_margin = equity / leverage
        free_margin = equity - used_margin
        
        # Create leveraged positions
        positions = [
            self.position_factory.create_leveraged_position(
                symbol="BTC/USDT",
                leverage=leverage,
                amount=1.0
            ),
            self.position_factory.create_leveraged_position(
                symbol="ETH/USDT",
                leverage=leverage,
                amount=10.0,
                price=3000.0
            )
        ]
        
        return self.create_with_positions(
            positions=positions,
            equity=equity,
            margin_level=margin_level,
            free_margin=free_margin,
            used_margin=used_margin,
            account_type="margin",
            **kwargs
        )
    
    def create_empty_account(self, **kwargs) -> Dict[str, Any]:
        """Create an empty account with zero balances.
        
        Args:
            **kwargs: Additional overrides
            
        Returns:
            Empty account data
        """
        return self.create(
            balances={},
            positions={},
            total_value=0.0,
            equity=0.0,
            pnl=0.0,
            **kwargs
        )
    
    def create_multi_currency_account(self,
                                     currencies: List[str] = None,
                                     **kwargs) -> Dict[str, Any]:
        """Create account with multiple currency balances.
        
        Args:
            currencies: List of currencies
            **kwargs: Additional overrides
            
        Returns:
            Multi-currency account data
        """
        if currencies is None:
            currencies = ["USDT", "BTC", "ETH", "BNB", "SOL"]
        
        balances = {}
        for i, currency in enumerate(currencies):
            amount = 1000.0 / (i + 1)  # Decreasing amounts
            balances[currency] = {
                "free": amount * 0.8,
                "used": amount * 0.2,
                "total": amount
            }
        
        return self.create(
            balances=balances,
            **kwargs
        )
    
    def _get_usd_price(self, currency_data: Any) -> float:
        """Get USD price for currency (simplified).
        
        Args:
            currency_data: Currency balance data
            
        Returns:
            USD price (1.0 for stablecoins)
        """
        # This is simplified - in real implementation would query prices
        return 1.0  # Assume everything is in USD terms