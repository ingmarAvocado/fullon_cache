"""Redis connection pool management with uvloop optimization.

This module provides a singleton connection pool for efficient Redis connections.
It handles connection configuration, pooling, health checks, and automatic
uvloop optimization for maximum performance.
"""

import asyncio
import logging
import os
import weakref
from typing import Any, Optional

from dotenv import load_dotenv
from redis.asyncio import ConnectionPool as RedisConnectionPool
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionError as RedisConnectionError

from .event_loop import EventLoopPolicy, configure_event_loop, get_policy_info
from .exceptions import ConfigurationError, ConnectionError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Singleton Redis connection pool manager with uvloop optimization.
    
    This class manages a single connection pool instance that is shared
    across all cache modules for efficient resource usage. It automatically
    configures uvloop for maximum performance when available.
    
    Features:
        - Automatic uvloop detection and configuration
        - Performance-optimized connection pooling
        - Platform-aware fallback to asyncio
        - Connection health monitoring
        - Memory and CPU efficient operations
    
    Example:
        pool = ConnectionPool()
        redis = await pool.get_connection()
        await redis.ping()
        
        # Check performance configuration
        info = pool.get_performance_info()
        print(f"Using {info['event_loop']} for optimal performance")
        
    Configuration via environment variables:
        REDIS_HOST: Redis server host (default: localhost)
        REDIS_PORT: Redis server port (default: 6379)
        REDIS_DB: Redis database number (default: 0)
        REDIS_PASSWORD: Redis password (optional)
        REDIS_MAX_CONNECTIONS: Max connections in pool (default: 50)
        REDIS_SOCKET_TIMEOUT: Socket timeout in seconds (default: 5)
        REDIS_SOCKET_CONNECT_TIMEOUT: Connection timeout (default: 5)
        FULLON_CACHE_EVENT_LOOP: Event loop policy (auto/asyncio/uvloop)
        FULLON_CACHE_AUTO_CONFIGURE: Auto-configure uvloop (default: true)
    """

    _instance: Optional['ConnectionPool'] = None
    _pools: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # Map event loops to pools
    _config: dict[str, Any] = {}

    def __new__(cls) -> 'ConnectionPool':
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the connection pool with configuration and uvloop optimization."""
        if self._initialized:
            return

        self._load_config()
        self._configure_event_loop()
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        self._config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'db': int(os.getenv('REDIS_DB', 0)),
            'password': os.getenv('REDIS_PASSWORD'),
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', 50)),
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', 5)),
            'socket_connect_timeout': int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', 5)),
            'decode_responses': True,  # Always decode for consistency
            'auto_configure_uvloop': os.getenv('FULLON_CACHE_AUTO_CONFIGURE', 'true').lower() == 'true',
        }

        # Validate configuration
        if self._config['port'] < 1 or self._config['port'] > 65535:
            raise ConfigurationError(
                f"Invalid Redis port: {self._config['port']}",
                config_key='REDIS_PORT'
            )

        if self._config['db'] < 0 or self._config['db'] > 15:
            raise ConfigurationError(
                f"Invalid Redis database number: {self._config['db']}",
                config_key='REDIS_DB'
            )

    def _configure_event_loop(self) -> None:
        """Configure the optimal event loop policy for performance."""
        if not self._config['auto_configure_uvloop']:
            logger.debug("Auto-configuration of uvloop disabled by configuration")
            return

        try:
            # Configure the event loop for optimal performance
            active_policy = configure_event_loop()

            if active_policy == EventLoopPolicy.UVLOOP:
                logger.info("uvloop configured for optimal Redis performance")
                # Increase max connections for uvloop due to better performance
                original_max = self._config['max_connections']
                self._config['max_connections'] = min(original_max * 2, 200)
                logger.debug(
                    f"Increased max connections from {original_max} to "
                    f"{self._config['max_connections']} for uvloop"
                )
            else:
                logger.info(f"Using {active_policy.value} event loop for Redis operations")

        except Exception as e:
            logger.warning(f"Failed to configure optimal event loop: {e}")
            # Continue with default asyncio

    def get_pool(self) -> RedisConnectionPool:
        """Get or create the Redis connection pool for the current event loop.
        
        Returns:
            RedisConnectionPool: The connection pool for the current event loop
            
        Raises:
            ConfigurationError: If configuration is invalid
            RuntimeError: If called outside of an async context
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("ConnectionPool.get_pool() must be called from an async context")

        # Check if we have a pool for this event loop
        if loop not in self._pools:
            pool_kwargs = {
                'host': self._config['host'],
                'port': self._config['port'],
                'db': self._config['db'],
                'max_connections': self._config['max_connections'],
                'socket_timeout': self._config['socket_timeout'],
                'socket_connect_timeout': self._config['socket_connect_timeout'],
                'decode_responses': self._config['decode_responses'],
            }

            if self._config['password']:
                pool_kwargs['password'] = self._config['password']

            pool = RedisConnectionPool(**pool_kwargs)
            self._pools[loop] = pool

            logger.debug(
                f"Created Redis connection pool for event loop {id(loop)}: "
                f"{self._config['host']}:{self._config['port']}/{self._config['db']} "
                f"(max_connections={self._config['max_connections']})"
            )

        return self._pools[loop]

    async def get_connection(self, decode_responses: bool = True) -> Redis:
        """Get a Redis connection from the pool.
        
        Args:
            decode_responses: Whether to decode responses (default: True)
            
        Returns:
            Redis: An async Redis client instance
            
        Raises:
            ConnectionError: If connection to Redis fails
        """
        try:
            pool = self.get_pool()

            # Create a new Redis instance with custom decode setting if needed
            if decode_responses != self._config['decode_responses']:
                # Need a separate connection with different decode setting
                redis = Redis(
                    host=self._config['host'],
                    port=self._config['port'],
                    db=self._config['db'],
                    password=self._config['password'],
                    decode_responses=decode_responses,
                    socket_timeout=self._config['socket_timeout'],
                    socket_connect_timeout=self._config['socket_connect_timeout'],
                )
            else:
                # Use the shared pool
                redis = Redis(connection_pool=pool)

            # Test the connection
            await redis.ping()
            return redis

        except RedisConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to Redis at {self._config['host']}:{self._config['port']}",
                host=self._config['host'],
                port=self._config['port'],
                original_error=e
            )
        except Exception as e:
            raise ConnectionError(
                f"Unexpected error connecting to Redis: {str(e)}",
                host=self._config['host'],
                port=self._config['port'],
                original_error=e
            )

    async def close(self) -> None:
        """Close all connection pools for all event loops.
        
        This should be called when shutting down the application.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, can't close async resources
            return

        # Close pool for current event loop
        if loop in self._pools:
            pool = self._pools[loop]
            try:
                await pool.aclose()
                logger.debug(f"Closed Redis connection pool for event loop {id(loop)}")
            except Exception as e:
                logger.warning(f"Error closing connection pool: {e}")
            finally:
                # Remove from dict
                self._pools.pop(loop, None)

    def get_config(self) -> dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            Dict containing the current Redis configuration
        """
        return self._config.copy()

    def get_performance_info(self) -> dict[str, Any]:
        """Get detailed performance information about the connection pool.
        
        Returns:
            Dict containing performance metrics and configuration details
        """
        info = {
            'redis_config': self.get_config(),
            'event_loop_info': get_policy_info(),
            'pool_stats': {},
        }

        # Add pool statistics for current event loop if available
        try:
            loop = asyncio.get_running_loop()
            if loop in self._pools:
                pool = self._pools[loop]
                info['pool_stats'] = {
                    'max_connections': pool.max_connections,
                    'created_connections': pool.created_connections,
                    'available_connections': len(pool._available_connections),
                    'in_use_connections': len(pool._in_use_connections),
                }
        except (RuntimeError, AttributeError):
            # Not in async context or pool doesn't have stats
            pass

        return info

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance.
        
        This is mainly useful for testing to ensure a clean state.
        WARNING: This does not properly close async connections.
        Use reset_async() when possible.
        """
        if cls._instance:
            # Clear all pools (they will be cleaned up by GC/weakref)
            cls._instance._pools.clear()
            cls._instance = None

    @classmethod
    async def reset_async(cls) -> None:
        """Reset the singleton instance with proper async cleanup.
        
        This properly closes all connections before resetting.
        """
        if cls._instance:
            # Close the pool for the current event loop
            await cls._instance.close()
            # Clear all pools
            cls._instance._pools.clear()
            cls._instance = None


async def get_redis(decode_responses: bool = True) -> Redis:
    """Convenience function to get a Redis connection.
    
    This is a shortcut for ConnectionPool().get_connection().
    
    Args:
        decode_responses: Whether to decode responses (default: True)
        
    Returns:
        Redis: An async Redis client instance
        
    Example:
        redis = await get_redis()
        await redis.set("key", "value")
    """
    pool = ConnectionPool()
    return await pool.get_connection(decode_responses=decode_responses)
