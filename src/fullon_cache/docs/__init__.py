"""Documentation module for Fullon Cache.

This module provides comprehensive guides and references accessible directly
from Python, making the library fully self-documenting.

Example:
    from fullon_cache.docs import quickstart, api_reference
    print(quickstart.GUIDE)
    print(api_reference.TICK_CACHE)
"""

from . import api_reference, caching_guide, migration, performance, quickstart, testing_guide, model_usage

__all__ = [
    'quickstart',
    'api_reference',
    'caching_guide',
    'testing_guide',
    'migration',
    'performance',
    'model_usage',
    'get_all_docs',
]


def get_all_docs() -> dict:
    """Get all documentation in a structured format.
    
    Returns:
        Dict mapping doc names to their content
        
    Example:
        docs = get_all_docs()
        for name, content in docs.items():
            print(f"\\n=== {name} ===\\n{content}")
    """
    return {
        'Quick Start': quickstart.GUIDE,
        'API Reference': api_reference.get_all_references(),
        'Caching Guide': caching_guide.GUIDE,
        'Testing Guide': testing_guide.GUIDE,
        'Migration Guide': migration.GUIDE,
        'Performance Guide': performance.GUIDE,
        'Model Usage Guide': model_usage.MODEL_USAGE_GUIDE,
        'Type Safety Guide': model_usage.TYPE_SAFETY_GUIDE,
        'Performance Optimization': model_usage.PERFORMANCE_GUIDE,
    }
