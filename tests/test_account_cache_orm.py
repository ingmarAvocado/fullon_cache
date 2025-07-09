"""Tests for AccountCache ORM-based interface refactoring."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Position

from fullon_cache.base_cache import BaseCache
from fullon_cache.account_cache import AccountCache


@pytest.fixture
def mock_base_cache():
    """Mock BaseCache for testing."""
    cache = AsyncMock(spec=BaseCache)
    # Mock the _to_redis_timestamp and _from_redis_timestamp methods
    cache._to_redis_timestamp.return_value = "2023-01-01T00:00:00Z"
    cache._from_redis_timestamp.return_value = datetime.now(UTC)
    return cache


@pytest.fixture
def account_cache(mock_base_cache):
    """Create AccountCache instance with mocked BaseCache."""
    cache = AccountCache()
    cache._cache = mock_base_cache
    return cache


@pytest.fixture
def sample_position():
    """Sample Position model for testing."""
    return Position(
        symbol="BTC/USDT",
        cost=50000.0,
        volume=0.1,
        fee=5.0,
        count=1.0,
        price=50000.0,
        timestamp=time.time(),
        ex_id="1",
        side="long",
        realized_pnl=0.0,
        unrealized_pnl=0.0
    )


@pytest.fixture
def sample_positions():
    """Sample Position models list for testing."""
    return [
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


@pytest.fixture
def mock_redis_context():
    """Mock redis context manager."""
    mock_redis = AsyncMock()
    return mock_redis


class TestAccountCacheORM:
    """Test cases for AccountCache ORM-based interface."""

    @pytest.mark.asyncio
    async def test_upsert_positions_with_position_models(self, account_cache, mock_base_cache, sample_positions):
        """Test upserting with fullon_orm.Position models."""
        # Setup mock redis context
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test
        result = await account_cache.upsert_positions(1, sample_positions)

        # Assert
        assert result is True
        
        # Verify hset was called
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "account_positions"
        assert call_args[0][1] == "1"  # ex_id as string
        
        # Verify the data was JSON serialized with positions
        stored_data = json.loads(call_args[0][2])
        assert "BTC/USDT" in stored_data
        assert "ETH/USDT" in stored_data
        assert stored_data["BTC/USDT"]["cost"] == 50000.0
        assert stored_data["BTC/USDT"]["volume"] == 0.1
        assert stored_data["ETH/USDT"]["cost"] == 3000.0
        assert stored_data["ETH/USDT"]["volume"] == 1.0
        assert "timestamp" in stored_data

    @pytest.mark.asyncio
    async def test_upsert_positions_empty_list_deletes(self, account_cache, mock_base_cache):
        """Test that empty positions list deletes data."""
        # Setup mock redis context
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hdel.return_value = 1

        # Test
        result = await account_cache.upsert_positions(1, [])

        # Assert
        assert result is True
        
        # Verify hdel was called
        mock_redis.hdel.assert_called_once_with("account_positions", "1")

    @pytest.mark.asyncio
    async def test_upsert_positions_error_handling(self, account_cache, mock_base_cache, sample_positions):
        """Test upsert_positions error handling."""
        # Setup mock to raise exception
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.side_effect = Exception("Redis error")

        # Test - should catch the exception and return False
        with patch('fullon_cache.account_cache.logger') as mock_logger:
            result = await account_cache.upsert_positions(1, sample_positions)

        # Assert
        assert result is False
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_single_position(self, account_cache, mock_base_cache, sample_position):
        """Test upserting single position."""
        # Setup existing data
        existing_data = {
            "ETH/USDT": {
                "cost": 3000.0,
                "volume": 1.0,
                "fee": 3.0,
                "count": 1.0,
                "price": 3000.0,
                "timestamp": time.time()
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(existing_data)
        mock_redis.hset.return_value = True

        # Test
        result = await account_cache.upsert_position(sample_position)

        # Assert
        assert result is True
        
        # Verify merge occurred
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        merged_data = json.loads(call_args[0][2])
        
        assert merged_data["BTC/USDT"]["cost"] == 50000.0  # New position
        assert merged_data["ETH/USDT"]["cost"] == 3000.0   # Preserved
        assert "timestamp" in merged_data

    @pytest.mark.asyncio
    async def test_upsert_single_position_no_existing_data(self, account_cache, mock_base_cache, sample_position):
        """Test upsert_position when no existing data exists."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = None  # No existing data
        mock_redis.hset.return_value = True

        # Test
        result = await account_cache.upsert_position(sample_position)

        # Assert
        assert result is True
        mock_redis.hset.assert_called_once()
        
        # Verify new position was stored
        call_args = mock_redis.hset.call_args
        stored_data = json.loads(call_args[0][2])
        assert stored_data["BTC/USDT"]["cost"] == 50000.0
        assert stored_data["BTC/USDT"]["volume"] == 0.1

    @pytest.mark.asyncio
    async def test_upsert_single_position_error_handling(self, account_cache, mock_base_cache, sample_position):
        """Test upsert_position error handling."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.side_effect = Exception("Redis error")

        # Test
        result = await account_cache.upsert_position(sample_position)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_position_returns_position_model(self, account_cache, mock_base_cache):
        """Test that get_position returns fullon_orm.Position model."""
        # Setup mock data
        position_data = {
            "BTC/USDT": {
                "cost": 50000.0,
                "volume": 0.1,
                "fee": 5.0,
                "count": 1.0,
                "price": 50000.0,
                "timestamp": time.time()
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(position_data)

        # Test
        result = await account_cache.get_position("BTC/USDT", "1")

        # Assert
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 50000.0
        assert result.volume == 0.1
        assert result.fee == 5.0
        assert result.ex_id == "1"

        # Verify correct Redis key was used
        mock_redis.hget.assert_called_once_with("account_positions", "1")

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, account_cache, mock_base_cache):
        """Test get_position when position not found."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = None

        # Test
        result = await account_cache.get_position("BTC/USDT", "1")

        # Assert
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_position_symbol_not_in_data(self, account_cache, mock_base_cache):
        """Test get_position when symbol not in position data."""
        # Setup data without BTC/USDT
        position_data = {
            "ETH/USDT": {
                "cost": 3000.0,
                "volume": 1.0,
                "fee": 3.0,
                "count": 1.0,
                "price": 3000.0,
                "timestamp": time.time()
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(position_data)

        # Test
        result = await account_cache.get_position("BTC/USDT", "1")

        # Assert
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_position_empty_ex_id(self, account_cache, mock_base_cache):
        """Test get_position with empty ex_id."""
        # Test
        result = await account_cache.get_position("BTC/USDT", "")

        # Assert
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_position_json_error(self, account_cache, mock_base_cache):
        """Test get_position with invalid JSON data."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = "invalid json"

        # Test
        result = await account_cache.get_position("BTC/USDT", "1")

        # Assert
        assert result is not None
        assert isinstance(result, Position)
        assert result.symbol == "BTC/USDT"
        assert result.cost == 0.0
        assert result.volume == 0.0

    @pytest.mark.asyncio
    async def test_get_all_positions_returns_position_list(self, account_cache, mock_base_cache):
        """Test that get_all_positions returns list of Position models."""
        # Setup multiple positions
        positions_data = {
            "1": json.dumps({
                "BTC/USDT": {
                    "cost": 50000.0,
                    "volume": 0.1,
                    "fee": 5.0,
                    "count": 1.0,
                    "price": 50000.0,
                    "timestamp": time.time()
                },
                "timestamp": "2023-01-01T00:00:00Z"
            }),
            "2": json.dumps({
                "ETH/USDT": {
                    "cost": 3000.0,
                    "volume": 1.0,
                    "fee": 3.0,
                    "count": 1.0,
                    "price": 3000.0,
                    "timestamp": time.time()
                },
                "timestamp": "2023-01-01T00:00:00Z"
            })
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hgetall.return_value = positions_data

        # Test
        result = await account_cache.get_all_positions()

        # Assert
        assert len(result) == 2
        assert all(isinstance(pos, Position) for pos in result)
        
        # Check specific positions
        btc_pos = next((p for p in result if p.symbol == "BTC/USDT"), None)
        assert btc_pos is not None
        assert btc_pos.cost == 50000.0
        assert btc_pos.ex_id == "1"

        eth_pos = next((p for p in result if p.symbol == "ETH/USDT"), None)
        assert eth_pos is not None
        assert eth_pos.cost == 3000.0
        assert eth_pos.ex_id == "2"

    @pytest.mark.asyncio
    async def test_get_all_positions_empty_data(self, account_cache, mock_base_cache):
        """Test get_all_positions with empty data."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hgetall.return_value = {}

        # Test
        result = await account_cache.get_all_positions()

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_positions_json_parse_error(self, account_cache, mock_base_cache):
        """Test get_all_positions with JSON parsing error."""
        positions_data = {
            "1": "invalid json",
            "2": json.dumps({
                "ETH/USDT": {
                    "cost": 3000.0,
                    "volume": 1.0,
                    "fee": 3.0,
                    "count": 1.0,
                    "price": 3000.0,
                    "timestamp": time.time()
                },
                "timestamp": "2023-01-01T00:00:00Z"
            })
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hgetall.return_value = positions_data

        # Test
        result = await account_cache.get_all_positions()

        # Assert - Should only get the valid position
        assert len(result) == 1
        assert result[0].symbol == "ETH/USDT"
        assert result[0].cost == 3000.0

    @pytest.mark.asyncio
    async def test_backward_compatibility_upsert_positions_legacy(self, account_cache, mock_base_cache):
        """Test backward compatibility with upsert_positions_legacy."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test legacy method
        positions_dict = {
            "BTC/USDT": {
                "cost": 50000.0,
                "volume": 0.1,
                "fee": 5.0,
                "price": 50000.0,
                "timestamp": time.time()
            },
            "ETH/USDT": {
                "cost": 3000.0,
                "volume": 1.0,
                "fee": 3.0,
                "price": 3000.0,
                "timestamp": time.time()
            }
        }
        
        # Should not raise exception
        result = await account_cache.upsert_positions_legacy(1, positions_dict)
        
        # Verify the underlying ORM method was called
        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_backward_compatibility_upsert_positions_legacy_empty_dict(self, account_cache, mock_base_cache):
        """Test upsert_positions_legacy with empty dict."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hdel.return_value = 1

        # Test
        result = await account_cache.upsert_positions_legacy(1, {})
        
        # Assert
        assert result is True
        mock_redis.hdel.assert_called_once_with("account_positions", "1")

    @pytest.mark.asyncio
    async def test_backward_compatibility_upsert_positions_legacy_update_date(self, account_cache, mock_base_cache):
        """Test upsert_positions_legacy with update_date=True."""
        existing_data = {
            "BTC/USDT": {
                "cost": 50000.0,
                "volume": 0.1,
                "fee": 5.0,
                "price": 50000.0,
                "timestamp": time.time()
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hget.return_value = json.dumps(existing_data)
        mock_redis.hset.return_value = True

        # Test
        result = await account_cache.upsert_positions_legacy(1, {}, update_date=True)
        
        # Assert
        assert result is True
        mock_redis.hset.assert_called_once()
        
        # Verify only timestamp was updated
        call_args = mock_redis.hset.call_args
        updated_data = json.loads(call_args[0][2])
        assert updated_data["BTC/USDT"]["cost"] == 50000.0  # Preserved
        assert "timestamp" in updated_data

    @pytest.mark.asyncio
    async def test_backward_compatibility_upsert_positions_legacy_error(self, account_cache, mock_base_cache):
        """Test upsert_positions_legacy error handling."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.side_effect = Exception("Redis error")

        # Test
        positions_dict = {"BTC/USDT": {"cost": 50000.0, "volume": 0.1, "fee": 5.0, "price": 50000.0, "timestamp": time.time()}}
        result = await account_cache.upsert_positions_legacy(1, positions_dict)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_position_model_properties(self, sample_position):
        """Test that Position model has expected properties."""
        # Test basic properties
        assert sample_position.symbol == "BTC/USDT"
        assert sample_position.cost == 50000.0
        assert sample_position.volume == 0.1
        assert sample_position.fee == 5.0
        assert sample_position.ex_id == "1"
        assert sample_position.side == "long"

    @pytest.mark.asyncio
    async def test_position_model_to_dict_from_dict(self, sample_position):
        """Test Position model serialization and deserialization."""
        # Test to_dict
        position_dict = sample_position.to_dict()
        assert isinstance(position_dict, dict)
        assert position_dict["symbol"] == sample_position.symbol
        assert position_dict["cost"] == sample_position.cost
        assert position_dict["volume"] == sample_position.volume

        # Test from_dict
        reconstructed_position = Position.from_dict(position_dict)
        assert reconstructed_position.symbol == sample_position.symbol
        assert reconstructed_position.cost == sample_position.cost
        assert reconstructed_position.volume == sample_position.volume
        assert reconstructed_position.fee == sample_position.fee

    @pytest.mark.asyncio
    async def test_integration_save_and_retrieve(self, account_cache, mock_base_cache, sample_positions):
        """Test integration of save and retrieve operations."""
        mock_redis = AsyncMock()
        mock_base_cache._redis_context.return_value.__aenter__.return_value = mock_redis
        mock_redis.hset.return_value = True

        # Test save operation
        save_result = await account_cache.upsert_positions(1, sample_positions)
        assert save_result is True

        # Mock the retrieval
        positions_data = {
            "BTC/USDT": {
                "cost": 50000.0,
                "volume": 0.1,
                "fee": 5.0,
                "count": 1.0,
                "price": 50000.0,
                "timestamp": time.time()
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }
        mock_redis.hget.return_value = json.dumps(positions_data)

        # Test retrieve operation
        retrieved_position = await account_cache.get_position("BTC/USDT", "1")
        assert retrieved_position is not None
        assert retrieved_position.symbol == "BTC/USDT"
        assert retrieved_position.cost == 50000.0
        assert retrieved_position.volume == 0.1