#!/usr/bin/env python
from waitress import serve

from src import create_app, log

# from src.api.views import run_scrape_all
from src.config.env_config import Config


def main():
    app = create_app()
    DEBUG = Config.FLASK_DEBUG
    HOST = Config.HOST
    PORT = Config.PORT

    if not DEBUG:
        print(f"Serving {app.name} on {HOST}:{PORT}...")
        serve(app, host=HOST, port=PORT)
    else:
        log.warning("Running %s in debug mode on %s:%s...", app.name, HOST, PORT)
        app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
    # run_scrape_all(2024)
