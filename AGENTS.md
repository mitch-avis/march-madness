# AGENTS.md

## Project overview

- Name: march-madness
- Type: Django web app with background scraping tasks
- Python: 3.11-3.13 (see pyproject.toml)
- Package manager: uv (requirements.in and requirements-dev.in compiled to txt)
- Primary apps: core (UI, health), scraper (API, tasks, scrapers)

## Key entry points

- Web server: manage.py runserver
- Convenience script: start_server.sh (runs dev server on 0.0.0.0:8080)
- Scraper CLI: run_teamrankings_scrapers.py (TeamRankings stats and ratings)
- ASGI/WSGI: asgi.py, wsgi.py

## Data and environment

- Data path: MARCH_MADNESS_DATA_PATH
  - Default in settings: ./data
  - start_server.sh sets a OneDrive path for WSL users
- Season year logic: CURRENT_YEAR uses get_current_season_year()
  - Rollover month: SEASON_YEAR_ROLLOVER_MONTH (default 7)
- CSV outputs
  - TeamRankingsStats{year}.csv
  - TeamRankingsRatings{year}.csv
  - Scores{year}.csv
  - AllScores.csv

## Architecture notes

- core/views.py: home page and health endpoint
- scraper/views.py: HTTP endpoints for scrape_all, stats, ratings, scores, tasks
- scraper/task_manager.py: in-memory task registry with background threads
- scraper/tr_scraper.py: TeamRankings stats and ratings (skips 2020)
- scraper/scores_scraper.py: Sports Reference tournament scores
- templates/index.html and static/css/style.css implement the UI and task polling

## Tests

- Tests live in core/tests.py and scraper/test_*.py
- pyproject.toml testpaths points to tests/ which is not present
- Run pytest with explicit paths
  - pytest core scraper
  - pytest scraper/test_utils.py

## Authoritative commands

### Environment setup

```bash
./update_requirements.sh
# Activate an existing venv if present
source .venv/bin/activate  # or: source venv/bin/activate
```

### Run the dev server

```bash
./start_server.sh
# or
python manage.py runserver
```

### Run TeamRankings scrapers without the server

```bash
python run_teamrankings_scrapers.py
python run_teamrankings_scrapers.py --dry-run
python run_teamrankings_scrapers.py --data-path "/mnt/c/Users/mitch/OneDrive/March Madness/Data"
python run_teamrankings_scrapers.py --start-year 2026 --end-year 2026
```

### Run tests

```bash
pytest core scraper
pytest scraper/test_views.py::ScrapeAllViewTests::test_scrape_all_success_response
```

### Format and lint

```bash
black .
ruff check .
```

## Conventions and guardrails

- Keep request logic resilient: use retry sessions and raise DataScrapingError on failures
- Use TaskCancelledError to stop background scrapes cleanly
- Prefer absolute imports for new modules; keep Django app imports consistent with local patterns
- Maintain deterministic tests by mocking network and filesystem access

## Files to read first

- README.md
- pyproject.toml
