from flask import Blueprint, jsonify

from src import log
from src.config.env_config import Config
from src.errors.views import APIError
from src.utils.utils import scrape_ratings, scrape_stats

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
    log.debug("testing")
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


@api_bp.route("/scrape_stats", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape_stats/<start_year>", methods=["GET"])
def run_scrape_stats(start_year):
    log.debug("running scraper")
    scrape_stats(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )


@api_bp.route("/scrape_ratings", defaults={"start_year": CURRENT_YEAR})
@api_bp.route("/scrape_ratings/<start_year>", methods=["GET"])
def run_scrape_ratings(start_year):
    log.debug("running scraper")
    scrape_ratings(int(start_year))
    return (
        jsonify(
            {
                "success": True,
            }
        ),
        200,
    )
