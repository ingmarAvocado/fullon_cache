"""Basic usage examples for Fullon Cache.

This module demonstrates fundamental cache operations including
storing, retrieving, and managing cached data.
"""

EXAMPLE = '''
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from fullon_cache import (
    TickCache, OrdersCache, AccountCache, TradesCache
)
from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.basic")


async def ticker_operations():
    """Demonstrate ticker cache operations."""
    print("\\n=== Ticker Cache Operations ===")
    
    # Initialize ticker cache
    tick_cache = TickCache()
    
    try:
        # Import fullon_orm models
        from fullon_orm.models import Tick, Symbol
        import time
        
        # Create symbol object
        symbol = Symbol(
            symbol="BTC/USDT",
            cat_ex_id=1,
            base="BTC",
            quote="USDT"
        )
        
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
        success = await tick_cache.set_ticker(symbol, tick)
        print(f"Set ticker successful: {success}")
        
        # Get ticker as ORM model
        ticker = await tick_cache.get_ticker(symbol)
        if ticker:
            print(f"Retrieved ticker: ${ticker.price}, Volume: {ticker.volume}")
            print(f"Spread: ${ticker.spread:.2f}, Spread %: {ticker.spread_percentage:.4f}%")
        
        # Get ticker from any exchange
        any_ticker = await tick_cache.get_any_ticker(symbol)
        if any_ticker:
            print(f"Any ticker: ${any_ticker.price} on {any_ticker.exchange}")
        
        # Get all tickers by exchange name
        all_tickers = await tick_cache.get_all_tickers(exchange_name="binance")
        print(f"Found {len(all_tickers)} tickers for Binance")
        
        # Delete ticker
        deleted = await tick_cache.delete_ticker(symbol)
        print(f"Deleted ticker: {deleted}")
        
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
        
        print("Updating positions...")
        success = await account_cache.upsert_positions(123, positions)
        print(f"Update successful: {success}")
        
        # Get specific position as ORM model
        position = await account_cache.get_position("BTC/USDT", "123")
        print(f"BTC position - Volume: {position.volume}, Cost: {position.cost}")
        
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
        print(f"Total positions: {len(all_positions)}")
        for pos in all_positions:
            print(f"  {pos.symbol}: Volume={pos.volume}, Cost={pos.cost}")
        
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





async def trade_operations():
    """Demonstrate trade cache operations."""
    print("\\n=== Trade Cache Operations ===")
    
    trades_cache = TradesCache()
    
    try:
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
        
        print(f"Pushing trade: {trade.symbol} {trade.side} {trade.volume}")
        success = await trades_cache.push_trade("binance", trade)
        print(f"Push successful: {success}")
        
        # Get all trades as ORM models (destructive read)
        trades = await trades_cache.get_trades("BTC/USDT", "binance")
        print(f"Retrieved {len(trades)} trades")
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
        
        print("\\nPushing user trade...")
        success = await trades_cache.push_user_trade("123", "binance", user_trade)
        print(f"User trade push successful: {success}")
        
        # Pop user trade
        popped_trade = await trades_cache.pop_user_trade("123", "binance")
        if popped_trade:
            print(f"Popped user trade: {popped_trade.symbol} {popped_trade.side}")
        
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
