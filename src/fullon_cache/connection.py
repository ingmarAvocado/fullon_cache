"""Redis connection pool management.

This module provides a singleton connection pool for efficient Redis connections.
It handles connection configuration, pooling, and health checks.
"""

import os
import asyncio
import weakref
from typing import Optional, Dict, Any
import logging
from redis.asyncio import Redis, ConnectionPool as RedisConnectionPool
from redis.asyncio.connection import ConnectionError as RedisConnectionError
from dotenv import load_dotenv

from .exceptions import ConnectionError, ConfigurationError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Singleton Redis connection pool manager.
    
    This class manages a single connection pool instance that is shared
    across all cache modules for efficient resource usage.
    
    Example:
        pool = ConnectionPool()
        redis = await pool.get_connection()
        await redis.ping()
        
    Configuration via environment variables:
        REDIS_HOST: Redis server host (default: localhost)
        REDIS_PORT: Redis server port (default: 6379)
        REDIS_DB: Redis database number (default: 0)
        REDIS_PASSWORD: Redis password (optional)
        REDIS_MAX_CONNECTIONS: Max connections in pool (default: 50)
        REDIS_SOCKET_TIMEOUT: Socket timeout in seconds (default: 5)
        REDIS_SOCKET_CONNECT_TIMEOUT: Connection timeout (default: 5)
    """
    
    _instance: Optional['ConnectionPool'] = None
    _pools: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # Map event loops to pools
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> 'ConnectionPool':
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool with configuration."""
        if self._initialized:
            return
            
        self._load_config()
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
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            Dict containing the current Redis configuration
        """
        return self._config.copy()
    
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