"""Custom exceptions for Fullon Cache.

This module defines all custom exceptions used throughout the cache system.
"""



class CacheError(Exception):
    """Base exception for all cache-related errors.
    
    This is the base class for all exceptions raised by the cache system.
    Catch this to handle any cache error generically.
    
    Example:
        try:
            ticker = await cache.get_ticker("binance", "BTC/USDT")
        except CacheError as e:
            logger.error(f"Cache operation failed: {e}")
            # Handle gracefully
    """
    pass


class ConnectionError(CacheError):
    """Raised when Redis connection fails.
    
    This error indicates that the cache system could not connect to Redis
    or lost connection during an operation.
    
    Attributes:
        host: Redis host that failed
        port: Redis port that failed
        original_error: The underlying Redis error
    """

    def __init__(self, message: str, host: str | None = None,
                 port: int | None = None, original_error: Exception | None = None):
        super().__init__(message)
        self.host = host
        self.port = port
        self.original_error = original_error


class SerializationError(CacheError):
    """Raised when data serialization/deserialization fails.
    
    This error occurs when the cache cannot serialize data for storage
    or deserialize data retrieved from Redis.
    
    Attributes:
        data_type: Type of data that failed to serialize
        operation: 'serialize' or 'deserialize'
    """

    def __init__(self, message: str, data_type: str | None = None,
                 operation: str | None = None):
        super().__init__(message)
        self.data_type = data_type
        self.operation = operation


class KeyNotFoundError(CacheError):
    """Raised when a requested key doesn't exist in cache.
    
    This is a specific type of cache miss that indicates the requested
    key was not found in Redis.
    
    Attributes:
        key: The Redis key that was not found
    """

    def __init__(self, key: str):
        super().__init__(f"Key not found: {key}")
        self.key = key


class ConfigurationError(CacheError):
    """Raised when cache configuration is invalid.
    
    This error indicates a problem with the cache configuration,
    such as missing required environment variables.
    
    Attributes:
        config_key: The configuration key that caused the error
    """

    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(message)
        self.config_key = config_key


class StreamError(CacheError):
    """Raised when Redis Stream operations fail.
    
    This error is specific to Redis Streams operations used in
    order and trade queues.
    
    Attributes:
        stream_key: The stream key that caused the error
        operation: The stream operation that failed
    """

    def __init__(self, message: str, stream_key: str | None = None,
                 operation: str | None = None):
        super().__init__(message)
        self.stream_key = stream_key
        self.operation = operation


class PubSubError(CacheError):
    """Raised when Redis Pub/Sub operations fail.
    
    This error is specific to publish/subscribe operations used
    for real-time ticker updates.
    
    Attributes:
        channel: The pub/sub channel that caused the error
    """

    def __init__(self, message: str, channel: str | None = None):
        super().__init__(message)
        self.channel = channel


class LockError(CacheError):
    """Raised when distributed lock operations fail.
    
    This error occurs when acquiring or releasing distributed locks
    for bot coordination fails.
    
    Attributes:
        lock_key: The lock key that caused the error
        holder: The current lock holder if known
    """

    def __init__(self, message: str, lock_key: str | None = None,
                 holder: str | None = None):
        super().__init__(message)
        self.lock_key = lock_key
        self.holder = holder
