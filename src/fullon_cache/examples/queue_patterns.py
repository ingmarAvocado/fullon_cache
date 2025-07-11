"""Queue patterns examples for Fullon Cache.

This module demonstrates order and trade queue management patterns.
"""

EXAMPLE = '''
import asyncio
import logging
from datetime import datetime, timezone
import time
from typing import Dict, Any

from fullon_cache import OrdersCache, TradesCache
from fullon_orm.models import Order, Trade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def order_queue_example():
    """Demonstrate order queue operations."""
    logger.info("\\n=== Order Queue Example ===")
    
    orders_cache = OrdersCache()
    
    try:
        # Push order IDs to processing queue
        order_pairs = [
            ("order_001", "local_001"),
            ("order_002", "local_002"),
            ("order_003", "local_003"),
        ]
        
        for oid, local_oid in order_pairs:
            await orders_cache.push_open_order(oid, local_oid)
            logger.info(f"Pushed order {oid} -> {local_oid}")
        
        # Save order data using fullon_orm.Order models
        for i, (oid, _) in enumerate(order_pairs):
            order = Order(
                ex_order_id=oid,
                symbol="BTC/USDT",
                side="buy" if i % 2 == 0 else "sell",
                volume=0.1 * (i + 1),
                price=50000 + (i * 100),
                status="pending",
                exchange="binance",
                timestamp=datetime.now(timezone.utc)
            )
            await orders_cache.save_order("binance", order)
            logger.info(f"Saved order {oid} using ORM model")
        
        # Pop orders from queue (FIFO)
        logger.info("\\nPopping orders from queue:")
        for _ in range(2):
            oid = order_pairs[_][0]
            local_oid = await orders_cache.pop_open_order(oid)
            if local_oid:
                logger.info(f"Popped order {oid} -> {local_oid}")
        
        # Get order status
        logger.info("\\nChecking order statuses:")
        for oid, _ in order_pairs:
            order = await orders_cache.get_order_status("binance", oid)
            if order:
                logger.info(f"Order {oid}: {order}")
        
        # Get all orders for exchange
        all_orders = await orders_cache.get_orders("binance")
        logger.info(f"\\nTotal orders for binance: {len(all_orders)}")
        
    finally:
        await orders_cache.close()


async def trade_queue_example():
    """Demonstrate trade queue operations."""
    logger.info("\\n=== Trade Queue Example ===")
    
    trades_cache = TradesCache()
    
    try:
        # Push public trades
        symbol = "BTC/USDT"
        exchange = "binance"
        
        for i in range(5):
            trade = {
                "id": f"trade_{i:03d}",
                "price": 50000 + (i * 10),
                "size": 0.01 * (i + 1),
                "side": "buy" if i % 2 == 0 else "sell",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            count = await trades_cache.push_trade_list(symbol, exchange, trade)
            logger.info(f"Pushed trade {trade['id']}, list size: {count}")
        
        # Get all trades
        trades = await trades_cache.get_trades_list(symbol, exchange)
        logger.info(f"\\nTotal trades in list: {len(trades)}")
        for trade in trades[-3:]:  # Last 3 trades
            logger.info(f"  {trade}")
        
        # Trade status management
        logger.info("\\nManaging trade statuses:")
        
        # Update trade status
        status_key = f"{exchange}:{symbol}:trade_001"
        await trades_cache.update_trade_status(status_key)
        status = await trades_cache.get_trade_status(status_key)
        logger.info(f"Trade status updated: {status}")
        
        # Get all trade statuses
        all_statuses = await trades_cache.get_all_trade_statuses()
        logger.info(f"Active trade statuses: {len(all_statuses)}")
        
        # User trades
        logger.info("\\nUser trade operations:")
        uid = "user_123"
        
        # Push user trades
        for i in range(3):
            user_trade = {
                "id": f"user_trade_{i:03d}",
                "price": 49900 + (i * 50),
                "size": 0.05,
                "side": "buy",
                "fee": 0.1,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await trades_cache.push_my_trades_list(uid, exchange, user_trade)
            logger.info(f"Pushed user trade {user_trade['id']}")
        
        # Pop user trades
        while True:
            trade = await trades_cache.pop_my_trade(uid, exchange, timeout=1)
            if trade:
                logger.info(f"Popped user trade: {trade['id']}")
            else:
                logger.info("No more user trades")
                break
                
    finally:
        await trades_cache.close()


async def advanced_queue_patterns():
    """Demonstrate advanced queue patterns."""
    logger.info("\\n=== Advanced Queue Patterns ===")
    
    orders_cache = OrdersCache()
    
    try:
        # Batch processing pattern
        logger.info("\\nBatch order processing:")
        
        # Push multiple orders
        batch_size = 10
        for i in range(batch_size):
            await orders_cache.push_open_order(f"batch_{i:03d}", f"local_batch_{i:03d}")
        
        # Process in batches
        processed = 0
        while processed < batch_size:
            # Process up to 3 at a time
            batch = []
            for _ in range(min(3, batch_size - processed)):
                oid = f"batch_{processed:03d}"
                local_oid = await orders_cache.pop_open_order(oid)
                if local_oid:
                    batch.append((oid, local_oid))
                    processed += 1
            
            if batch:
                logger.info(f"Processing batch of {len(batch)} orders")
                # Simulate batch processing
                await asyncio.sleep(0.5)
        
        # Priority queue pattern (using multiple queues)
        logger.info("\\nPriority queue pattern:")
        
        # High priority orders
        for i in range(3):
            await orders_cache.push_open_order(f"high_{i}", f"local_high_{i}")
            await orders_cache.save_order_data("binance", f"high_{i}", {"priority": "high"})
        
        # Normal priority orders
        for i in range(5):
            await orders_cache.push_open_order(f"normal_{i}", f"local_normal_{i}")
            await orders_cache.save_order_data("binance", f"normal_{i}", {"priority": "normal"})
        
        # Process high priority first
        logger.info("Processing high priority orders first...")
        # In real implementation, you'd check different queues
        
    finally:
        await orders_cache.close()


async def main():
    """Run all queue pattern examples."""
    print("Fullon Cache Queue Patterns Examples")
    print("====================================")
    
    await order_queue_example()
    await trade_queue_example()
    await advanced_queue_patterns()
    
    print("\\nQueue pattern examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
'''

# Make the example runnable when imported
async def main():
    """Execute the queue pattern examples."""
    exec_globals = {}
    exec(EXAMPLE, exec_globals)
    await exec_globals['main']()

__all__ = ['EXAMPLE', 'main']
