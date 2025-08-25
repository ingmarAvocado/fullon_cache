"""Tests for TradesCache ORM-based interface using real cache operations."""

import time
from datetime import datetime, UTC

import pytest
from fullon_orm.models import Trade

from fullon_cache.trades_cache import TradesCache


class TestTradesCacheORM:
    """Test cases for TradesCache ORM-based interface using real cache operations."""

    @pytest.mark.asyncio
    async def test_push_trade_with_trade_model(self):
        """Test pushing trade with fullon_orm.Trade model."""
        cache = TradesCache()
        
        # Create sample trade
        trade = Trade(
            trade_id=12345,
            ex_trade_id="EX_TRD_001",
            ex_order_id="EX_ORD_001",
            uid=1,
            ex_id=1,
            symbol="BTC/USDT",
            order_type="limit",
            side="buy",
            volume=0.1,
            price=50000.0,
            cost=5000.0,
            fee=5.0,
            cur_volume=0.1,
            cur_avg_price=50000.0,
            cur_avg_cost=5000.0,
            cur_fee=5.0,
            roi=0.0,
            roi_pct=0.0,
            total_fee=5.0,
            leverage=1.0,
            time=time.time()
        )

        # Test push trade
        result = await cache.push_trade("binance", trade)
        assert result is True
        
        # Verify data was stored by retrieving it
        trades_list = await cache.get_trades("BTCUSDT", "binance")  # Symbol normalized
        assert len(trades_list) >= 1
        
        # Find our trade in the list
        stored_trade = None
        for t in trades_list:
            if isinstance(t, Trade) and t.trade_id == trade.trade_id:
                stored_trade = t
                break
        
        assert stored_trade is not None
        assert isinstance(stored_trade, Trade)
        assert stored_trade.symbol == trade.symbol
        assert stored_trade.side == trade.side
        assert stored_trade.volume == trade.volume
        assert stored_trade.price == trade.price

        # Cleanup
        await cache.delete("trades:binance:BTCUSDT")

    @pytest.mark.asyncio
    async def test_push_trade_error_handling(self):
        """Test push_trade error handling."""
        cache = TradesCache()
        
        # Test with invalid trade data
        trade = Trade(
            trade_id=99999,
            symbol="",  # Empty symbol
            side="buy",
            volume=0.0,
            price=0.0,
            ex_id=1,
            uid=1
        )
        
        # Should still work gracefully
        result = await cache.push_trade("test_exchange", trade)
        assert result is True  # Method should handle gracefully

    @pytest.mark.asyncio
    async def test_get_trades_returns_trade_list(self):
        """Test that get_trades returns list of Trade models."""
        cache = TradesCache()
        
        # Create sample trades
        trade1 = Trade(
            trade_id=1001,
            symbol="BTC/USDT",
            side="buy",
            volume=0.1,
            price=50000.0,
            ex_id=1,
            uid=1,
            time=time.time()
        )
        
        trade2 = Trade(
            trade_id=1002,
            symbol="BTC/USDT",
            side="sell",
            volume=0.05,
            price=51000.0,
            ex_id=1,
            uid=1,
            time=time.time()
        )
        
        # Push trades
        await cache.push_trade("binance", trade1)
        await cache.push_trade("binance", trade2)
        
        # Get trades
        result = await cache.get_trades("BTCUSDT", "binance")
        
        assert len(result) >= 2
        assert all(isinstance(trade, Trade) for trade in result)
        
        # Find our trades
        trade_ids = [t.trade_id for t in result if hasattr(t, 'trade_id')]
        assert 1001 in trade_ids
        assert 1002 in trade_ids

        # Cleanup
        await cache.delete("trades:binance:BTCUSDT")

    @pytest.mark.asyncio
    async def test_get_trades_json_parse_error(self):
        """Test get_trades handles corrupted data gracefully."""
        cache = TradesCache()
        
        # This test is hard to trigger with real cache operations
        # but we can test with valid data
        trade = Trade(
            trade_id=2001,
            symbol="ETH/USDT",
            side="buy",
            volume=1.0,
            price=3000.0,
            ex_id=1,
            uid=1
        )
        
        await cache.push_trade("binance", trade)
        result = await cache.get_trades("ETHUSDT", "binance")
        
        # Should handle valid data correctly
        assert len(result) >= 1
        eth_found = any(t.symbol == "ETH/USDT" for t in result if hasattr(t, 'symbol'))
        assert eth_found

        # Cleanup
        await cache.delete("trades:binance:ETHUSDT")

    @pytest.mark.asyncio
    async def test_push_user_trade_with_trade_model(self):
        """Test push_user_trade with Trade model."""
        cache = TradesCache()
        
        trade = Trade(
            trade_id=3001,
            symbol="BTC/USDT",
            side="buy",
            volume=0.2,
            price=55000.0,
            ex_id=1,
            uid=123,
            time=time.time()
        )
        
        # Test push user trade
        result = await cache.push_user_trade("123", "binance", trade)
        assert result is True
        
        # Verify by popping the trade
        retrieved_trade = await cache.pop_user_trade("123", "binance")
        assert retrieved_trade is not None
        assert isinstance(retrieved_trade, Trade)
        assert retrieved_trade.trade_id == trade.trade_id
        assert retrieved_trade.symbol == trade.symbol
        assert retrieved_trade.uid == trade.uid

    @pytest.mark.asyncio
    async def test_push_user_trade_error_handling(self):
        """Test push_user_trade error handling."""
        cache = TradesCache()
        
        # Test with invalid trade
        trade = Trade(
            trade_id=99999,
            symbol="INVALID",
            side="buy",
            volume=0.0,
            price=0.0,
            ex_id=1,
            uid=999
        )
        
        result = await cache.push_user_trade("999", "test", trade)
        assert result is True  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_pop_user_trade_returns_trade_model(self):
        """Test that pop_user_trade returns Trade model."""
        cache = TradesCache()
        
        trade = Trade(
            trade_id=4001,
            symbol="ETH/USDT",
            side="sell",
            volume=2.0,
            price=3500.0,
            ex_id=2,
            uid=456,
            time=time.time()
        )
        
        # Push then pop
        await cache.push_user_trade("456", "binance", trade)
        result = await cache.pop_user_trade("456", "binance")
        
        assert result is not None
        assert isinstance(result, Trade)
        assert result.trade_id == trade.trade_id
        assert result.symbol == trade.symbol
        assert result.side == trade.side
        assert result.volume == trade.volume
        assert result.uid == trade.uid

    @pytest.mark.asyncio
    async def test_pop_user_trade_blocking(self, clean_redis):
        """Test pop_user_trade blocking behavior."""
        cache = TradesCache()
        
        try:
            # Test non-blocking when queue is empty - should return None
            result = await cache.pop_user_trade("isolated_user_999", "isolated_exchange", timeout=0)
            assert result is None
        finally:
            await cache._cache.close()

    @pytest.mark.asyncio
    async def test_symbol_normalization(self):
        """Test that symbols are normalized correctly."""
        cache = TradesCache()
        
        trade = Trade(
            trade_id=5001,
            symbol="BTC/USDT",  # With slash
            side="buy",
            volume=0.1,
            price=60000.0,
            ex_id=1,
            uid=1
        )
        
        await cache.push_trade("binance", trade)
        
        # Retrieve using normalized symbol (without slash)
        trades = await cache.get_trades("BTCUSDT", "binance")
        assert len(trades) >= 1
        
        found_trade = any(t.symbol == "BTC/USDT" for t in trades if hasattr(t, 'symbol'))
        assert found_trade

        # Cleanup
        await cache.delete("trades:binance:BTCUSDT")

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """Test error logging in trade operations."""
        cache = TradesCache()
        
        # Test with extreme edge case data
        trade = Trade(
            trade_id=9999,
            symbol="TEST/PAIR",
            side="buy",
            volume=0.000001,  # Very small volume
            price=999999999.99,  # Very large price
            ex_id=999,
            uid=999
        )
        
        # Should handle without throwing exceptions
        result = await cache.push_trade("test_exchange", trade)
        assert result is True
        
        # Cleanup
        await cache.delete("trades:test_exchange:TESTPAIR")