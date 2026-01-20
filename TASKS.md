# TASKS.md — xingest Implementation Roadmap

## Phase 1: Project Setup ✅
- [x] Project setup (pyproject.toml, folder structure)
- [x] `exceptions.py` - Exception hierarchy
- [x] `models/` - All Pydantic models (ProfileData, TweetData, ScrapeResult)

## Phase 2: Core Scraping (Validate Early) ✅
- [x] `core/fetcher.py` - Playwright automation (minimal, get HTML)
- [x] `core/parser.py` - BeautifulSoup extraction (profile + tweets)
- [x] `core/transformer.py` - Data normalization (counts, dates)

## Phase 3: Live Validation Checkpoint
- [ ] Scrape 3-4 live X/Twitter accounts (e.g., @elonmusk, @openai, @anthropic, @github)
- [ ] Verify parsed data matches expected structure
- [ ] Save raw HTML to `tests/fixtures/` for integration tests
- [ ] Document any selector issues or edge cases found

## Phase 4: Infrastructure
- [ ] `config.py` - Configuration management
- [ ] `logging/setup.py` - Structlog configuration
- [ ] `cache/base.py` - Cache interface
- [ ] `cache/sqlite_cache.py` - SQLite implementation
- [ ] `proxy/rotating.py` - Proxy rotation

## Phase 5: Orchestration
- [ ] `core/orchestrator.py` - Pipeline coordinator
- [ ] `core/exporter.py` - JSON output
- [ ] `__init__.py` - Public API

## Phase 6: CLI & Polish
- [ ] `cli.py` - Typer CLI
- [ ] `cache/redis_cache.py` - Redis implementation
- [ ] Unit tests (parser, transformer)
- [ ] Integration tests (using cached fixtures)
- [ ] Documentation (README.md)

---

## Future Enhancements
- [ ] Scroll to load more tweets (configurable depth)
- [ ] Media download (images, videos)
- [ ] DataFrame/Pandas output option
- [ ] Webhook notifications on scrape complete
- [ ] Scheduled scraping (cron-like)
- [ ] Metrics export (Prometheus)
- [ ] Docker image
- [ ] Tweet thread expansion
- [ ] Reply/quote tweet detection
