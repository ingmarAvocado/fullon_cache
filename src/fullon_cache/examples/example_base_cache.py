#!/usr/bin/env python3
"""
BaseCache Operations Demo Tool

This tool demonstrates core Redis operations and connection management
functionality provided by the BaseCache class.

Features:
- Redis connection testing and health checks
- Basic Redis operations (set, get, delete)
- Key pattern matching and bulk operations
- Error queue management
- Context manager usage
- Connection pooling demonstrations

Usage:
    python example_base_cache.py --operations basic --keys 100
    python example_base_cache.py --operations all --verbose
    python example_base_cache.py --test-connection
    python example_base_cache.py --help
"""

import asyncio
import argparse
import sys
import time
import random
from typing import Dict, Any, List, Optional

try:
    from fullon_cache import BaseCache
except ImportError:
    from ..base_cache import BaseCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.base")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with BaseCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def basic_operations_demo(cache: BaseCache, verbose: bool = False) -> bool:
    """Demonstrate basic Redis operations."""
    print("📋 === Basic Redis Operations Demo ===")
    
    try:
        # Test basic set/get operations
        test_key = "demo:basic:test"
        test_value = {"message": "Hello Redis", "timestamp": time.time()}
        
        print("🔄 Testing basic SET/GET operations...")
        await cache.set_data(test_key, test_value, ttl=60)
        
        retrieved = await cache.get_data(test_key)
        if retrieved and retrieved.get("message") == "Hello Redis":
            print("✅ SET/GET operations working correctly")
        else:
            print("❌ SET/GET operations failed")
            return False
        
        # Test key existence and deletion
        exists_before = await cache.key_exists(test_key)
        await cache.delete_key(test_key)
        exists_after = await cache.key_exists(test_key)
        
        if exists_before and not exists_after:
            print("✅ Key deletion working correctly")
        else:
            print("❌ Key deletion failed")
            return False
            
        if verbose:
            print(f"   📊 Key existed before deletion: {exists_before}")
            print(f"   📊 Key exists after deletion: {exists_after}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic operations demo failed: {e}")
        return False


async def bulk_operations_demo(cache: BaseCache, key_count: int = 100, verbose: bool = False) -> bool:
    """Demonstrate bulk operations and key patterns."""
    print("📦 === Bulk Operations Demo ===")
    
    try:
        # Create multiple test keys
        print(f"🔄 Creating {key_count} test keys...")
        start_time = time.time()
        
        for i in range(key_count):
            key = f"demo:bulk:item_{i:04d}"
            value = {
                "id": i,
                "data": f"test_data_{i}",
                "created": time.time()
            }
            await cache.set_data(key, value, ttl=300)
            
            if verbose and i % 20 == 0:
                print(f"   📤 Created {i + 1}/{key_count} keys")
        
        create_time = time.time() - start_time
        print(f"✅ Created {key_count} keys in {create_time:.2f}s ({key_count/create_time:.1f} keys/sec)")
        
        # Test pattern matching
        print("🔍 Testing key pattern matching...")
        pattern_keys = await cache.get_keys("demo:bulk:*")
        
        if len(pattern_keys) >= key_count:
            print(f"✅ Pattern matching found {len(pattern_keys)} keys")
        else:
            print(f"❌ Pattern matching failed: found {len(pattern_keys)}, expected {key_count}")
            return False
        
        # Clean up bulk keys
        print("🧹 Cleaning up test keys...")
        cleanup_start = time.time()
        
        for key in pattern_keys:
            await cache.delete_key(key)
        
        cleanup_time = time.time() - cleanup_start
        print(f"✅ Cleaned up {len(pattern_keys)} keys in {cleanup_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Bulk operations demo failed: {e}")
        return False


async def error_queue_demo(cache: BaseCache, verbose: bool = False) -> bool:
    """Demonstrate error queue functionality."""
    print("🚨 === Error Queue Demo ===")
    
    try:
        # Push some test errors
        test_errors = [
            "Connection timeout to exchange",
            "Invalid symbol format",
            "Rate limit exceeded"
        ]
        
        print("🔄 Adding test errors to global queue...")
        for error in test_errors:
            await cache.push_global_error(error)
            if verbose:
                print(f"   📤 Added error: {error}")
        
        # Pop errors from queue
        print("🔄 Retrieving errors from queue...")
        retrieved_errors = []
        
        while True:
            error = await cache.pop_global_error()
            if error is None:
                break
            retrieved_errors.append(error)
            if verbose:
                print(f"   📥 Retrieved error: {error}")
        
        if len(retrieved_errors) == len(test_errors):
            print(f"✅ Error queue working correctly ({len(retrieved_errors)} errors)")
            return True
        else:
            print(f"❌ Error queue failed: pushed {len(test_errors)}, retrieved {len(retrieved_errors)}")
            return False
        
    except Exception as e:
        print(f"❌ Error queue demo failed: {e}")
        return False


async def context_manager_demo(verbose: bool = False) -> bool:
    """Demonstrate context manager usage."""
    print("🔄 === Context Manager Demo ===")
    
    try:
        # Test context manager
        print("🔄 Testing context manager resource cleanup...")
        
        async with BaseCache() as cache:
            # Perform some operations inside context
            await cache.set_data("demo:context:test", {"active": True}, ttl=60)
            exists = await cache.key_exists("demo:context:test")
            
            if verbose:
                print(f"   📊 Key exists inside context: {exists}")
            
            if not exists:
                print("❌ Context manager operations failed")
                return False
        
        print("✅ Context manager cleanup completed successfully")
        
        # Verify cleanup by creating new instance
        cache2 = BaseCache()
        try:
            await cache2.delete_key("demo:context:test")
            await cache2.close()
        except Exception:
            pass  # Expected if connection was properly closed
        
        return True
        
    except Exception as e:
        print(f"❌ Context manager demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache BaseCache Demo")
    print("=============================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with BaseCache() as cache:
            results["basic"] = await basic_operations_demo(cache, args.verbose)
    
    if args.operations in ["bulk", "all"]:
        async with BaseCache() as cache:
            results["bulk"] = await bulk_operations_demo(cache, args.keys, args.verbose)
    
    if args.operations in ["errors", "all"]:
        async with BaseCache() as cache:
            results["errors"] = await error_queue_demo(cache, args.verbose)
    
    if args.operations in ["context", "all"]:
        results["context"] = await context_manager_demo(args.verbose)
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All BaseCache operations completed successfully!")
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
        choices=["basic", "bulk", "errors", "context", "all"],
        default="all",
        help="Operations to demonstrate (default: all)"
    )
    parser.add_argument(
        "--keys",
        type=int,
        default=50,
        help="Number of keys for bulk operations (default: 50)"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Only test Redis connection and exit"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed operation info"
    )
    
    args = parser.parse_args()
    
    # Handle connection-only test
    if args.test_connection:
        try:
            success = asyncio.run(test_redis_connection())
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            sys.exit(1)
    
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