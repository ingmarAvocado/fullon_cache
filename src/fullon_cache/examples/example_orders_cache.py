#!/usr/bin/env python3
"""
OrdersCache Operations Demo Tool

This tool demonstrates order queue management and order status tracking
functionality provided by the OrdersCache class.

Features:
- FIFO order queue operations with Redis lists
- Order status tracking with TTL expiration
- Bulk order processing and management
- Order data persistence and retrieval
- Queue statistics and monitoring
- Order lifecycle demonstration

Usage:
    python example_orders_cache.py --operations basic --orders 50
    python example_orders_cache.py --operations queue --batch-size 10 --verbose
    python example_orders_cache.py --operations status --verbose
    python example_orders_cache.py --help
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
    from fullon_cache import OrdersCache
except ImportError:
    from ..orders_cache import OrdersCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.orders")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with OrdersCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_queue_operations(cache: OrdersCache, order_count: int = 50, verbose: bool = False) -> bool:
    """Demonstrate basic FIFO order queue operations."""
    print("📋 === Basic Order Queue Operations Demo ===")
    
    try:
        queue_id = "demo_queue"
        
        print(f"🔄 Pushing {order_count} orders to queue...")
        start_time = time.time()
        
        # Push orders to queue
        order_ids = []
        for i in range(order_count):
            order_id = f"order_{i:04d}_{int(time.time())}"
            order_ids.append(order_id)
            
            await cache.push_open_order(order_id, queue_id)
            
            if verbose and i % 10 == 0:
                print(f"   📤 Pushed {i + 1}/{order_count} orders")
        
        push_time = time.time() - start_time
        print(f"✅ Pushed {order_count} orders in {push_time:.2f}s ({order_count/push_time:.1f} ops/sec)")
        
        # Pop orders from queue (FIFO verification)
        print("🔄 Popping orders from queue...")
        start_time = time.time()
        
        popped_orders = []
        while True:
            order_id = await cache.pop_open_order(queue_id)
            if order_id is None:
                break
            popped_orders.append(order_id)
            
            if verbose and len(popped_orders) % 10 == 0:
                print(f"   📥 Popped {len(popped_orders)} orders")
        
        pop_time = time.time() - start_time
        popped_count = len(popped_orders)
        
        print(f"✅ Popped {popped_count} orders in {pop_time:.2f}s ({popped_count/pop_time:.1f} ops/sec)")
        
        # Verify FIFO order
        if popped_count == order_count:
            fifo_correct = all(popped_orders[i] == order_ids[i] for i in range(order_count))
            if fifo_correct:
                print("🎉 FIFO order maintained correctly!")
                return True
            else:
                print("❌ FIFO order was not maintained")
                return False
        else:
            print(f"❌ Order count mismatch: pushed {order_count}, popped {popped_count}")
            return False
        
    except Exception as e:
        print(f"❌ Basic queue operations failed: {e}")
        return False


async def order_status_operations(cache: OrdersCache, verbose: bool = False) -> bool:
    """Demonstrate order status tracking with TTL."""
    print("📊 === Order Status Tracking Demo ===")
    
    try:
        # Create test orders with different statuses
        test_orders = [
            {"id": f"status_order_{i:03d}", "status": status}
            for i, status in enumerate([
                "pending", "filled", "cancelled", "partial", "expired"
            ] * 3)  # 15 orders total
        ]
        
        print(f"🔄 Setting status for {len(test_orders)} orders...")
        
        # Set order statuses
        for order in test_orders:
            # Set status with 1 hour TTL
            await cache.set_order_status(order["id"], order["status"], ttl=3600)
            
            if verbose:
                print(f"   📊 Order {order['id']}: {order['status']}")
        
        print(f"✅ Set statuses for {len(test_orders)} orders")
        
        # Retrieve and verify statuses
        print("🔄 Retrieving order statuses...")
        status_counts = {}
        
        for order in test_orders:
            retrieved_status = await cache.get_order_status(order["id"])
            
            if retrieved_status != order["status"]:
                print(f"❌ Status mismatch for {order['id']}: expected {order['status']}, got {retrieved_status}")
                return False
            
            status_counts[retrieved_status] = status_counts.get(retrieved_status, 0) + 1
            
            if verbose:
                print(f"   📊 {order['id']}: {retrieved_status}")
        
        print("📈 Status Distribution:")
        for status, count in status_counts.items():
            print(f"   📊 {status}: {count} orders")
        
        # Test bulk status updates
        print("🔄 Testing bulk status updates...")
        bulk_order_ids = [order["id"] for order in test_orders[:5]]
        
        await cache.set_orders_status(bulk_order_ids, "filled")
        
        # Verify bulk update
        bulk_success = True
        for order_id in bulk_order_ids:
            status = await cache.get_order_status(order_id)
            if status != "filled":
                bulk_success = False
                break
        
        if bulk_success:
            print("✅ Bulk status update successful")
        else:
            print("❌ Bulk status update failed")
            return False
        
        print("✅ Order status operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Order status operations failed: {e}")
        return False


async def order_data_operations(cache: OrdersCache, verbose: bool = False) -> bool:
    """Demonstrate order data persistence and retrieval."""
    print("💾 === Order Data Operations Demo ===")
    
    try:
        from fullon_orm.models import Order
        
        # Create test orders with complete data
        test_orders = []
        exchanges = ["binance", "kraken", "coinbase"]
        
        for i in range(9):  # 3 orders per exchange
            exchange = exchanges[i % 3]
            order = Order(
                id=5000 + i,
                user_id=100,
                exchange_id=1,
                symbol="BTC/USDT",
                side="buy" if i % 2 == 0 else "sell",
                order_type="limit",
                amount=Decimal(str(random.uniform(0.1, 1.0))),
                price=Decimal(str(47000 + random.uniform(-1000, 1000))),
                status="pending",
                timestamp=datetime.now(timezone.utc),
                ex_order_id=f"EX_{exchange.upper()}_{i:04d}"
            )
            test_orders.append((exchange, order))
        
        print(f"🔄 Saving {len(test_orders)} order records...")
        
        # Save order data
        for exchange, order in test_orders:
            success = await cache.save_order_data(exchange, order.ex_order_id, {
                "id": order.id,
                "user_id": order.user_id,
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "amount": float(order.amount),
                "price": float(order.price),
                "status": order.status,
                "timestamp": order.timestamp.isoformat(),
                "ex_order_id": order.ex_order_id
            })
            
            if not success:
                print(f"❌ Failed to save order data for {exchange}:{order.ex_order_id}")
                return False
            
            if verbose:
                print(f"   💾 Saved {exchange}:{order.ex_order_id} ({order.side} {float(order.amount)} {order.symbol})")
        
        print(f"✅ Saved {len(test_orders)} order records")
        
        # Retrieve and verify order data
        print("🔄 Retrieving order data...")
        
        for exchange, order in test_orders:
            retrieved_data = await cache.get_order_data(exchange, order.ex_order_id)
            
            if not retrieved_data:
                print(f"❌ Failed to retrieve order data for {exchange}:{order.ex_order_id}")
                return False
            
            # Verify key fields
            if (retrieved_data.get("id") != order.id or 
                retrieved_data.get("symbol") != order.symbol or
                retrieved_data.get("side") != order.side):
                print(f"❌ Data mismatch for {exchange}:{order.ex_order_id}")
                return False
            
            if verbose:
                print(f"   📊 Retrieved {exchange}:{order.ex_order_id}: {retrieved_data['side']} {retrieved_data['amount']} {retrieved_data['symbol']}")
        
        # Test order data deletion
        print("🔄 Testing order data cleanup...")
        cleanup_order = test_orders[0]
        exchange, order = cleanup_order
        
        # Delete order data
        await cache.delete_order_data(exchange, order.ex_order_id)
        
        # Verify deletion
        deleted_data = await cache.get_order_data(exchange, order.ex_order_id)
        if deleted_data is not None:
            print(f"❌ Order data was not deleted for {exchange}:{order.ex_order_id}")
            return False
        
        print("✅ Order data operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Order data operations failed: {e}")
        return False


async def batch_processing_demo(cache: OrdersCache, batch_size: int = 10, verbose: bool = False) -> bool:
    """Demonstrate batch order processing."""
    print("📦 === Batch Order Processing Demo ===")
    
    try:
        total_orders = batch_size * 3
        queue_id = "batch_processing_queue"
        
        print(f"🔄 Creating {total_orders} orders for batch processing...")
        
        # Create orders in batches
        all_order_ids = []
        for batch in range(3):
            batch_orders = []
            for i in range(batch_size):
                order_id = f"batch_{batch}_{i:03d}_{int(time.time())}"
                batch_orders.append(order_id)
                all_order_ids.append(order_id)
            
            # Push batch to queue
            for order_id in batch_orders:
                await cache.push_open_order(order_id, queue_id)
            
            if verbose:
                print(f"   📦 Batch {batch + 1}: {len(batch_orders)} orders")
        
        print(f"✅ Created {total_orders} orders in {batch_size}-order batches")
        
        # Process orders in batches
        print(f"🔄 Processing orders in batches of {batch_size}...")
        processed_batches = 0
        total_processed = 0
        
        while True:
            # Pop a batch
            batch = []
            for _ in range(batch_size):
                order_id = await cache.pop_open_order(queue_id)
                if order_id is None:
                    break
                batch.append(order_id)
            
            if not batch:
                break
            
            # Simulate batch processing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Set status for entire batch
            await cache.set_orders_status(batch, "processed")
            
            processed_batches += 1
            total_processed += len(batch)
            
            if verbose:
                print(f"   ⚡ Processed batch {processed_batches}: {len(batch)} orders")
        
        print(f"✅ Processed {total_processed} orders in {processed_batches} batches")
        
        # Verify all orders were processed
        if total_processed == total_orders:
            print("🎉 All orders processed successfully!")
            return True
        else:
            print(f"❌ Processing incomplete: {total_processed}/{total_orders}")
            return False
        
    except Exception as e:
        print(f"❌ Batch processing demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache OrdersCache Demo")
    print("================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with OrdersCache() as cache:
            results["basic"] = await basic_queue_operations(cache, args.orders, args.verbose)
    
    if args.operations in ["status", "all"]:
        async with OrdersCache() as cache:
            results["status"] = await order_status_operations(cache, args.verbose)
    
    if args.operations in ["data", "all"]:
        async with OrdersCache() as cache:
            results["data"] = await order_data_operations(cache, args.verbose)
    
    if args.operations in ["batch", "all"]:
        async with OrdersCache() as cache:
            results["batch"] = await batch_processing_demo(cache, args.batch_size, args.verbose)
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All OrdersCache operations completed successfully!")
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
        choices=["basic", "status", "data", "batch", "all"],
        default="all",
        help="Operations to demonstrate (default: all)"
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=50,
        help="Number of orders for basic operations (default: 50)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing demo (default: 10)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed order info"
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