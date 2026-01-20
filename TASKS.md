# TASKS.md — xingest Implementation Roadmap

## Phase 1: Project Setup ✅
- [x] Project setup (pyproject.toml, folder structure)
- [x] `exceptions.py` - Exception hierarchy
- [x] `models/` - All Pydantic models (ProfileData, TweetData, ScrapeResult)

## Phase 2: Core Scraping (Validate Early) ✅
- [x] `core/fetcher.py` - Playwright automation (minimal, get HTML)
- [x] `core/parser.py` - BeautifulSoup extraction (profile + tweets)
- [x] `core/transformer.py` - Data normalization (counts, dates)

## Phase 3: Live Validation Checkpoint ✅
- [x] Scrape 5 live X/Twitter accounts (@okx, @nodepay, @jason, @cz_binance, @nikitabier)
- [x] Verify parsed data matches expected structure
- [x] Save raw HTML to `tests/fixtures/` for integration tests
- [x] Selectors working - no issues found

### Test Structure
- **Unit tests** (`pytest tests/test_parser.py`) — Parse cached HTML fixtures, no internet, run frequently
- **Integration tests** (`python tests/test_integration_scrape.py`) — Live scraping, requires internet, run sparingly

## Phase 4: Infrastructure ✅
- [x] `config.py` - Configuration management (Pydantic Settings, env vars)
- [x] `logging/setup.py` - Structlog configuration (JSON/console output)
- [x] `cache/base.py` - Cache interface (abstract base class)
- [x] `cache/sqlite_cache.py` - SQLite implementation (async, TTL support)
- [x] `proxy/rotating.py` - Proxy rotation (round-robin/random)

## Phase 5: Orchestration ✅
- [x] `core/orchestrator.py` - Pipeline coordinator (Scraper class with caching)
- [x] `core/exporter.py` - JSON output (save/load/merge utilities)
- [x] `__init__.py` - Public API (Scraper, config, models, exporters)

## Phase 6: CLI & Polish ✅
- [x] `cli.py` - Typer CLI (scrape, info, cache commands)
- [x] `cache/redis_cache.py` - Redis implementation (async, TTL support)
- [x] Unit tests (97 tests covering parser, transformer, config, cache, proxy, orchestrator, exporter)
- [x] Integration tests (live scraping with validation)
- [x] Documentation (README.md, CONTRIBUTING.md, docs/ARCHITECTURE.md)

---

## Future Enhancements
- [ ] Scroll to load more tweets (configurable depth)
- [ ] Media download (images, videos)
- [x] DataFrame/Pandas output option (to_tweets_df, to_profile_df, save_csv)
- [ ] Webhook notifications on scrape complete
- [ ] Scheduled scraping (cron-like)
- [ ] Metrics export (Prometheus)
- [ ] Docker image
- [ ] Tweet thread expansion
- [ ] Reply/quote tweet detection
