"""Basic usage examples for Fullon Cache.

This module demonstrates fundamental cache operations including
storing, retrieving, and managing cached data.
"""

EXAMPLE = '''
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fullon_cache import (
    TickCache, OrdersCache, AccountCache, 
    ExchangeCache, SymbolCache
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ticker_operations():
    """Demonstrate ticker cache operations."""
    print("\\n=== Ticker Cache Operations ===")
    
    # Initialize ticker cache
    tick_cache = TickCache()
    
    try:
        # === NEW ORM-BASED METHODS (RECOMMENDED) ===
        print("\\n--- Using ORM-based methods ---")
        
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
        
        print(f"Storing ticker (ORM): BTC/USDT @ ${tick.price}")
        success = await tick_cache.update_ticker_orm("binance", tick)
        print(f"Update successful: {success}")
        
        # Get ticker as ORM model
        ticker = await tick_cache.get_ticker_orm("BTC/USDT", "binance")
        if ticker:
            print(f"Retrieved ticker (ORM): ${ticker.price}, Volume: {ticker.volume}")
            print(f"Spread: ${ticker.spread:.2f}, Spread %: {ticker.spread_percentage:.4f}%")
        
        # Get price tick from any exchange
        price_tick = await tick_cache.get_price_tick_orm("BTC/USDT")
        if price_tick:
            print(f"Best price (ORM): ${price_tick.price} on {price_tick.exchange}")
        
        # === LEGACY METHODS (STILL SUPPORTED) ===
        print("\\n--- Using legacy methods ---")
        
        # Update ticker data (legacy)
        ticker_data = {
            "bid": 50000.0,
            "ask": 50001.0,
            "last": 50000.5,
            "volume": 1234.56,
            "time": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"Storing ticker (legacy): BTC/USDT @ ${ticker_data['last']}")
        await tick_cache.update_ticker("BTC/USDT", "binance", ticker_data)
        
        # Get ticker price and timestamp
        price, timestamp = await tick_cache.get_ticker("BTC/USDT", "binance")
        print(f"Retrieved price (legacy): ${price} at {timestamp}")
        
        # Get price from any exchange
        any_price = await tick_cache.get_ticker_any("BTC/USDT")
        print(f"Price from any exchange (legacy): ${any_price}")
        
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
        # === NEW ORM-BASED METHODS (RECOMMENDED) ===
        print("\\n--- Using ORM-based methods ---")
        
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
        
        print(f"Saving order (ORM): {order.symbol} {order.side} {order.volume}")
        success = await orders_cache.save_order("binance", order)
        print(f"Save successful: {success}")
        
        # Get order as ORM model
        retrieved_order = await orders_cache.get_order("binance", "EX_12345")
        if retrieved_order:
            print(f"Retrieved order (ORM): {retrieved_order.symbol} - Status: {retrieved_order.status}")
        
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
            print(f"Final order (ORM): Status={final_order.status}, Final Volume={final_order.final_volume}")
        
        # === LEGACY METHODS (STILL SUPPORTED) ===
        print("\\n--- Using legacy methods ---")
        
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
        print(f"Saved order data (legacy): {order_data}")
        
        # Get order status
        order = await orders_cache.get_order_status("binance", "order123")
        if order:
            print(f"Order found (legacy): {order.symbol} - Status: {order.status}")
        
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
        # Update positions
        positions = {
            "BTC/USDT": {"size": 0.5, "cost": 25000.0},
            "ETH/USDT": {"size": 10.0, "cost": 20000.0}
        }
        
        print("Updating positions...")
        await account_cache.upsert_positions(123, positions)
        
        # Get specific position
        position = await account_cache.get_position("BTC/USDT", "123")
        print(f"BTC position - Size: {position.size}, Cost: {position.cost}")
        
        # Update account data
        account_data = {
            "balance": 10000.0,
            "equity": 12000.0,
            "margin": 2000.0
        }
        await account_cache.upsert_user_account(123, account_data)
        print("Updated account data")
        
        # Get all positions
        all_positions = await account_cache.get_all_positions()
        print(f"Total positions across all accounts: {len(all_positions)}")
        
    finally:
        await account_cache.close()


async def symbol_operations():
    """Demonstrate symbol cache operations."""
    print("\\n=== Symbol Cache Operations ===")
    
    async with SymbolCache() as symbol_cache:
        # Get all symbols for an exchange
        symbols = await symbol_cache.get_symbols("binance")
        print(f"Found {len(symbols)} symbols for Binance")
        
        # Get specific symbol
        btc = await symbol_cache.get_symbol("BTC/USDT", exchange_name="binance")
        if btc:
            print(f"BTC/USDT - ID: {btc.symbol_id}, Min size: {btc.min_order_size}")


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


async def main():
    """Run all examples."""
    print("Fullon Cache Basic Usage Examples")
    print("=================================")
    
    await ticker_operations()
    await order_operations()
    await account_operations()
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
