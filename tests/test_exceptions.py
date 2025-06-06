"""Tests for fullon_cache exceptions module."""

import pytest
from fullon_cache.exceptions import (
    CacheError, ConnectionError, SerializationError, KeyNotFoundError,
    ConfigurationError, StreamError, PubSubError, LockError
)


class TestCacheError:
    """Test the base CacheError exception."""
    
    def test_basic_exception(self):
        """Test basic exception creation and message."""
        error = CacheError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)
    
    def test_inheritance(self):
        """Test that CacheError inherits from Exception."""
        error = CacheError("test")
        assert isinstance(error, Exception)
        assert type(error).__name__ == "CacheError"


class TestConnectionError:
    """Test the ConnectionError exception."""
    
    def test_basic_creation(self):
        """Test creating ConnectionError with just message."""
        error = ConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.host is None
        assert error.port is None
        assert error.original_error is None
    
    def test_with_host_and_port(self):
        """Test creating ConnectionError with host and port."""
        error = ConnectionError("Connection failed", host="localhost", port=6379)
        assert str(error) == "Connection failed"
        assert error.host == "localhost"
        assert error.port == 6379
        assert error.original_error is None
    
    def test_with_original_error(self):
        """Test creating ConnectionError with original error."""
        original = RuntimeError("Socket timeout")
        error = ConnectionError("Connection failed", original_error=original)
        assert str(error) == "Connection failed"
        assert error.original_error is original
        assert isinstance(error.original_error, RuntimeError)
    
    def test_full_attributes(self):
        """Test creating ConnectionError with all attributes."""
        original = OSError("Connection refused")
        error = ConnectionError(
            "Redis connection failed",
            host="redis.example.com",
            port=6380,
            original_error=original
        )
        assert str(error) == "Redis connection failed"
        assert error.host == "redis.example.com"
        assert error.port == 6380
        assert error.original_error is original
    
    def test_inheritance(self):
        """Test that ConnectionError inherits from CacheError."""
        error = ConnectionError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestSerializationError:
    """Test the SerializationError exception."""
    
    def test_basic_creation(self):
        """Test creating SerializationError with just message."""
        error = SerializationError("Failed to serialize")
        assert str(error) == "Failed to serialize"
        assert error.data_type is None
        assert error.operation is None
    
    def test_with_data_type(self):
        """Test creating SerializationError with data type."""
        error = SerializationError("Failed to serialize", data_type="OrderData")
        assert str(error) == "Failed to serialize"
        assert error.data_type == "OrderData"
        assert error.operation is None
    
    def test_with_operation(self):
        """Test creating SerializationError with operation."""
        error = SerializationError("Failed to process", operation="deserialize")
        assert str(error) == "Failed to process"
        assert error.data_type is None
        assert error.operation == "deserialize"
    
    def test_full_attributes(self):
        """Test creating SerializationError with all attributes."""
        error = SerializationError(
            "JSON encoding failed",
            data_type="TickerData",
            operation="serialize"
        )
        assert str(error) == "JSON encoding failed"
        assert error.data_type == "TickerData"
        assert error.operation == "serialize"
    
    def test_inheritance(self):
        """Test that SerializationError inherits from CacheError."""
        error = SerializationError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestKeyNotFoundError:
    """Test the KeyNotFoundError exception."""
    
    def test_creation(self):
        """Test creating KeyNotFoundError."""
        error = KeyNotFoundError("ticker:binance:BTCUSDT")
        assert str(error) == "Key not found: ticker:binance:BTCUSDT"
        assert error.key == "ticker:binance:BTCUSDT"
    
    def test_with_different_keys(self):
        """Test KeyNotFoundError with different key formats."""
        keys = [
            "simple_key",
            "namespace:key",
            "deep:nested:key:structure",
            "key_with_special_chars!@#",
            ""  # empty key
        ]
        
        for key in keys:
            error = KeyNotFoundError(key)
            assert str(error) == f"Key not found: {key}"
            assert error.key == key
    
    def test_inheritance(self):
        """Test that KeyNotFoundError inherits from CacheError."""
        error = KeyNotFoundError("test_key")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test the ConfigurationError exception."""
    
    def test_basic_creation(self):
        """Test creating ConfigurationError with just message."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert error.config_key is None
    
    def test_with_config_key(self):
        """Test creating ConfigurationError with config key."""
        error = ConfigurationError("Missing value", config_key="REDIS_HOST")
        assert str(error) == "Missing value"
        assert error.config_key == "REDIS_HOST"
    
    def test_various_config_scenarios(self):
        """Test ConfigurationError for various configuration scenarios."""
        scenarios = [
            ("Missing required environment variable", "REDIS_PASSWORD"),
            ("Invalid port number", "REDIS_PORT"),
            ("Malformed connection string", "REDIS_URL"),
            ("Unsupported cache backend", "CACHE_BACKEND"),
        ]
        
        for message, key in scenarios:
            error = ConfigurationError(message, config_key=key)
            assert str(error) == message
            assert error.config_key == key
    
    def test_inheritance(self):
        """Test that ConfigurationError inherits from CacheError."""
        error = ConfigurationError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestStreamError:
    """Test the StreamError exception."""
    
    def test_basic_creation(self):
        """Test creating StreamError with just message."""
        error = StreamError("Stream operation failed")
        assert str(error) == "Stream operation failed"
        assert error.stream_key is None
        assert error.operation is None
    
    def test_with_stream_key(self):
        """Test creating StreamError with stream key."""
        error = StreamError("Stream not found", stream_key="orders:queue")
        assert str(error) == "Stream not found"
        assert error.stream_key == "orders:queue"
        assert error.operation is None
    
    def test_with_operation(self):
        """Test creating StreamError with operation."""
        error = StreamError("Operation failed", operation="XREAD")
        assert str(error) == "Operation failed"
        assert error.stream_key is None
        assert error.operation == "XREAD"
    
    def test_full_attributes(self):
        """Test creating StreamError with all attributes."""
        error = StreamError(
            "Failed to add to stream",
            stream_key="trades:pending",
            operation="XADD"
        )
        assert str(error) == "Failed to add to stream"
        assert error.stream_key == "trades:pending"
        assert error.operation == "XADD"
    
    def test_various_operations(self):
        """Test StreamError with various Redis Stream operations."""
        operations = ["XADD", "XREAD", "XRANGE", "XDEL", "XTRIM", "XGROUP"]
        
        for op in operations:
            error = StreamError("Operation error", operation=op)
            assert error.operation == op
    
    def test_inheritance(self):
        """Test that StreamError inherits from CacheError."""
        error = StreamError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestPubSubError:
    """Test the PubSubError exception."""
    
    def test_basic_creation(self):
        """Test creating PubSubError with just message."""
        error = PubSubError("Publish failed")
        assert str(error) == "Publish failed"
        assert error.channel is None
    
    def test_with_channel(self):
        """Test creating PubSubError with channel."""
        error = PubSubError("Subscribe failed", channel="ticker:updates")
        assert str(error) == "Subscribe failed"
        assert error.channel == "ticker:updates"
    
    def test_various_channels(self):
        """Test PubSubError with various channel names."""
        channels = [
            "ticker:binance:*",
            "orders:filled",
            "system:alerts",
            "bot:status:changes",
            "market:data:BTC/USDT"
        ]
        
        for channel in channels:
            error = PubSubError("Channel error", channel=channel)
            assert error.channel == channel
    
    def test_inheritance(self):
        """Test that PubSubError inherits from CacheError."""
        error = PubSubError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestLockError:
    """Test the LockError exception."""
    
    def test_basic_creation(self):
        """Test creating LockError with just message."""
        error = LockError("Lock acquisition failed")
        assert str(error) == "Lock acquisition failed"
        assert error.lock_key is None
        assert error.holder is None
    
    def test_with_lock_key(self):
        """Test creating LockError with lock key."""
        error = LockError("Lock exists", lock_key="bot:binance:BTCUSDT")
        assert str(error) == "Lock exists"
        assert error.lock_key == "bot:binance:BTCUSDT"
        assert error.holder is None
    
    def test_with_holder(self):
        """Test creating LockError with holder."""
        error = LockError("Lock held by another", holder="bot_123")
        assert str(error) == "Lock held by another"
        assert error.lock_key is None
        assert error.holder == "bot_123"
    
    def test_full_attributes(self):
        """Test creating LockError with all attributes."""
        error = LockError(
            "Cannot acquire lock",
            lock_key="exchange:kraken:lock",
            holder="bot_456"
        )
        assert str(error) == "Cannot acquire lock"
        assert error.lock_key == "exchange:kraken:lock"
        assert error.holder == "bot_456"
    
    def test_various_lock_scenarios(self):
        """Test LockError for various locking scenarios."""
        scenarios = [
            ("Lock timeout", "resource:1", "process_A"),
            ("Deadlock detected", "shared:resource", "process_B"),
            ("Lock expired", "temp:lock", None),
            ("Invalid lock token", None, "unknown"),
        ]
        
        for message, key, holder in scenarios:
            error = LockError(message, lock_key=key, holder=holder)
            assert str(error) == message
            assert error.lock_key == key
            assert error.holder == holder
    
    def test_inheritance(self):
        """Test that LockError inherits from CacheError."""
        error = LockError("test")
        assert isinstance(error, CacheError)
        assert isinstance(error, Exception)


class TestExceptionHandling:
    """Test exception handling patterns."""
    
    def test_catching_specific_exceptions(self):
        """Test catching specific cache exceptions."""
        # Test catching ConnectionError
        try:
            raise ConnectionError("Redis down", host="localhost", port=6379)
        except ConnectionError as e:
            assert e.host == "localhost"
            assert e.port == 6379
        
        # Test catching KeyNotFoundError
        try:
            raise KeyNotFoundError("missing:key")
        except KeyNotFoundError as e:
            assert e.key == "missing:key"
    
    def test_catching_base_exception(self):
        """Test catching all cache errors with base CacheError."""
        exceptions = [
            ConnectionError("conn error"),
            SerializationError("serial error"),
            KeyNotFoundError("key"),
            ConfigurationError("config error"),
            StreamError("stream error"),
            PubSubError("pubsub error"),
            LockError("lock error")
        ]
        
        for exc in exceptions:
            try:
                raise exc
            except CacheError as e:
                assert isinstance(e, CacheError)
                # Verify we caught the right exception
                assert type(e).__name__ in [
                    "ConnectionError", "SerializationError", "KeyNotFoundError",
                    "ConfigurationError", "StreamError", "PubSubError", "LockError"
                ]
    
    def test_exception_chaining(self):
        """Test exception chaining for better error context."""
        try:
            try:
                # Simulate a low-level error
                raise OSError("Network unreachable")
            except OSError as original:
                # Wrap in our custom exception
                raise ConnectionError(
                    "Failed to connect to Redis",
                    host="redis.example.com",
                    port=6379,
                    original_error=original
                ) from original
        except ConnectionError as e:
            assert e.original_error is not None
            assert isinstance(e.original_error, OSError)
            assert str(e.original_error) == "Network unreachable"
            assert e.__cause__ is not None  # Python's exception chaining
    
    def test_exception_context_preservation(self):
        """Test that exception context is preserved properly."""
        # Test SerializationError with context
        try:
            data = {"invalid": object()}  # object() can't be JSON serialized
            raise SerializationError(
                "Cannot serialize object",
                data_type=str(type(data)),
                operation="serialize"
            )
        except SerializationError as e:
            assert "dict" in e.data_type
            assert e.operation == "serialize"
        
        # Test StreamError with context
        try:
            raise StreamError(
                "Stream trimming failed",
                stream_key="orders:completed",
                operation="XTRIM"
            )
        except StreamError as e:
            assert e.stream_key == "orders:completed"
            assert e.operation == "XTRIM"


class TestExceptionEdgeCases:
    """Test edge cases for exception handling."""
    
    def test_empty_strings(self):
        """Test exceptions with empty string attributes."""
        error1 = ConnectionError("", host="", port=0)
        assert str(error1) == ""
        assert error1.host == ""
        assert error1.port == 0
        
        error2 = KeyNotFoundError("")
        assert str(error2) == "Key not found: "
        assert error2.key == ""
    
    def test_none_values(self):
        """Test exceptions with None values."""
        error = ConnectionError("Error", host=None, port=None, original_error=None)
        assert error.host is None
        assert error.port is None
        assert error.original_error is None
    
    def test_unicode_handling(self):
        """Test exceptions with unicode characters."""
        unicode_key = "ticker:币安:比特币"
        error = KeyNotFoundError(unicode_key)
        assert error.key == unicode_key
        assert unicode_key in str(error)
    
    def test_very_long_messages(self):
        """Test exceptions with very long messages."""
        long_message = "Error: " + "x" * 10000
        error = CacheError(long_message)
        assert str(error) == long_message
    
    def test_special_characters(self):
        """Test exceptions with special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        error = ConfigurationError(special_chars, config_key=special_chars)
        assert str(error) == special_chars
        assert error.config_key == special_chars


class TestExceptionUsagePatterns:
    """Test common usage patterns for exceptions."""
    
    def test_connection_retry_pattern(self):
        """Test pattern for retrying on connection errors."""
        attempts = []
        max_retries = 3
        
        for i in range(max_retries):
            try:
                attempts.append(i)
                if i < max_retries - 1:
                    raise ConnectionError(
                        f"Attempt {i+1} failed",
                        host="localhost",
                        port=6379
                    )
                # Success on last attempt
                break
            except ConnectionError as e:
                if i == max_retries - 1:
                    # Re-raise on last attempt
                    raise
        
        assert len(attempts) == max_retries
    
    def test_fallback_pattern(self):
        """Test pattern for fallback on cache miss."""
        cache_hit = False
        
        try:
            raise KeyNotFoundError("cache:user:123")
        except KeyNotFoundError:
            # Fallback to database
            cache_hit = False
        
        assert cache_hit is False
    
    def test_error_aggregation_pattern(self):
        """Test pattern for aggregating multiple errors."""
        errors = []
        
        operations = [
            ("op1", ConnectionError("Connection 1 failed")),
            ("op2", SerializationError("Serialization failed")),
            ("op3", StreamError("Stream failed")),
        ]
        
        for op_name, error in operations:
            try:
                raise error
            except CacheError as e:
                errors.append((op_name, type(e).__name__, str(e)))
        
        assert len(errors) == 3
        assert errors[0] == ("op1", "ConnectionError", "Connection 1 failed")
        assert errors[1] == ("op2", "SerializationError", "Serialization failed")
        assert errors[2] == ("op3", "StreamError", "Stream failed")