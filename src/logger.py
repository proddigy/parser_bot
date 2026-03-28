"""
This module contains the logger class.
"""

import logging
import os
import sys
import traceback
from src.settings import DEBUG, LOG_FORMAT, LOG_DIR
from src.settings import LOG_DEBUG_FILE_PATH, LOG_INFO_FILE_PATH, LOG_WARNING_FILE_PATH, \
    LOG_ERROR_FILE_PATH

logging.basicConfig(format=LOG_FORMAT)
os.makedirs(LOG_DIR, exist_ok=True)


class CustomLogger:
    """
    Custom logger class that can be extended by other logger classes.
    """

    def __init__(self, logger_name, log_level, log_file_path):
        self.__logger = logging.getLogger(logger_name)
        self.__logger.setLevel(log_level)
        handler = logging.FileHandler(log_file_path)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.encoding = 'utf-8'
        self.__logger.addHandler(handler)

        if DEBUG:
            with open(log_file_path, 'w', encoding='utf-8'):
                pass

    def __call__(self, *args, **kwargs):
        exc_info = kwargs.pop('exc_info', False)
        if exc_info and self.__logger.level == logging.ERROR:
            kwargs['exc_info'] = True
        self.__logger.log(self.__logger.level, *args, **kwargs)


class LoggerDebug(CustomLogger):
    """
    Logger debug class
    """

    def __init__(self):
        super().__init__('debug_logger', logging.DEBUG, LOG_DEBUG_FILE_PATH)


class LoggerInfo(CustomLogger):
    """
    Logger info class
    """

    def __init__(self):
        super().__init__('info_logger', logging.INFO, LOG_INFO_FILE_PATH)


class LoggerWarning(CustomLogger):
    """
    Logger warning class
    """

    def __init__(self):
        super().__init__('warning_logger', logging.WARNING, LOG_WARNING_FILE_PATH)


class LoggerError(CustomLogger):
    """
    Logger error class
    """

    def __init__(self):
        super().__init__('error_logger', logging.ERROR, LOG_ERROR_FILE_PATH)


class Logger:
    """
    Logger class
    """

    def __init__(self):
        self.debug = LoggerDebug()
        self.info = LoggerInfo()
        self.warning = LoggerWarning()
        self.error = LoggerError()


logger = Logger()
