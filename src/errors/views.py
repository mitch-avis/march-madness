from flask import Blueprint, jsonify
from werkzeug.exceptions import HTTPException

from src import log  # pylint: disable=R0401

errors_bp = Blueprint("errors", __name__)


class APIError(Exception):
    """APIError Exception"""

    name = "Internal Server Error"
    code = 500

    def __init__(self, error=None, value=str(), message=str()):
        super().__init__()
        if error is not None:
            self.name = error[0]
            self.code = error[1]
        self.description = {
            "value": value,
            "message": message,
        }


def to_dict(error):
    response = {
        "code": error.code,
        "error": error.name,
        "message": error.description,
        "success": False,
    }
    return response


@errors_bp.app_errorhandler(Exception)
def handle_exception(error: Exception):
    if isinstance(error, (APIError, HTTPException)):
        status_code = error.code
        response = to_dict(error)
    else:
        status_code = 500
        response = {
            "code": status_code,
            "error": "Internal Server Error",
            "message": str(error),
            "success": False,
        }
    log.debug(str(response))
    return jsonify(response), status_code
