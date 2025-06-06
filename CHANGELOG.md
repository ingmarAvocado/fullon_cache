# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of fullon_cache
- BaseCache with async Redis connection pooling
- ProcessCache for process monitoring and health checks
- TickCache with real-time pub/sub for market data
- OrdersCache using Redis Streams for order queue management
- TradesCache using Redis Streams for trade processing
- ExchangeCache with ORM integration for exchange metadata
- SymbolCache with trading symbol information and validation
- AccountCache for user accounts and position tracking
- BotCache for bot coordination with distributed locking
- OHLCVCache for candlestick data storage and aggregation
- Comprehensive test suite with 100% coverage target
- Self-documenting architecture with detailed docstrings
- Example scripts demonstrating usage patterns
- Type hints throughout for better IDE support
- Async/await support for all operations
- Environment-based configuration via .env files

### Security
- Redis password authentication support
- SSL/TLS connection support
- No sensitive data logging

## [0.1.0] - TBD
- Initial release