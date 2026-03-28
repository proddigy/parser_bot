"""
This module contains settings that are used in other modules.
"""
import os
import pathlib

try:
    from decouple import config as decouple_config
except ImportError:
    decouple_config = None


def config(name, default=None, cast=str):
    if decouple_config is not None:
        return decouple_config(name, default=default, cast=cast)

    value = os.getenv(name, default)
    if value is None:
        return None
    if cast is bool:
        return str(value).lower() in {"1", "true", "yes", "on"}
    return cast(value)


BASE_DIR = pathlib.Path(__file__).parent

DEBUG = config("DEBUG", default=False, cast=bool)
PARSER_UPDATE_INTERVAL = config("PARSER_UPDATE_INTERVAL", default=5, cast=int)
VINTED_ITEMS_PER_PAGE = config("VINTED_ITEMS_PER_PAGE", default=96, cast=int)

DOMAIN = config("VINTED_DOMAIN", default="pl")
API_TOKEN = config("API_TOKEN", default="000000:TEST_TOKEN")

DB_USER = config("DB_USER", default="")
DB_PASSWORD = config("DB_PASSWORD", default="")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = config("DB_PORT", default="5432")
DB_NAME = config("DB_NAME", default="")


# LOGGING
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = config("LOG_LEVEL", default="debug")
LOG_DIR = BASE_DIR / "logs"

LOG_DEBUG_FILE_PATH = os.path.join(LOG_DIR, 'log_debug.log')
LOG_INFO_FILE_PATH = os.path.join(LOG_DIR, 'log_info.log')
LOG_WARNING_FILE_PATH = os.path.join(LOG_DIR, 'log_warning.log')
LOG_ERROR_FILE_PATH = os.path.join(LOG_DIR, 'log_error.log')
