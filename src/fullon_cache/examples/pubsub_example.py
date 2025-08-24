#!/usr/bin/env python3
"""
Real-Time Ticker Pub/Sub Demo Tool

This tool demonstrates live ticker pub/sub functionality with subscriber monitoring
and real-time price updates across multiple exchanges.

Features:
- Live ticker feeds with pub/sub patterns
- Multiple exchange simulation (Binance, Kraken)
- Real-time price monitoring and statistics
- Beautiful output with emojis and status indicators
- Configurable duration and update intervals
- Subscriber connection monitoring

Usage:
    python pubsub_example.py --exchanges binance,kraken --duration 30
    python pubsub_example.py --symbols BTC/USDT,ETH/USDT --verbose
    python pubsub_example.py --mode publisher --duration 60
    python pubsub_example.py --mode subscriber --channels "tickers:*"
    python pubsub_example.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import TickCache, BaseCache
except ImportError:
    from ..tick_cache import TickCache
    from ..base_cache import BaseCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.pubsub")


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


async def ticker_publisher(cache: TickCache, exchange: str, symbols: List[str], 
                          duration: int = 10, verbose: bool = False) -> Dict[str, int]:
    """Simulate ticker updates being published."""
    print(f"🔄 Starting ticker publisher for {exchange} (symbols: {', '.join(symbols)})")
    
    from fullon_orm.models import Symbol, Tick
    
    # Create Symbol objects for clean interface
    symbol_objects = {}
    for sym in symbols:
        base, quote = sym.split('/')
        symbol_objects[sym] = Symbol(
            symbol=sym,
            cat_ex_id=1,
            base=base,
            quote=quote
        )
    
    stats = {symbol: 0 for symbol in symbols}
    start_time = time.time()
    end_time = start_time + duration
    
    try:
        while time.time() < end_time:
            for symbol_str in symbols:
                # Generate realistic random price data
                base_prices = {"BTC/USDT": 50000, "ETH/USDT": 3000, "ADA/USDT": 1.5}
                base_price = base_prices.get(symbol_str, 100)
                price = base_price * (1 + random.uniform(-0.02, 0.02))  # ±2% variation
                
                # Create ticker using fullon_orm.Tick model
                tick = Tick(
                    symbol=symbol_str,
                    exchange=exchange,
                    price=price,
                    volume=random.uniform(100, 1000),
                    time=time.time(),
                    bid=price * 0.999,
                    ask=price * 1.001,
                    last=price
                )
                
                # Use new clean interface for publishing
                symbol_obj = symbol_objects[symbol_str]
                success = await cache.set_ticker(symbol_obj, tick)
                
                if success:
                    stats[symbol_str] += 1
                    if verbose:
                        print(f"   📊 {exchange}: {symbol_str} @ ${price:,.2f}")
                else:
                    print(f"❌ Failed to publish {symbol_str} ticker")
                
            await asyncio.sleep(1)  # Update every second
            
        elapsed = time.time() - start_time
        total_published = sum(stats.values())
        print(f"✅ Publisher {exchange} completed: {total_published} tickers in {elapsed:.1f}s")
        return stats
        
    except Exception as e:
        print(f"❌ Publisher {exchange} failed: {e}")
        return stats


async def ticker_subscriber(base_cache: BaseCache, channel: str, 
                          duration: int = 10, verbose: bool = False) -> int:
    """Subscribe to ticker updates."""
    print(f"🔄 Starting subscriber for channel: {channel}")
    
    received_count = 0
    start_time = time.time()
    
    try:
        async for message in base_cache.subscribe(channel):
            if message['type'] == 'message':
                received_count += 1
                if verbose:
                    print(f"   📨 Received on {message['channel']}: {message['data']}")
                elif received_count % 10 == 0:  # Show progress every 10 messages
                    elapsed = time.time() - start_time
                    rate = received_count / elapsed if elapsed > 0 else 0
                    print(f"   📊 Received {received_count} messages ({rate:.1f}/sec)")
                
            # Check if we should stop
            if time.time() > start_time + duration:
                break
                
        elapsed = time.time() - start_time
        rate = received_count / elapsed if elapsed > 0 else 0
        print(f"✅ Subscriber {channel} completed: {received_count} messages ({rate:.1f}/sec)")
        return received_count
        
    except asyncio.CancelledError:
        elapsed = time.time() - start_time
        rate = received_count / elapsed if elapsed > 0 else 0
        print(f"🔄 Subscriber {channel} cancelled: {received_count} messages ({rate:.1f}/sec)")
        return received_count
    except Exception as e:
        print(f"❌ Subscriber {channel} error: {e}")
        return received_count


async def price_monitor(cache: TickCache, symbols: List[str], 
                       interval: int = 2, checks: int = 5, verbose: bool = False) -> Dict[str, List[float]]:
    """Monitor prices using direct cache access."""
    print(f"🔄 Starting price monitor for {checks} checks every {interval}s")
    
    price_history = {symbol: [] for symbol in symbols}
    
    try:
        for check in range(checks):
            if verbose:
                print(f"\n📊 === Price Check #{check + 1} ===")
            else:
                print(f"\n📊 Current Prices (Check #{check + 1})")
                
            for symbol in symbols:
                # Get price from any exchange
                price = await cache.get_price(symbol)
                if price > 0:
                    price_history[symbol].append(price)
                    trend = ""
                    if len(price_history[symbol]) > 1:
                        prev_price = price_history[symbol][-2]
                        if price > prev_price:
                            trend = "📈"
                        elif price < prev_price:
                            trend = "📉"
                        else:
                            trend = "➡️"
                    
                    print(f"   {trend} {symbol}: ${price:,.2f}")
                    
                    # Also demonstrate getting full ticker as ORM model
                    if verbose:
                        ticker = await cache.get_ticker(symbol, "binance")
                        if ticker:
                            spread = ticker.ask - ticker.bid
                            print(f"      📊 Bid=${ticker.bid:.2f}, Ask=${ticker.ask:.2f}, "
                                  f"Spread=${spread:.2f}, Volume={ticker.volume:.2f}")
                else:
                    print(f"   ❌ {symbol}: No price available")
                    
            await asyncio.sleep(interval)
            
        return price_history
        
    except Exception as e:
        print(f"❌ Price monitor failed: {e}")
        return price_history


async def run_publisher_mode(args) -> bool:
    """Run in publisher-only mode."""
    print("🚀 Running in Publisher Mode")
    
    async with TickCache() as cache:
        exchanges = args.exchanges.split(',')
        symbols = args.symbols.split(',')
        
        # Start publishers for each exchange
        publisher_tasks = []
        for exchange in exchanges:
            task = asyncio.create_task(
                ticker_publisher(cache, exchange.strip(), symbols, args.duration, args.verbose)
            )
            publisher_tasks.append(task)
        
        # Wait for all publishers to complete
        results = await asyncio.gather(*publisher_tasks, return_exceptions=True)
        
        # Summary
        total_published = 0
        for i, result in enumerate(results):
            if isinstance(result, dict):
                exchange_total = sum(result.values())
                total_published += exchange_total
                print(f"✅ {exchanges[i]}: {exchange_total} tickers published")
            else:
                print(f"❌ {exchanges[i]} failed: {result}")
        
        print(f"📊 Total published: {total_published} tickers")
        return True


async def run_subscriber_mode(args) -> bool:
    """Run in subscriber-only mode."""
    print("🚀 Running in Subscriber Mode")
    
    async with BaseCache() as cache:
        channels = args.channels.split(',')
        
        # Start subscribers for each channel
        subscriber_tasks = []
        for channel in channels:
            task = asyncio.create_task(
                ticker_subscriber(cache, channel.strip(), args.duration, args.verbose)
            )
            subscriber_tasks.append(task)
        
        # Wait for all subscribers to complete
        results = await asyncio.gather(*subscriber_tasks, return_exceptions=True)
        
        # Summary
        total_received = 0
        for i, result in enumerate(results):
            if isinstance(result, int):
                total_received += result
                print(f"✅ {channels[i]}: {result} messages received")
            else:
                print(f"❌ {channels[i]} failed: {result}")
        
        print(f"📊 Total received: {total_received} messages")
        return True


async def run_full_demo(args) -> bool:
    """Run full pub/sub demo with publishers, subscribers, and monitoring."""
    print("🚀 Running Full Pub/Sub Demo")
    
    tick_cache = TickCache()
    base_cache = BaseCache()
    
    try:
        exchanges = args.exchanges.split(',')
        symbols = args.symbols.split(',')
        
        # Prepare channels based on exchanges and symbols
        channels = []
        for exchange in exchanges:
            for symbol in symbols:
                channels.append(f"tickers:{exchange.strip()}:{symbol.strip()}")
        
        # Start subscribers first
        print(f"\n🔄 Starting {len(channels)} subscribers...")
        subscriber_tasks = []
        for channel in channels[:3]:  # Limit to first 3 channels to avoid spam
            task = asyncio.create_task(
                ticker_subscriber(base_cache, channel, args.duration, args.verbose)
            )
            subscriber_tasks.append(task)
        
        # Give subscribers time to connect
        await asyncio.sleep(0.5)
        
        # Start publishers
        print(f"\n🔄 Starting {len(exchanges)} publishers...")
        publisher_tasks = []
        for exchange in exchanges:
            task = asyncio.create_task(
                ticker_publisher(tick_cache, exchange.strip(), symbols, args.duration, args.verbose)
            )
            publisher_tasks.append(task)
        
        # Start price monitor
        monitor_task = asyncio.create_task(
            price_monitor(tick_cache, symbols, interval=2, checks=args.duration // 2, verbose=args.verbose)
        )
        
        # Wait for publishers to finish
        print(f"\n🔄 Running demo for {args.duration} seconds...")
        publisher_results = await asyncio.gather(*publisher_tasks, return_exceptions=True)
        
        # Wait for monitor
        price_history = await monitor_task
        
        # Cancel subscribers
        for task in subscriber_tasks:
            task.cancel()
        
        # Wait for subscriber cleanup
        subscriber_results = await asyncio.gather(*subscriber_tasks, return_exceptions=True)
        
        # Summary
        print(f"\n📊 === Demo Summary ===")
        
        # Publisher stats
        total_published = 0
        for i, result in enumerate(publisher_results):
            if isinstance(result, dict):
                exchange_total = sum(result.values())
                total_published += exchange_total
        print(f"📤 Total published: {total_published} tickers")
        
        # Subscriber stats
        total_received = 0
        for result in subscriber_results:
            if isinstance(result, int):
                total_received += result
        print(f"📥 Total received: {total_received} messages")
        
        # Price stats
        for symbol, prices in price_history.items():
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)
                volatility = ((max_price - min_price) / avg_price) * 100
                print(f"📊 {symbol}: Avg=${avg_price:.2f}, Range=${min_price:.2f}-${max_price:.2f}, "
                      f"Volatility={volatility:.2f}%")
        
        return True
        
    finally:
        await tick_cache.close()
        await base_cache.close()


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache Pub/Sub Demo")
    print("============================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    
    # Run based on mode
    if args.mode == "publisher":
        success = await run_publisher_mode(args)
    elif args.mode == "subscriber":
        success = await run_subscriber_mode(args)
    else:  # full demo
        success = await run_full_demo(args)
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 === Final Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    
    if success:
        print("🎉 Pub/Sub demo completed successfully!")
        return True
    else:
        print("❌ Pub/Sub demo encountered errors")
        return False


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--mode",
        choices=["full", "publisher", "subscriber"],
        default="full",
        help="Demo mode (default: full)"
    )
    parser.add_argument(
        "--exchanges",
        default="binance,kraken",
        help="Comma-separated list of exchanges (default: binance,kraken)"
    )
    parser.add_argument(
        "--symbols",
        default="BTC/USDT,ETH/USDT",
        help="Comma-separated list of symbols (default: BTC/USDT,ETH/USDT)"
    )
    parser.add_argument(
        "--channels",
        default="tickers:*",
        help="Comma-separated list of channels for subscriber mode (default: tickers:*)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Demo duration in seconds (default: 15)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed message logging"
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