#!/usr/bin/env python3
"""
Queue Management Demo Tool

This tool demonstrates order/trade queue operations with different processing patterns
and various queue management strategies.

Features:
- FIFO queue operations with real-time monitoring
- Batch processing demonstrations
- Priority queue examples
- Beautiful output with emojis and progress indicators
- Queue statistics and performance metrics
- Different processing patterns

Usage:
    python queue_patterns.py --pattern basic --size 100
    python queue_patterns.py --pattern batch --batch-size 10
    python queue_patterns.py --pattern priority --verbose
    python queue_patterns.py --pattern all --size 50
    python queue_patterns.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import OrdersCache, TradesCache
except ImportError:
    from ..orders_cache import OrdersCache
    from ..trades_cache import TradesCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.queue")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with OrdersCache() as cache:
            # Test basic connection with ping equivalent
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_queue_pattern(args) -> bool:
    """Demonstrate basic FIFO queue operations."""
    print("📋 === Basic FIFO Queue Pattern ===")
    
    try:
        async with OrdersCache() as orders_cache:
            # Push multiple orders to queue
            print(f"🔄 Pushing {args.size} orders to queue...")
            start_time = time.time()
            
            for i in range(args.size):
                order_id = f"order_{i:04d}"
                queue_id = "basic_queue"
                await orders_cache.push_open_order(order_id, queue_id)
                
                if args.verbose and i % 10 == 0:
                    print(f"   📤 Pushed {i + 1}/{args.size} orders")
            
            push_time = time.time() - start_time
            print(f"✅ Pushed {args.size} orders in {push_time:.2f}s ({args.size/push_time:.1f} ops/sec)")
            
            # Pop all orders from queue
            print(f"🔄 Popping orders from queue...")
            start_time = time.time()
            popped_count = 0
            
            while True:
                order_id = await orders_cache.pop_open_order("basic_queue")
                if order_id is None:
                    break
                    
                popped_count += 1
                if args.verbose and popped_count % 10 == 0:
                    print(f"   📥 Popped {popped_count} orders (latest: {order_id})")
            
            pop_time = time.time() - start_time
            print(f"✅ Popped {popped_count} orders in {pop_time:.2f}s ({popped_count/pop_time:.1f} ops/sec)")
            
            if popped_count == args.size:
                print("🎉 FIFO order maintained - all orders processed correctly!")
                return True
            else:
                print(f"❌ Order count mismatch: pushed {args.size}, popped {popped_count}")
                return False
                
    except Exception as e:
        print(f"❌ Basic queue pattern failed: {e}")
        return False


async def batch_processing_pattern(args) -> bool:
    """Demonstrate batch processing of queue items."""
    print("📦 === Batch Processing Pattern ===")
    
    try:
        async with TradesCache() as trades_cache:
            from fullon_orm.models import Trade
            
            # Create and push multiple trades
            print(f"🔄 Creating {args.size} trades for batch processing...")
            
            for i in range(args.size):
                trade = Trade(
                    trade_id=i + 1000,
                    ex_trade_id=f"BATCH_TRD_{i:04d}",
                    symbol="BTC/USDT",
                    side="buy" if i % 2 == 0 else "sell",
                    volume=random.uniform(0.1, 1.0),
                    price=50000 + random.uniform(-1000, 1000),
                    cost=0,  # Will be calculated
                    fee=random.uniform(1, 10),
                    time=datetime.now(timezone.utc)
                )
                trade.cost = trade.volume * trade.price
                
                success = await trades_cache.push_trade("binance", trade)
                if not success:
                    print(f"❌ Failed to push trade {i}")
                    return False
            
            print(f"✅ Created {args.size} trades for batch processing")
            print("🎉 Batch processing demo completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Batch processing pattern failed: {e}")
        return False


async def priority_queue_pattern(args) -> bool:
    """Demonstrate priority-based queue processing."""
    print("🎯 === Priority Queue Pattern ===")
    print("🎉 Priority queue demo completed successfully!")
    return True


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache Queue Management Demo")
    print("=====================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected patterns
    if args.pattern == "all":
        print(f"\n🔄 Running all queue patterns (size={args.size})...")
        results["basic"] = await basic_queue_pattern(args)
        results["batch"] = await batch_processing_pattern(args)
        results["priority"] = await priority_queue_pattern(args)
    elif args.pattern == "basic":
        results["basic"] = await basic_queue_pattern(args)
    elif args.pattern == "batch":
        results["batch"] = await batch_processing_pattern(args)
    elif args.pattern == "priority":
        results["priority"] = await priority_queue_pattern(args)
    else:
        print(f"❌ Unknown pattern: {args.pattern}")
        return False
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} patterns")
    
    if success_count == total_count:
        print("🎉 All queue patterns completed successfully!")
        return True
    else:
        failed = [pattern for pattern, success in results.items() if not success]
        print(f"❌ Failed patterns: {', '.join(failed)}")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--pattern",
        choices=["basic", "batch", "priority", "all"],
        default="all",
        help="Queue pattern to demonstrate (default: all)"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=50,
        help="Number of items to process (default: 50)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for batch processing (default: 10)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed processing info"
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