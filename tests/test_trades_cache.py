"""Tests for simplified TradesCache with queue operations only."""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from fullon_cache import TradesCache
from fullon_orm.models import Trade


class TestTradesCacheQueues:
    """Test queue operations for trade management."""
    
    @pytest.mark.asyncio
    async def test_push_trade_list(self, trades_cache):
        """Test push_trade_list method."""
        trade_data = {
            "id": "12345",
            "price": 50000.0,
            "amount": 0.1,
            "side": "buy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Push trade to list
        length = await trades_cache.push_trade_list(
            "BTC/USDT", "binance", trade_data
        )
        assert length > 0
        
        # Verify trade status was updated
        status = await trades_cache.get_trade_status("binance")
        assert status is not None
        assert isinstance(status, datetime)
    
    @pytest.mark.asyncio
    async def test_push_trade_list_with_orm_object(self, trades_cache):
        """Test pushing Trade ORM object."""
        trade = Trade(
            trade_id="TRD123",
            ex_order_id="ORD123",
            ex_id="binance",
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            uid="123"
        )
        
        length = await trades_cache.push_trade_list(
            "BTC/USDT", "binance", trade
        )
        assert length > 0
    
    @pytest.mark.asyncio
    async def test_get_trades_list(self, trades_cache):
        """Test getting and clearing trades list."""
        # Push trades to list
        trades = [
            {
                "id": f"btc_trade_{i}",
                "price": 50000.0 + i * 100,
                "amount": 0.01 * (i + 1),
                "side": "buy" if i % 2 == 0 else "sell"
            }
            for i in range(5)
        ]
        
        for trade in trades:
            await trades_cache.push_trade_list(
                "BTC/USDT", "binance", trade
            )
        
        # Get all trades (this also clears the list)
        retrieved_trades = await trades_cache.get_trades_list(
            "BTC/USDT", "binance"
        )
        assert len(retrieved_trades) == 5
        
        # Verify trades match
        for i, trade in enumerate(retrieved_trades):
            assert trade["id"] == f"btc_trade_{i}"
            assert trade["price"] == 50000.0 + i * 100
        
        # Verify list is now empty
        empty_trades = await trades_cache.get_trades_list(
            "BTC/USDT", "binance"
        )
        assert len(empty_trades) == 0
    
    @pytest.mark.asyncio
    async def test_push_my_trades_list(self, trades_cache):
        """Test pushing user trades to list."""
        trade_data = {
            "id": "user_trade_123",
            "symbol": "ETH/USDT",
            "price": 3000.0,
            "amount": 1.0,
            "side": "sell",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Push user trade
        length = await trades_cache.push_my_trades_list(
            "user_789", "binance", trade_data
        )
        assert length == 1
        
        # Push another
        length = await trades_cache.push_my_trades_list(
            "user_789", "binance", trade_data
        )
        assert length == 2
    
    @pytest.mark.asyncio
    async def test_pop_my_trade(self, trades_cache):
        """Test popping user trades."""
        # Push some trades
        trades = [
            {"id": f"trade_{i}", "price": 100.0 * i}
            for i in range(3)
        ]
        
        for trade in trades:
            await trades_cache.push_my_trades_list(
                "user_999", "kraken", trade
            )
        
        # Pop trades (FIFO)
        popped = await trades_cache.pop_my_trade("user_999", "kraken")
        assert popped is not None
        assert popped["id"] == "trade_0"
        
        # Pop with timeout (non-blocking)
        popped = await trades_cache.pop_my_trade("user_999", "kraken", timeout=0)
        assert popped is not None
        assert popped["id"] == "trade_1"
        
        # Try to pop from empty queue
        await trades_cache.pop_my_trade("user_999", "kraken")  # Pop last one
        popped = await trades_cache.pop_my_trade("user_999", "kraken", timeout=0)
        assert popped is None
    
    @pytest.mark.asyncio
    async def test_pop_my_trade_with_timeout(self, trades_cache):
        """Test pop with blocking timeout."""
        # Try to pop from empty queue with 1 second timeout
        start_time = datetime.now(timezone.utc)
        popped = await trades_cache.pop_my_trade("user_timeout", "binance", timeout=1)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        assert popped is None
        assert elapsed >= 1  # Should have waited at least 1 second


class TestTradesCacheStatus:
    """Test trade status tracking methods."""
    
    @pytest.mark.asyncio
    async def test_update_trade_status(self, trades_cache):
        """Test updating trade status timestamp."""
        success = await trades_cache.update_trade_status("kraken")
        assert success is True
        
        # Verify timestamp was set
        status = await trades_cache.get_trade_status("kraken")
        assert status is not None
        assert isinstance(status, datetime)
        assert status.tzinfo == timezone.utc
    
    @pytest.mark.asyncio
    async def test_get_trade_status(self, trades_cache):
        """Test getting trade status timestamp."""
        # Set a status
        await trades_cache.update_trade_status("coinbase")
        
        # Get it back
        status = await trades_cache.get_trade_status("coinbase")
        assert status is not None
        assert isinstance(status, datetime)
        
        # Non-existent key
        status = await trades_cache.get_trade_status("fake_exchange")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_all_trade_statuses(self, trades_cache):
        """Test getting all trade statuses."""
        # Create multiple statuses
        exchanges = ["binance", "kraken", "coinbase"]
        for exchange in exchanges:
            await trades_cache.update_trade_status(exchange)
        
        # Get all
        statuses = await trades_cache.get_all_trade_statuses()
        assert len(statuses) >= 3
        
        # Check format
        for key, timestamp in statuses.items():
            assert key.startswith("TRADE:STATUS:")
            assert isinstance(timestamp, datetime)
            assert timestamp.tzinfo == timezone.utc
    
    @pytest.mark.asyncio
    async def test_get_trade_status_keys(self, trades_cache):
        """Test getting trade status keys."""
        # Create some keys
        await trades_cache.update_trade_status("exchange1")
        await trades_cache.update_trade_status("exchange2")
        
        # Get keys
        keys = await trades_cache.get_trade_status_keys()
        assert len(keys) >= 2
        assert all(key.startswith("TRADE:STATUS:") for key in keys)
        
        # Test with different prefix
        await trades_cache.update_user_trade_status("user_test")
        user_keys = await trades_cache.get_trade_status_keys("USER_TRADE:STATUS")
        assert any("user_test" in key for key in user_keys)
    
    @pytest.mark.asyncio
    async def test_update_user_trade_status(self, trades_cache):
        """Test updating user trade status."""
        # Update with auto timestamp
        success = await trades_cache.update_user_trade_status("user_123")
        assert success is True
        
        # Update with specific timestamp
        specific_time = datetime.now(timezone.utc)
        success = await trades_cache.update_user_trade_status(
            "user_456", timestamp=specific_time
        )
        assert success is True
        
        # Verify timestamps
        status_key = "USER_TRADE:STATUS:user_456"
        async with trades_cache._cache._redis_context() as redis_client:
            value = await redis_client.get(status_key)
        assert value is not None
        # Parse the stored ISO timestamp
        stored_dt = trades_cache._cache._from_redis_timestamp(value)
        assert stored_dt is not None
        # Compare timestamps (allowing for small differences due to serialization)
        assert abs(stored_dt.timestamp() - specific_time.timestamp()) < 0.001
    
    @pytest.mark.asyncio
    async def test_delete_user_trade_statuses(self, trades_cache):
        """Test deleting all user trade statuses."""
        # Create some user trade statuses
        await trades_cache.update_user_trade_status("user_1")
        await trades_cache.update_user_trade_status("user_2")
        await trades_cache.update_user_trade_status("user_3")
        
        # Delete all
        success = await trades_cache.delete_user_trade_statuses()
        assert success is True
        
        # Verify they're gone
        keys = await trades_cache.get_trade_status_keys("USER_TRADE:STATUS")
        assert len(keys) == 0


class TestTradesCacheIntegration:
    """Integration tests for queue methods."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_trade_queue_workflow(self, trades_cache):
        """Test complete trade queue workflow."""
        symbol = "ETH/USDT"
        exchange = "binance"
        
        # 1. Push multiple trades
        for i in range(10):
            trade = {
                "id": f"trade_{i}",
                "price": 3000.0 + i,
                "amount": 0.1,
                "side": "buy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await trades_cache.push_trade_list(symbol, exchange, trade)
        
        # 2. Verify status was updated
        status = await trades_cache.get_trade_status(exchange)
        assert status is not None
        
        # 3. Get and clear all trades
        all_trades = await trades_cache.get_trades_list(symbol, exchange)
        assert len(all_trades) == 10
        
        # 4. Verify trades are ordered
        for i, trade in enumerate(all_trades):
            assert trade["id"] == f"trade_{i}"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_user_trade_queue_workflow(self, trades_cache):
        """Test user trade queue management workflow."""
        user_id = "user_integration_test"
        exchanges = ["binance", "kraken", "coinbase"]
        
        # 1. Push trades to different exchanges
        for exchange in exchanges:
            for i in range(5):
                trade = {
                    "id": f"{exchange}_trade_{i}",
                    "symbol": "BTC/USDT",
                    "price": 50000.0,
                    "amount": 0.01,
                    "side": "buy"
                }
                await trades_cache.push_my_trades_list(
                    user_id, exchange, trade
                )
        
        # 2. Update user trade statuses
        for exchange in exchanges:
            key = f"{user_id}:{exchange}"
            await trades_cache.update_user_trade_status(key)
        
        # 3. Get all user trade statuses
        statuses = await trades_cache.get_all_trade_statuses("USER_TRADE:STATUS")
        assert len(statuses) >= 3
        
        # 4. Pop trades from each exchange
        for exchange in exchanges:
            # Pop first trade
            trade = await trades_cache.pop_my_trade(user_id, exchange)
            assert trade is not None
            assert trade["id"] == f"{exchange}_trade_0"
        
        # 5. Clean up user trade statuses
        await trades_cache.delete_user_trade_statuses()
        
        # 6. Verify cleanup
        remaining_statuses = await trades_cache.get_trade_status_keys("USER_TRADE:STATUS")
        assert len(remaining_statuses) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_mixed_queue_usage(self, trades_cache):
        """Test using different queue methods together."""
        # 1. Use list method to push trade
        list_trade = {
            "id": "LIST_001",
            "price": 3100.0,
            "amount": 0.5,
            "side": "sell"
        }
        await trades_cache.push_trade_list("ETH/USDT", "binance", list_trade)
        
        # 2. Push user trade
        user_trade = {
            "id": "USER_001",
            "price": 3200.0,
            "amount": 1.0,
            "side": "buy"
        }
        await trades_cache.push_my_trades_list("user_123", "binance", user_trade)
        
        # 3. Get list trades
        list_trades = await trades_cache.get_trades_list("ETH/USDT", "binance")
        assert len(list_trades) == 1
        assert list_trades[0]["id"] == "LIST_001"
        
        # 4. Pop user trade
        popped = await trades_cache.pop_my_trade("user_123", "binance")
        assert popped is not None
        assert popped["id"] == "USER_001"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, trades_cache):
        """Test error handling in various scenarios."""
        # Test with empty trade data
        result = await trades_cache.push_trade_list("BTC/USDT", "binance", {})
        assert result > 0  # Should still work with empty dict
        
        # Test with None timeout (should use 0)
        result = await trades_cache.pop_my_trade("user_test", "binance", timeout=None)
        assert result is None  # Empty queue
        
        # Test status methods with empty keys
        status = await trades_cache.get_trade_status("")
        assert status is None
        
        # Test with very long key
        long_key = "x" * 1000
        success = await trades_cache.update_trade_status(long_key)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_redis_connection_errors(self, trades_cache):
        """Test error handling when Redis operations fail."""
        # Temporarily break the Redis connection to trigger error paths
        import unittest.mock
        
        # Test push_trade_list error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.push_trade_list("BTC/USDT", "binance", {"id": "test"})
            assert result == 0
        
        # Test update_trade_status error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.update_trade_status("test_exchange")
            assert result is False
        
        # Test get_trade_status error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.get_trade_status("test_exchange")
            assert result is None
        
        # Test get_all_trade_statuses error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.get_all_trade_statuses()
            assert result == {}
        
        # Test get_trade_status_keys error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.get_trade_status_keys()
            assert result == []
        
        # Test update_user_trade_status error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.update_user_trade_status("test_user")
            assert result is False
        
        # Test delete_user_trade_statuses error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.delete_user_trade_statuses()
            assert result is False
        
        # Test push_my_trades_list error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.push_my_trades_list("user", "exchange", {"id": "test"})
            assert result == 0
        
        # Test pop_my_trade error path (not timeout)
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.pop_my_trade("user", "exchange")
            assert result is None
        
        # Test get_trades_list error path
        with unittest.mock.patch.object(trades_cache._cache, '_redis_context') as mock_context:
            mock_context.side_effect = Exception("Redis connection failed")
            result = await trades_cache.get_trades_list("BTC/USDT", "binance")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, trades_cache):
        """Test handling of invalid JSON in trades list."""
        # Insert invalid JSON directly into Redis to test error handling
        symbol = "TEST/USD"
        exchange = "test_exchange"
        normalized_symbol = symbol.replace("/", "")
        redis_key = f"trades:{exchange}:{normalized_symbol}"
        
        # Insert invalid JSON
        async with trades_cache._cache._redis_context() as redis_client:
            await redis_client.rpush(redis_key, "invalid_json_data")
            await redis_client.rpush(redis_key, "{invalid_json}")
            await redis_client.rpush(redis_key, '{"valid": "json"}')
        
        # This should handle the invalid JSON gracefully
        trades = await trades_cache.get_trades_list(symbol, exchange)
        # Should only get the valid JSON item
        assert len(trades) == 1
        assert trades[0]["valid"] == "json"
    
    @pytest.mark.asyncio
    async def test_blocking_timeout_with_actual_timeout(self, trades_cache):
        """Test blocking timeout behavior that actually times out."""
        import asyncio
        import time
        
        # Test blocking pop with timeout that actually waits
        start = time.time()
        result = await trades_cache.pop_my_trade("empty_user", "empty_exchange", timeout=1)
        elapsed = time.time() - start
        
        assert result is None
        assert elapsed >= 1.0  # Should have waited at least 1 second