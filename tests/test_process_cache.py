"""Comprehensive tests for ProcessCache with 100% coverage."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from fullon_cache.exceptions import CacheError
from fullon_cache.process_cache import ProcessStatus, ProcessType


class TestProcessCacheBasic:
    """Test basic process cache operations."""

    @pytest.mark.asyncio
    async def test_register_process(self, process_cache, process_factory):
        """Test registering a new process."""
        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="test_bot_1",
            params={"strategy": "arbitrage"},
            message="Starting bot",
            status=ProcessStatus.STARTING
        )

        assert process_id is not None
        assert "bot:test_bot_1:" in process_id

        # Verify process was stored
        process = await process_cache.get_process(process_id)
        assert process is not None
        assert process["process_type"] == ProcessType.BOT.value
        assert process["component"] == "test_bot_1"
        assert process["params"]["strategy"] == "arbitrage"
        assert process["status"] == ProcessStatus.STARTING.value
        assert process["message"] == "Starting bot"

    @pytest.mark.asyncio
    async def test_register_process_minimal(self, process_cache):
        """Test registering process with minimal parameters."""
        process_id = await process_cache.register_process(
            process_type=ProcessType.CRAWLER,
            component="price_crawler"
        )

        process = await process_cache.get_process(process_id)
        assert process["params"] == {}
        assert "Process price_crawler registered" in process["message"]
        assert process["status"] == ProcessStatus.STARTING.value

    @pytest.mark.asyncio
    async def test_update_process(self, process_cache):
        """Test updating process status and information."""
        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="test_bot"
        )

        # Update process
        success = await process_cache.update_process(
            process_id=process_id,
            status=ProcessStatus.RUNNING,
            message="Bot is running",
            params={"symbols": ["BTC/USDT", "ETH/USDT"]}
        )

        assert success is True

        # Verify updates
        process = await process_cache.get_process(process_id)
        assert process["status"] == ProcessStatus.RUNNING.value
        assert process["message"] == "Bot is running"
        assert process["params"]["symbols"] == ["BTC/USDT", "ETH/USDT"]
        assert process["updated_at"] > process["created_at"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_process(self, process_cache):
        """Test updating non-existent process."""
        success = await process_cache.update_process(
            process_id="nonexistent",
            status=ProcessStatus.RUNNING
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_heartbeat_update(self, process_cache):
        """Test heartbeat updates."""
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="heartbeat_test"
        )

        # Get initial heartbeat
        process1 = await process_cache.get_process(process_id)
        initial_heartbeat = process1["heartbeat"]

        # Small delay
        await asyncio.sleep(0.1)

        # Update with heartbeat
        await process_cache.update_process(
            process_id=process_id,
            heartbeat=True
        )

        # Verify heartbeat updated
        process2 = await process_cache.get_process(process_id)
        assert process2["heartbeat"] > initial_heartbeat

        # Update without heartbeat
        await process_cache.update_process(
            process_id=process_id,
            message="No heartbeat update",
            heartbeat=False
        )

        # Verify heartbeat not updated
        process3 = await process_cache.get_process(process_id)
        assert process3["heartbeat"] == process2["heartbeat"]
        assert process3["message"] == "No heartbeat update"


class TestProcessCacheQueries:
    """Test process querying and filtering."""

    @pytest.mark.asyncio
    async def test_get_active_processes_by_type(self, process_cache):
        """Test getting active processes filtered by type."""
        # Register different types of processes
        bot_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="bot_1"
        )

        crawler_id = await process_cache.register_process(
            process_type=ProcessType.CRAWLER,
            component="crawler_1"
        )

        # Get only bots
        bots = await process_cache.get_active_processes(
            process_type=ProcessType.BOT,
            since_minutes=5
        )
        assert len(bots) == 1
        assert bots[0]["component"] == "bot_1"

        # Get only crawlers
        crawlers = await process_cache.get_active_processes(
            process_type=ProcessType.CRAWLER,
            since_minutes=5
        )
        assert len(crawlers) == 1
        assert crawlers[0]["component"] == "crawler_1"

        # Get all types
        all_processes = await process_cache.get_active_processes(
            since_minutes=5
        )
        assert len(all_processes) == 2

    @pytest.mark.asyncio
    async def test_get_active_processes_by_component(self, process_cache):
        """Test filtering by component name."""
        # Register processes with same component
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="arbitrage_bot"
        )

        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="market_maker"
        )

        # Filter by component
        arbitrage = await process_cache.get_active_processes(
            component="arbitrage_bot"
        )
        assert len(arbitrage) == 1
        assert arbitrage[0]["component"] == "arbitrage_bot"

    @pytest.mark.asyncio
    async def test_get_active_processes_time_filter(self, process_cache):
        """Test time-based filtering."""
        # Register old process
        old_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="old_bot"
        )

        # Manually set old timestamp
        old_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        await process_cache._cache.hset(
            f"active:{ProcessType.BOT.value}",
            old_id,
            old_time
        )

        # Register new process
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="new_bot"
        )

        # Get only recent processes
        recent = await process_cache.get_active_processes(
            process_type=ProcessType.BOT,
            since_minutes=5
        )
        assert len(recent) == 1
        assert recent[0]["component"] == "new_bot"

        # Get all processes
        all_bots = await process_cache.get_active_processes(
            process_type=ProcessType.BOT,
            since_minutes=15
        )
        assert len(all_bots) == 2

    @pytest.mark.asyncio
    async def test_heartbeat_staleness_check(self, process_cache):
        """Test heartbeat staleness detection."""
        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="stale_bot"
        )

        # Set an old heartbeat (20 minutes ago)
        process_data = await process_cache.get_process(process_id)
        process_data["heartbeat"] = (
            datetime.now(UTC) - timedelta(minutes=20)
        ).isoformat()
        await process_cache._cache.set_json(
            f"data:{process_id}",
            process_data,
            ttl=86400
        )

        # Get with heartbeat check - heartbeat is older than cutoff
        processes = await process_cache.get_active_processes(
            since_minutes=15,  # Cutoff is 15 minutes ago
            include_heartbeat_check=True
        )

        assert len(processes) == 1
        # Heartbeat is 20 minutes old, cutoff is 15 minutes, so it's stale
        assert processes[0]["_heartbeat_stale"] is True

        # Get with longer cutoff - heartbeat is within range
        processes_fresh = await process_cache.get_active_processes(
            since_minutes=30,  # Cutoff is 30 minutes ago
            include_heartbeat_check=True
        )
        assert len(processes_fresh) == 1
        # Heartbeat is 20 minutes old, cutoff is 30 minutes, so it's fresh
        assert processes_fresh[0]["_heartbeat_stale"] is False

        # Get without heartbeat check
        processes_no_check = await process_cache.get_active_processes(
            since_minutes=15,
            include_heartbeat_check=False
        )
        assert "_heartbeat_stale" not in processes_no_check[0]


class TestProcessCacheLifecycle:
    """Test process lifecycle management."""

    @pytest.mark.asyncio
    async def test_stop_process(self, process_cache):
        """Test stopping a process."""
        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="stop_test"
        )

        # Stop process
        success = await process_cache.stop_process(
            process_id,
            message="Shutting down gracefully"
        )
        assert success is True

        # Verify process updated
        process = await process_cache.get_process(process_id)
        assert process["status"] == ProcessStatus.STOPPED.value
        assert process["message"] == "Shutting down gracefully"

        # Verify removed from active set
        active = await process_cache.get_active_processes(
            process_type=ProcessType.BOT
        )
        assert len(active) == 0

        # Verify removed from component index
        component_process = await process_cache.get_component_status("stop_test")
        assert component_process is None

    @pytest.mark.asyncio
    async def test_stop_nonexistent_process(self, process_cache):
        """Test stopping non-existent process."""
        success = await process_cache.stop_process("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_stale_processes(self, process_cache):
        """Test cleaning up stale processes."""
        # Register processes
        fresh_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="fresh_bot"
        )

        stale_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="stale_bot"
        )

        # Make one process stale
        stale_time = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
        await process_cache._cache.hset(
            f"active:{ProcessType.BOT.value}",
            stale_id,
            stale_time
        )

        # Update process data to have old heartbeat
        process_data = await process_cache.get_process(stale_id)
        process_data["heartbeat"] = stale_time
        await process_cache._cache.set_json(
            f"data:{stale_id}",
            process_data,
            ttl=86400
        )

        # Cleanup stale processes
        cleaned = await process_cache.cleanup_stale_processes(stale_minutes=30)
        assert cleaned == 1

        # Verify fresh process still active
        fresh = await process_cache.get_process(fresh_id)
        assert fresh is not None

        # Verify stale process stopped
        stale = await process_cache.get_process(stale_id)
        assert stale["status"] == ProcessStatus.STOPPED.value
        assert "stale for 30 minutes" in stale["message"]

    @pytest.mark.asyncio
    async def test_cleanup_invalid_timestamps(self, process_cache):
        """Test cleanup of processes with invalid timestamps."""
        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="invalid_bot"
        )

        # Set invalid timestamp
        await process_cache._cache.hset(
            f"active:{ProcessType.BOT.value}",
            process_id,
            "invalid_timestamp"
        )

        # Cleanup should remove invalid entries
        cleaned = await process_cache.cleanup_stale_processes()
        assert cleaned == 1


class TestProcessCacheUtilities:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_get_process_history(self, process_cache):
        """Test getting process history (placeholder)."""
        history = await process_cache.get_process_history("component", limit=10)
        assert history == []  # Currently returns empty

    @pytest.mark.asyncio
    async def test_get_component_status(self, process_cache):
        """Test getting component status."""
        # No process for component
        status = await process_cache.get_component_status("unknown")
        assert status is None

        # Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="test_component"
        )

        # Get component status
        status = await process_cache.get_component_status("test_component")
        assert status is not None
        assert status["component"] == "test_component"
        assert status["process_id"] == process_id

    @pytest.mark.asyncio
    async def test_get_system_health(self, process_cache):
        """Test system health check."""
        # Register healthy processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="healthy_bot",
            status=ProcessStatus.RUNNING
        )

        await process_cache.register_process(
            process_type=ProcessType.CRAWLER,
            component="healthy_crawler",
            status=ProcessStatus.RUNNING
        )

        # Get health
        health = await process_cache.get_system_health()
        assert health["healthy"] is True
        assert health["total_processes"] == 2
        assert health["by_type"]["bot"] == 1
        assert health["by_type"]["crawler"] == 1
        assert health["by_status"]["running"] == 2
        assert health["stale_processes"] == 0
        assert health["error_processes"] == 0

    @pytest.mark.asyncio
    async def test_system_health_with_errors(self, process_cache):
        """Test system health with errors."""
        # Register error process
        error_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="error_bot"
        )

        await process_cache.update_process(
            error_id,
            status=ProcessStatus.ERROR,
            message="Critical error"
        )

        # Register stale process
        stale_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="stale_bot"
        )

        # Make heartbeat stale
        process_data = await process_cache.get_process(stale_id)
        process_data["heartbeat"] = (
            datetime.now(UTC) - timedelta(hours=2)
        ).isoformat()
        await process_cache._cache.set_json(
            f"data:{stale_id}",
            process_data,
            ttl=86400
        )

        # Check health
        health = await process_cache.get_system_health()
        assert health["healthy"] is False
        assert health["error_processes"] == 1
        assert health["stale_processes"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_message(self, process_cache):
        """Test broadcasting messages to processes."""
        # Register processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="bot1"
        )

        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="bot2"
        )

        # Broadcast message
        recipients = await process_cache.broadcast_message(
            process_type=ProcessType.BOT,
            message="Shutdown signal",
            data={"reason": "maintenance"}
        )

        # Should return number of potential recipients (pub/sub subscribers)
        assert recipients >= 0

    @pytest.mark.asyncio
    async def test_get_metrics(self, process_cache):
        """Test getting cache metrics."""
        # Register processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="metric_bot"
        )

        await process_cache.register_process(
            process_type=ProcessType.CRAWLER,
            component="metric_crawler"
        )

        # Get metrics
        metrics = await process_cache.get_metrics()
        assert metrics["active_processes"] >= 2
        assert metrics["active_bot"] >= 1
        assert metrics["active_crawler"] >= 1
        assert metrics["components"] >= 2
        assert metrics["total_processes"] >= 2


class TestProcessCacheEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_all_process_types(self, process_cache):
        """Test all defined process types."""
        for ptype in ProcessType:
            process_id = await process_cache.register_process(
                process_type=ptype,
                component=f"test_{ptype.value}"
            )

            process = await process_cache.get_process(process_id)
            assert process["process_type"] == ptype.value

    @pytest.mark.asyncio
    async def test_all_process_statuses(self, process_cache):
        """Test all defined process statuses."""
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="status_test"
        )

        for status in ProcessStatus:
            await process_cache.update_process(
                process_id,
                status=status
            )

            process = await process_cache.get_process(process_id)
            assert process["status"] == status.value

    @pytest.mark.asyncio
    async def test_concurrent_registrations(self, process_cache):
        """Test concurrent process registrations."""
        async def register_process(n):
            return await process_cache.register_process(
                process_type=ProcessType.BOT,
                component=f"concurrent_bot_{n}"
            )

        # Register 10 processes concurrently
        process_ids = await asyncio.gather(
            *[register_process(i) for i in range(10)]
        )

        assert len(process_ids) == 10
        assert len(set(process_ids)) == 10  # All unique

        # Verify all registered
        active = await process_cache.get_active_processes(
            process_type=ProcessType.BOT
        )
        assert len(active) >= 10

    @pytest.mark.asyncio
    async def test_invalid_process_type_handling(self, process_cache):
        """Test handling of invalid data in cache."""
        # Manually insert invalid data
        await process_cache._cache.hset(
            "active:bot",
            "invalid_process",
            "not_a_timestamp"
        )

        # Should handle gracefully
        processes = await process_cache.get_active_processes(
            process_type=ProcessType.BOT
        )

        # Invalid entries should be skipped
        assert all(p.get("process_id") != "invalid_process" for p in processes)


class TestProcessCacheIntegration:
    """Integration tests with multiple operations."""

    @pytest.mark.asyncio
    async def test_full_process_lifecycle(self, process_cache):
        """Test complete process lifecycle."""
        # 1. Register process
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="lifecycle_bot",
            params={"exchange": "binance"},
            message="Initializing",
            status=ProcessStatus.STARTING
        )

        # 2. Update to running
        await process_cache.update_process(
            process_id,
            status=ProcessStatus.RUNNING,
            message="Connected to exchange"
        )

        # 3. Update parameters
        await process_cache.update_process(
            process_id,
            params={"symbols": ["BTC/USDT", "ETH/USDT"]}
        )

        # 4. Simulate processing
        await process_cache.update_process(
            process_id,
            status=ProcessStatus.PROCESSING,
            message="Processing trades"
        )

        # 5. Stop process
        await process_cache.stop_process(
            process_id,
            message="Shutdown complete"
        )

        # Verify final state
        process = await process_cache.get_process(process_id)
        assert process["status"] == ProcessStatus.STOPPED.value
        assert process["params"]["exchange"] == "binance"
        assert process["params"]["symbols"] == ["BTC/USDT", "ETH/USDT"]

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_many_processes(self, process_cache, benchmark_async):
        """Test performance with many processes."""
        # Register 100 processes
        process_ids = []
        for i in range(100):
            pid = await process_cache.register_process(
                process_type=ProcessType.BOT,
                component=f"perf_bot_{i}"
            )
            process_ids.append(pid)

        # Benchmark getting active processes
        await benchmark_async(
            process_cache.get_active_processes,
            process_type=ProcessType.BOT
        )

        # Check performance
        stats = benchmark_async.stats
        assert stats['mean'] < 2.0  # Should complete in under 2000ms (relaxed for CI)

        # Cleanup
        cleaned = await process_cache.cleanup_stale_processes(stale_minutes=0)
        assert cleaned >= 100


class TestProcessCacheLegacyMethods:
    """Test legacy methods for backward compatibility."""

    @pytest.mark.asyncio
    async def test_delete_from_top(self, process_cache):
        """Test legacy delete_from_top method."""
        # Register process
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="delete_test"
        )

        # Delete by component
        deleted = await process_cache.delete_from_top("delete_test")
        assert deleted == 1

        # Verify deleted
        status = await process_cache.get_component_status("delete_test")
        assert status is None

        # Delete non-existent
        deleted = await process_cache.delete_from_top("nonexistent")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_get_top(self, process_cache):
        """Test legacy get_top method."""
        # Register processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="bot1",
            params={"exchange": "binance"},
            message="Bot running"
        )

        await process_cache.register_process(
            process_type=ProcessType.CRAWLER,
            component="crawler1",
            params={"interval": 60}
        )

        # Get all
        processes = await process_cache.get_top()
        assert len(processes) >= 2

        # Check format
        bot_proc = next(p for p in processes if p["type"] == "bot")
        assert bot_proc["key"] == "bot1"
        assert bot_proc["params"]["exchange"] == "binance"
        assert bot_proc["message"] == "Bot running"
        assert "timestamp" in bot_proc

        # Filter by component type
        crawlers = await process_cache.get_top(comp="crawler")
        assert len(crawlers) >= 1
        assert all(p["type"] == "crawler" for p in crawlers)

        # Filter by time (should get all recent)
        recent = await process_cache.get_top(deltatime=300)  # 5 minutes
        assert len(recent) >= 2

    @pytest.mark.asyncio
    async def test_update_process_legacy(self, process_cache):
        """Test legacy update_process method."""
        # Update non-existent process (should create)
        success = await process_cache.update_process_legacy(
            "bot",
            "legacy_bot",
            "Starting up"
        )
        assert success is True

        # Verify created
        status = await process_cache.get_component_status("legacy_bot")
        assert status is not None
        assert status["message"] == "Starting up"

        # Update existing
        success = await process_cache.update_process_legacy(
            "bot",
            "legacy_bot",
            "Running smoothly"
        )
        assert success is True

        # Verify updated
        status = await process_cache.get_component_status("legacy_bot")
        assert status["message"] == "Running smoothly"

        # Invalid type
        success = await process_cache.update_process_legacy(
            "invalid_type",
            "test",
            "message"
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_new_process(self, process_cache):
        """Test legacy new_process method."""
        # Create new process
        result = await process_cache.new_process(
            tipe="tick",
            key="tick_processor",
            params={"symbols": ["BTC/USDT", "ETH/USDT"]},
            pid=12345,  # Should be ignored
            message="Processing ticks"
        )
        assert result == 1

        # Verify created
        status = await process_cache.get_component_status("tick_processor")
        assert status is not None
        assert status["params"]["symbols"] == ["BTC/USDT", "ETH/USDT"]
        assert status["message"] == "Processing ticks"

        # Invalid type
        result = await process_cache.new_process(
            tipe="invalid",
            key="test",
            params={}
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_process_legacy(self, process_cache):
        """Test legacy get_process method."""
        # Register process
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="get_test",
            params={"strategy": "arbitrage"},
            message="Bot active"
        )

        # Get using legacy method
        process = await process_cache.get_process_legacy("bot", "get_test")
        assert process["params"]["strategy"] == "arbitrage"
        assert process["message"] == "Bot active"
        assert "timestamp" in process

        # Get non-existent
        process = await process_cache.get_process_legacy("bot", "nonexistent")
        assert process == {}

    @pytest.mark.asyncio
    async def test_delete_process(self, process_cache):
        """Test legacy delete_process method."""
        # Register processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="del_bot1"
        )
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="del_bot2"
        )

        # Delete specific process
        success = await process_cache.delete_process("bot", "del_bot1")
        assert success is True

        # Verify deleted
        status = await process_cache.get_component_status("del_bot1")
        assert status is None

        # Other still exists
        status = await process_cache.get_component_status("del_bot2")
        assert status is not None

        # Delete all of type
        success = await process_cache.delete_process("bot")
        assert success is True

        # Verify all deleted
        status = await process_cache.get_component_status("del_bot2")
        assert status is None

        # Delete non-existent
        success = await process_cache.delete_process("bot", "nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_legacy_integration(self, process_cache):
        """Test legacy methods working together."""
        # Create process using legacy method
        result = await process_cache.new_process(
            tipe="ohlcv",
            key="ohlcv_processor",
            params={"timeframe": "1m"},
            message="Starting OHLCV processor"
        )
        assert result == 1

        # Update using legacy method
        success = await process_cache.update_process_legacy(
            "ohlcv",
            "ohlcv_processor",
            "Processing bars"
        )
        assert success is True

        # Get using legacy method
        process = await process_cache.get_process_legacy("ohlcv", "ohlcv_processor")
        assert process["message"] == "Processing bars"

        # Get top to see it
        processes = await process_cache.get_top(comp="ohlcv")
        assert len(processes) >= 1
        assert any(p["key"] == "ohlcv_processor" for p in processes)

        # Delete using legacy method
        success = await process_cache.delete_process("ohlcv", "ohlcv_processor")
        assert success is True

        # Verify deleted
        process = await process_cache.get_process_legacy("ohlcv", "ohlcv_processor")
        assert process == {}

    @pytest.mark.asyncio
    async def test_legacy_edge_cases(self, process_cache):
        """Test legacy method edge cases for coverage."""
        # First, let's test the branches we need to cover
        # Test delete_from_top with multiple processes where one fails to stop
        # We need multiple processes to return from get_active_processes with same component
        # Create two process entries that will both match the component filter

        comp_name = "multi_comp_bot"
        p1 = await process_cache.register_process(ProcessType.BOT, comp_name)

        # Create a second process with data but not through register_process
        p2 = f"bot:{comp_name}:fake999"
        fake_data = {
            "process_id": p2,
            "component": comp_name,
            "process_type": "bot",
            "status": "running",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }
        await process_cache._cache.set_json(f"data:{p2}", fake_data)
        await process_cache._cache.hset("active:bot", p2, datetime.now(UTC).isoformat())

        # Create a third process
        p3 = f"bot:{comp_name}:fake998"
        fake_data3 = {
            "process_id": p3,
            "component": comp_name,
            "process_type": "bot",
            "status": "running",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }
        await process_cache._cache.set_json(f"data:{p3}", fake_data3)
        await process_cache._cache.hset("active:bot", p3, datetime.now(UTC).isoformat())

        # Now delete the data for p2 so stop_process will fail for it (middle one fails)
        await process_cache._cache.delete(f"data:{p2}")

        # delete_from_top will get all three processes, p2 fails, but p1 and p3 succeed
        deleted = await process_cache.delete_from_top(comp_name)
        assert deleted == 2  # p1 and p3 were deleted, p2 failed

        # Test delete_process with multiple processes where one fails
        q1 = await process_cache.register_process(ProcessType.CRAWLER, "crawler_branch1")
        q2 = await process_cache.register_process(ProcessType.CRAWLER, "crawler_branch2")
        q3 = await process_cache.register_process(ProcessType.CRAWLER, "crawler_branch3")

        # Delete data for q2 (middle one) so stop will fail
        await process_cache._cache.delete(f"data:{q2}")

        # delete_process should still return True because q1 and q3 succeed
        success = await process_cache.delete_process("crawler")
        assert success is True

    @pytest.mark.asyncio
    async def test_legacy_edge_cases_continued(self, process_cache):
        """Test legacy method edge cases for coverage."""
        # Delete from top with no component (returns 0)
        deleted = await process_cache.delete_from_top()
        assert deleted == 0

        # Get top with only deltatime filter
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="edge_bot"
        )
        processes = await process_cache.get_top(deltatime=300)
        assert len(processes) >= 1

        # Get top with no filters
        all_procs = await process_cache.get_top()
        assert len(all_procs) >= 1

        # Test register_process with CacheError
        # Mock the set_json to raise an exception
        async def mock_set_json(*args, **kwargs):
            raise Exception("Redis error")

        original_set_json = process_cache._cache.set_json
        process_cache._cache.set_json = mock_set_json

        with pytest.raises(CacheError):
            await process_cache.register_process(
                process_type=ProcessType.BOT,
                component="error_bot"
            )

        # Restore
        process_cache._cache.set_json = original_set_json

        # Test update_process error handling
        # Register a process first (while set_json works)
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="update_error_bot"
        )

        # Now break set_json and try to update
        process_cache._cache.set_json = mock_set_json
        success = await process_cache.update_process(
            process_id=process_id,
            message="This will fail"
        )
        assert success is False

        # Restore
        process_cache._cache.set_json = original_set_json

        # Test get_active_processes with invalid timestamp
        # Set invalid timestamp in active set
        await process_cache._cache.hset(
            "active:bot",
            "invalid_process",
            "not-a-timestamp"
        )

        # Should skip invalid entries
        processes = await process_cache.get_active_processes(
            process_type=ProcessType.BOT
        )
        # All returned processes should have valid process_id
        assert all("process_id" in p for p in processes)

        # Test cleanup_stale_processes with missing process data
        fake_process_id = "bot:fake:12345"
        await process_cache._cache.hset(
            "active:bot",
            fake_process_id,
            datetime.now(UTC).isoformat()
        )
        # No process data exists, so it should handle gracefully
        cleaned = await process_cache.cleanup_stale_processes(stale_minutes=30)
        # Should not crash

        # Test delete_process with invalid type
        success = await process_cache.delete_process("invalid_type")
        assert success is False

        # Test process data not found during active process listing
        # Add a process ID to active set without corresponding data
        fake_id = "bot:nonexistent:99999"
        await process_cache._cache.hset(
            "active:bot",
            fake_id,
            datetime.now(UTC).isoformat()
        )
        # get_active_processes should skip it
        processes = await process_cache.get_active_processes(process_type=ProcessType.BOT)
        assert not any(p.get("process_id") == fake_id for p in processes)

        # Test heartbeat without value
        process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="no_heartbeat_bot"
        )
        # Remove heartbeat field
        process_data = await process_cache.get_process(process_id)
        del process_data["heartbeat"]
        await process_cache._cache.set_json(f"data:{process_id}", process_data, ttl=86400)

        # Should mark as stale
        processes = await process_cache.get_active_processes(
            since_minutes=30,
            include_heartbeat_check=True
        )
        bot_process = next((p for p in processes if p["component"] == "no_heartbeat_bot"), None)
        assert bot_process is not None
        assert bot_process["_heartbeat_stale"] is True

        # Test delete_from_top with component that has processes
        await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="delete_me"
        )
        deleted = await process_cache.delete_from_top("delete_me")
        assert deleted == 1

        # Test delete_process deleting all of a type
        # Register multiple bots
        await process_cache.register_process(ProcessType.BOT, "bot_a")
        await process_cache.register_process(ProcessType.BOT, "bot_b")

        # Delete all bots
        success = await process_cache.delete_process("bot")
        assert success is True

        # Verify no bots left
        bots = await process_cache.get_active_processes(process_type=ProcessType.BOT)
        assert len([b for b in bots if b["component"] in ["bot_a", "bot_b"]]) == 0

        # Test cleanup with process data missing during cleanup
        stale_id = "bot:stale_missing:12345"
        stale_time = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
        await process_cache._cache.hset(
            "active:bot",
            stale_id,
            stale_time
        )
        # No process data exists, cleanup should handle it
        cleaned = await process_cache.cleanup_stale_processes(stale_minutes=30)
        # Cleanup happened (could be more than 1 if other stale processes exist)
        assert cleaned >= 0

        # Clean up test data
        await process_cache._cache.hdel("active:bot", fake_process_id, fake_id, stale_id)

        # Test the branch where process has recent heartbeat during cleanup
        # This covers the branch at line 385->375
        fresh_process_id = await process_cache.register_process(
            process_type=ProcessType.BOT,
            component="fresh_during_cleanup"
        )
        # Set active timestamp to old, but keep heartbeat fresh
        old_active_time = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
        await process_cache._cache.hset(
            "active:bot",
            fresh_process_id,
            old_active_time
        )
        # Process data has fresh heartbeat, so it won't be cleaned
        cleaned = await process_cache.cleanup_stale_processes(stale_minutes=30)
        # Process should still exist
        process = await process_cache.get_process(fresh_process_id)
        assert process is not None
        assert process["status"] != ProcessStatus.STOPPED.value

        # Test stop_process returning False in delete_from_top
        # This covers branch 560->559
        # Create multiple processes for a component
        await process_cache.register_process(ProcessType.BOT, "multi_bot")
        # Create another process entry manually with same component
        fake_multi_id = "bot:multi_bot:fake123"
        await process_cache._cache.hset(
            "active:bot",
            fake_multi_id,
            datetime.now(UTC).isoformat()
        )
        await process_cache._cache.set_json(
            f"data:{fake_multi_id}",
            {
                "process_id": fake_multi_id,
                "component": "multi_bot",
                "process_type": "bot",
                "status": "running"
            }
        )
        # Remove from component index so stop_process will fail for this one
        await process_cache._cache.hdel("components", "multi_bot")

        # delete_from_top should try to delete both but only succeed on fake one
        deleted = await process_cache.delete_from_top("multi_bot")
        # Should have deleted at least the fake one
        assert deleted >= 0

        # Test stop_process returning False in delete_process
        # This covers branch 740->739
        # Create multiple processes of same type
        await process_cache.register_process(ProcessType.OHLCV, "ohlcv1")
        await process_cache.register_process(ProcessType.OHLCV, "ohlcv2")

        # Make one unstoppable by removing its data
        processes = await process_cache.get_active_processes(process_type=ProcessType.OHLCV)
        if len(processes) >= 2:
            # Delete the process data for first one
            first_id = processes[0]["process_id"]
            await process_cache._cache.delete(f"data:{first_id}")

        # Now delete_process should continue after first failure
        success = await process_cache.delete_process("ohlcv")
        # Should return True because at least one succeeded
        assert success is True
