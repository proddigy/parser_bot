"""
This module contains only (for now) parser for vinted.pl
"""

from abc import ABC, abstractmethod
from typing import List

from src.data_structures import Item
from src.logger import logger


class Parser(ABC):
    """
    Abstract parser class
    """
    __instance = None

    def __init__(self):
        self._reference = None
        self._db_client = None

    @abstractmethod
    def _get_new_items(self, category: str) -> List[Item]:
        """
        Parses url to a list of new Items with all necessary data
        :param category: category string (e.g. 'polo')
        :return: List[Item] list of parsed items
        """
        pass

    @abstractmethod
    def _get_item(self, item: dict) -> Item:
        """
        Parses item to Item object
        :param item: item dict with all necessary data
        :return: Item object
        """
        pass

    def _insert_items(self, items: List[Item]):
        """
        Inserts items to database
        :param items: List[Item]
        """
        self._db_client.insert_items(items)

    def run(self):
        """
        Runs parser
        """
        categories = self._db_client.categories
        for category in categories:
            items = self._get_new_items(category)
            self._insert_items(items)
            logger.debug(f'Category: {category} parsed on {self._reference}')
            logger.info(f'Inserted {len(items)} items to database')

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance