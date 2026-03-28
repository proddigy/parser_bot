import time

import requests
from src.logger import logger
from src.settings import DOMAIN

HEADERS = {
    "User-Agent": "PostmanRuntime/7.28.4",
    "Host": "www.vinted.pl",
}

VINTED_URL = f"https://www.vinted.{DOMAIN}"
VINTED_AUTH_URL = f"https://www.vinted.{DOMAIN}/auth/token_refresh"
VINTED_API_URL = f"https://www.vinted.{DOMAIN}/api/v2"
VINTED_PRODUCTS_ENDPOINT = "catalog/items"


class VintedRequester:
    """
    requester class used to perform http requests to vinted.pl
    """

    def __init__(self):
        self.vinted_url = VINTED_URL
        self.vinted_auth_url = VINTED_AUTH_URL
        self.vinted_api_url = VINTED_API_URL
        self.vinted_products_endpoint = VINTED_PRODUCTS_ENDPOINT
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._cookies_initialized = False

    def get(self, url, data=None):
        """
        Perform a http get request.
        :param url: str
        :param data: dict, optional
        :return: dict
            Json format
        """
        self.ensure_initialized()
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.get(url, params=data)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(
                    f"GET request failed for {url} on attempt {attempt}/{attempts}: {e}",
                    exc_info=True,
                )
                self.set_cookies()

        raise RuntimeError(f"Failed to fetch {url} after {attempts} attempts")

    def post(self, url, params=None):
        """
        Perform a http post request.
        :param url: url to post to
        :param params: params to post
        :return: none
        """
        self.ensure_initialized()
        response = self.session.post(url, params)
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(e, exc_info=True)
            self.set_cookies()

        return response

    def ensure_initialized(self):
        if not self._cookies_initialized:
            self.set_cookies()

    def set_cookies(self, attempt=1):
        """used to set cookies"""
        while attempt <= 3:
            try:
                response = self.session.post(self.vinted_auth_url)
                response.raise_for_status()
                self._cookies_initialized = True
                logger.info("Cookies set!")
                return
            except Exception as e:
                logger.error(
                    f"There was an error fetching cookies for {self.vinted_url} on attempt {attempt}: {e}",
                    exc_info=True,
                )
                attempt += 1

        logger.error("Failed to set cookies after 3 attempts")
        time.sleep(60)
        raise RuntimeError(f"Failed to refresh cookies for {self.vinted_url}")


_requester = None


def get_requester() -> VintedRequester:
    global _requester
    if _requester is None:
        _requester = VintedRequester()
    return _requester

