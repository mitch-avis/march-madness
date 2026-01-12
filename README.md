# March Madness Data Scraper and Analyzer

![NCAA March Madness](https://upload.wikimedia.org/wikipedia/commons/2/28/March_Madness_logo.svg)

## 📋 Features

- **Multi-Source Data Collection**: Automated scraping from various basketball statistics sources:
  - Comprehensive team statistics from TeamRankings.com
  - Historical tournament results from [Sports Reference](https://www.sports-reference.com/cbb/postseason/men)
- **Asynchronous Processing**: Background task system for non-blocking data collection
- **Progress Tracking**: Real-time updates on long-running scraping tasks
- **Web Interface**: User-friendly dashboard to trigger and monitor data collection

## 🔧 Installation

### Prerequisites

- Python 3.8+
- Django 3.2+
- PostgreSQL (recommended) or SQLite
- Required Python packages (see `requirements.txt`)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/mitch-avis/march-madness.git
   cd march-madness
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run database migrations:

   ```bash
   python manage.py migrate
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

6. Access the web interface at <http://127.0.0.1:8000/>

## 🚀 Usage

### Data Collection

The application allows collecting several types of NCAA basketball data:

#### Via Web Interface

1. Navigate to the main dashboard
2. Click on one of the scraping options:
   - **Scrape All Data**: Collects all available data types in sequence
   - **Scrape Team Statistics**: Comprehensive team performance stats
   - **Scrape Team Ratings**: Various rating systems for comparative analysis
   - **Scrape Tournament Scores**: Historical game results from past tournaments
3. Monitor progress on the dashboard

#### Via API

The application exposes RESTful endpoints for triggering scraping tasks:

```bash
# Scrape all data types from 2015 onward
curl -X GET http://127.0.0.1:8000/scraper/all/2015/

# Check task status
curl -X GET http://127.0.0.1:8000/scraper/task/[task-id]/
```

#### Run scrapers without the server

If you only want to refresh TeamRankings stats/ratings (and don’t want to start the Django dev
server), run:

```bash
python run_teamrankings_scrapers.py
```

This uses the same `MARCH_MADNESS_DATA_PATH` env var as the server. If it’s not set,
the script will default to the OneDrive path from `start_server.sh` when that folder exists.

Optional:

```bash
# Just validate imports / show what would run
python run_teamrankings_scrapers.py --dry-run

# Force a specific output folder
python run_teamrankings_scrapers.py --data-path "/mnt/c/Users/mitch/OneDrive/March Madness/Data"

# Override year range
python run_teamrankings_scrapers.py --start-year 2026 --end-year 2026
```

### Data Files

The application generates several CSV files in the `data` directory:

| File Pattern | Description |
| ------------ | ----------- |
| `TeamRankings[Year].csv` | Team statistics for a specific year |
| `TeamRankingsRatings[Year].csv` | Team ratings for a specific year |
| `Scores[Year].csv` | Tournament game results for a specific year |
| `AllScores.csv` | Consolidated game results across all years |

## 🏗️ Project Structure

```sh
march-madness/
├── core/                 # Core application
│   ├── views.py          # Main application views
│   └── urls.py           # URL routing for core app
├── data/                 # Directory for scraped data files
├── march_madness/        # Project settings module
├── scraper/              # Data scraping application
│   ├── task_manager.py   # Background task orchestration
│   ├── utils.py          # Scraping utilities
│   ├── views.py          # API endpoints for scraping
│   └── urls.py           # URL routing for scraper
├── static/               # Static assets
│   └── css/              # Stylesheets
├── templates/            # HTML templates
└── manage.py             # Django management script
```

## 📊 API Reference

### Endpoints

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/scraper/all/[year]/` | GET | Start scraping all data types from specified year |
| `/scraper/stats/[year]/` | GET | Scrape team statistics from specified year |
| `/scraper/ratings/[year]/` | GET | Scrape team ratings from specified year |
| `/scraper/scores/[year]/` | GET | Scrape tournament scores from specified year |
| `/scraper/task/[task_id]/` | GET | Get status of a specific task |
| `/scraper/tasks/` | GET | Get list of recent tasks |

### Response Format

Success response:

```json
{
  "success": true,
  "message": "Scraping started in the background",
  "task_id": "12345-abcde-67890",
  "status": "RUNNING"
}
```

Error response:

```json
{
  "success": false,
  "error": "Invalid year format: expected integer"
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- NCAA for making March the most exciting month in sports
- Data sources: teamrankings.com, sports-reference.com
- The Python and Django communities for their excellent tools
