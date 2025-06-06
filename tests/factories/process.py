"""Process factory for test data generation."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fullon_cache.process_cache import ProcessType, ProcessStatus


class ProcessFactory:
    """Factory for creating test process data."""
    
    def __init__(self):
        self._counter = 0
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Create process data with defaults.
        
        Args:
            **kwargs: Override any default values
            
        Returns:
            Dictionary with process data
            
        Example:
            factory = ProcessFactory()
            process = factory.create(
                process_type=ProcessType.BOT,
                component="arbitrage_bot_1"
            )
        """
        self._counter += 1
        
        defaults = {
            "process_type": ProcessType.BOT,
            "component": f"test_component_{self._counter}",
            "params": {"test": True, "counter": self._counter},
            "message": "Test process",
            "status": ProcessStatus.RUNNING,
        }
        
        # Handle string types
        if "process_type" in kwargs and isinstance(kwargs["process_type"], str):
            kwargs["process_type"] = ProcessType(kwargs["process_type"])
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = ProcessStatus(kwargs["status"])
        
        # Merge with provided kwargs
        result = defaults.copy()
        result.update(kwargs)
        
        return result
    
    def create_bot_process(self, 
                          bot_name: str,
                          symbol: str = "BTC/USDT",
                          exchange: str = "binance",
                          **kwargs) -> Dict[str, Any]:
        """Create a bot process.
        
        Args:
            bot_name: Name of the bot
            symbol: Trading symbol
            exchange: Exchange name
            **kwargs: Additional overrides
            
        Returns:
            Bot process data
        """
        return self.create(
            process_type=ProcessType.BOT,
            component=bot_name,
            params={
                "symbol": symbol,
                "exchange": exchange,
                "strategy": kwargs.pop("strategy", "grid"),
                "active": True
            },
            message=f"Bot {bot_name} started on {exchange}:{symbol}",
            **kwargs
        )
    
    def create_crawler_process(self,
                              crawler_type: str = "tick",
                              exchanges: list = None,
                              **kwargs) -> Dict[str, Any]:
        """Create a crawler process.
        
        Args:
            crawler_type: Type of crawler (tick, ohlcv, etc.)
            exchanges: List of exchanges to crawl
            **kwargs: Additional overrides
            
        Returns:
            Crawler process data
        """
        if exchanges is None:
            exchanges = ["binance", "kraken"]
            
        return self.create(
            process_type=ProcessType.CRAWLER,
            component=f"{crawler_type}_crawler",
            params={
                "crawler_type": crawler_type,
                "exchanges": exchanges,
                "interval": kwargs.pop("interval", 1),
                "symbols": kwargs.pop("symbols", ["BTC/USDT", "ETH/USDT"])
            },
            message=f"Crawler {crawler_type} monitoring {len(exchanges)} exchanges",
            **kwargs
        )
    
    def create_service_process(self,
                              service_type: str,
                              **kwargs) -> Dict[str, Any]:
        """Create a service process.
        
        Args:
            service_type: Type of service
            **kwargs: Additional overrides
            
        Returns:
            Service process data
        """
        process_type_map = {
            "bot_status": ProcessType.BOT_STATUS_SERVICE,
            "user_trades": ProcessType.USER_TRADES_SERVICE,
            "account": ProcessType.ACCOUNT,
            "order": ProcessType.ORDER,
        }
        
        process_type = process_type_map.get(service_type, ProcessType.BOT_STATUS_SERVICE)
        
        return self.create(
            process_type=process_type,
            component=f"{service_type}_service",
            params={
                "service_type": service_type,
                "workers": kwargs.pop("workers", 4),
                "batch_size": kwargs.pop("batch_size", 100)
            },
            message=f"{service_type} service initialized",
            **kwargs
        )
    
    def create_error_process(self,
                            error_message: str = "Process encountered an error",
                            **kwargs) -> Dict[str, Any]:
        """Create a process in error state.
        
        Args:
            error_message: Error message
            **kwargs: Additional overrides
            
        Returns:
            Error process data
        """
        return self.create(
            status=ProcessStatus.ERROR,
            message=error_message,
            params={
                "error": True,
                "error_time": datetime.now(timezone.utc).isoformat(),
                "error_details": kwargs.pop("error_details", "Test error")
            },
            **kwargs
        )
    
    def create_stale_process(self, minutes_old: int = 60, **kwargs) -> Dict[str, Any]:
        """Create a stale process.
        
        Args:
            minutes_old: How many minutes old the process should be
            **kwargs: Additional overrides
            
        Returns:
            Stale process data
        """
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
        
        return self.create(
            status=ProcessStatus.IDLE,
            message="Process is stale",
            params={
                "last_heartbeat": old_time.isoformat(),
                "stale": True
            },
            **kwargs
        )
    
    def create_batch(self, 
                    count: int,
                    process_types: list = None,
                    statuses: list = None) -> list:
        """Create multiple processes.
        
        Args:
            count: Number of processes to create
            process_types: List of process types to cycle through
            statuses: List of statuses to cycle through
            
        Returns:
            List of process dictionaries
        """
        if process_types is None:
            process_types = [ProcessType.BOT, ProcessType.CRAWLER, ProcessType.ORDER]
        
        if statuses is None:
            statuses = [ProcessStatus.RUNNING, ProcessStatus.IDLE, ProcessStatus.PROCESSING]
        
        processes = []
        
        for i in range(count):
            process_type = process_types[i % len(process_types)]
            status = statuses[i % len(statuses)]
            
            process = self.create(
                process_type=process_type,
                component=f"{process_type.value}_component_{i}",
                status=status,
                params={
                    "index": i,
                    "batch": True
                },
                message=f"Batch process {i} of {count}"
            )
            processes.append(process)
        
        return processes