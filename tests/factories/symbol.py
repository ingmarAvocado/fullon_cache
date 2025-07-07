"""Symbol factory for test data generation."""

from fullon_orm.models import Symbol as ORMSymbol


class SymbolFactory:
    """Factory for creating test symbols."""

    def __init__(self):
        self._counter = 0

    def __call__(self, **kwargs) -> ORMSymbol:
        """Create a symbol with defaults.
        
        This is callable to maintain compatibility with existing usage.
        
        Args:
            **kwargs: Symbol attributes
            
        Returns:
            ORM Symbol object
        """
        return self.create(**kwargs)

    def create(self, **kwargs) -> ORMSymbol:
        """Create a symbol with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            ORM Symbol object
            
        Example:
            factory = SymbolFactory()
            symbol = factory.create(
                symbol="ETH/USDT",
                exchange_name="binance"
            )
        """
        self._counter += 1

        # Use provided symbol to determine base/quote if not explicitly provided
        if 'symbol' in kwargs and '/' in kwargs['symbol']:
            parts = kwargs['symbol'].split('/')
            if 'base' not in kwargs:
                kwargs['base'] = parts[0]
            if 'quote' not in kwargs:
                kwargs['quote'] = parts[1]

        defaults = {
            'symbol_id': self._counter,
            'symbol': f'TEST{self._counter}/USDT',
            'cat_ex_id': 1,
            'base': f'TEST{self._counter}',
            'quote': 'USDT',
            'futures': False,
            'decimals': 8,
            'updateframe': '1h',
            'backtest': 30,
            'only_ticker': False
        }

        # Extract exchange_name for caching but don't pass to ORM
        exchange_name = kwargs.pop('exchange_name', None)

        # Merge defaults with kwargs
        final_args = {**defaults}
        final_args.update(kwargs)

        # Create ORM Symbol
        symbol = ORMSymbol(**final_args)

        # Store exchange_name for test purposes
        if exchange_name:
            symbol._cached_exchange_name = exchange_name

        return symbol

    def create_orm_model(self, **kwargs) -> ORMSymbol:
        """Create an ORM model for fullon_orm.Symbol.
        
        Args:
            **kwargs: Symbol attributes
            
        Returns:
            ORM Symbol object
        """
        return self.create(**kwargs)

    def create_futures_symbol(self, **kwargs) -> ORMSymbol:
        """Create a futures symbol.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Futures ORM Symbol object
        """
        defaults = {
            'futures': True,
            'symbol': kwargs.get('symbol', 'BTC-PERP'),
            'base': 'BTC',
            'quote': 'USD',
            'decimals': 2,
        }
        defaults.update(kwargs)

        return self.create(**defaults)

    def create_spot_symbol(self, base: str = "BTC", quote: str = "USDT", **kwargs) -> ORMSymbol:
        """Create a spot trading symbol.
        
        Args:
            base: Base currency
            quote: Quote currency
            **kwargs: Additional overrides
            
        Returns:
            Spot ORM Symbol object
        """
        return self.create(
            symbol=f"{base}/{quote}",
            base=base,
            quote=quote,
            futures=False,
            **kwargs
        )

    def create_batch(self,
                    count: int,
                    exchange_name: str = "binance",
                    base_prefix: str = "TEST",
                    quotes: list = None) -> list:
        """Create multiple symbols.
        
        Args:
            count: Number of symbols to create
            exchange_name: Exchange name
            base_prefix: Prefix for base currency
            quotes: List of quote currencies to cycle through
            
        Returns:
            List of ORM Symbol objects
        """
        if quotes is None:
            quotes = ["USDT", "BTC", "ETH", "BUSD"]

        symbols = []

        for i in range(count):
            quote = quotes[i % len(quotes)]
            symbol = self.create(
                symbol=f"{base_prefix}{i}/{quote}",
                base=f"{base_prefix}{i}",
                quote=quote,
                exchange_name=exchange_name,
                cat_ex_id=1,
                decimals=8 if quote == "BTC" else 2
            )
            symbols.append(symbol)

        return symbols

    def create_exchange_symbols(self, exchanges: list, symbol_name: str = "BTC/USDT") -> dict:
        """Create the same symbol across multiple exchanges.
        
        Args:
            exchanges: List of exchange names
            symbol_name: Symbol to create
            
        Returns:
            Dictionary mapping exchange to ORM Symbol object
        """
        result = {}

        for i, exchange in enumerate(exchanges):
            symbol = self.create(
                symbol=symbol_name,
                exchange_name=exchange,
                cat_ex_id=i + 1
            )
            result[exchange] = symbol

        return result
