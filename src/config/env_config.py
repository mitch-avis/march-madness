from os import getenv


class Config:
    FLASK_APP = getenv("FLASK_APP", "march_madness")
    FLASK_DEBUG = getenv("FLASK_DEBUG", "True").lower() in ("true", "t", "1")
    HOST = getenv("HOST", "0.0.0.0")
    PORT = getenv("PORT", "8080")
    ALLOWED_ORIGINS = getenv("ALLOWED_ORIGINS", "*")
