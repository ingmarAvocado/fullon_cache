"""Exchange WebSocket error queue management.

This module provides a simple cache for WebSocket error queuing,
inheriting from ProcessCache as per the architecture.
"""

import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .process_cache import ProcessCache
from .exceptions import CacheError

logger = logging.getLogger(__name__)


@dataclass
class Exchange:
    """Exchange data model."""
    id: int
    name: str
    ex_id: str
    cat_ex_id: str
    limits: Dict[str, Any]
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass  
class ExchangeAccount:
    """Exchange account data model."""
    id: int
    exchange_id: int
    user_id: int
    name: str
    api_key: str
    test_mode: bool = False
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExchangeCache(ProcessCache):
    """Cache for exchange WebSocket error management.
    
    This cache provides WebSocket error queue functionality for exchanges,
    allowing services to track and handle WebSocket connection errors.
    
    Inherits from ProcessCache following the architectural hierarchy.
    
    Example:
        cache = ExchangeCache()
        
        # Push error to queue
        await cache.push_ws_error("connection timeout", "binance_1")
        
        # Pop error from queue (blocking)
        error = await cache.pop_ws_error("binance_1", timeout=5)
        if error:
            print(f"WebSocket error: {error}")
    """
    
    def __init__(self):
        """Initialize the exchange cache."""
        super().__init__()
        self._key_prefix = "exchange"
    
    async def push_ws_error(self, error: str, ex_id: str) -> None:
        """Push WebSocket error to queue.
        
        Args:
            error: Error message
            ex_id: Exchange ID
            
        Example:
            await cache.push_ws_error("Connection lost", "binance_1")
        """
        redis_key = f"ws_error:{ex_id}"
        await self._cache.rpush(redis_key, error)
    
    async def pop_ws_error(self, ex_id: str, timeout: int = 0) -> Optional[str]:
        """Pop WebSocket error from queue (blocking).
        
        Args:
            ex_id: Exchange ID
            timeout: Blocking timeout in seconds (0 = no timeout)
            
        Returns:
            Error message or None if timeout
            
        Example:
            # Block until error available
            error = await cache.pop_ws_error("binance_1")
            
            # With timeout
            error = await cache.pop_ws_error("binance_1", timeout=5)
        """
        redis_key = f"ws_error:{ex_id}"
        
        try:
            result = await self._cache.blpop([redis_key], timeout=timeout)
            if result:
                # blpop returns (key, value) tuple
                return result[1]
        except Exception as e:
            logger.error(f"Failed to pop WebSocket error: {e}")
        
        return None