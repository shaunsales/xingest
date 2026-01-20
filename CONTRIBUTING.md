# Contributing to xingest

## Development Setup

```bash
# Clone and install in editable mode
git clone https://github.com/yourusername/xingest.git
cd xingest
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

## Running Tests

### Unit Tests (Fast, No Internet)

Run frequently during development:

```bash
# All unit tests
pytest tests/test_parser.py tests/test_config.py tests/test_cache.py tests/test_proxy.py -v

# Specific test file
pytest tests/test_parser.py -v

# With coverage
pytest --cov=xingest tests/
```

### Integration Tests (Slow, Requires Internet)

Run sparingly to avoid rate limiting:

```bash
python tests/test_integration_scrape.py
```

This will:
1. Scrape 5 live X/Twitter accounts
2. Validate extracted data
3. Update HTML/JSON fixtures in `tests/fixtures/`

## Code Style

- **Formatter**: Ruff (line length: 100)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy xingest/
```

## Adding New Test Accounts

1. Add username to `TEST_ACCOUNTS` in `tests/test_integration_scrape.py`
2. Run integration tests to generate fixtures
3. Update `EXPECTED_DATA` in `tests/test_parser.py`

## Pull Request Checklist

- [ ] Unit tests pass locally
- [ ] New code has type hints
- [ ] Docstrings for public functions
- [ ] No regressions in existing tests
