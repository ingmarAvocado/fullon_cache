"""Examples module for Fullon Cache.

This module provides runnable examples demonstrating various cache operations.

Example:
    from fullon_cache.examples import basic_usage
    import asyncio
    
    # Run basic examples
    asyncio.run(basic_usage.main())
"""

from . import basic_usage, bot_coordination, performance_test, pubsub_example, queue_patterns

__all__ = [
    'basic_usage',
    'pubsub_example',
    'queue_patterns',
    'bot_coordination',
    'performance_test',
    'get_all_examples',
]


def get_all_examples() -> dict:
    """Get descriptions of all available examples.
    
    Returns:
        Dict mapping example names to their descriptions
    """
    return {
        'basic_usage': 'Basic cache operations - get/set/delete',
        'pubsub_example': 'Real-time ticker updates with pub/sub',
        'queue_patterns': 'Order and trade queue management',
        'bot_coordination': 'Multi-bot coordination and locking',
        'performance_test': 'Benchmark cache performance',
    }
