.PHONY: help install test test-watch test-cov lint format type-check clean run-redis stop-redis

# Default target
.DEFAULT_GOAL := help

# Help command
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make lint         - Run linting"
	@echo "  make format       - Format code"
	@echo "  make type-check   - Run type checking"
	@echo "  make clean        - Clean cache and build files"
	@echo "  make run-redis    - Start Redis in Docker"
	@echo "  make stop-redis   - Stop Redis container"

# Install dependencies
install:
	poetry install

# Run tests
test:
	poetry run pytest -xvs

# Run tests in watch mode
test-watch:
	poetry run ptw --clear

# Run tests with coverage
test-cov:
	poetry run pytest --cov=fullon_cache --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Run linting
lint:
	poetry run ruff check .

# Format code
format:
	poetry run ruff format .
	poetry run ruff check --fix .

# Type checking
type-check:
	poetry run mypy .

# Clean cache and build files
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -delete
	find . -type d -name '.mypy_cache' -delete
	find . -type d -name '.ruff_cache' -delete
	find . -type d -name 'htmlcov' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name 'coverage.xml' -delete

# Run Redis in Docker
run-redis:
	docker run -d --name fullon-redis -p 6379:6379 redis:7-alpine
	@echo "Redis started on port 6379"

# Stop Redis
stop-redis:
	docker stop fullon-redis
	docker rm fullon-redis
	@echo "Redis stopped and removed"