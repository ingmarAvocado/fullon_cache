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
        # Update ticker data
        ticker_data = {
            "bid": 50000.0,
            "ask": 50001.0,
            "last": 50000.5,
            "volume": 1234.56,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"Storing ticker: BTC/USDT @ ${ticker_data['last']}")
        await tick_cache.update_ticker("BTC/USDT", "binance", ticker_data)
        
        # Get ticker price and timestamp
        price, timestamp = await tick_cache.get_ticker("BTC/USDT", "binance")
        print(f"Retrieved price: ${price} at {timestamp}")
        
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
        # Push order to queue
        await orders_cache.push_open_order("order123", "local456")
        print("Pushed order to queue")
        
        # Save order data
        order_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000,
            "status": "pending"
        }
        await orders_cache.save_order_data("binance", "order123", order_data)
        print(f"Saved order data: {order_data}")
        
        # Get order status
        order = await orders_cache.get_order_status("binance", "order123")
        if order:
            print(f"Order found with data: {order}")
        
        # Pop order from queue
        local_id = await orders_cache.pop_open_order("order123")
        print(f"Popped order with local ID: {local_id}")
        
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
