#!/usr/bin/env python3
"""
TradesCache Operations Demo Tool

This tool demonstrates trade data queuing, status management, and processing
functionality provided by the TradesCache class.

Features:
- Trade queue management with push/pop operations
- Trade status tracking and bulk updates
- Trade data persistence and retrieval
- Bulk trade processing and statistics
- Trade filtering and search capabilities
- Performance monitoring for trade operations

Usage:
    python example_trades_cache.py --operations basic --trades 100
    python example_trades_cache.py --operations queue --batch-size 20 --verbose
    python example_trades_cache.py --operations status --verbose
    python example_trades_cache.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

try:
    from fullon_cache import TradesCache
except ImportError:
    from ..trades_cache import TradesCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.trades")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with TradesCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_trade_operations(cache: TradesCache, trade_count: int = 100, verbose: bool = False) -> bool:
    """Demonstrate basic trade queue operations."""
    print("💱 === Basic Trade Operations Demo ===")
    
    try:
        from fullon_orm.models import Trade
        
        exchange = "binance"
        print(f"🔄 Creating and queuing {trade_count} trades...")
        
        # Create test trades
        trades_data = []
        start_time = time.time()
        
        for i in range(trade_count):
            trade = Trade(
                trade_id=10000 + i,
                ex_trade_id=f"TRADE_{exchange.upper()}_{i:06d}",
                symbol=random.choice(["BTC/USDT", "ETH/USDT", "ADA/USDT"]),
                side=random.choice(["buy", "sell"]),
                volume=Decimal(str(random.uniform(0.1, 5.0))),
                price=Decimal(str(random.uniform(100, 50000))),
                cost=Decimal("0"),  # Will be calculated
                fee=Decimal(str(random.uniform(0.1, 10.0))),
                time=datetime.now(timezone.utc)
            )
            trade.cost = trade.volume * trade.price
            trades_data.append(trade)
            
            # Push to queue
            success = await cache.push_trade(exchange, trade)
            if not success:
                print(f"❌ Failed to push trade {i}")
                return False
            
            if verbose and i % 20 == 0:
                print(f"   📤 Pushed {i + 1}/{trade_count} trades")
        
        push_time = time.time() - start_time
        print(f"✅ Pushed {trade_count} trades in {push_time:.2f}s ({trade_count/push_time:.1f} trades/sec)")
        
        # Pop trades from queue
        print("🔄 Popping trades from queue...")
        start_time = time.time()
        
        popped_trades = []
        while True:
            trade = await cache.pop_trade(exchange)
            if trade is None:
                break
            popped_trades.append(trade)
            
            if verbose and len(popped_trades) % 20 == 0:
                print(f"   📥 Popped {len(popped_trades)} trades")
        
        pop_time = time.time() - start_time
        popped_count = len(popped_trades)
        
        print(f"✅ Popped {popped_count} trades in {pop_time:.2f}s ({popped_count/pop_time:.1f} trades/sec)")
        
        if popped_count == trade_count:
            print("🎉 All trades processed successfully!")
            
            # Verify trade data integrity
            if popped_trades and hasattr(popped_trades[0], 'symbol'):
                sample_trade = popped_trades[0]
                if verbose:
                    print(f"   📊 Sample trade: {sample_trade.side} {float(sample_trade.volume):.4f} {sample_trade.symbol} @ ${float(sample_trade.price):.2f}")
                return True
        else:
            print(f"❌ Trade count mismatch: pushed {trade_count}, popped {popped_count}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Basic trade operations failed: {e}")
        return False


async def trade_status_operations(cache: TradesCache, verbose: bool = False) -> bool:
    """Demonstrate trade status tracking."""
    print("📊 === Trade Status Operations Demo ===")
    
    try:
        # Create test trade IDs with different statuses
        test_trade_ids = [f"status_trade_{i:04d}" for i in range(20)]
        statuses = ["pending", "confirmed", "settled", "failed", "cancelled"]
        
        print(f"🔄 Setting status for {len(test_trade_ids)} trades...")
        
        # Set individual trade statuses
        for i, trade_id in enumerate(test_trade_ids):
            status = statuses[i % len(statuses)]
            await cache.set_trade_status(trade_id, status)
            
            if verbose:
                print(f"   📊 Trade {trade_id}: {status}")
        
        # Verify individual statuses
        print("🔄 Verifying individual trade statuses...")
        status_counts = {}
        
        for i, trade_id in enumerate(test_trade_ids):
            expected_status = statuses[i % len(statuses)]
            actual_status = await cache.get_trade_status(trade_id)
            
            if actual_status != expected_status:
                print(f"❌ Status mismatch for {trade_id}: expected {expected_status}, got {actual_status}")
                return False
            
            status_counts[actual_status] = status_counts.get(actual_status, 0) + 1
        
        print("📈 Status Distribution:")
        for status, count in status_counts.items():
            print(f"   📊 {status}: {count} trades")
        
        # Test bulk status operations
        print("🔄 Testing bulk status operations...")
        bulk_trade_ids = test_trade_ids[:10]  # First 10 trades
        
        # Set bulk status
        await cache.set_trades_status(bulk_trade_ids, "processed")
        
        # Verify bulk update
        bulk_success = True
        for trade_id in bulk_trade_ids:
            status = await cache.get_trade_status(trade_id)
            if status != "processed":
                bulk_success = False
                break
        
        if bulk_success:
            print("✅ Bulk status update successful")
        else:
            print("❌ Bulk status update failed")
            return False
        
        print("✅ Trade status operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Trade status operations failed: {e}")
        return False


async def batch_trade_processing(cache: TradesCache, batch_size: int = 20, verbose: bool = False) -> bool:
    """Demonstrate batch trade processing."""
    print("📦 === Batch Trade Processing Demo ===")
    
    try:
        from fullon_orm.models import Trade
        
        total_batches = 5
        total_trades = batch_size * total_batches
        exchange = "kraken"
        
        print(f"🔄 Creating {total_trades} trades in {total_batches} batches...")
        
        # Create and queue trades in batches
        for batch_num in range(total_batches):
            batch_trades = []
            
            for i in range(batch_size):
                trade_id = batch_num * batch_size + i
                trade = Trade(
                    trade_id=20000 + trade_id,
                    ex_trade_id=f"BATCH_{exchange.upper()}_{batch_num}_{i:03d}",
                    symbol=random.choice(["BTC/USDT", "ETH/USDT", "DOT/USDT"]),
                    side=random.choice(["buy", "sell"]),
                    volume=Decimal(str(random.uniform(0.5, 2.0))),
                    price=Decimal(str(random.uniform(1000, 40000))),
                    cost=Decimal("0"),
                    fee=Decimal(str(random.uniform(1, 5))),
                    time=datetime.now(timezone.utc)
                )
                trade.cost = trade.volume * trade.price
                batch_trades.append(trade)
                
                # Queue trade
                await cache.push_trade(exchange, trade)
            
            if verbose:
                print(f"   📦 Batch {batch_num + 1}: {len(batch_trades)} trades queued")
        
        print(f"✅ Queued {total_trades} trades in {total_batches} batches")
        
        # Process trades in batches
        print(f"🔄 Processing trades in batches of {batch_size}...")
        processed_batches = 0
        total_processed = 0
        total_volume = Decimal("0")
        total_value = Decimal("0")
        
        while True:
            # Pop a batch of trades
            batch = []
            for _ in range(batch_size):
                trade = await cache.pop_trade(exchange)
                if trade is None:
                    break
                batch.append(trade)
            
            if not batch:
                break
            
            # Process batch statistics
            batch_volume = sum(trade.volume for trade in batch)
            batch_value = sum(trade.cost for trade in batch)
            
            total_volume += batch_volume
            total_value += batch_value
            
            # Simulate batch processing
            await asyncio.sleep(0.05)  # Simulate processing time
            
            # Update status for batch
            trade_ids = [trade.ex_trade_id for trade in batch]
            await cache.set_trades_status(trade_ids, "batch_processed")
            
            processed_batches += 1
            total_processed += len(batch)
            
            if verbose:
                print(f"   ⚡ Batch {processed_batches}: {len(batch)} trades, "
                      f"Vol: {float(batch_volume):.2f}, Value: ${float(batch_value):,.2f}")
        
        print(f"📊 Processing Summary:")
        print(f"   📦 Batches processed: {processed_batches}")
        print(f"   💱 Total trades: {total_processed}")
        print(f"   📈 Total volume: {float(total_volume):.2f}")
        print(f"   💰 Total value: ${float(total_value):,.2f}")
        
        if total_processed == total_trades:
            print("🎉 Batch processing completed successfully!")
            return True
        else:
            print(f"❌ Processing incomplete: {total_processed}/{total_trades}")
            return False
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return False


async def trade_analytics_demo(cache: TradesCache, verbose: bool = False) -> bool:
    """Demonstrate trade analytics and reporting."""
    print("📈 === Trade Analytics Demo ===")
    
    try:
        from fullon_orm.models import Trade
        
        exchange = "coinbase"
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        
        print("🔄 Creating diverse trade dataset...")
        
        # Create trades with varied characteristics
        trades_by_symbol = {}
        total_trades = 60  # 20 per symbol
        
        for i in range(total_trades):
            symbol = symbols[i % len(symbols)]
            
            # Generate realistic price ranges
            price_ranges = {"BTC/USDT": (45000, 50000), "ETH/USDT": (3000, 3500), "ADA/USDT": (1.0, 1.5)}
            min_price, max_price = price_ranges[symbol]
            
            trade = Trade(
                trade_id=30000 + i,
                ex_trade_id=f"ANALYTICS_{exchange.upper()}_{i:04d}",
                symbol=symbol,
                side="buy" if i % 3 == 0 else "sell",  # More sells than buys
                volume=Decimal(str(random.uniform(0.1, 3.0))),
                price=Decimal(str(random.uniform(min_price, max_price))),
                cost=Decimal("0"),
                fee=Decimal(str(random.uniform(0.1, 8.0))),
                time=datetime.now(timezone.utc)
            )
            trade.cost = trade.volume * trade.price
            
            # Track by symbol
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = []
            trades_by_symbol[symbol].append(trade)
            
            await cache.push_trade(exchange, trade)
        
        # Process and analyze trades
        print("🔄 Analyzing trade patterns...")
        analytics = {}
        
        # Pop all trades and analyze
        all_trades = []
        while True:
            trade = await cache.pop_trade(exchange)
            if trade is None:
                break
            all_trades.append(trade)
        
        # Calculate analytics by symbol
        for symbol in symbols:
            symbol_trades = [t for t in all_trades if t.symbol == symbol]
            
            if symbol_trades:
                total_volume = sum(t.volume for t in symbol_trades)
                total_value = sum(t.cost for t in symbol_trades)
                avg_price = sum(t.price for t in symbol_trades) / len(symbol_trades)
                buy_trades = [t for t in symbol_trades if t.side == "buy"]
                sell_trades = [t for t in symbol_trades if t.side == "sell"]
                
                analytics[symbol] = {
                    "trade_count": len(symbol_trades),
                    "total_volume": float(total_volume),
                    "total_value": float(total_value),
                    "avg_price": float(avg_price),
                    "buy_count": len(buy_trades),
                    "sell_count": len(sell_trades),
                    "buy_ratio": len(buy_trades) / len(symbol_trades) if symbol_trades else 0
                }
        
        # Display analytics
        print("📊 Trade Analytics by Symbol:")
        for symbol, stats in analytics.items():
            print(f"\n   📈 {symbol}:")
            print(f"      💱 Trades: {stats['trade_count']}")
            print(f"      📊 Volume: {stats['total_volume']:.4f}")
            print(f"      💰 Value: ${stats['total_value']:,.2f}")
            print(f"      💲 Avg Price: ${stats['avg_price']:,.2f}")
            print(f"      📈 Buy/Sell: {stats['buy_count']}/{stats['sell_count']} ({stats['buy_ratio']:.1%} buys)")
        
        # Overall statistics
        total_all = sum(stats['trade_count'] for stats in analytics.values())
        total_value_all = sum(stats['total_value'] for stats in analytics.values())
        
        print(f"\n📊 Overall Statistics:")
        print(f"   💱 Total trades: {total_all}")
        print(f"   💰 Total value: ${total_value_all:,.2f}")
        print(f"   📊 Symbols analyzed: {len(analytics)}")
        
        if total_all == total_trades:
            print("✅ Trade analytics completed successfully!")
            return True
        else:
            print(f"❌ Analytics incomplete: {total_all}/{total_trades} trades")
            return False
        
    except Exception as e:
        print(f"❌ Trade analytics failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache TradesCache Demo")
    print("================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with TradesCache() as cache:
            results["basic"] = await basic_trade_operations(cache, args.trades, args.verbose)
    
    if args.operations in ["status", "all"]:
        async with TradesCache() as cache:
            results["status"] = await trade_status_operations(cache, args.verbose)
    
    if args.operations in ["batch", "all"]:
        async with TradesCache() as cache:
            results["batch"] = await batch_trade_processing(cache, args.batch_size, args.verbose)
    
    if args.operations in ["analytics", "all"]:
        async with TradesCache() as cache:
            results["analytics"] = await trade_analytics_demo(cache, args.verbose)
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All TradesCache operations completed successfully!")
        return True
    else:
        failed = [op for op, success in results.items() if not success]
        print(f"❌ Failed operations: {', '.join(failed)}")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--operations",
        choices=["basic", "status", "batch", "analytics", "all"],
        default="all",
        help="Operations to demonstrate (default: all)"
    )
    parser.add_argument(
        "--trades",
        type=int,
        default=100,
        help="Number of trades for basic operations (default: 100)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Batch size for processing demo (default: 20)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed trade info"
    )
    
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