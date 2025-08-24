#!/usr/bin/env python3
"""
AccountCache Operations Demo Tool

This tool demonstrates account and position management functionality
provided by the AccountCache class.

Features:
- Account balance caching and retrieval
- Position tracking with cost basis calculations
- Account data synchronization with database
- Balance updates and position modifications
- Account summary and portfolio views
- Context manager usage for account operations

Usage:
    python example_account_cache.py --operations basic --accounts 3
    python example_account_cache.py --operations positions --verbose
    python example_account_cache.py --operations all --accounts 5
    python example_account_cache.py --help
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
    from fullon_cache import AccountCache
except ImportError:
    from ..account_cache import AccountCache

from fullon_log import get_component_logger

logger = get_component_logger("fullon.cache.examples.account")


async def test_redis_connection() -> bool:
    """Test Redis connection with helpful error reporting."""
    try:
        async with AccountCache() as cache:
            await cache.ping()
            print("✅ Redis connection successful")
            return True
    except Exception as e:
        print("❌ Redis connection failed - is Redis running?")
        print(f"   Error: {e}")
        print("   Try: redis-server or docker run -d -p 6379:6379 redis")
        return False


async def account_operations_demo(cache: AccountCache, account_count: int = 3, verbose: bool = False) -> bool:
    """Demonstrate account balance operations."""
    print("💰 === Account Balance Operations Demo ===")
    
    try:
        from fullon_orm.models import Account
        
        # Create test accounts
        test_accounts = []
        for i in range(account_count):
            account = Account(
                id=1000 + i,
                user_id=100 + i,
                exchange_id=1,  # Binance
                account_name=f"test_account_{i}",
                dry_run=True
            )
            test_accounts.append(account)
        
        print(f"🔄 Setting up {account_count} test accounts...")
        
        # Set account balances
        for i, account in enumerate(test_accounts):
            balance_data = {
                "BTC": {"total": Decimal("1.5"), "free": Decimal("1.2"), "used": Decimal("0.3")},
                "ETH": {"total": Decimal("10.0"), "free": Decimal("8.5"), "used": Decimal("1.5")},
                "USDT": {"total": Decimal("5000.0"), "free": Decimal("4200.0"), "used": Decimal("800.0")}
            }
            
            success = await cache.set_account_balance(account, balance_data)
            if not success:
                print(f"❌ Failed to set balance for account {account.id}")
                return False
            
            if verbose:
                print(f"   💳 Set balance for account {account.id}: {len(balance_data)} currencies")
        
        print(f"✅ Account balances set successfully")
        
        # Retrieve and verify balances
        print("🔄 Retrieving account balances...")
        for account in test_accounts:
            balance = await cache.get_account_balance(account)
            
            if balance and "BTC" in balance:
                btc_total = float(balance["BTC"]["total"])
                if verbose:
                    print(f"   💰 Account {account.id}: BTC balance = {btc_total}")
                
                if btc_total != 1.5:
                    print(f"❌ Balance mismatch for account {account.id}")
                    return False
            else:
                print(f"❌ Failed to retrieve balance for account {account.id}")
                return False
        
        print("✅ Account balance operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Account operations demo failed: {e}")
        return False


async def position_operations_demo(cache: AccountCache, verbose: bool = False) -> bool:
    """Demonstrate position tracking operations."""
    print("📊 === Position Tracking Demo ===")
    
    try:
        from fullon_orm.models import Account, Position
        
        # Create test account
        account = Account(
            id=2000,
            user_id=200,
            exchange_id=1,
            account_name="position_test_account",
            dry_run=True
        )
        
        # Create test positions
        positions = [
            Position(
                id=1,
                user_id=200,
                symbol="BTC/USDT",
                exchange="binance",
                side="long",
                size=Decimal("0.5"),
                entry_price=Decimal("45000.0"),
                current_price=Decimal("47000.0"),
                unrealized_pnl=Decimal("1000.0"),
                timestamp=datetime.now(timezone.utc)
            ),
            Position(
                id=2,
                user_id=200,
                symbol="ETH/USDT",
                exchange="binance",
                side="short",
                size=Decimal("2.0"),
                entry_price=Decimal("3200.0"),
                current_price=Decimal("3100.0"),
                unrealized_pnl=Decimal("200.0"),
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        print("🔄 Setting up test positions...")
        
        # Set positions
        for position in positions:
            success = await cache.set_position(account, position)
            if not success:
                print(f"❌ Failed to set position for {position.symbol}")
                return False
            
            if verbose:
                print(f"   📈 Set {position.side} position: {position.symbol} @ ${float(position.entry_price)}")
        
        # Retrieve positions
        print("🔄 Retrieving positions...")
        retrieved_positions = await cache.get_positions(account)
        
        if len(retrieved_positions) == len(positions):
            print(f"✅ Retrieved {len(retrieved_positions)} positions successfully")
            
            for symbol, pos_data in retrieved_positions.items():
                if verbose:
                    print(f"   📊 {symbol}: {pos_data.get('side')} size={pos_data.get('size')} PnL={pos_data.get('unrealized_pnl')}")
        else:
            print(f"❌ Position count mismatch: expected {len(positions)}, got {len(retrieved_positions)}")
            return False
        
        # Update a position
        print("🔄 Updating position prices...")
        updated_position = positions[0]
        updated_position.current_price = Decimal("48000.0")
        updated_position.unrealized_pnl = Decimal("1500.0")
        
        success = await cache.set_position(account, updated_position)
        if not success:
            print("❌ Failed to update position")
            return False
        
        # Verify update
        updated_positions = await cache.get_positions(account)
        btc_position = updated_positions.get("BTC/USDT", {})
        
        if float(btc_position.get("current_price", 0)) == 48000.0:
            print("✅ Position update successful")
        else:
            print("❌ Position update failed")
            return False
        
        print("✅ Position tracking operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Position operations demo failed: {e}")
        return False


async def portfolio_summary_demo(cache: AccountCache, verbose: bool = False) -> bool:
    """Demonstrate portfolio summary functionality."""
    print("📈 === Portfolio Summary Demo ===")
    
    try:
        from fullon_orm.models import Account
        
        # Create test account
        account = Account(
            id=3000,
            user_id=300,
            exchange_id=1,
            account_name="portfolio_account",
            dry_run=True
        )
        
        # Set diverse portfolio
        portfolio_data = {
            "BTC": {"total": Decimal("2.0"), "free": Decimal("1.8"), "used": Decimal("0.2")},
            "ETH": {"total": Decimal("15.0"), "free": Decimal("12.0"), "used": Decimal("3.0")},
            "ADA": {"total": Decimal("1000.0"), "free": Decimal("950.0"), "used": Decimal("50.0")},
            "USDT": {"total": Decimal("10000.0"), "free": Decimal("8500.0"), "used": Decimal("1500.0")}
        }
        
        print("🔄 Setting up diverse portfolio...")
        success = await cache.set_account_balance(account, portfolio_data)
        
        if not success:
            print("❌ Failed to set portfolio data")
            return False
        
        # Retrieve and analyze portfolio
        balance = await cache.get_account_balance(account)
        
        if not balance:
            print("❌ Failed to retrieve portfolio")
            return False
        
        print("📊 Portfolio Analysis:")
        total_assets = len(balance)
        total_value_estimate = 0
        
        # Simple value estimation (in practice, you'd use real prices)
        price_estimates = {"BTC": 47000, "ETH": 3100, "ADA": 1.2, "USDT": 1.0}
        
        for currency, amounts in balance.items():
            total = float(amounts["total"])
            free = float(amounts["free"])
            used = float(amounts["used"])
            
            estimated_value = total * price_estimates.get(currency, 0)
            total_value_estimate += estimated_value
            
            if verbose:
                print(f"   💰 {currency}: Total={total:,.4f}, Free={free:,.4f}, Used={used:,.4f} (≈${estimated_value:,.2f})")
            else:
                print(f"   💰 {currency}: {total:,.4f} (≈${estimated_value:,.2f})")
        
        print(f"📈 Total Assets: {total_assets}")
        print(f"💵 Estimated Portfolio Value: ${total_value_estimate:,.2f}")
        print("✅ Portfolio summary completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Portfolio summary demo failed: {e}")
        return False


async def run_demo(args) -> bool:
    """Main demo runner based on CLI arguments."""
    print("🚀 Fullon Cache AccountCache Demo")
    print("=================================")
    
    # Connection test
    print("\n🔌 Testing Redis connection...")
    if not await test_redis_connection():
        return False
    
    start_time = time.time()
    results = {}
    
    # Run selected operations
    if args.operations in ["basic", "all"]:
        async with AccountCache() as cache:
            results["basic"] = await account_operations_demo(cache, args.accounts, args.verbose)
    
    if args.operations in ["positions", "all"]:
        async with AccountCache() as cache:
            results["positions"] = await position_operations_demo(cache, args.verbose)
    
    if args.operations in ["portfolio", "all"]:
        async with AccountCache() as cache:
            results["portfolio"] = await portfolio_summary_demo(cache, args.verbose)
    
    # Summary
    elapsed = time.time() - start_time
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 === Summary ===")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"✅ Success: {success_count}/{total_count} operations")
    
    if success_count == total_count:
        print("🎉 All AccountCache operations completed successfully!")
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
        choices=["basic", "positions", "portfolio", "all"],
        default="all",
        help="Operations to demonstrate (default: all)"
    )
    parser.add_argument(
        "--accounts",
        type=int,
        default=3,
        help="Number of test accounts (default: 3)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed account info"
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