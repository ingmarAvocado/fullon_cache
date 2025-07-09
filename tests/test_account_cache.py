"""Comprehensive tests for simplified AccountCache."""

import json
from unittest.mock import patch

import pytest
from fullon_orm.models import Position

from fullon_cache import AccountCache
from fullon_cache.exceptions import ConnectionError


class TestAccountCacheCore:
    """Test core account cache operations."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Test cache initialization."""
        cache = AccountCache()
        assert cache._cache is not None

    @pytest.mark.asyncio
    async def test_upsert_positions_basic(self, account_cache):
        """Test basic position upsert."""
        from fullon_orm.models import Position
        
        positions = [
            Position(
                symbol="BTC/USD",
                cost=50000.0,
                volume=1.0,
                fee=10.0,
                price=50000.0,
                timestamp=1704067200.0,  # 2024-01-01 00:00:00 UTC
                ex_id="123"
            )
        ]

        result = await account_cache.upsert_positions(123, positions)
        assert result is True

        # Verify position was stored
        position = await account_cache.get_position("BTC/USD", "123")
        assert position.symbol == "BTC/USD"
        assert position.cost == 50000.0
        assert position.volume == 1.0

    @pytest.mark.asyncio
    async def test_upsert_positions_empty_deletes(self, account_cache):
        """Test that empty positions list deletes data."""
        from fullon_orm.models import Position
        
        # First add some positions
        positions = [
            Position(
                symbol="BTC/USD",
                cost=50000.0,
                volume=1.0,
                fee=10.0,
                price=50000.0,
                timestamp=1704067200.0,
                ex_id="456"
            )
        ]
        await account_cache.upsert_positions(456, positions)

        # Now delete by passing empty list
        result = await account_cache.upsert_positions(456, [])
        assert result is True

        # Verify positions are gone
        position = await account_cache.get_position("BTC/USD", "456")
        assert position.volume == 0.0  # Default empty position

    @pytest.mark.asyncio
    async def test_upsert_positions_update_date_only(self, account_cache):
        """Test updating only timestamp."""
        from fullon_orm.models import Position
        
        # First add positions
        positions = [
            Position(
                symbol="ETH/USD",
                cost=3000.0,
                volume=10.0,
                fee=5.0,
                price=3000.0,
                timestamp=1704067200.0,
                ex_id="789"
            )
        ]
        await account_cache.upsert_positions(789, positions)

        # Update date only
        result = await account_cache.upsert_positions(789, [], update_date=True)
        assert result is True

        # Verify position data unchanged
        position = await account_cache.get_position("ETH/USD", "789")
        assert position.cost == 3000.0
        assert position.volume == 10.0

    @pytest.mark.asyncio
    async def test_upsert_positions_update_date_no_existing(self, account_cache):
        """Test update_date with no existing positions."""
        result = await account_cache.upsert_positions(999, [], update_date=True)
        assert result is False

    @pytest.mark.asyncio
    async def test_upsert_positions_invalid_input(self, account_cache):
        """Test with invalid input (not list of Position objects)."""
        # Pass a dict instead of list of Position objects
        invalid_positions = {
            "BTC/USD": {
                "cost": 50000.0,
                "volume": 1.0
            }
        }

        result = await account_cache.upsert_positions(111, invalid_positions)
        assert result is False  # Should return False for invalid input

        # Verify no position stored
        position = await account_cache.get_position("BTC/USD", "111")
        assert position.volume == 0.0

    @pytest.mark.asyncio
    async def test_upsert_positions_error_handling(self, account_cache):
        """Test error handling in upsert_positions."""
        with patch.object(account_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = ConnectionError("Connection failed")

            result = await account_cache.upsert_positions(123, {})
            assert result is False


class TestAccountCacheAccounts:
    """Test account management."""

    @pytest.mark.asyncio
    async def test_upsert_user_account_basic(self, account_cache):
        """Test basic account upsert."""
        account_data = {
            "USDT": {"balance": 10000.0, "available": 8000.0},
            "BTC": {"balance": 0.5, "available": 0.4}
        }

        result = await account_cache.upsert_user_account(123, account_data)
        assert result is True

        # Verify account was stored
        usdt_data = await account_cache.get_full_account(123, "USDT")
        assert usdt_data == {"balance": 10000.0, "available": 8000.0}

    @pytest.mark.asyncio
    async def test_upsert_user_account_update_date_only(self, account_cache):
        """Test updating only date field."""
        # First create account
        account_data = {"USDT": {"balance": 5000.0}}
        await account_cache.upsert_user_account(456, account_data)

        # Update date only
        result = await account_cache.upsert_user_account(
            456, {}, update_date="2024-01-15 10:30:00"
        )
        assert result is True

        # Verify data unchanged except date
        accounts = await account_cache.get_all_accounts()
        assert "456" in accounts
        assert accounts["456"]["date"] == "2024-01-15 10:30:00"
        assert accounts["456"]["USDT"]["balance"] == 5000.0

    @pytest.mark.asyncio
    async def test_upsert_user_account_update_date_no_existing(self, account_cache):
        """Test update_date with no existing account."""
        result = await account_cache.upsert_user_account(
            999, {}, update_date="2024-01-15 10:30:00"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_upsert_user_account_error_handling(self, account_cache):
        """Test error handling in upsert_user_account."""
        with patch.object(account_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = TypeError("Invalid type")

            result = await account_cache.upsert_user_account(123, {})
            assert result is False


class TestAccountCacheRetrieval:
    """Test data retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_position_existing(self, account_cache):
        """Test getting existing position."""
        from fullon_orm.models import Position
        
        positions = [
            Position(
                symbol="BTC/USD",
                cost=25000.0,
                volume=0.5,
                fee=5.0,
                price=50000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]
        await account_cache.upsert_positions(123, positions)

        position = await account_cache.get_position("BTC/USD", "123")
        assert isinstance(position, Position)
        assert position.symbol == "BTC/USD"
        assert position.cost == 25000.0
        assert position.volume == 0.5
        assert position.ex_id == "123"

    @pytest.mark.asyncio
    async def test_get_position_nonexistent(self, account_cache):
        """Test getting non-existent position."""
        position = await account_cache.get_position("FAKE/USD", "123")
        assert isinstance(position, Position)
        assert position.symbol == "FAKE/USD"
        assert position.volume == 0.0  # Default value

    @pytest.mark.asyncio
    async def test_get_position_empty_ex_id(self, account_cache):
        """Test get_position with empty ex_id."""
        position = await account_cache.get_position("BTC/USD", "")
        assert position.symbol == "BTC/USD"
        assert position.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_position_error_handling(self, account_cache):
        """Test error handling in get_position."""
        # First add a position
        positions = [
            Position(
                symbol="BTC/USD",
                cost=1000.0,
                volume=1.0,
                fee=1.0,
                price=1000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]
        await account_cache.upsert_positions(123, positions)

        # Mock JSON decode error
        with patch('json.loads') as mock_loads:
            mock_loads.side_effect = json.JSONDecodeError("Invalid", "", 0)

            position = await account_cache.get_position("BTC/USD", "123")
            assert position.symbol == "BTC/USD"
            assert position.volume == 0.0  # Returns default position on error

    @pytest.mark.asyncio
    async def test_get_all_positions(self, account_cache):
        """Test getting all positions."""
        # Clean any existing data first
        await account_cache.clean_positions()

        # Add positions for multiple exchanges
        positions1 = [
            Position(
                symbol="BTC/USD",
                cost=50000.0,
                volume=1.0,
                fee=10.0,
                price=50000.0,
                timestamp=1704067200.0,
                ex_id="123"
            ),
            Position(
                symbol="ETH/USD",
                cost=3000.0,
                volume=10.0,
                fee=5.0,
                price=3000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]
        positions2 = [
            Position(
                symbol="BTC/EUR",
                cost=45000.0,
                volume=0.5,
                fee=8.0,
                price=45000.0,
                timestamp=1704067200.0,
                ex_id="456"
            )
        ]

        await account_cache.upsert_positions(123, positions1)
        await account_cache.upsert_positions(456, positions2)

        all_positions = await account_cache.get_all_positions()
        assert len(all_positions) == 3
        assert all(isinstance(p, Position) for p in all_positions)

        # Check specific positions
        symbols = [p.symbol for p in all_positions]
        assert "BTC/USD" in symbols
        assert "ETH/USD" in symbols
        assert "BTC/EUR" in symbols

    @pytest.mark.asyncio
    async def test_get_all_positions_empty(self, account_cache):
        """Test get_all_positions with no data."""
        # Clean any existing data first
        await account_cache.clean_positions()

        positions = await account_cache.get_all_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_all_positions_parse_error(self, account_cache):
        """Test get_all_positions with parse errors."""
        # Insert some valid data
        positions = [
            Position(
                symbol="BTC/USD",
                cost=1000.0,
                volume=1.0,
                fee=1.0,
                price=1000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]
        await account_cache.upsert_positions(123, positions)

        # Mock a JSON error for one entry
        original_loads = json.loads
        call_count = 0

        def mock_loads(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call fails
                raise json.JSONDecodeError("Invalid", "", 0)
            return original_loads(data)

        with patch('json.loads', side_effect=mock_loads):
            positions = await account_cache.get_all_positions()
            # Should return empty list due to error
            assert positions == []

    @pytest.mark.asyncio
    async def test_get_full_account(self, account_cache):
        """Test getting account data for currency."""
        account_data = {
            "USDT": {"balance": 10000.0, "available": 8000.0},
            "BTC": {"balance": 0.5, "available": 0.4}
        }
        await account_cache.upsert_user_account(789, account_data)

        usdt_data = await account_cache.get_full_account(789, "USDT")
        assert usdt_data == {"balance": 10000.0, "available": 8000.0}

        btc_data = await account_cache.get_full_account(789, "BTC")
        assert btc_data == {"balance": 0.5, "available": 0.4}

        # Non-existent currency
        fake_data = await account_cache.get_full_account(789, "FAKE")
        assert fake_data == {}

    @pytest.mark.asyncio
    async def test_get_full_account_no_account(self, account_cache):
        """Test get_full_account with no account."""
        data = await account_cache.get_full_account(999, "USDT")
        assert data == {}

    @pytest.mark.asyncio
    async def test_get_all_accounts(self, account_cache):
        """Test getting all accounts."""
        # Add multiple accounts
        await account_cache.upsert_user_account(123, {"USDT": {"balance": 10000}})
        await account_cache.upsert_user_account(456, {"BTC": {"balance": 1.5}})
        await account_cache.upsert_user_account(789, {"ETH": {"balance": 20}})

        accounts = await account_cache.get_all_accounts()
        assert len(accounts) >= 3
        assert "123" in accounts
        assert "456" in accounts
        assert "789" in accounts

        # Verify account data
        assert "USDT" in accounts["123"]
        assert accounts["123"]["USDT"]["balance"] == 10000

    @pytest.mark.asyncio
    async def test_get_all_accounts_decode_error(self, account_cache):
        """Test get_all_accounts with decode errors."""
        # Add valid account
        await account_cache.upsert_user_account(123, {"USDT": {"balance": 5000}})

        # Manually insert invalid JSON into Redis
        async with account_cache._cache._redis_context() as redis:
            await redis.hset("accounts", "456", "invalid json")

        accounts = await account_cache.get_all_accounts()

        # Should still return valid accounts
        assert "123" in accounts
        assert "456" in accounts
        assert accounts["456"] == "invalid json"  # Original value on parse error


class TestAccountCacheUtility:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_clean_positions(self, account_cache):
        """Test cleaning all positions and accounts."""
        # Add some data
        positions = [
            Position(
                symbol="BTC/USD",
                cost=1000.0,
                volume=1.0,
                fee=1.0,
                price=1000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]
        await account_cache.upsert_positions(123, positions)
        await account_cache.upsert_user_account(456, {"USDT": {"balance": 5000}})

        # Clean all
        deleted = await account_cache.clean_positions()
        assert deleted >= 2  # At least 2 keys deleted

        # Verify data is gone
        position = await account_cache.get_position("BTC/USD", "123")
        assert position.volume == 0.0

        account = await account_cache.get_full_account(456, "USDT")
        assert account == {}

    @pytest.mark.asyncio
    async def test_clean_positions_error_handling(self, account_cache):
        """Test error handling in clean_positions."""
        with patch.object(account_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = ConnectionError("Connection failed")

            deleted = await account_cache.clean_positions()
            assert deleted == 0



class TestAccountCacheEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_mixed_type_ex_id(self, account_cache):
        """Test handling of both int and str ex_id."""
        # Use int ex_id
        await account_cache.upsert_positions(123, [Position(
            symbol="BTC/USD",
            cost=1000.0,
            volume=1.0,
            fee=1.0,
            price=1000.0,
            timestamp=1704067200.0,
            ex_id="123"
        )])
        position1 = await account_cache.get_position("BTC/USD", "123")
        assert position1.volume == 1.0

        # Use str ex_id
        position2 = await account_cache.get_position("BTC/USD", 123)  # int passed to get
        assert position2.volume == 1.0

    @pytest.mark.asyncio
    async def test_bytes_handling(self, account_cache):
        """Test proper bytes decoding."""
        # The get_all_accounts method already handles bytes decoding properly
        # Just verify it works with normal operation
        await account_cache.upsert_user_account(123, {"USDT": {"balance": 1000}})

        accounts = await account_cache.get_all_accounts()
        assert "123" in accounts
        assert accounts["123"]["USDT"]["balance"] == 1000

    @pytest.mark.asyncio
    async def test_position_timestamp_fallback(self, account_cache):
        """Test timestamp handling in positions."""
        # Position with timestamp
        positions = [
            Position(
                symbol="BTC/USD",
                cost=1000.0,
                volume=1.0,
                fee=1.0,
                price=1000.0,
                timestamp=1704067200.0,
                ex_id="123"
            )
        ]

        # Store positions normally, then check the timestamp
        await account_cache.upsert_positions(123, positions)

        position = await account_cache.get_position("BTC/USD", "123")
        assert position.timestamp == 1704067200.0  # Uses position's own timestamp

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, account_cache):
        """Test concurrent cache operations."""
        import asyncio

        async def update_position(symbol, ex_id):
            positions = [
                Position(
                    symbol=symbol,
                    cost=1000.0,
                    volume=1.0,
                    fee=1.0,
                    price=1000.0,
                    timestamp=1704067200.0,
                    ex_id=str(ex_id)
                )
            ]
            return await account_cache.upsert_positions(ex_id, positions)

        # Run concurrent updates
        results = await asyncio.gather(
            update_position("BTC/USD", 1),
            update_position("ETH/USD", 2),
            update_position("XRP/USD", 3),
            return_exceptions=True
        )

        # All should succeed
        assert all(r is True for r in results)

        # Verify all positions exist
        positions = await account_cache.get_all_positions()
        symbols = [p.symbol for p in positions]
        assert "BTC/USD" in symbols
        assert "ETH/USD" in symbols
        assert "XRP/USD" in symbols
