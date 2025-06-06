# Contributing to Fullon Cache

Thank you for your interest in contributing to Fullon Cache! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone git@github.com:YOUR_USERNAME/fullon_cache.git
   cd fullon_cache
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Set up pre-commit hooks**
   ```bash
   poetry run pre-commit install
   ```

5. **Start Redis** (required for tests)
   ```bash
   make run-redis
   ```

## Development Workflow

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following the existing patterns
   - Add comprehensive docstrings
   - Include type hints
   - Write tests for new functionality

3. **Run tests**
   ```bash
   make test
   ```

4. **Check code coverage**
   ```bash
   make test-cov
   ```

5. **Format and lint your code**
   ```bash
   make format
   make lint
   ```

6. **Type check**
   ```bash
   make type-check
   ```

## Code Style Guidelines

- Use async/await for all Redis operations
- Follow PEP 8 with the modifications configured in ruff
- Use descriptive variable names
- Add comprehensive docstrings (Google style)
- Include type hints for all function parameters and returns
- Keep functions focused and small
- Use dataclasses for data models
- Use enums for constants

## Testing Guidelines

- Write tests for all new functionality
- Aim for 100% code coverage
- Use real Redis instances (no mocking)
- Group tests in classes by functionality
- Use descriptive test names that explain what is being tested
- Include edge cases and error conditions
- Add performance tests for critical paths (mark with `@pytest.mark.performance`)
- Add integration tests (mark with `@pytest.mark.integration`)

## Documentation

- Update docstrings for any modified functions
- Update README.md if adding new features
- Add examples to the examples module if appropriate
- Update CHANGELOG.md with your changes

## Commit Messages

Follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc)
- `refactor:` Code refactoring
- `test:` Test additions or modifications
- `chore:` Maintenance tasks
- `perf:` Performance improvements

Example:
```
feat: add retry logic to Redis connections

- Add exponential backoff for connection retries
- Configure max retry attempts via environment
- Add tests for retry behavior
```

## Pull Request Process

1. Update your branch with the latest main
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. Ensure all tests pass and coverage is maintained

3. Create a pull request with:
   - Clear title describing the change
   - Description of what was changed and why
   - Link to any related issues
   - Screenshots if applicable

4. Wait for code review and address any feedback

## Reporting Issues

When reporting issues, please include:

- Python version
- Redis version
- Minimal code example to reproduce
- Full error messages and stack traces
- Expected vs actual behavior

## Questions?

If you have questions about contributing, please open an issue for discussion.