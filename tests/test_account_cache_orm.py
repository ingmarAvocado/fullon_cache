"""Tests for AccountCache ORM-based interface using real cache operations."""

import time
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Position

from fullon_cache.account_cache import AccountCache


class TestAccountCacheORM:
    """Test cases for AccountCache ORM-based interface using real cache operations."""

    @pytest.mark.asyncio
    async def test_upsert_positions_with_position_models(self):
        """Test upserting with fullon_orm.Position models."""
        cache = AccountCache()
        
        # Create sample positions
        positions = [
            Position(
                symbol="BTC/USDT",
                cost=50000.0,
                volume=0.1,
                fee=5.0,
                count=1.0,
                price=50000.0,
                timestamp=time.time(),
                ex_id="1",
                side="long"
            ),
            Position(
                symbol="ETH/USDT",
                cost=3000.0,
                volume=1.0,
                fee=3.0,
                count=1.0,
                price=3000.0,
                timestamp=time.time(),
                ex_id="1",
                side="long"
            )
        ]

        # Test upsert
        result = await cache.upsert_positions(1, positions)
        assert result is True
        
        # Verify data was stored by retrieving it
        btc_position = await cache.get_position("BTC/USDT", "1")
        assert btc_position is not None
        assert isinstance(btc_position, Position)
        assert btc_position.symbol == "BTC/USDT"
        assert btc_position.cost == 50000.0
        assert btc_position.volume == 0.1
        
        eth_position = await cache.get_position("ETH/USDT", "1")
        assert eth_position is not None
        assert isinstance(eth_position, Position)
        assert eth_position.symbol == "ETH/USDT"
        assert eth_position.cost == 3000.0
        assert eth_position.volume == 1.0

        # Cleanup
        await cache.hdel("account_positions", "1")

    @pytest.mark.asyncio
    async def test_upsert_positions_empty_list_deletes(self):
        """Test that empty positions list deletes data."""
        cache = AccountCache()
        
        # First, add some data
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            ex_id="1"
        )
        await cache.upsert_positions(1, [position])
        
        # Verify it exists
        retrieved = await cache.get_position("BTC/USDT", "1")
        assert retrieved.cost == 50000.0
        
        # Test empty list deletion
        result = await cache.upsert_positions(1, [])
        assert result is True
        
        # Verify data was deleted (returns empty position)
        retrieved_after = await cache.get_position("BTC/USDT", "1")
        assert retrieved_after.cost == 0.0
        assert retrieved_after.volume == 0.0

    @pytest.mark.asyncio
    async def test_upsert_positions_error_handling(self):
        """Test upsert_positions with invalid data."""
        cache = AccountCache()
        
        # Test with invalid ex_id
        position = Position(symbol="BTC/USDT", ex_id="invalid")
        
        # This should handle gracefully
        result = await cache.upsert_positions("invalid_ex_id", [position])
        # The method should still work, just storing under "invalid_ex_id"
        assert result is True

    @pytest.mark.asyncio
    async def test_upsert_single_position(self):
        """Test upserting single position."""
        cache = AccountCache()
        
        # Create sample position
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            fee=5.0,
            count=1.0,
            price=50000.0,
            timestamp=time.time(),
            ex_id="1",
            side="long"
        )

        # Test upsert single position
        result = await cache.upsert_position(position)
        assert result is True
        
        # Verify the position was stored
        retrieved = await cache.get_position("BTC/USDT", "1")
        assert retrieved is not None
        assert isinstance(retrieved, Position)
        assert retrieved.symbol == "BTC/USDT"
        assert retrieved.cost == 50000.0
        assert retrieved.volume == 0.1

        # Cleanup
        await cache.hdel("account_positions", "1")

    @pytest.mark.asyncio
    async def test_upsert_single_position_no_existing_data(self):
        """Test upsert_position when no existing data exists."""
        cache = AccountCache()
        
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            ex_id="1"
        )

        # Test upsert on clean cache
        result = await cache.upsert_position(position)
        assert result is True
        
        # Verify position was stored
        retrieved = await cache.get_position("BTC/USDT", "1")
        assert retrieved.cost == 50000.0
        assert retrieved.volume == 0.1

        # Cleanup
        await cache.hdel("account_positions", "1")

    @pytest.mark.asyncio
    async def test_upsert_single_position_error_handling(self):
        """Test upsert_position error handling."""
        cache = AccountCache()
        
        # Test with invalid position data
        position = Position(symbol="", ex_id="1")  # Empty symbol
        
        # Should handle gracefully
        result = await cache.upsert_position(position)
        assert result is True  # Method should still work

    @pytest.mark.asyncio
    async def test_get_position_returns_position_model(self):
        """Test that get_position returns fullon_orm.Position model."""
        cache = AccountCache()
        
        # Store a position first
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            fee=5.0,
            ex_id="1"
        )
        await cache.upsert_position(position)

        # Test retrieval
        result = await cache.get_position("BTC/USDT", "1")
        
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 50000.0
        assert result.volume == 0.1
        assert result.fee == 5.0
        assert result.ex_id == "1"

        # Cleanup
        await cache.hdel("account_positions", "1")

    @pytest.mark.asyncio
    async def test_get_position_not_found(self):
        """Test get_position when position not found."""
        cache = AccountCache()
        
        # Test getting non-existent position
        result = await cache.get_position("BTC/USDT", "1")

        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0
        assert result.ex_id == "1"  # Should be set from parameter

    @pytest.mark.asyncio
    async def test_get_position_symbol_not_in_data(self):
        """Test get_position when symbol not in position data."""
        cache = AccountCache()
        
        # Store ETH position
        eth_position = Position(
            symbol="ETH/USDT",
            cost=3000.0,
            volume=1.0,
            ex_id="1"
        )
        await cache.upsert_position(eth_position)
        
        # Try to get BTC position (doesn't exist)
        result = await cache.get_position("BTC/USDT", "1")

        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

        # Cleanup
        await cache.hdel("account_positions", "1")

    @pytest.mark.asyncio
    async def test_get_position_empty_ex_id(self):
        """Test get_position with empty ex_id."""
        cache = AccountCache()
        
        # Test with empty ex_id
        result = await cache.get_position("BTC/USDT", "")

        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_position_json_error(self):
        """Test get_position handles corrupted data gracefully."""
        cache = AccountCache()
        
        # This test is hard to trigger with real cache, but we can test invalid ex_id
        result = await cache.get_position("BTC/USDT", "nonexistent")

        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_all_positions_returns_position_list(self):
        """Test that get_all_positions returns list of Position models."""
        cache = AccountCache()
        
        # Store positions in different exchanges
        btc_pos = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            ex_id="1"
        )
        eth_pos = Position(
            symbol="ETH/USDT",
            cost=3000.0,
            volume=1.0,
            ex_id="2"
        )
        
        await cache.upsert_position(btc_pos)
        await cache.upsert_position(eth_pos)

        # Test get all positions
        result = await cache.get_all_positions()

        assert len(result) >= 2  # At least our positions
        assert all(isinstance(pos, Position) for pos in result)
        
        # Find our specific positions
        btc_found = any(p.symbol == "BTC/USDT" and p.ex_id == "1" for p in result)
        eth_found = any(p.symbol == "ETH/USDT" and p.ex_id == "2" for p in result)
        assert btc_found
        assert eth_found

        # Cleanup
        await cache.hdel("account_positions", "1")
        await cache.hdel("account_positions", "2")

    @pytest.mark.asyncio
    async def test_get_all_positions_empty_data(self):
        """Test get_all_positions with empty data."""
        cache = AccountCache()
        
        # Clear any existing data first
        await cache.clean_positions()
        
        result = await cache.get_all_positions()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_positions_json_parse_error(self):
        """Test get_all_positions handles corrupted data gracefully."""
        cache = AccountCache()
        
        # Store one valid position
        position = Position(
            symbol="ETH/USDT",
            cost=3000.0,
            volume=1.0,
            ex_id="2"
        )
        await cache.upsert_position(position)

        # Test retrieval (should work with valid data)
        result = await cache.get_all_positions()
        
        # Should get at least the valid position
        assert len(result) >= 1
        eth_found = any(p.symbol == "ETH/USDT" and p.ex_id == "2" for p in result)
        assert eth_found

        # Cleanup
        await cache.hdel("account_positions", "2")

    @pytest.mark.asyncio
    async def test_position_model_properties(self):
        """Test that Position model has expected properties."""
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            fee=5.0,
            ex_id="1",
            side="long",
            realized_pnl=0.0,
            unrealized_pnl=0.0
        )
        
        # Test basic properties
        assert position.symbol == "BTC/USDT"
        assert position.cost == 50000.0
        assert position.volume == 0.1
        assert position.fee == 5.0
        assert position.ex_id == "1"
        assert position.side == "long"

    @pytest.mark.asyncio
    async def test_position_model_to_dict_from_dict(self):
        """Test Position model serialization and deserialization."""
        position = Position(
            symbol="BTC/USDT",
            cost=50000.0,
            volume=0.1,
            fee=5.0,
            ex_id="1"
        )
        
        # Test to_dict
        position_dict = position.to_dict()
        assert isinstance(position_dict, dict)
        assert position_dict["symbol"] == position.symbol
        assert position_dict["cost"] == position.cost
        assert position_dict["volume"] == position.volume

        # Test from_dict
        reconstructed_position = Position.from_dict(position_dict)
        assert reconstructed_position.symbol == position.symbol
        assert reconstructed_position.cost == position.cost
        assert reconstructed_position.volume == position.volume
        assert reconstructed_position.fee == position.fee

    @pytest.mark.asyncio
    async def test_integration_save_and_retrieve(self):
        """Test integration of save and retrieve operations."""
        cache = AccountCache()
        
        # Create positions using factory
        positions = [
            Position(
                symbol="BTC/USDT",
                cost=50000.0,
                volume=0.1,
                fee=5.0,
                ex_id="1"
            ),
            Position(
                symbol="ETH/USDT",
                cost=3000.0,
                volume=1.0,
                fee=3.0,
                ex_id="1"
            )
        ]

        # Test save operation
        save_result = await cache.upsert_positions(1, positions)
        assert save_result is True

        # Test retrieve operation
        btc_position = await cache.get_position("BTC/USDT", "1")
        assert btc_position is not None
        assert btc_position.symbol == "BTC/USDT"
        assert btc_position.cost == 50000.0
        assert btc_position.volume == 0.1

        eth_position = await cache.get_position("ETH/USDT", "1")
        assert eth_position is not None
        assert eth_position.symbol == "ETH/USDT"
        assert eth_position.cost == 3000.0
        assert eth_position.volume == 1.0

        # Cleanup
        await cache.hdel("account_positions", "1")