"""Examples module for Fullon Cache.

This module provides executable CLI tools demonstrating various cache operations.
Each cache class now has its own dedicated example file with comprehensive demonstrations.

Structure:
- Cache-specific examples: example_*_cache.py (recommended for focused testing)
- Legacy multi-purpose examples: basic_usage.py, pubsub_example.py, etc.

Example:
    # Run cache-specific examples (recommended)
    python -m fullon_cache.examples.example_base_cache --operations basic --verbose
    python -m fullon_cache.examples.example_tick_cache --operations pubsub --duration 30
    python -m fullon_cache.examples.example_bot_cache --bots 5 --symbols BTC/USDT,ETH/USDT

    # Run legacy multi-purpose examples
    python -m fullon_cache.examples.basic_usage --operation ticker --verbose
    python -m fullon_cache.examples.pubsub_example --exchanges binance,kraken --duration 30

    # Or run programmatically
    from fullon_cache.examples import example_base_cache
    import asyncio
    # Use example functions directly
"""

# Note: Individual examples are not imported by default to avoid circular imports
# when running examples directly. Import them explicitly when needed:
#
# from fullon_cache.examples import example_account_cache
# from fullon_cache.examples import basic_usage

__all__ = [
    # Cache-specific examples
    "example_account_cache",
    "example_bot_cache",
    "example_tick_cache",
    "example_orders_cache",
    "example_trades_cache",
    "example_process_cache",
    "example_ohlcv_cache",
    # Legacy examples
    "basic_usage",
    "pubsub_example",
    "queue_patterns",
    "bot_coordination",
    "performance_test",
    # Utility functions
    "get_all_examples",
    "get_cache_examples",
    "get_legacy_examples",
]


def get_cache_examples() -> dict:
    """Get cache-specific examples (recommended).

    Returns:
        Dict mapping cache example names to their descriptions and CLI usage
    """
    return {
        "example_account_cache": {
            "description": "AccountCache operations - balances, positions, portfolio management",
            "cli": "python example_account_cache.py --operations all --accounts 5 --verbose",
            "features": [
                "Account balances",
                "Position tracking",
                "Portfolio analysis",
                "Multi-account management",
            ],
        },
        "example_bot_cache": {
            "description": "BotCache operations - coordination, exchange blocking, status tracking",
            "cli": "python example_bot_cache.py --bots 3 --symbols BTC/USDT,ETH/USDT --duration 30",
            "features": [
                "Multi-bot coordination",
                "Exchange blocking",
                "Status tracking",
                "Conflict resolution",
            ],
        },
        "example_tick_cache": {
            "description": "TickCache operations - real-time tickers, pub/sub, price monitoring",
            "cli": "python example_tick_cache.py --operations pubsub "
            + "--symbols BTC/USDT,ETH/USDT --duration 20",
            "features": [
                "Real-time tickers",
                "Pub/sub patterns",
                "Price monitoring",
                "Multi-exchange data",
            ],
        },
        "example_orders_cache": {
            "description": "OrdersCache operations - FIFO queues, "
            + "status tracking, batch processing",
            "cli": "python example_orders_cache.py --operations all --orders 100 --batch-size 20",
            "features": [
                "FIFO order queues",
                "Status tracking",
                "Batch processing",
                "Order lifecycle",
            ],
        },
        "example_trades_cache": {
            "description": "TradesCache operations - trade queues, analytics, bulk processing",
            "cli": "python example_trades_cache.py --operations all --trades 200 --batch-size 50",
            "features": [
                "Trade queues",
                "Status management",
                "Analytics",
                "Bulk processing",
                "Statistics",
            ],
        },
        "example_process_cache": {
            "description": "ProcessCache operations - monitoring, filtering, health tracking",
            "cli": "python example_process_cache.py --operations monitoring "
            + "--duration 30 --verbose",
            "features": [
                "Process monitoring",
                "Time-based filtering",
                "Health tracking",
                "Statistics",
            ],
        },
        "example_ohlcv_cache": {
            "description": "OHLCVCache operations - candlestick data, timeframes, analysis",
            "cli": "python example_ohlcv_cache.py --operations all "
            + "--bars 200 --timeframes 1m,5m,1h",
            "features": [
                "OHLCV data",
                "Multiple timeframes",
                "Data analysis",
                "Performance testing",
            ],
        },
    }


def get_legacy_examples() -> dict:
    """Get legacy multi-purpose examples.

    Returns:
        Dict mapping legacy example names to their descriptions and CLI usage
    """
    return {
        "basic_usage": {
            "description": "Cache operations demo with status reporting",
            "cli": "python basic_usage.py --operation ticker --verbose",
            "features": [
                "Ticker operations",
                "Order management",
                "Account data",
                "Trade processing",
            ],
        },
        "pubsub_example": {
            "description": "Real-time ticker pub/sub with monitoring",
            "cli": "python pubsub_example.py --exchanges binance,kraken --duration 30",
            "features": [
                "Live ticker feeds",
                "Multiple exchanges",
                "Price monitoring",
                "Pub/sub patterns",
            ],
        },
        "queue_patterns": {
            "description": "Order/trade queue management patterns",
            "cli": "python queue_patterns.py --pattern batch --size 100",
            "features": [
                "FIFO operations",
                "Batch processing",
                "Priority queues",
                "Queue statistics",
            ],
        },
        "bot_coordination": {
            "description": "Multi-bot coordination and conflict resolution",
            "cli": "python bot_coordination.py --bots 5 --duration 60",
            "features": [
                "Multi-bot simulation",
                "Exchange blocking",
                "Conflict resolution",
                "Trading efficiency",
            ],
        },
        "performance_test": {
            "description": "Cache performance benchmarking with statistics",
            "cli": "python performance_test.py --iterations 1000 --operations all",
            "features": [
                "Timing statistics",
                "Performance thresholds",
                "Benchmark reports",
                "Regression detection",
            ],
        },
    }


def get_all_examples() -> dict:
    """Get all available examples (cache-specific and legacy).

    Returns:
        Dict mapping all example names to their descriptions and CLI usage
    """
    return {**get_cache_examples(), **get_legacy_examples()}
