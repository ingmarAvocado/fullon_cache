"""Basic usage examples for Fullon Cache.

This module demonstrates fundamental cache operations including
storing, retrieving, and managing cached data.
"""

EXAMPLE = '''
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from fullon_cache import (
    TickCache, OrdersCache, AccountCache, TradesCache,
    ExchangeCache, SymbolCache
)
from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.basic")


async def ticker_operations():
    """Demonstrate ticker cache operations."""
    print("\\n=== Ticker Cache Operations ===")
    
    # Initialize ticker cache
    tick_cache = TickCache()
    
    try:
        # Import fullon_orm Tick model
        from fullon_orm.models import Tick
        import time
        
        # Create ticker with ORM model
        tick = Tick(
            symbol="BTC/USDT",
            exchange="binance",
            price=50000.0,
            volume=1234.56,
            time=time.time(),
            bid=49999.0,
            ask=50001.0,
            last=50000.5
        )
        
        print(f"Storing ticker: BTC/USDT @ ${tick.price}")
        success = await tick_cache.update_ticker("binance", tick)
        print(f"Update successful: {success}")
        
        # Get ticker as ORM model
        ticker = await tick_cache.get_ticker("BTC/USDT", "binance")
        if ticker:
            print(f"Retrieved ticker: ${ticker.price}, Volume: {ticker.volume}")
            print(f"Spread: ${ticker.spread:.2f}, Spread %: {ticker.spread_percentage:.4f}%")
        
        # Get price tick from any exchange
        price_tick = await tick_cache.get_price_tick("BTC/USDT")
        if price_tick:
            print(f"Best price: ${price_tick.price} on {price_tick.exchange}")
        
        # Get price from any exchange
        any_price = await tick_cache.get_ticker_any("BTC/USDT")
        print(f"Price from any exchange: ${any_price}")
        
        # Get all tickers for an exchange
        tickers = await tick_cache.get_tickers("binance")
        print(f"Found {len(tickers)} tickers for Binance")
        
    finally:
        await tick_cache.close()


async def order_operations():
    """Demonstrate order cache operations."""
    print("\\n=== Order Cache Operations ===")
    
    orders_cache = OrdersCache()
    
    try:
        # Import fullon_orm Order model
        from fullon_orm.models import Order
        from datetime import datetime, timezone
        
        # Create order with ORM model
        order = Order(
            ex_order_id="EX_12345",
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=50000.0,
            status="open",
            order_type="limit",
            bot_id=123,
            uid=456,
            ex_id=789,
            timestamp=datetime.now(timezone.utc)
        )
        
        print(f"Saving order: {order.symbol} {order.side} {order.volume}")
        success = await orders_cache.save_order("binance", order)
        print(f"Save successful: {success}")
        
        # Get order as ORM model
        retrieved_order = await orders_cache.get_order("binance", "EX_12345")
        if retrieved_order:
            print(f"Retrieved order: {retrieved_order.symbol} - Status: {retrieved_order.status}")
        
        # Update order with partial data
        update_order = Order(
            ex_order_id="EX_12345",
            status="filled",
            final_volume=0.095
        )
        
        print("Updating order status to filled")
        success = await orders_cache.update_order("binance", update_order)
        print(f"Update successful: {success}")
        
        # Get updated order
        final_order = await orders_cache.get_order("binance", "EX_12345")
        if final_order:
            print(f"Final order: Status={final_order.status}, Final Volume={final_order.final_volume}")
        
        # Push order to queue
        await orders_cache.push_open_order("order123", "local456")
        print("Pushed order to queue")
        
        # Save order data
        order_data = {
            "symbol": "ETH/USDT",
            "side": "buy",
            "volume": 0.1,
            "price": 3000,
            "status": "pending"
        }
        await orders_cache.save_order_data("binance", "order123", order_data)
        print(f"Saved order data: {order_data}")
        
        # Get order status
        order = await orders_cache.get_order_status("binance", "order123")
        if order:
            print(f"Order found: {order.symbol} - Status: {order.status}")
        
        # Pop order from queue
        popped_id = await orders_cache.pop_open_order("local456")
        print(f"Popped order with ID: {popped_id}")
        
    finally:
        await orders_cache.close()


async def account_operations():
    """Demonstrate account cache operations."""
    print("\\n=== Account Cache Operations ===")
    
    account_cache = AccountCache()
    
    try:
        # === NEW ORM-BASED METHODS (RECOMMENDED) ===
        print("\\n--- Using ORM-based methods ---")
        
        # Import fullon_orm Position model
        from fullon_orm.models import Position
        import time
        
        # Create positions with ORM models
        positions = [
            Position(
                symbol="BTC/USDT",
                cost=25000.0,
                volume=0.5,
                fee=25.0,
                count=1.0,
                price=50000.0,
                timestamp=time.time(),
                ex_id="123",
                side="long"
            ),
            Position(
                symbol="ETH/USDT",
                cost=20000.0,
                volume=10.0,
                fee=20.0,
                count=1.0,
                price=2000.0,
                timestamp=time.time(),
                ex_id="123",
                side="long"
            )
        ]
        
        print("Updating positions with ORM models...")
        success = await account_cache.upsert_positions(123, positions)
        print(f"Update successful: {success}")
        
        # Get specific position as ORM model
        position = await account_cache.get_position("BTC/USDT", "123")
        print(f"BTC position (ORM) - Volume: {position.volume}, Cost: {position.cost}")
        
        # Upsert single position
        new_position = Position(
            symbol="ADA/USDT",
            cost=1000.0,
            volume=1000.0,
            fee=1.0,
            count=1.0,
            price=1.0,
            timestamp=time.time(),
            ex_id="123",
            side="long"
        )
        success = await account_cache.upsert_position(new_position)
        print(f"Single position upsert successful: {success}")
        
        # Get all positions as ORM models
        all_positions = await account_cache.get_all_positions()
        print(f"Total positions (ORM): {len(all_positions)}")
        for pos in all_positions:
            print(f"  {pos.symbol}: Volume={pos.volume}, Cost={pos.cost}")
        
        # === LEGACY METHODS (STILL SUPPORTED) ===
        print("\\n--- Using legacy methods ---")
        
        # Update positions using legacy dict format
        positions_dict = {
            "BTC/USDT": {"cost": 25000.0, "volume": 0.5, "fee": 25.0, "price": 50000.0, "timestamp": time.time()},
            "ETH/USDT": {"cost": 20000.0, "volume": 10.0, "fee": 20.0, "price": 2000.0, "timestamp": time.time()}
        }
        
        print("Updating positions with legacy dict format...")
        await account_cache.upsert_positions(123, positions_dict)
        
        # Update account data
        account_data = {
            "balance": 10000.0,
            "equity": 12000.0,
            "margin": 2000.0
        }
        await account_cache.upsert_user_account(123, account_data)
        print("Updated account data")
        
    finally:
        await account_cache.close()


async def symbol_operations():
    """Demonstrate symbol cache operations."""
    print("\\n=== Symbol Cache Operations ===")
    
    async with SymbolCache() as symbol_cache:
        # === NEW ORM-BASED METHODS (RECOMMENDED) ===
        print("\\n--- Using ORM-based methods ---")
        
        # Import fullon_orm Symbol model
        from fullon_orm.models import Symbol
        
        # Create symbol with ORM model
        symbol = Symbol(
            symbol="BTC/USDT",
            cat_ex_id=1,
            base="BTC",
            quote="USDT",
            decimals=8,
            updateframe="1h",
            backtest=30,
            futures=False,
            only_ticker=False
        )
        
        print(f"Adding symbol (ORM): {symbol.symbol}")
        success = await symbol_cache.add_symbol(symbol)
        print(f"Add successful: {success}")
        
        # Check if symbol exists
        exists = await symbol_cache.symbol_exists(symbol)
        print(f"Symbol exists: {exists}")
        
        # Get symbol using ORM model as search criteria
        search_symbol = Symbol(symbol="BTC/USDT", cat_ex_id=1)
        retrieved_symbol = await symbol_cache.get_symbol_by_model(search_symbol)
        if retrieved_symbol:
            print(f"Retrieved symbol (ORM): {retrieved_symbol.symbol}")
            print(f"  Base: {retrieved_symbol.base}, Quote: {retrieved_symbol.quote}")
            print(f"  Decimals: {retrieved_symbol.decimals}")
            print(f"  Futures: {retrieved_symbol.futures}")
        
        # Update symbol with new data
        symbol.decimals = 10
        symbol.backtest = 60
        print("\\nUpdating symbol with new decimals and backtest values...")
        success = await symbol_cache.update_symbol(symbol)
        print(f"Update successful: {success}")
        
        # Get all symbols for the same exchange
        exchange_symbols = await symbol_cache.get_symbols_for_exchange(symbol)
        print(f"\\nFound {len(exchange_symbols)} symbols on same exchange")
        
        # Create another symbol for the same exchange
        eth_symbol = Symbol(
            symbol="ETH/USDT",
            cat_ex_id=1,
            base="ETH",
            quote="USDT",
            decimals=18,
            updateframe="1h",
            backtest=30,
            futures=False,
            only_ticker=False
        )
        
        await symbol_cache.add_symbol(eth_symbol)
        print(f"Added second symbol: {eth_symbol.symbol}")
        
        # Get updated exchange symbols list
        exchange_symbols = await symbol_cache.get_symbols_for_exchange(symbol)
        print(f"Now have {len(exchange_symbols)} symbols on exchange")
        
        # Delete symbol using ORM model
        print("\\nDeleting BTC/USDT symbol...")
        success = await symbol_cache.delete_symbol_orm(symbol)
        print(f"Delete successful: {success}")
        
        # === LEGACY METHODS (STILL SUPPORTED) ===
        print("\\n--- Using legacy methods ---")
        
        # Get all symbols for an exchange (legacy)
        symbols = await symbol_cache.get_symbols("binance")
        print(f"Found {len(symbols)} symbols for Binance (legacy)")
        
        # Get specific symbol (legacy)
        btc = await symbol_cache.get_symbol("BTC/USDT", exchange_name="binance")
        if btc:
            print(f"BTC/USDT (legacy) - ID: {btc.symbol_id}")
            print(f"  Base: {btc.base}, Quote: {btc.quote}")
        else:
            print("BTC/USDT not found (expected after deletion)")
        
        # Get symbols by exchange ID (legacy)
        symbols_by_id = await symbol_cache.get_symbols_by_ex_id(1)
        print(f"Exchange ID 1 has {len(symbols_by_id)} symbols (legacy)")
        
        # Delete symbol (legacy method)
        if symbols_by_id:
            first_symbol = symbols_by_id[0]
            print(f"Deleting {first_symbol.symbol} using legacy method...")
            await symbol_cache.delete_symbol(first_symbol.symbol, exchange_name="binance")


async def exchange_operations():
    """Demonstrate exchange cache operations."""
    print("\\n=== Exchange Cache Operations ===")
    
    exchange_cache = ExchangeCache()
    
    try:
        # Push WebSocket error
        await exchange_cache.push_ws_error("Connection timeout", "binance")
        print("Pushed WebSocket error")
        
        # Pop error (non-blocking)
        error = await exchange_cache.pop_ws_error("binance", timeout=0)
        if error:
            print(f"WebSocket error: {error}")
            
    finally:
        await exchange_cache.close()


async def trade_operations():
    """Demonstrate trade cache operations."""
    print("\\n=== Trade Cache Operations ===")
    
    trades_cache = TradesCache()
    
    try:
        # === NEW ORM-BASED METHODS (RECOMMENDED) ===
        print("\\n--- Using ORM-based methods ---")
        
        # Import fullon_orm Trade model
        from fullon_orm.models import Trade
        from datetime import datetime, timezone
        
        # Create trade with ORM model
        trade = Trade(
            trade_id=12345,
            ex_trade_id="EX_TRD_001",
            ex_order_id="EX_ORD_001",
            uid=1,
            ex_id=1,
            symbol="BTC/USDT",
            order_type="limit",
            side="buy",
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            time=datetime.now(timezone.utc)
        )
        
        print(f"Pushing trade (ORM): {trade.symbol} {trade.side} {trade.volume}")
        success = await trades_cache.push_trade("binance", trade)
        print(f"Push successful: {success}")
        
        # Get all trades as ORM models (destructive read)
        trades = await trades_cache.get_trades("BTC/USDT", "binance")
        print(f"Retrieved {len(trades)} trades (ORM)")
        for t in trades:
            print(f"  Trade {t.trade_id}: {t.side} {t.volume} @ ${t.price}")
        
        # User trade operations
        user_trade = Trade(
            trade_id=67890,
            ex_trade_id="USER_TRD_001",
            symbol="ETH/USDT",
            side="sell",
            volume=1.0,
            price=3000.0,
            cost=3000.0,
            fee=3.0,
            time=datetime.now(timezone.utc)
        )
        
        print("\\nPushing user trade (ORM)...")
        success = await trades_cache.push_user_trade("123", "binance", user_trade)
        print(f"User trade push successful: {success}")
        
        # Pop user trade
        popped_trade = await trades_cache.pop_user_trade("123", "binance")
        if popped_trade:
            print(f"Popped user trade (ORM): {popped_trade.symbol} {popped_trade.side}")
        
        # === LEGACY METHODS (STILL SUPPORTED) ===
        print("\\n--- Using legacy methods ---")
        
        # Push trade using legacy dict format
        trade_data = {
            "trade_id": 11111,
            "symbol": "BTC/USDT",
            "side": "buy",
            "volume": 0.05,
            "price": 49000.0,
            "cost": 2450.0,
            "fee": 2.45
        }
        
        print(f"Pushing trade (legacy): {trade_data['symbol']} {trade_data['side']}")
        result = await trades_cache.push_trade_list("BTC/USDT", "binance", trade_data)
        print(f"Legacy push result: {result}")
        
        # Get trades as dict list (destructive read)
        trade_dicts = await trades_cache.get_trades_list("BTC/USDT", "binance")
        print(f"Retrieved {len(trade_dicts)} trades (legacy)")
        for td in trade_dicts:
            print(f"  Trade {td.get('trade_id', 'N/A')}: {td.get('side', 'N/A')} {td.get('volume', 0)} @ ${td.get('price', 0)}")
        
        # User trade operations (legacy)
        user_trade_data = {
            "trade_id": 22222,
            "symbol": "ADA/USDT",
            "side": "buy",
            "volume": 1000.0,
            "price": 0.5,
            "cost": 500.0,
            "fee": 0.5
        }
        
        print("\\nPushing user trade (legacy)...")
        result = await trades_cache.push_my_trades_list("456", "binance", user_trade_data)
        print(f"User trade push result: {result}")
        
        # Pop user trade (legacy)
        popped_data = await trades_cache.pop_my_trade("456", "binance")
        if popped_data:
            print(f"Popped user trade (legacy): {popped_data.get('symbol', 'N/A')} {popped_data.get('side', 'N/A')}")
        
        # Status operations
        print("\\nTrade status operations...")
        await trades_cache.update_trade_status("binance")
        status = await trades_cache.get_trade_status("binance")
        if status:
            print(f"Trade status for binance: {status}")
        
    finally:
        await trades_cache.close()


async def main():
    """Run all examples."""
    print("Fullon Cache Basic Usage Examples")
    print("=================================")
    
    await ticker_operations()
    await order_operations()
    await account_operations()
    await trade_operations()
    await symbol_operations()
    await exchange_operations()
    
    print("\\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
'''

# Make the example runnable when imported
async def main():
    """Execute the basic usage examples."""
    exec_globals = {}
    exec(EXAMPLE, exec_globals)
    await exec_globals['main']()

__all__ = ['EXAMPLE', 'main']
