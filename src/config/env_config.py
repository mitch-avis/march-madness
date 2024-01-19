from datetime import datetime
from os import getenv
from os.path import abspath, dirname, join


class Config:
    FLASK_APP = getenv("FLASK_APP", "march_madness")
    FLASK_DEBUG = getenv("FLASK_DEBUG", "True").lower() in ("true", "t", "1")
    HOST = getenv("HOST", "0.0.0.0")
    PORT = getenv("PORT", "8080")
    ALLOWED_ORIGINS = getenv("ALLOWED_ORIGINS", "*")
    ROOT_DIR = dirname(dirname(dirname(abspath(__file__))))
    DATA_PATH = join(ROOT_DIR, "data")
    START_YEAR = 2008
    CURRENT_YEAR = datetime.now().year
