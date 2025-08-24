#!/usr/bin/env python3
"""
Cache Operations Demo Tool

This tool demonstrates Fullon Cache operations with real-time feedback
and comprehensive error handling.

Features:
- Interactive cache testing with status reporting
- Beautiful output with emojis and progress indicators
- Command-line interface with help system
- Proper error handling for Redis connection issues
- Comprehensive demonstration of all cache types

Usage:
    python basic_usage.py --operation ticker
    python basic_usage.py --operation orders
    python basic_usage.py --operation account
    python basic_usage.py --operation trades
    python basic_usage.py --operation all --verbose
    python basic_usage.py --help
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from fullon_cache import TickCache, OrdersCache, AccountCache, TradesCache
except ImportError:
    # Handle cases where we're running from within the package
    from ..tick_cache import TickCache
    from ..orders_cache import OrdersCache
    from ..account_cache import AccountCache
    from ..trades_cache import TradesCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.basic")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with TickCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def ticker_operations(verbose: bool = False) -> bool:
    """Demonstrate ticker cache operations."""
    print("\n📈 === Ticker Cache Operations ===")
    
    try:
        async with TickCache() as tick_cache:
            if verbose:
                print("🔄 Initializing ticker cache...")
            
            # Import fullon_orm models
            from fullon_orm.models import Tick, Symbol
            
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
            
            print(f"🔄 Storing ticker: BTC/USDT @ ${tick.price:,.2f}")
            success = await tick_cache.set_ticker(symbol, tick)
            if success:
                print("✅ Set ticker successful")
            else:
                print("❌ Set ticker failed")
                return False
            
            # Get ticker as ORM model
            if verbose:
                print("🔄 Retrieving ticker...")
            ticker = await tick_cache.get_ticker(symbol)
            if ticker:
                print(f"✅ Retrieved ticker: ${ticker.price:,.2f}, Volume: {ticker.volume:,.2f}")
                print(f"   📊 Spread: ${ticker.spread:.2f}, Spread %: {ticker.spread_percentage:.4f}%")
            else:
                print("❌ Failed to retrieve ticker")
                return False
            
            # Get ticker from any exchange
            any_ticker = await tick_cache.get_any_ticker(symbol)
            if any_ticker:
                print(f"✅ Any ticker: ${any_ticker.price:,.2f} on {any_ticker.exchange}")
            
            # Get all tickers by exchange name
            all_tickers = await tick_cache.get_all_tickers(exchange_name="binance")
            print(f"✅ Found {len(all_tickers)} tickers for Binance")
            
            # Delete ticker
            if verbose:
                print("🔄 Deleting ticker...")
            deleted = await tick_cache.delete_ticker(symbol)
            print(f"✅ Deleted ticker: {deleted}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ticker operations failed: {e}")
        return False


async def order_operations(verbose: bool = False) -> bool:
    """Demonstrate order cache operations."""
    print("\n📋 === Order Cache Operations ===")
    
    try:
        async with OrdersCache() as orders_cache:
            if verbose:
                print("🔄 Initializing orders cache...")
            
            # Import fullon_orm Order model
            from fullon_orm.models import Order
            
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
            
            print(f"🔄 Saving order: {order.symbol} {order.side} {order.volume}")
            success = await orders_cache.save_order("binance", order)
            if success:
                print("✅ Save order successful")
            else:
                print("❌ Save order failed")
                return False
            
            # Get order as ORM model
            if verbose:
                print("🔄 Retrieving order...")
            retrieved_order = await orders_cache.get_order("binance", "EX_12345")
            if retrieved_order:
                print(f"✅ Retrieved order: {retrieved_order.symbol} - Status: {retrieved_order.status}")
            else:
                print("❌ Failed to retrieve order")
                return False
            
            # Update order with partial data
            update_order = Order(
                ex_order_id="EX_12345",
                status="filled",
                final_volume=0.095
            )
            
            print("🔄 Updating order status to filled")
            success = await orders_cache.update_order("binance", update_order)
            if success:
                print("✅ Update order successful")
            else:
                print("❌ Update order failed")
                return False
            
            # Get updated order
            final_order = await orders_cache.get_order("binance", "EX_12345")
            if final_order:
                print(f"✅ Final order: Status={final_order.status}, Final Volume={final_order.final_volume}")
            
            # Queue operations
            await orders_cache.push_open_order("order123", "local456")
            print("✅ Pushed order to queue")
            
            # Pop order from queue
            popped_id = await orders_cache.pop_open_order("local456")
            print(f"✅ Popped order with ID: {popped_id}")
            
            return True
            
    except Exception as e:
        print(f"❌ Order operations failed: {e}")
        return False


async def account_operations(verbose: bool = False) -> bool:
    """Demonstrate account cache operations."""
    print("\n👤 === Account Cache Operations ===")
    
    try:
        async with AccountCache() as account_cache:
            if verbose:
                print("🔄 Initializing account cache...")
            
            # Import fullon_orm Position model
            from fullon_orm.models import Position
            
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
            
            print("🔄 Updating positions...")
            success = await account_cache.upsert_positions(123, positions)
            if success:
                print("✅ Update positions successful")
            else:
                print("❌ Update positions failed")
                return False
            
            # Get specific position as ORM model
            if verbose:
                print("🔄 Retrieving BTC position...")
            position = await account_cache.get_position("BTC/USDT", "123")
            if position:
                print(f"✅ BTC position - Volume: {position.volume}, Cost: ${position.cost:,.2f}")
            else:
                print("❌ Failed to retrieve position")
                return False
            
            # Get all positions as ORM models
            all_positions = await account_cache.get_all_positions()
            print(f"✅ Total positions: {len(all_positions)}")
            for pos in all_positions:
                print(f"   💰 {pos.symbol}: Volume={pos.volume}, Cost=${pos.cost:,.2f}")
            
            # Update account data
            account_data = {
                "balance": 10000.0,
                "equity": 12000.0,
                "margin": 2000.0
            }
            await account_cache.upsert_user_account(123, account_data)
            print("✅ Updated account data")
            
            return True
            
    except Exception as e:
        print(f"❌ Account operations failed: {e}")
        return False


async def trade_operations(verbose: bool = False) -> bool:
    """Demonstrate trade cache operations."""
    print("\n💱 === Trade Cache Operations ===")
    
    try:
        async with TradesCache() as trades_cache:
            if verbose:
                print("🔄 Initializing trades cache...")
            
            # Import fullon_orm Trade model
            from fullon_orm.models import Trade
            
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
            
            print(f"🔄 Pushing trade: {trade.symbol} {trade.side} {trade.volume}")
            success = await trades_cache.push_trade("binance", trade)
            if success:
                print("✅ Push trade successful")
            else:
                print("❌ Push trade failed")
                return False
            
            # Get all trades as ORM models (destructive read)
            if verbose:
                print("🔄 Retrieving trades...")
            trades = await trades_cache.get_trades("BTC/USDT", "binance")
            print(f"✅ Retrieved {len(trades)} trades")
            for t in trades:
                print(f"   💱 Trade {t.trade_id}: {t.side} {t.volume} @ ${t.price:,.2f}")
            
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
            
            print("🔄 Pushing user trade...")
            success = await trades_cache.push_user_trade("123", "binance", user_trade)
            if success:
                print("✅ User trade push successful")
            else:
                print("❌ User trade push failed")
                return False
            
            # Pop user trade
            popped_trade = await trades_cache.pop_user_trade("123", "binance")
            if popped_trade:
                print(f"✅ Popped user trade: {popped_trade.symbol} {popped_trade.side}")
            
            return True
            
    except Exception as e:
        print(f"❌ Trade operations failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache Operations Demo")
    print("===============================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    # Run selected operations
    operations = {
        "ticker": ("📈 Ticker Operations", ticker_operations),
        "orders": ("📋 Order Operations", order_operations), 
        "account": ("👤 Account Operations", account_operations),
        "trades": ("💱 Trade Operations", trade_operations),
    }
    
    results = {}
    start_time = time.time()
    
    if args.operation == "all":
        print(f"\n🔄 Running all operations (verbose={args.verbose})...")
        for op_name, (desc, func) in operations.items():
            print(f"\n{desc}")
            results[op_name] = await func(args.verbose)
    else:
        if args.operation in operations:
            desc, func = operations[args.operation]
            print(f"\n🔄 Running {desc.lower()}...")
            results[args.operation] = await func(args.verbose)
        else:
            print(f"❌ Unknown operation: {args.operation}")
            return False
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All operations completed successfully!")
        return True
    else:
        failed = [op for op, success in results.items() if not success]
        print(f"❌ Failed operations: {', '.join(failed)}")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--operation", 
        choices=["ticker", "orders", "account", "trades", "all"],
        default="all",
        help="Operation to test (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Verbose output with detailed progress"
    )
    
    # Handle help manually for better formatting
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    try:
        success = asyncio.run(run_demo(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🔄 Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


# Support both direct execution and import
if __name__ == "__main__":
    main()