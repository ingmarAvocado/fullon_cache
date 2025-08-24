#!/usr/bin/env python3
"""
ProcessCache Operations Demo Tool

This tool demonstrates system process monitoring and tracking functionality
provided by the ProcessCache class.

Features:
- Process lifecycle monitoring and management
- Process status tracking with timestamps
- Time-based process filtering and queries
- Process health monitoring and alerts
- Multi-process coordination tracking
- Process statistics and reporting

Usage:
    python example_process_cache.py --operations basic --processes 10
    python example_process_cache.py --operations monitoring --duration 30 --verbose
    python example_process_cache.py --operations filtering --verbose
    python example_process_cache.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import ProcessCache
except ImportError:
    from ..process_cache import ProcessCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.process")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with ProcessCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_process_operations(cache: ProcessCache, process_count: int = 10, verbose: bool = False) -> bool:
    """Demonstrate basic process tracking operations."""
    print("⚙️ === Basic Process Operations Demo ===")
    
    try:
        # Supported process types from CLAUDE.md
        process_types = ['tick', 'ohlcv', 'bot', 'account', 'order', 'bot_status_service', 'crawler', 'user_trades_service']
        
        print(f"🔄 Registering {process_count} processes...")
        
        # Add processes with current timestamps
        added_processes = []
        for i in range(process_count):
            process_type = process_types[i % len(process_types)]
            process_id = f"{process_type}_process_{i:03d}"
            
            await cache.add_process(process_type, process_id)
            added_processes.append((process_type, process_id))
            
            if verbose:
                print(f"   ➕ Added {process_type}: {process_id}")
        
        print(f"✅ Added {process_count} processes")
        
        # Retrieve and verify processes
        print("🔄 Retrieving process lists...")
        
        for process_type in set(pt for pt, _ in added_processes):
            processes = await cache.get_processes(process_type)
            
            expected_count = sum(1 for pt, _ in added_processes if pt == process_type)
            if len(processes) < expected_count:
                print(f"❌ Process count mismatch for {process_type}: expected {expected_count}, got {len(processes)}")
                return False
            
            if verbose:
                print(f"   📊 {process_type}: {len(processes)} processes")
                for process in processes[:3]:  # Show first 3
                    print(f"      - {process}")
        
        # Test time-based filtering
        print("🔄 Testing time-based process filtering...")
        
        # Add a process with specific timestamp (5 minutes ago)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        await cache.add_process('test_process', 'old_process', timestamp=old_time)
        
        # Get processes from last 2 minutes (should not include old process)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
        recent_processes = await cache.get_processes('test_process', since=recent_cutoff)
        
        # Get all test processes
        all_test_processes = await cache.get_processes('test_process')
        
        if len(all_test_processes) > len(recent_processes):
            print("✅ Time-based filtering working correctly")
            if verbose:
                print(f"   📊 All test processes: {len(all_test_processes)}")
                print(f"   📊 Recent test processes: {len(recent_processes)}")
        else:
            print("❌ Time-based filtering not working properly")
            return False
        
        print("✅ Basic process operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Basic process operations failed: {e}")
        return False


async def process_monitoring_demo(cache: ProcessCache, duration: int = 30, verbose: bool = False) -> bool:
    """Demonstrate real-time process monitoring."""
    print("📊 === Process Monitoring Demo ===")
    
    try:
        monitoring_processes = [
            ('bot', 'monitor_bot_001'),
            ('tick', 'monitor_tick_001'),
            ('account', 'monitor_account_001')
        ]
        
        print(f"🔄 Starting {duration}s monitoring simulation...")
        
        # Start monitoring tasks
        monitor_tasks = []
        for process_type, process_id in monitoring_processes:
            task = asyncio.create_task(
                simulate_process_activity(cache, process_type, process_id, duration, verbose)
            )
            monitor_tasks.append(task)
        
        # Monitor overall system
        system_monitor_task = asyncio.create_task(
            monitor_system_processes(cache, monitoring_processes, duration, verbose)
        )
        
        # Wait for all monitoring to complete
        process_results = await asyncio.gather(*monitor_tasks, return_exceptions=True)
        system_result = await system_monitor_task
        
        # Analyze results
        successful_processes = sum(1 for result in process_results if isinstance(result, dict))
        
        print(f"📊 Monitoring Results:")
        print(f"   ⚙️ Monitored processes: {len(monitoring_processes)}")
        print(f"   ✅ Successful processes: {successful_processes}")
        print(f"   📈 System monitoring: {'✅' if system_result else '❌'}")
        
        if successful_processes == len(monitoring_processes) and system_result:
            print("✅ Process monitoring completed successfully")
            return True
        else:
            print("❌ Process monitoring had issues")
            return False
        
    except Exception as e:
        print(f"❌ Process monitoring failed: {e}")
        return False


async def simulate_process_activity(cache: ProcessCache, process_type: str, process_id: str, 
                                  duration: int, verbose: bool = False) -> Dict[str, int]:
    """Simulate activity for a single process."""
    stats = {"updates": 0, "errors": 0}
    start_time = time.time()
    end_time = start_time + duration
    
    try:
        while time.time() < end_time:
            # Add process entry (simulating periodic heartbeat)
            await cache.add_process(process_type, process_id)
            stats["updates"] += 1
            
            if verbose and stats["updates"] % 5 == 0:
                print(f"   💓 {process_id}: {stats['updates']} heartbeats")
            
            # Simulate varying update intervals
            await asyncio.sleep(random.uniform(1.0, 3.0))
        
        if verbose:
            print(f"   ✅ {process_id} completed with {stats['updates']} updates")
        
        return stats
        
    except Exception as e:
        stats["errors"] += 1
        logger.error(f"Process {process_id} simulation failed", error=str(e))
        return stats


async def monitor_system_processes(cache: ProcessCache, monitored_processes: List, 
                                 duration: int, verbose: bool = False) -> bool:
    """Monitor overall system process health."""
    start_time = time.time()
    end_time = start_time + duration
    checks = 0
    
    try:
        while time.time() < end_time:
            await asyncio.sleep(5)  # Check every 5 seconds
            checks += 1
            
            # Check each process type
            system_healthy = True
            process_counts = {}
            
            for process_type, _ in monitored_processes:
                processes = await cache.get_processes(process_type)
                process_counts[process_type] = len(processes)
                
                if len(processes) == 0:
                    system_healthy = False
            
            if verbose:
                print(f"   🔍 System check #{checks}: {process_counts}")
                if not system_healthy:
                    print("   ⚠️ Some processes missing!")
        
        print(f"✅ System monitoring completed: {checks} health checks")
        return True
        
    except Exception as e:
        print(f"❌ System monitoring failed: {e}")
        return False


async def process_filtering_demo(cache: ProcessCache, verbose: bool = False) -> bool:
    """Demonstrate advanced process filtering capabilities."""
    print("🔍 === Process Filtering Demo ===")
    
    try:
        # Create test data with specific timestamps
        test_data = []
        base_time = datetime.now(timezone.utc)
        
        # Add processes at different time intervals
        time_offsets = [0, -300, -600, -1800, -3600]  # 0, 5min, 10min, 30min, 1hour ago
        
        for i, offset in enumerate(time_offsets):
            timestamp = base_time + timedelta(seconds=offset)
            process_id = f"filter_test_{i:02d}"
            await cache.add_process('filter_test', process_id, timestamp=timestamp)
            test_data.append((process_id, timestamp))
            
            if verbose:
                print(f"   📅 Added {process_id} at {timestamp.strftime('%H:%M:%S')}")
        
        print(f"✅ Created {len(test_data)} test processes with varying timestamps")
        
        # Test different time filters
        filter_tests = [
            ("Last 2 minutes", timedelta(minutes=2)),
            ("Last 15 minutes", timedelta(minutes=15)),
            ("Last 45 minutes", timedelta(minutes=45)),
            ("Last 2 hours", timedelta(hours=2))
        ]
        
        print("🔄 Testing time-based filters...")
        
        for filter_name, time_delta in filter_tests:
            since_time = base_time - time_delta
            filtered_processes = await cache.get_processes('filter_test', since=since_time)
            
            # Count expected processes
            expected = sum(1 for _, ts in test_data if ts >= since_time)
            actual = len(filtered_processes)
            
            if verbose:
                print(f"   🔍 {filter_name}: {actual} processes (expected ~{expected})")
            
            if actual > 0:  # Should have at least some processes
                print(f"   ✅ {filter_name}: {actual} processes found")
            else:
                print(f"   ❌ {filter_name}: No processes found")
                return False
        
        # Test process existence and cleanup
        print("🔄 Testing process cleanup...")
        
        # Get all filter_test processes
        all_filter_processes = await cache.get_processes('filter_test')
        
        if len(all_filter_processes) >= len(test_data):
            print(f"✅ All {len(all_filter_processes)} test processes accessible")
        else:
            print(f"❌ Missing processes: expected {len(test_data)}, found {len(all_filter_processes)}")
            return False
        
        print("✅ Process filtering demo completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Process filtering demo failed: {e}")
        return False


async def process_statistics_demo(cache: ProcessCache, verbose: bool = False) -> bool:
    """Demonstrate process statistics and reporting."""
    print("📈 === Process Statistics Demo ===")
    
    try:
        process_types = ['tick', 'bot', 'account', 'order']
        
        print("🔄 Creating diverse process dataset...")
        
        # Create varied process data
        total_processes = 0
        for process_type in process_types:
            # Create different numbers of processes per type
            count = random.randint(3, 8)
            
            for i in range(count):
                process_id = f"stats_{process_type}_{i:02d}"
                # Add some processes with older timestamps
                offset_hours = random.randint(0, 24)
                timestamp = datetime.now(timezone.utc) - timedelta(hours=offset_hours)
                
                await cache.add_process(process_type, process_id, timestamp=timestamp)
                total_processes += 1
        
        print(f"✅ Created {total_processes} processes across {len(process_types)} types")
        
        # Gather statistics
        print("🔄 Analyzing process statistics...")
        
        statistics = {}
        for process_type in process_types:
            # Get all processes of this type
            all_processes = await cache.get_processes(process_type)
            
            # Get recent processes (last hour)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_processes = await cache.get_processes(process_type, since=recent_cutoff)
            
            statistics[process_type] = {
                "total": len(all_processes),
                "recent": len(recent_processes),
                "activity_rate": len(recent_processes) / max(len(all_processes), 1)
            }
        
        # Display statistics
        print("📊 Process Statistics by Type:")
        
        total_all = 0
        total_recent = 0
        
        for process_type, stats in statistics.items():
            total_all += stats["total"]
            total_recent += stats["recent"]
            
            print(f"\n   ⚙️ {process_type.upper()}:")
            print(f"      📊 Total: {stats['total']}")
            print(f"      🕐 Recent (1h): {stats['recent']}")
            print(f"      📈 Activity: {stats['activity_rate']:.1%}")
        
        print(f"\n📊 Overall Statistics:")
        print(f"   ⚙️ Total processes: {total_all}")
        print(f"   🕐 Recent activity: {total_recent}")
        print(f"   📈 System activity: {total_recent/max(total_all, 1):.1%}")
        
        # Health assessment
        if total_all > 0 and total_recent > 0:
            health_score = (total_recent / total_all) * 100
            if health_score > 50:
                print(f"   ✅ System health: Excellent ({health_score:.1f}%)")
            elif health_score > 25:
                print(f"   🟡 System health: Good ({health_score:.1f}%)")
            else:
                print(f"   🟠 System health: Needs attention ({health_score:.1f}%)")
        
        print("✅ Process statistics analysis completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Process statistics demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache ProcessCache Demo")
    print("=================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with ProcessCache() as cache:
            results["basic"] = await basic_process_operations(cache, args.processes, args.verbose)
    
    if args.operations in ["monitoring", "all"]:
        async with ProcessCache() as cache:
            results["monitoring"] = await process_monitoring_demo(cache, args.duration, args.verbose)
    
    if args.operations in ["filtering", "all"]:
        async with ProcessCache() as cache:
            results["filtering"] = await process_filtering_demo(cache, args.verbose)
    
    if args.operations in ["statistics", "all"]:
        async with ProcessCache() as cache:
            results["statistics"] = await process_statistics_demo(cache, args.verbose)
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All ProcessCache operations completed successfully!")
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
        choices=["basic", "monitoring", "filtering", "statistics", "all"],
        default="all",
        help="Operations to demonstrate (default: all)"
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=10,
        help="Number of processes for basic operations (default: 10)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Duration for monitoring demo in seconds (default: 15)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed process info"
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