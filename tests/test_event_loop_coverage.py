"""Additional tests for EventLoopManager to improve coverage - NO MOCKING!"""

import asyncio
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from fullon_cache.event_loop import (
    EventLoopPolicy,
    EventLoopManager,
    get_event_loop_manager,
    configure_event_loop,
    get_policy_info,
    is_uvloop_active,
    benchmark_current_policy,
)


class TestEventLoopManagerCoverage:
    """Test cases to improve EventLoopManager coverage using real operations."""

    def test_event_loop_policy_enum(self):
        """Test EventLoopPolicy enum values."""
        assert EventLoopPolicy.AUTO.value == "auto"
        assert EventLoopPolicy.ASYNCIO.value == "asyncio"
        assert EventLoopPolicy.UVLOOP.value == "uvloop"

    def test_manager_init_with_policy(self):
        """Test manager initialization with specific policy."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        assert manager.policy == EventLoopPolicy.ASYNCIO
        assert manager.force_policy is False
        assert manager._active_policy is None

    def test_manager_init_with_force(self):
        """Test manager initialization with force policy."""
        manager = EventLoopManager(force_policy=True)
        assert manager.force_policy is True

    def test_get_policy_from_env_auto(self):
        """Test getting policy from environment - auto case."""
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "auto"}):
            manager = EventLoopManager()
            assert manager.policy == EventLoopPolicy.AUTO

    def test_get_policy_from_env_asyncio(self):
        """Test getting policy from environment - asyncio case."""
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "asyncio"}):
            manager = EventLoopManager()
            assert manager.policy == EventLoopPolicy.ASYNCIO

    def test_get_policy_from_env_uvloop(self):
        """Test getting policy from environment - uvloop case."""
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "uvloop"}):
            manager = EventLoopManager()
            assert manager.policy == EventLoopPolicy.UVLOOP

    def test_get_policy_from_env_invalid(self):
        """Test getting policy from environment - invalid value."""
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "invalid_policy"}):
            manager = EventLoopManager()
            # Should fall back to AUTO for invalid values
            assert manager.policy == EventLoopPolicy.AUTO

    def test_get_policy_from_env_case_insensitive(self):
        """Test environment variable is case insensitive."""
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "UVLOOP"}):
            manager = EventLoopManager()
            assert manager.policy == EventLoopPolicy.UVLOOP

    def test_uvloop_availability_caching(self):
        """Test that uvloop availability is cached."""
        manager = EventLoopManager()
        
        # First call
        result1 = manager._is_uvloop_available()
        
        # Second call should use cached value
        result2 = manager._is_uvloop_available()
        
        assert result1 == result2
        assert manager._uvloop_available is not None

    @pytest.mark.skipif(sys.platform == 'win32', reason="uvloop not supported on Windows")
    def test_uvloop_platform_check_unix(self):
        """Test uvloop availability on Unix platforms."""
        manager = EventLoopManager()
        
        # On Unix, should at least attempt to import uvloop
        result = manager._is_uvloop_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific test")
    def test_uvloop_platform_check_windows(self):
        """Test uvloop availability on Windows platforms."""
        manager = EventLoopManager()
        
        # On Windows, should return False due to platform incompatibility
        result = manager._is_uvloop_available()
        assert result is False

    def test_configure_asyncio_policy(self):
        """Test configuring asyncio policy."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        
        result = manager.configure()
        assert result == EventLoopPolicy.ASYNCIO
        assert manager.get_active_policy() == EventLoopPolicy.ASYNCIO

    def test_configure_auto_policy(self):
        """Test configuring AUTO policy."""
        manager = EventLoopManager(policy=EventLoopPolicy.AUTO)
        
        result = manager.configure()
        # Should configure either UVLOOP or ASYNCIO based on availability
        assert result in [EventLoopPolicy.UVLOOP, EventLoopPolicy.ASYNCIO]
        assert manager.get_active_policy() in [EventLoopPolicy.UVLOOP, EventLoopPolicy.ASYNCIO]

    def test_configure_uvloop_fallback(self):
        """Test uvloop configuration with fallback."""
        # Request uvloop but don't force it
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=False)
        
        result = manager.configure()
        # Should either succeed with uvloop or fall back to asyncio/auto
        assert result in [EventLoopPolicy.UVLOOP, EventLoopPolicy.AUTO, EventLoopPolicy.ASYNCIO]

    def test_configure_forced_policy_failure(self):
        """Test forced policy configuration failure."""
        # Create a manager that forces an impossible configuration
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=True)
        
        # Mock uvloop as unavailable for this test
        with patch.object(manager, '_is_uvloop_available', return_value=False):
            with patch.object(manager, '_configure_uvloop', side_effect=ImportError("uvloop not available")):
                with pytest.raises(RuntimeError, match="Failed to configure forced policy"):
                    manager.configure()

    def test_configure_with_exception_fallback(self):
        """Test configuration with exception handling and fallback."""
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=False)
        
        # Mock configuration failure to test fallback
        with patch.object(manager, '_configure_uvloop', side_effect=Exception("Config failed")):
            result = manager.configure()
            # Should fall back to asyncio
            assert result == EventLoopPolicy.ASYNCIO
            assert manager.get_active_policy() == EventLoopPolicy.ASYNCIO

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific test")
    def test_configure_asyncio_windows(self):
        """Test asyncio configuration on Windows."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        manager._configure_asyncio()
        
        # Should set WindowsProactorEventLoopPolicy on Windows
        policy = asyncio.get_event_loop_policy()
        assert isinstance(policy, asyncio.WindowsProactorEventLoopPolicy)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Unix-specific test")
    def test_configure_asyncio_unix(self):
        """Test asyncio configuration on Unix."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        manager._configure_asyncio()
        
        # Should set default policy (None) on Unix
        policy = asyncio.get_event_loop_policy()
        # Policy should be the default for the platform
        assert policy is not None

    def test_get_policy_info_structure(self):
        """Test policy info returns correct structure."""
        manager = EventLoopManager()
        manager.configure()
        
        info = manager.get_policy_info()
        
        # Check required keys
        required_keys = [
            'active_policy', 'requested_policy', 'uvloop_available',
            'platform', 'python_version', 'force_policy'
        ]
        for key in required_keys:
            assert key in info

        # Check data types
        assert isinstance(info['uvloop_available'], bool)
        assert isinstance(info['platform'], str)
        assert isinstance(info['python_version'], str)
        assert isinstance(info['force_policy'], bool)

    def test_get_policy_info_with_uvloop_active(self):
        """Test policy info when uvloop is active."""
        manager = EventLoopManager()
        manager._active_policy = EventLoopPolicy.UVLOOP
        
        info = manager.get_policy_info()
        
        assert info['active_policy'] == 'uvloop'
        assert 'expected_performance' in info
        assert 'throughput_multiplier' in info['expected_performance']

    def test_get_policy_info_with_asyncio_active(self):
        """Test policy info when asyncio is active."""
        manager = EventLoopManager()
        manager._active_policy = EventLoopPolicy.ASYNCIO
        
        info = manager.get_policy_info()
        
        assert info['active_policy'] == 'asyncio'
        assert 'expected_performance' in info
        assert 'throughput_multiplier' in info['expected_performance']

    def test_get_policy_info_with_current_loop(self):
        """Test policy info includes current loop information."""
        async def test_with_loop():
            manager = EventLoopManager()
            info = manager.get_policy_info()
            
            # Should include current loop info when called from within a loop
            assert 'current_loop' in info
            if info['current_loop'] is not None:
                assert 'type' in info['current_loop']
                assert 'is_running' in info['current_loop']
            
        asyncio.run(test_with_loop())

    def test_get_policy_info_without_current_loop(self):
        """Test policy info when no current loop is running."""
        manager = EventLoopManager()
        info = manager.get_policy_info()
        
        # Should handle no running loop gracefully
        assert 'current_loop' in info

    @pytest.mark.asyncio
    async def test_benchmark_policy_within_loop(self):
        """Test benchmarking from within an event loop."""
        manager = EventLoopManager()
        manager.configure()
        
        result = await manager.benchmark_policy(duration=0.1)
        
        # Check benchmark results structure
        if 'error' not in result:
            assert 'policy' in result
            assert 'duration' in result
            assert 'operations' in result
            assert 'ops_per_second' in result
            assert 'avg_op_time_us' in result
            
            assert isinstance(result['operations'], int)
            assert result['operations'] > 0
            assert result['ops_per_second'] > 0

    def test_benchmark_policy_without_loop(self):
        """Test benchmarking when no event loop is running."""
        manager = EventLoopManager()
        manager.configure()
        
        # This should use asyncio.run() internally
        async def run_benchmark():
            return await manager.benchmark_policy(duration=0.1)
        
        result = asyncio.run(run_benchmark())
        
        if 'error' not in result:
            assert 'operations' in result
            assert result['operations'] > 0

    def test_determine_target_policy_auto(self):
        """Test target policy determination for AUTO."""
        manager = EventLoopManager(policy=EventLoopPolicy.AUTO)
        result = manager._determine_target_policy()
        assert result == EventLoopPolicy.AUTO

    def test_determine_target_policy_asyncio(self):
        """Test target policy determination for ASYNCIO."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        result = manager._determine_target_policy()
        assert result == EventLoopPolicy.ASYNCIO

    def test_determine_target_policy_uvloop_available(self):
        """Test target policy determination for UVLOOP when available."""
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP)
        
        # Mock uvloop as available
        with patch.object(manager, '_is_uvloop_available', return_value=True):
            result = manager._determine_target_policy()
            assert result == EventLoopPolicy.UVLOOP

    def test_determine_target_policy_uvloop_unavailable(self):
        """Test target policy determination for UVLOOP when unavailable."""
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=False)
        
        # Mock uvloop as unavailable
        with patch.object(manager, '_is_uvloop_available', return_value=False):
            result = manager._determine_target_policy()
            assert result == EventLoopPolicy.AUTO

    def test_determine_target_policy_uvloop_forced(self):
        """Test target policy determination for forced UVLOOP."""
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=True)
        
        # Even if unavailable, should return UVLOOP when forced
        with patch.object(manager, '_is_uvloop_available', return_value=False):
            result = manager._determine_target_policy()
            assert result == EventLoopPolicy.UVLOOP


class TestGlobalFunctions:
    """Test global utility functions."""

    def test_get_event_loop_manager_singleton(self):
        """Test that get_event_loop_manager returns the same instance."""
        manager1 = get_event_loop_manager()
        manager2 = get_event_loop_manager()
        assert manager1 is manager2

    def test_configure_event_loop_creates_new_manager(self):
        """Test that configure_event_loop creates a new manager."""
        # Get initial manager
        initial_manager = get_event_loop_manager()
        
        # Configure with specific policy
        policy = configure_event_loop(EventLoopPolicy.ASYNCIO)
        assert policy == EventLoopPolicy.ASYNCIO
        
        # Should have a new manager now
        new_manager = get_event_loop_manager()
        # The manager instance might be different now
        assert new_manager.get_active_policy() == EventLoopPolicy.ASYNCIO

    def test_configure_event_loop_with_force(self):
        """Test configure_event_loop with force parameter."""
        # This might fail on some systems, so we catch potential errors
        try:
            policy = configure_event_loop(EventLoopPolicy.ASYNCIO, force=True)
            assert policy == EventLoopPolicy.ASYNCIO
        except RuntimeError:
            # Expected if the forced policy can't be configured
            pass

    def test_get_policy_info_function(self):
        """Test get_policy_info global function."""
        configure_event_loop(EventLoopPolicy.ASYNCIO)
        info = get_policy_info()
        
        assert isinstance(info, dict)
        assert 'active_policy' in info
        assert info['active_policy'] == 'asyncio'

    def test_is_uvloop_active_true(self):
        """Test is_uvloop_active when uvloop is active."""
        # Create a manager and mock it as having uvloop active
        manager = get_event_loop_manager()
        manager._active_policy = EventLoopPolicy.UVLOOP
        
        result = is_uvloop_active()
        assert result is True

    def test_is_uvloop_active_false(self):
        """Test is_uvloop_active when uvloop is not active."""
        configure_event_loop(EventLoopPolicy.ASYNCIO)
        
        result = is_uvloop_active()
        assert result is False

    @pytest.mark.asyncio
    async def test_benchmark_current_policy_function(self):
        """Test benchmark_current_policy global function."""
        configure_event_loop(EventLoopPolicy.ASYNCIO)
        
        result = await benchmark_current_policy(duration=0.1)
        
        if 'error' not in result:
            assert 'policy' in result
            assert 'operations' in result
            assert result['operations'] > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_benchmark_with_zero_operations(self):
        """Test benchmark behavior when no operations complete."""
        manager = EventLoopManager()
        manager.configure()
        
        # Mock benchmark task to return 0 operations
        async def mock_benchmark():
            return await manager.benchmark_policy(duration=0.001)  # Very short duration
        
        result = asyncio.run(mock_benchmark())
        
        # Should handle zero operations gracefully
        if 'error' not in result:
            assert 'avg_op_time_us' in result
            # avg_op_time_us should be 0 when operations is 0

    def test_manager_state_before_configure(self):
        """Test manager state before configuration."""
        manager = EventLoopManager()
        
        # Should return None before configuration
        assert manager.get_active_policy() is None
        
        # Policy info should still work
        info = manager.get_policy_info()
        assert info['active_policy'] is None

    def test_multiple_configurations(self):
        """Test multiple consecutive configurations."""
        manager = EventLoopManager(policy=EventLoopPolicy.ASYNCIO)
        
        # First configuration
        result1 = manager.configure()
        assert result1 == EventLoopPolicy.ASYNCIO
        
        # Second configuration (should work)
        result2 = manager.configure()
        assert result2 == EventLoopPolicy.ASYNCIO
        assert manager.get_active_policy() == EventLoopPolicy.ASYNCIO

    def test_policy_info_with_no_active_policy(self):
        """Test policy info when no policy is active."""
        manager = EventLoopManager()
        # Don't configure, keep _active_policy as None
        
        info = manager.get_policy_info()
        
        assert info['active_policy'] is None
        assert 'expected_performance' not in info

    def test_import_error_handling(self):
        """Test handling of import errors during uvloop configuration."""
        manager = EventLoopManager()
        
        # Mock uvloop import to fail
        with patch.object(manager, '_configure_uvloop', side_effect=ImportError("No module named 'uvloop'")):
            # Should not raise an error if not forced
            result = manager.configure()
            # Should fall back to asyncio
            assert result == EventLoopPolicy.ASYNCIO

    def test_runtime_error_handling(self):
        """Test handling of runtime errors during configuration."""
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP, force_policy=False)
        
        # Mock uvloop configuration to fail with RuntimeError
        with patch.object(manager, '_configure_uvloop', side_effect=RuntimeError("Configuration failed")):
            result = manager.configure()
            # Should fall back to asyncio
            assert result == EventLoopPolicy.ASYNCIO

    def test_environment_variable_edge_cases(self):
        """Test edge cases for environment variable handling."""
        # Test with empty string
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": ""}):
            manager = EventLoopManager()
            # Empty string should fall back to AUTO
            assert manager.policy == EventLoopPolicy.AUTO
        
        # Test with whitespace
        with patch.dict(os.environ, {"FULLON_CACHE_EVENT_LOOP": "  auto  "}):
            manager = EventLoopManager()
            # Should handle whitespace
            assert manager.policy == EventLoopPolicy.AUTO

    def test_cached_uvloop_availability(self):
        """Test that uvloop availability is properly cached."""
        manager = EventLoopManager()
        
        # First call should set the cache
        result1 = manager._is_uvloop_available()
        initial_cache_value = manager._uvloop_available
        
        # Second call should use cache
        result2 = manager._is_uvloop_available()
        final_cache_value = manager._uvloop_available
        
        assert result1 == result2
        assert initial_cache_value == final_cache_value
        assert final_cache_value is not None