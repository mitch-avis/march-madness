from flask import Blueprint, jsonify

from src import log
from src.config.env_config import Config
from src.errors.views import APIError
from src.utils.utils import scrape_ratings, scrape_scores, scrape_stats

CURRENT_YEAR = Config.CURRENT_YEAR
BAD_REQUEST = ["Bad Request", 400]
NOT_FOUND = ["Not Found", 404]
UNPROCESSABLE_CONTENT = ["Unprocessable Content", 422]

api_bp = Blueprint("api", __name__)


@api_bp.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
    return response


@api_bp.route("/")
def home():
    """Home endpoint."""
    greeting = "Welcome!"
    log.debug("%s", greeting)
    return (
        jsonify(
            {
                "success": True,
                "message": greeting,
            }
        ),
        200,
    )


@api_bp.route("/test", defaults={"test_value": None})
@api_bp.route("/test/<test_value>", methods=["GET"])
def get_test(test_value):
    log.debug("Testing...")
    if test_value is None:
        value = None
        message = "No test_value found."
        raise APIError(NOT_FOUND, value, message)
    return (
        jsonify(
            {
                "success": True,
                "test_value": test_value,
            }
        ),
        200,
    )


@api_bp.route("/scrape/all", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape/all/<start_year>", methods=["GET"])
def run_scrape_all(start_year):
    log.debug("Running scraper:all...")
    scrape_ratings(int(start_year))
    scrape_stats(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )


@api_bp.route("/scrape/stats", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape/stats/<start_year>", methods=["GET"])
def run_scrape_stats(start_year):
    log.debug("Running scraper:stats...")
    scrape_stats(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )


@api_bp.route("/scrape/ratings", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape/ratings/<start_year>", methods=["GET"])
def run_scrape_ratings(start_year):
    log.debug("Running scraper:ratings...")
    scrape_ratings(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )


@api_bp.route("/scrape/scores", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape/scores/<start_year>", methods=["GET"])
def run_scrape_scores(start_year):
    log.debug("Running scraper:scores...")
    scrape_scores(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )
