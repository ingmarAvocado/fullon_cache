"""Tests for ExchangeCache WebSocket error management."""

import asyncio

import pytest

from fullon_cache import ExchangeCache


class TestExchangeCacheWebSocketErrors:
    """Test WebSocket error queue operations."""

    @pytest.mark.asyncio
    async def test_push_pop_ws_error(self, clean_redis):
        """Test pushing and popping WebSocket errors."""
        cache = ExchangeCache()
        ex_id = "binance_1"

        # Push error
        await cache.push_ws_error("Connection timeout", ex_id)

        # Pop error
        error = await cache.pop_ws_error(ex_id, timeout=1)
        assert error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_pop_ws_error_empty_queue(self, clean_redis):
        """Test popping from empty queue with timeout."""
        cache = ExchangeCache()
        ex_id = "kraken_1"

        # Pop from empty queue should timeout
        error = await cache.pop_ws_error(ex_id, timeout=1)
        assert error is None

    @pytest.mark.asyncio
    async def test_multiple_ws_errors(self, clean_redis):
        """Test multiple errors in queue."""
        cache = ExchangeCache()
        ex_id = "bitfinex_1"

        # Push multiple errors
        errors = ["Error 1", "Error 2", "Error 3"]
        for err in errors:
            await cache.push_ws_error(err, ex_id)

        # Pop in FIFO order
        for expected in errors:
            error = await cache.pop_ws_error(ex_id, timeout=1)
            assert error == expected

    @pytest.mark.asyncio
    async def test_ws_errors_different_exchanges(self, clean_redis):
        """Test error isolation between exchanges."""
        cache = ExchangeCache()

        # Push errors to different exchanges
        await cache.push_ws_error("Binance error", "binance_1")
        await cache.push_ws_error("Kraken error", "kraken_1")

        # Pop should get correct error for each exchange
        binance_error = await cache.pop_ws_error("binance_1", timeout=1)
        kraken_error = await cache.pop_ws_error("kraken_1", timeout=1)

        assert binance_error == "Binance error"
        assert kraken_error == "Kraken error"

    @pytest.mark.asyncio
    async def test_blocking_pop(self, clean_redis):
        """Test blocking pop operation."""
        cache = ExchangeCache()
        ex_id = "test_exchange"

        # Start a coroutine that will push an error after a delay
        async def push_delayed():
            await asyncio.sleep(0.5)
            await cache.push_ws_error("Delayed error", ex_id)

        # Start the delayed push
        push_task = asyncio.create_task(push_delayed())

        # This should block until the error is pushed
        error = await cache.pop_ws_error(ex_id, timeout=2)

        await push_task
        assert error == "Delayed error"

    @pytest.mark.asyncio
    async def test_inheritance_from_process_cache(self, clean_redis):
        """Test that ExchangeCache inherits from ProcessCache."""
        cache = ExchangeCache()

        # Should have access to ProcessCache methods
        from fullon_cache.process_cache import ProcessType

        # Register a process (from ProcessCache)
        process_id = await cache.register_process(
            ProcessType.TICK,
            "test_component",
            {"test": True}
        )
        assert process_id is not None

        # Get process to verify it works
        process = await cache.get_process(process_id)
        assert process is not None
        assert process["component"] == "test_component"

        # Should still be able to use WebSocket error methods
        await cache.push_ws_error("Test error", "test_ex")
        error = await cache.pop_ws_error("test_ex", timeout=1)
        assert error == "Test error"
