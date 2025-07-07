"""Tests for the utils module."""



def test_utils_import():
    """Test that utils module can be imported."""
    from fullon_cache import utils

    # Test that __all__ is defined
    assert hasattr(utils, '__all__')
    assert isinstance(utils.__all__, list)
    assert utils.__all__ == []
