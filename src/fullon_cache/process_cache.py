"""Process monitoring and tracking cache.

This module provides functionality to track and monitor various system processes
including bots, crawlers, order processors, and other components.
"""

import json
from fullon_log import get_component_logger
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from .base_cache import BaseCache
from .exceptions import CacheError

logger = get_component_logger("fullon.cache.process")


class ProcessType(str, Enum):
    """Valid process types in the system."""
    TICK = "tick"
    OHLCV = "ohlcv"
    BOT = "bot"
    ACCOUNT = "account"
    ORDER = "order"
    BOT_STATUS_SERVICE = "bot_status_service"
    CRAWLER = "crawler"
    USER_TRADES_SERVICE = "user_trades_service"


class ProcessStatus(str, Enum):
    """Process status states."""
    STARTING = "starting"
    RUNNING = "running"
    PROCESSING = "processing"
    IDLE = "idle"
    ERROR = "error"
    STOPPED = "stopped"


class ProcessCache:
    """Cache for process monitoring and tracking.
    
    This cache tracks various system processes, their status, and health.
    Processes are identified by a unique ID and include timestamp, parameters,
    and status messages.
    
    Features:
        - Process registration and tracking
        - Status updates with timestamps
        - Time-based filtering
        - Process health monitoring
        - Component-based organization
        
    Example:
        cache = ProcessCache()
        
        # Register a new process
        process_id = await cache.register_process(
            process_type=ProcessType.BOT,
            component="arbitrage_bot_1",
            params={"exchanges": ["binance", "kraken"]},
            message="Started arbitrage bot"
        )
        
        # Update process status
        await cache.update_process(
            process_id=process_id,
            status=ProcessStatus.PROCESSING,
            message="Found arbitrage opportunity"
        )
        
        # Get active processes
        active = await cache.get_active_processes(
            process_type=ProcessType.BOT,
            since_minutes=5
        )
    """

    def __init__(self):
        """Initialize the process cache."""
        self._cache = BaseCache(key_prefix="process")

    async def __aenter__(self):
        """Enter async context manager."""
        await self._cache.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager with cleanup."""
        return await self._cache.__aexit__(exc_type, exc_val, exc_tb)

    async def close(self):
        """Close the cache and cleanup resources."""
        await self._cache.close()

    async def register_process(
        self,
        process_type: ProcessType,
        component: str,
        params: dict[str, Any] | None = None,
        message: str | None = None,
        status: ProcessStatus = ProcessStatus.STARTING
    ) -> str:
        """Register a new process.
        
        Args:
            process_type: Type of process (bot, crawler, etc.)
            component: Component identifier (e.g., "arbitrage_bot_1")
            params: Process parameters/configuration
            message: Initial status message
            status: Initial process status
            
        Returns:
            Unique process ID
            
        Raises:
            CacheError: If registration fails
            
        Example:
            process_id = await cache.register_process(
                process_type=ProcessType.BOT,
                component="market_maker_1",
                params={"symbol": "BTC/USDT", "spread": 0.001},
                message="Starting market maker"
            )
        """
        # Generate unique process ID
        timestamp = datetime.now(UTC)
        process_id = f"{process_type.value}:{component}:{timestamp.timestamp()}"

        # Process data
        process_data = {
            "process_id": process_id,
            "process_type": process_type.value,
            "component": component,
            "params": params or {},
            "status": status.value,
            "message": message or f"Process {component} registered",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
            "heartbeat": timestamp.isoformat(),
        }

        try:
            # Store process data
            await self._cache.set_json(
                f"data:{process_id}",
                process_data,
                ttl=86400  # 24 hour TTL
            )

            # Add to active set
            await self._cache.hset(
                f"active:{process_type.value}",
                process_id,
                timestamp.isoformat()
            )

            # Add to component index
            await self._cache.hset(
                "components",
                component,
                process_id
            )

            logger.debug(f"Registered process: {process_id}")
            return process_id

        except Exception as e:
            logger.error(f"Failed to register process: {e}")
            raise CacheError(f"Failed to register process: {str(e)}")

    async def update_process(
        self,
        process_id: str,
        status: ProcessStatus | None = None,
        message: str | None = None,
        params: dict[str, Any] | None = None,
        heartbeat: bool = True
    ) -> bool:
        """Update process status and information.
        
        Args:
            process_id: Process ID to update
            status: New status (optional)
            message: Status message (optional)
            params: Updated parameters (optional)
            heartbeat: Update heartbeat timestamp
            
        Returns:
            True if updated successfully
            
        Example:
            success = await cache.update_process(
                process_id=process_id,
                status=ProcessStatus.PROCESSING,
                message="Processing batch 1/10"
            )
        """
        # Get current process data
        process_data = await self._cache.get_json(f"data:{process_id}")
        if not process_data:
            logger.warning(f"Process not found: {process_id}")
            return False

        # Update fields
        timestamp = datetime.now(UTC)
        process_data["updated_at"] = timestamp.isoformat()

        if heartbeat:
            process_data["heartbeat"] = timestamp.isoformat()

        if status:
            process_data["status"] = status.value

        if message:
            process_data["message"] = message

        if params:
            process_data["params"].update(params)

        try:
            # Save updated data
            await self._cache.set_json(
                f"data:{process_id}",
                process_data,
                ttl=86400  # Reset TTL
            )

            # Update active timestamp
            await self._cache.hset(
                f"active:{process_data['process_type']}",
                process_id,
                timestamp.isoformat()
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update process {process_id}: {e}")
            return False

    async def get_process(self, process_id: str) -> dict[str, Any] | None:
        """Get process information.
        
        Args:
            process_id: Process ID
            
        Returns:
            Process data dictionary or None if not found
        """
        return await self._cache.get_json(f"data:{process_id}")

    async def get_active_processes(
        self,
        process_type: ProcessType | None = None,
        component: str | None = None,
        since_minutes: int = 5,
        include_heartbeat_check: bool = True
    ) -> list[dict[str, Any]]:
        """Get active processes filtered by criteria.
        
        Args:
            process_type: Filter by process type
            component: Filter by component name
            since_minutes: Only include processes active in last N minutes
            include_heartbeat_check: Check heartbeat for liveness
            
        Returns:
            List of active process data dictionaries
            
        Example:
            # Get all active bots
            bots = await cache.get_active_processes(
                process_type=ProcessType.BOT,
                since_minutes=5
            )
            
            # Get specific component
            processes = await cache.get_active_processes(
                component="arbitrage_bot_1"
            )
        """
        active_processes = []
        cutoff_time = datetime.now(UTC) - timedelta(minutes=since_minutes)

        # Determine which process types to check
        if process_type:
            types_to_check = [process_type]
        else:
            types_to_check = list(ProcessType)

        # Check each process type
        for ptype in types_to_check:
            # Get all processes of this type
            processes = await self._cache.hgetall(f"active:{ptype.value}")

            for process_id, timestamp_str in processes.items():
                # Check if process is recent enough
                try:
                    last_update = datetime.fromisoformat(timestamp_str)
                    if last_update < cutoff_time:
                        continue
                except (ValueError, TypeError):
                    continue

                # Get full process data
                process_data = await self.get_process(process_id)
                if not process_data:
                    continue

                # Apply filters
                if component and process_data.get("component") != component:
                    continue

                # Check heartbeat if requested
                if include_heartbeat_check:
                    try:
                        heartbeat = datetime.fromisoformat(process_data.get("heartbeat", ""))
                        if heartbeat < cutoff_time:
                            # Mark as potentially dead
                            process_data["_heartbeat_stale"] = True
                        else:
                            process_data["_heartbeat_stale"] = False
                    except (ValueError, TypeError, KeyError):
                        process_data["_heartbeat_stale"] = True

                active_processes.append(process_data)

        # Sort by updated_at descending
        active_processes.sort(
            key=lambda p: p.get("updated_at", ""),
            reverse=True
        )

        return active_processes

    async def stop_process(self, process_id: str, message: str | None = None) -> bool:
        """Mark a process as stopped.
        
        Args:
            process_id: Process ID to stop
            message: Optional stop message
            
        Returns:
            True if stopped successfully
        """
        process_data = await self.get_process(process_id)
        if not process_data:
            return False

        # Update status to stopped
        await self.update_process(
            process_id=process_id,
            status=ProcessStatus.STOPPED,
            message=message or "Process stopped",
            heartbeat=False
        )

        # Remove from active set
        await self._cache.hdel(
            f"active:{process_data['process_type']}",
            process_id
        )

        # Remove from component index
        await self._cache.hdel("components", process_data["component"])

        logger.debug(f"Stopped process: {process_id}")
        return True

    async def cleanup_stale_processes(self, stale_minutes: int = 30) -> int:
        """Clean up stale processes that haven't updated recently.
        
        Args:
            stale_minutes: Consider process stale after N minutes
            
        Returns:
            Number of processes cleaned up
        """
        cleaned = 0
        cutoff_time = datetime.now(UTC) - timedelta(minutes=stale_minutes)

        for process_type in ProcessType:
            processes = await self._cache.hgetall(f"active:{process_type.value}")

            for process_id, timestamp_str in processes.items():
                try:
                    last_update = datetime.fromisoformat(timestamp_str)
                    if last_update < cutoff_time:
                        # Check heartbeat
                        process_data = await self.get_process(process_id)
                        if process_data:
                            heartbeat = datetime.fromisoformat(
                                process_data.get("heartbeat", timestamp_str)
                            )
                            if heartbeat < cutoff_time:
                                # Process is stale
                                await self.stop_process(
                                    process_id,
                                    f"Process stale for {stale_minutes} minutes"
                                )
                                cleaned += 1
                except (ValueError, TypeError):
                    # Invalid timestamp, remove
                    await self._cache.hdel(f"active:{process_type.value}", process_id)
                    cleaned += 1

        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} stale processes")

        return cleaned

    async def get_process_history(
        self,
        component: str,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get process history for a component.
        
        Args:
            component: Component name
            limit: Maximum number of records
            
        Returns:
            List of historical process data
        """
        # This would typically query from a database
        # For now, return empty as we only track active processes
        return []

    async def get_component_status(self, component: str) -> dict[str, Any] | None:
        """Get current status of a component.
        
        Args:
            component: Component name
            
        Returns:
            Current process data for component or None
        """
        # Get process ID from component index
        process_id = await self._cache.hget("components", component)
        if not process_id:
            return None

        return await self.get_process(process_id)

    async def get_system_health(self) -> dict[str, Any]:
        """Get overall system health based on process status.
        
        Returns:
            Dictionary with health metrics
        """
        health = {
            "healthy": True,
            "total_processes": 0,
            "by_type": {},
            "by_status": {},
            "stale_processes": 0,
            "error_processes": 0,
        }

        # Get all active processes
        processes = await self.get_active_processes(
            since_minutes=60,  # Check last hour
            include_heartbeat_check=True
        )

        health["total_processes"] = len(processes)

        # Count by type and status
        for process in processes:
            # By type
            ptype = process.get("process_type", "unknown")
            health["by_type"][ptype] = health["by_type"].get(ptype, 0) + 1

            # By status
            status = process.get("status", "unknown")
            health["by_status"][status] = health["by_status"].get(status, 0) + 1

            # Check for issues
            if process.get("_heartbeat_stale"):
                health["stale_processes"] += 1

            if status == ProcessStatus.ERROR.value:
                health["error_processes"] += 1

        # Determine overall health
        if health["error_processes"] > 0 or health["stale_processes"] > 0:
            health["healthy"] = False

        return health

    async def broadcast_message(
        self,
        process_type: ProcessType,
        message: str,
        data: dict[str, Any] | None = None
    ) -> int:
        """Broadcast a message to all processes of a type.
        
        This uses pub/sub to send messages to running processes.
        
        Args:
            process_type: Target process type
            message: Message to broadcast
            data: Optional data payload
            
        Returns:
            Number of potential recipients
        """
        channel = f"process:broadcast:{process_type.value}"

        payload = {
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        return await self._cache.publish(channel, json.dumps(payload))

    async def get_metrics(self) -> dict[str, Any]:
        """Get process cache metrics.
        
        Returns:
            Dictionary with cache metrics
        """
        metrics = {
            "total_processes": 0,
            "active_processes": 0,
            "components": 0,
        }

        # Count processes by type
        for process_type in ProcessType:
            count = len(await self._cache.hgetall(f"active:{process_type.value}"))
            metrics[f"active_{process_type.value}"] = count
            metrics["active_processes"] += count

        # Count total components
        metrics["components"] = len(await self._cache.hgetall("components"))

        # Count total process data entries
        process_count = 0
        async for _ in self._cache.scan_keys("data:*"):
            process_count += 1
        metrics["total_processes"] = process_count

        return metrics

    # Legacy methods for backward compatibility

    async def delete_from_top(self, component: str | None = None) -> int:
        """Legacy method: Delete a process entry from the top of the cache.
        
        Args:
            component: The component type to delete. Defaults to None.
            
        Returns:
            Number of deleted entries.
            
        Note:
            This is a legacy method for backward compatibility.
            Use stop_process() for proper process lifecycle management.
        """
        if component:
            # In legacy, this deleted the entire hash
            # We'll interpret this as stopping all processes of a component
            deleted = 0
            processes = await self.get_active_processes(component=component)
            for process in processes:
                if await self.stop_process(process["process_id"]):
                    deleted += 1
            return deleted
        return 0

    async def get_top(self, deltatime: int | None = None, comp: str | None = None) -> list[dict]:
        """Legacy method: Get processes with optional time and component filters.
        
        Args:
            deltatime: Delta time in seconds. If provided, only objects with a timestamp
                      within the past deltatime seconds will be returned.
            comp: Component type to filter on.
            
        Returns:
            List of process dictionaries meeting the filtering criteria.
            
        Note:
            This is a legacy method. Use get_active_processes() for new code.
        """
        rows = []

        # Convert deltatime to minutes for get_active_processes
        if deltatime:
            since_minutes = deltatime / 60
        else:
            since_minutes = 60 * 24  # Default to 24 hours

        # Get processes
        processes = await self.get_active_processes(
            since_minutes=since_minutes,
            include_heartbeat_check=False
        )

        for process in processes:
            # Convert to legacy format
            obj = {
                "type": process["process_type"],
                "key": process["component"],
                "params": process.get("params", {}),
                "message": process.get("message", ""),
                "timestamp": process.get("updated_at", process.get("created_at", ""))
            }

            # Apply filters
            if comp and obj["type"] != comp:
                continue

            rows.append(obj)

        return rows

    async def update_process_legacy(self, tipe: str, key: str, message: str = "") -> bool:
        """Legacy method: Update a process entry in the cache.
        
        Args:
            tipe: The type of process (e.g., "tick").
            key: The key identifying the process (component name).
            message: Optional message to include with the process update.
            
        Returns:
            True if the operation was successful, False otherwise.
            
        Note:
            This is a legacy method signature. It will try to find an existing
            process or create a new one if not found.
        """
        # Find existing process
        component_process = await self.get_component_status(key)

        if component_process:
            # Update existing - use the modern update_process method
            return await self.update_process(
                process_id=component_process["process_id"],
                message=message
            )
        else:
            # Create new process
            logger.warning(f"No record for {tipe}:{key} attempting to create")
            try:
                # Map string type to ProcessType enum
                process_type = ProcessType(tipe)
                process_id = await self.register_process(
                    process_type=process_type,
                    component=key,
                    params={},
                    message=message
                )
                return bool(process_id)
            except ValueError:
                logger.error(f"Invalid process type: {tipe}")
                return False

    async def new_process(
        self,
        tipe: str,
        key: str,
        params: dict[str, Any],
        pid: Any | None = None,
        message: str = ""
    ) -> int:
        """Legacy method: Add a new process entry to the cache.
        
        Args:
            tipe: The type of process (e.g., "tick").
            key: The key identifying the process (component name).
            params: A dictionary containing the process parameters.
            pid: The process ID. Obsolete, ignored.
            message: Optional message to include with the new process.
            
        Returns:
            1 if added successfully, 0 if not.
            
        Note:
            This is a legacy method. Use register_process() for new code.
        """
        try:
            # Map string type to ProcessType enum
            process_type = ProcessType(tipe)
            process_id = await self.register_process(
                process_type=process_type,
                component=key,
                params=params,
                message=message
            )
            return 1 if process_id else 0
        except ValueError:
            logger.error(f"Invalid process type: {tipe}")
            return 0

    async def get_process_legacy(self, tipe: str, key: str) -> dict[str, Any]:
        """Legacy method: Get process information from Redis.
        
        Args:
            tipe: Type of process (e.g. "tick", "ohlcv", "account").
            key: Key identifying the process (component name).
            
        Returns:
            Process information dictionary, or empty dict if not found.
            
        Note:
            This is a legacy method. Use get_process(process_id) or 
            get_component_status(component) for new code.
        """
        # Look up by component
        component_process = await self.get_component_status(key)
        if component_process:
            # Convert to legacy format
            return {
                "params": component_process.get("params", {}),
                "message": component_process.get("message", ""),
                "timestamp": component_process.get("updated_at", "")
            }
        return {}

    async def delete_process(self, tipe: str, key: str = '') -> bool:
        """Legacy method: Delete a process from the cache.
        
        Args:
            tipe: The type of process to delete.
            key: The key identifying the process to delete.
            
        Returns:
            True if the process was deleted, False otherwise.
            
        Note:
            This is a legacy method. Use stop_process() for new code.
        """
        if key:
            # Delete specific process
            component_process = await self.get_component_status(key)
            if component_process:
                return await self.stop_process(component_process["process_id"])
            return False
        else:
            # Delete all processes of type
            deleted = False
            try:
                process_type = ProcessType(tipe)
                processes = await self.get_active_processes(process_type=process_type)
                for process in processes:
                    if await self.stop_process(process["process_id"]):
                        deleted = True
                return deleted
            except ValueError:
                return False
