"""Event loop management with uvloop optimization.

This module provides automatic uvloop detection and configuration for maximum
performance in async operations. It automatically falls back to standard asyncio
on unsupported platforms.
"""

import asyncio
import logging
import os
import sys
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventLoopPolicy(Enum):
    """Available event loop policies."""
    AUTO = "auto"
    ASYNCIO = "asyncio"
    UVLOOP = "uvloop"


class EventLoopManager:
    """Manager for event loop policies with uvloop optimization.
    
    This class handles automatic detection and configuration of the best
    available event loop policy, with preference for uvloop when available.
    
    Features:
        - Automatic uvloop detection and installation
        - Graceful fallback to asyncio on unsupported platforms
        - Configuration via environment variables
        - Performance monitoring and logging
        
    Example:
        # Automatic configuration (recommended)
        manager = EventLoopManager()
        manager.configure()
        
        # Manual policy selection
        manager = EventLoopManager(policy=EventLoopPolicy.UVLOOP)
        manager.configure()
        
        # Check what's currently active
        print(f"Active policy: {manager.get_active_policy()}")
    """

    def __init__(self, policy: EventLoopPolicy | None = None,
                 force_policy: bool = False):
        """Initialize the event loop manager.
        
        Args:
            policy: Specific policy to use (None for auto-detection)
            force_policy: Whether to force the policy even if not optimal
        """
        self.policy = policy or self._get_policy_from_env()
        self.force_policy = force_policy
        self._active_policy: EventLoopPolicy | None = None
        self._uvloop_available: bool | None = None

    def _get_policy_from_env(self) -> EventLoopPolicy:
        """Get event loop policy from environment variables.
        
        Returns:
            EventLoopPolicy based on FULLON_CACHE_EVENT_LOOP env var
        """
        env_policy = os.getenv('FULLON_CACHE_EVENT_LOOP', 'auto').lower()

        try:
            return EventLoopPolicy(env_policy)
        except ValueError:
            logger.warning(
                f"Invalid event loop policy '{env_policy}', using AUTO. "
                f"Valid options: {[p.value for p in EventLoopPolicy]}"
            )
            return EventLoopPolicy.AUTO

    def _is_uvloop_available(self) -> bool:
        """Check if uvloop is available and can be imported.
        
        Returns:
            True if uvloop is available and platform is supported
        """
        if self._uvloop_available is not None:
            return self._uvloop_available

        # Check platform compatibility
        if sys.platform == 'win32':
            logger.debug("uvloop not supported on Windows")
            self._uvloop_available = False
            return False

        try:
            import uvloop
            self._uvloop_available = True
            logger.debug(f"uvloop {uvloop.__version__} detected and available")
            return True
        except ImportError:
            logger.debug("uvloop not installed or not available")
            self._uvloop_available = False
            return False

    def configure(self) -> EventLoopPolicy:
        """Configure the optimal event loop policy.
        
        This method analyzes the available options and configures
        the best event loop policy for performance.
        
        Returns:
            The EventLoopPolicy that was actually configured
            
        Raises:
            RuntimeError: If forced policy is not available
        """
        target_policy = self._determine_target_policy()

        try:
            if target_policy == EventLoopPolicy.UVLOOP:
                self._configure_uvloop()
            elif target_policy == EventLoopPolicy.ASYNCIO:
                self._configure_asyncio()
            else:
                # AUTO policy - use best available
                if self._is_uvloop_available():
                    self._configure_uvloop()
                    target_policy = EventLoopPolicy.UVLOOP
                else:
                    self._configure_asyncio()
                    target_policy = EventLoopPolicy.ASYNCIO

            self._active_policy = target_policy
            logger.info(f"Event loop configured: {target_policy.value}")

            return target_policy

        except Exception as e:
            if self.force_policy:
                raise RuntimeError(
                    f"Failed to configure forced policy {target_policy.value}: {e}"
                )

            # Fallback to asyncio
            logger.warning(
                f"Failed to configure {target_policy.value}, falling back to asyncio: {e}"
            )
            self._configure_asyncio()
            self._active_policy = EventLoopPolicy.ASYNCIO
            return EventLoopPolicy.ASYNCIO

    def _determine_target_policy(self) -> EventLoopPolicy:
        """Determine which policy should be configured.
        
        Returns:
            The target EventLoopPolicy to configure
        """
        if self.policy == EventLoopPolicy.AUTO:
            return EventLoopPolicy.AUTO
        elif self.policy == EventLoopPolicy.UVLOOP:
            if not self.force_policy and not self._is_uvloop_available():
                logger.warning(
                    "uvloop policy requested but not available, using auto-detection"
                )
                return EventLoopPolicy.AUTO
            return EventLoopPolicy.UVLOOP
        else:
            return EventLoopPolicy.ASYNCIO

    def _configure_uvloop(self) -> None:
        """Configure uvloop as the event loop policy.
        
        Raises:
            ImportError: If uvloop is not available
            RuntimeError: If uvloop configuration fails
        """
        try:
            import uvloop

            # Install uvloop as the default event loop policy
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

            logger.debug(
                f"uvloop {uvloop.__version__} configured as event loop policy"
            )

        except ImportError as e:
            raise ImportError(f"uvloop is not available: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to configure uvloop: {e}")

    def _configure_asyncio(self) -> None:
        """Configure standard asyncio as the event loop policy."""
        # Reset to default asyncio policy
        if sys.platform == 'win32':
            # Use WindowsProactorEventLoopPolicy on Windows for better performance
            asyncio.set_event_loop_policy(
                asyncio.WindowsProactorEventLoopPolicy()
            )
            logger.debug("Windows Proactor event loop policy configured")
        else:
            # Use default policy on Unix systems
            asyncio.set_event_loop_policy(None)
            logger.debug("Default asyncio event loop policy configured")

    def get_active_policy(self) -> EventLoopPolicy | None:
        """Get the currently active event loop policy.
        
        Returns:
            The active EventLoopPolicy or None if not configured
        """
        return self._active_policy

    def get_policy_info(self) -> dict[str, Any]:
        """Get detailed information about the current event loop configuration.
        
        Returns:
            Dict containing policy information and performance characteristics
        """
        info = {
            'active_policy': self._active_policy.value if self._active_policy else None,
            'requested_policy': self.policy.value,
            'uvloop_available': self._is_uvloop_available(),
            'platform': sys.platform,
            'python_version': sys.version,
            'force_policy': self.force_policy,
        }

        # Add performance expectations
        if self._active_policy == EventLoopPolicy.UVLOOP:
            info['expected_performance'] = {
                'throughput_multiplier': '2-4x vs asyncio',
                'memory_efficiency': 'Up to 50% reduction',
                'concurrency_support': 'Excellent (100k+ connections)',
            }
        elif self._active_policy == EventLoopPolicy.ASYNCIO:
            info['expected_performance'] = {
                'throughput_multiplier': '1x (baseline)',
                'memory_efficiency': 'Standard',
                'concurrency_support': 'Good (10k+ connections)',
            }

        # Add current loop info if available
        try:
            loop = asyncio.get_running_loop()
            info['current_loop'] = {
                'type': type(loop).__name__,
                'is_running': loop.is_running(),
            }
        except RuntimeError:
            info['current_loop'] = None

        return info

    async def benchmark_policy(self, duration: float = 1.0) -> dict[str, Any]:
        """Run a simple benchmark of the current event loop policy.
        
        Args:
            duration: How long to run the benchmark in seconds
            
        Returns:
            Dict with benchmark results
        """
        import time

        async def benchmark_task():
            """Simple benchmark task."""
            start_time = time.perf_counter()
            operations = 0

            while time.perf_counter() - start_time < duration:
                # Simple async operation
                await asyncio.sleep(0)
                operations += 1

            return operations

        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, run directly
                start_time = time.perf_counter()
                operations = await benchmark_task()
                total_time = time.perf_counter() - start_time
            except RuntimeError:
                # No running loop, use asyncio.run()
                start_time = time.perf_counter()
                operations = asyncio.run(benchmark_task())
                total_time = time.perf_counter() - start_time

            return {
                'policy': self._active_policy.value if self._active_policy else 'unknown',
                'duration': total_time,
                'operations': operations,
                'ops_per_second': operations / total_time,
                'avg_op_time_us': (total_time / operations) * 1_000_000 if operations > 0 else 0,
            }

        except Exception as e:
            return {
                'error': str(e),
                'policy': self._active_policy.value if self._active_policy else 'unknown',
            }


# Global event loop manager instance
_global_manager: EventLoopManager | None = None


def get_event_loop_manager() -> EventLoopManager:
    """Get the global event loop manager instance.
    
    Returns:
        The global EventLoopManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = EventLoopManager()
    return _global_manager


def configure_event_loop(policy: EventLoopPolicy | None = None,
                        force: bool = False) -> EventLoopPolicy:
    """Configure the global event loop policy.
    
    This is a convenience function for configuring the event loop
    with optimal performance settings.
    
    Args:
        policy: Specific policy to use (None for auto-detection)
        force: Whether to force the policy even if not optimal
        
    Returns:
        The EventLoopPolicy that was actually configured
        
    Example:
        # Use automatic detection (recommended)
        policy = configure_event_loop()
        print(f"Using {policy.value} event loop")
        
        # Force uvloop (will raise error if not available)
        configure_event_loop(EventLoopPolicy.UVLOOP, force=True)
    """
    global _global_manager
    _global_manager = EventLoopManager(policy=policy, force_policy=force)
    return _global_manager.configure()


def get_policy_info() -> dict[str, Any]:
    """Get information about the current event loop configuration.
    
    Returns:
        Dict containing detailed policy information
    """
    manager = get_event_loop_manager()
    return manager.get_policy_info()


def is_uvloop_active() -> bool:
    """Check if uvloop is currently active.
    
    Returns:
        True if uvloop is the active event loop policy
    """
    manager = get_event_loop_manager()
    return manager.get_active_policy() == EventLoopPolicy.UVLOOP


async def benchmark_current_policy(duration: float = 1.0) -> dict[str, Any]:
    """Benchmark the current event loop policy.
    
    Args:
        duration: How long to run the benchmark in seconds
        
    Returns:
        Dict with benchmark results
    """
    manager = get_event_loop_manager()
    return await manager.benchmark_policy(duration)
