"""Test that all modules can be imported successfully."""



class TestImports:
    """Test module imports."""

    def test_import_base_cache(self):
        """Test importing BaseCache."""
        from fullon_cache import BaseCache
        assert BaseCache is not None

    def test_import_process_cache(self):
        """Test importing ProcessCache."""
        from fullon_cache import ProcessCache
        from fullon_cache.process_cache import ProcessStatus, ProcessType
        assert ProcessCache is not None
        assert ProcessType is not None
        assert ProcessStatus is not None

    def test_import_tick_cache(self):
        """Test importing TickCache."""
        from fullon_cache import TickCache
        assert TickCache is not None

    def test_import_orders_cache(self):
        """Test importing OrdersCache."""
        from fullon_cache import OrdersCache
        assert OrdersCache is not None

    def test_import_trades_cache(self):
        """Test importing TradesCache."""
        from fullon_cache import TradesCache
        assert TradesCache is not None



    def test_import_account_cache(self):
        """Test importing AccountCache."""
        from fullon_cache import AccountCache
        assert AccountCache is not None

    def test_import_bot_cache(self):
        """Test importing BotCache."""
        from fullon_cache import BotCache
        assert BotCache is not None

    def test_import_ohlcv_cache(self):
        """Test importing OHLCVCache."""
        from fullon_cache import OHLCVCache
        assert OHLCVCache is not None

    def test_import_exceptions(self):
        """Test importing exceptions."""
        from fullon_cache.exceptions import CacheError, ConnectionError, StreamError
        assert CacheError is not None
        assert ConnectionError is not None
        assert StreamError is not None

    def test_import_examples(self):
        """Test importing examples module."""
        from fullon_cache import examples
        assert examples is not None
        assert hasattr(examples, 'get_all_examples')
        # Note: basic_usage was removed as it was legacy code

    def test_main_package_exports(self):
        """Test that main package exports all expected items."""
        import fullon_cache

        expected_exports = [
            'BaseCache',
            'ProcessCache',
            'TickCache',
            'OrdersCache',
            'TradesCache',
            'AccountCache',
            'BotCache',
            'OHLCVCache',
            'CacheError',
            'ConnectionError',
            'StreamError',
            'examples',
            # Note: 'docs' removed as it was legacy
        ]

        for export in expected_exports:
            assert hasattr(fullon_cache, export), f"Missing export: {export}"

    def test_version_info(self):
        """Test version information."""
        import fullon_cache
        assert hasattr(fullon_cache, '__version__')
        assert fullon_cache.__version__ == '0.4.0'
