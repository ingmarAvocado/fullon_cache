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

import argparse
import asyncio
import sys
import time
from datetime import UTC, datetime

try:
    from fullon_cache import AccountCache
except ImportError:
    from ..account_cache import AccountCache

from fullon_log import get_component_logger
from fullon_orm.models import Position

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


async def account_operations_demo(
    cache: AccountCache, account_count: int = 3, verbose: bool = False
) -> bool:
    """Demonstrate account balance operations."""
    print("💰 === Account Balance Operations Demo ===")

    try:
        # Create test account data (using exchange IDs since Account model doesn't exist)
        test_exchange_ids = []
        for i in range(account_count):
            exchange_id = 1000 + i
            test_exchange_ids.append(exchange_id)

        print(f"🔄 Setting up {account_count} test accounts...")

        # Set account balances using fullon_orm methods
        for _i, exchange_id in enumerate(test_exchange_ids):
            balance_data = {
                "BTC": {"total": 1.5, "free": 1.2, "used": 0.3},
                "ETH": {"total": 10.0, "free": 8.5, "used": 1.5},
                "USDT": {"total": 5000.0, "free": 4200.0, "used": 800.0},
            }

            success = await cache.upsert_user_account(exchange_id, balance_data)
            if not success:
                print(f"❌ Failed to set balance for exchange {exchange_id}")
                return False

            if verbose:
                print(
                    f"   💳 Set balance for exchange {exchange_id}: {len(balance_data)} currencies"
                )

        print("✅ Account balances set successfully")

        # Retrieve and verify balances
        print("🔄 Retrieving account balances...")
        for exchange_id in test_exchange_ids:
            # Get account data for BTC currency
            btc_balance = await cache.get_full_account(exchange_id, "BTC")

            if btc_balance and "total" in btc_balance:
                btc_total = float(btc_balance["total"])
                if verbose:
                    print(f"   💰 Exchange {exchange_id}: BTC balance = {btc_total}")

                if abs(btc_total - 1.5) > 0.01:  # Allow small floating point differences
                    print(f"❌ Balance mismatch for exchange {exchange_id}")
                    return False
            else:
                print(f"❌ Failed to retrieve balance for exchange {exchange_id}")
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
        # Create test exchange ID
        exchange_id = 2000

        # Create test positions using fullon_orm Position model
        positions = [
            Position(
                symbol="BTC/USDT",
                cost=22500.0,  # 0.5 * 45000
                volume=0.5,
                fee=22.5,
                price=45000.0,
                timestamp=datetime.now(UTC).timestamp(),
                ex_id=str(exchange_id),
            ),
            Position(
                symbol="ETH/USDT",
                cost=6400.0,  # 2.0 * 3200
                volume=2.0,
                fee=6.4,
                price=3200.0,
                timestamp=datetime.now(UTC).timestamp(),
                ex_id=str(exchange_id),
            ),
        ]

        print("🔄 Setting up test positions...")

        # Set positions using AccountCache upsert_positions
        success = await cache.upsert_positions(exchange_id, positions)
        if not success:
            print("❌ Failed to set positions")
            return False

        for position in positions:
            if verbose:
                print(
                    f"   📈 Set position: {position.symbol} @ ${position.price} "
                    + f"(Vol: {position.volume})"
                )

        # Retrieve positions
        print("🔄 Retrieving positions...")
        retrieved_positions = await cache.get_all_positions()

        # Filter positions for our exchange
        our_positions = [p for p in retrieved_positions if p.ex_id == str(exchange_id)]

        if len(our_positions) == len(positions):
            print(f"✅ Retrieved {len(our_positions)} positions successfully")

            for position in our_positions:
                if verbose:
                    print(
                        f"   📊 {position.symbol}: Vol={position.volume}, "
                        + f"Cost=${position.cost}, Price=${position.price}"
                    )
        else:
            print(
                f"❌ Position count mismatch: expected {len(positions)}, got {len(our_positions)}"
            )
            return False

        # Update a position
        print("🔄 Updating position prices...")
        updated_position = positions[0]
        updated_position.price = 48000.0
        updated_position.cost = updated_position.volume * updated_position.price

        success = await cache.upsert_position(updated_position)
        if not success:
            print("❌ Failed to update position")
            return False

        # Verify update
        btc_position = await cache.get_position("BTC/USDT", str(exchange_id))

        if abs(btc_position.price - 48000.0) < 0.01:
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
        # Create test exchange ID
        exchange_id = 3000

        # Set diverse portfolio
        portfolio_data = {
            "BTC": {"total": 2.0, "free": 1.8, "used": 0.2},
            "ETH": {"total": 15.0, "free": 12.0, "used": 3.0},
            "ADA": {"total": 1000.0, "free": 950.0, "used": 50.0},
            "USDT": {"total": 10000.0, "free": 8500.0, "used": 1500.0},
        }

        print("🔄 Setting up diverse portfolio...")
        success = await cache.upsert_user_account(exchange_id, portfolio_data)

        if not success:
            print("❌ Failed to set portfolio data")
            return False

        # Retrieve and analyze portfolio
        all_accounts = await cache.get_all_accounts()
        balance = all_accounts.get(str(exchange_id), {})

        if not balance:
            print("❌ Failed to retrieve portfolio")
            return False

        print("📊 Portfolio Analysis:")
        total_assets = 0
        total_value_estimate = 0

        # Simple value estimation (in practice, you'd use real prices)
        price_estimates = {"BTC": 47000, "ETH": 3100, "ADA": 1.2, "USDT": 1.0}

        for currency, amounts in balance.items():
            if currency == "date":  # Skip the timestamp field
                continue

            total_assets += 1
            total = float(amounts["total"])
            free = float(amounts["free"])
            used = float(amounts["used"])

            estimated_value = total * price_estimates.get(currency, 0)
            total_value_estimate += estimated_value

            if verbose:
                print(
                    f"   💰 {currency}: Total={total:,.4f}, Free={free:,.4f}, "
                    + f"Used={used:,.4f} (≈${estimated_value:,.2f})"
                )
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

    print("\n📊 === Summary ===")
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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--operations",
        choices=["basic", "positions", "portfolio", "all"],
        default="all",
        help="Operations to demonstrate (default: all)",
    )
    parser.add_argument(
        "--accounts", type=int, default=3, help="Number of test accounts (default: 3)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with detailed account info"
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
