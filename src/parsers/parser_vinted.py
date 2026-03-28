"""
This module contains parser for vinted.pl
"""

import os
import re
import urllib3

from src.data_structures import Item
from src.db_client.db_client_vinted import VintedDbClient
from src.db_client.models import Category
from src.logger import logger
from src.requester import get_requester
from src.settings import BASE_DIR
from src.parsers.utils import vinted_category_url
from src.parsers.parser_abc import Parser


class VintedParser(Parser):
    """
    Parser for vinted.pl
    """

    def __init__(self):
        super().__init__()
        self._db_client = VintedDbClient()
        self._reference = 'vinted'

    def __str__(self):
        return 'Vinted Parser'

    def __call__(self, *args, **kwargs):
        logger.debug('Starting Vinted Parser')
        for category in self._db_client.categories:
            logger.debug(f'Parsing {category}')
            new_items = self._get_new_items(category)
            if new_items:
                self._insert_items(new_items)
            else:
                logger.debug('No new items')
        logger.debug(f'Done parsing f{category}')

    def _get_new_items(self, category: Category) -> list[Item]:
        #  I need to get all the categories and then get all the items from each
        api_url = vinted_category_url(category)
        search_response = get_requester().get(api_url)
        items = search_response['items']
        unique_ids = self._db_client.unique_ids
        logger.debug(f'Found {len(unique_ids)} unique ids in database')
        result = [self._get_item(item, category) for item in items]
        logger.debug(f'Fetched {len(items)} items from API for category_id {category}')
        return result

    def _get_item(self, item: dict, category: Category) -> Item:
        return Item(
            title=item['title'],
            unique_id=item['id'],
            price=item['price'],
            brand_name=item['brand_title'],
            size=item['size_title'],
            url=item['url'],
            image_url=item['photo']['url'],
            category_id=category.id,
        )

    def _insert_items(self, items: list[Item]):
        logger.debug(f'Inserting {len(items)} items to database')
        try:
            self._db_client.insert_items(items)
            logger.debug(f'Inserted {len(items)} items to the database')
            logger.debug('Database updated')
        except Exception as e:
            logger.error(e)
            logger.error('Failed to insert items to database', exc_info=True)

_vinted_parser = None


def get_vinted_parser() -> VintedParser:
    global _vinted_parser
    if _vinted_parser is None:
        _vinted_parser = VintedParser()
    return _vinted_parser


if __name__ == '__main__':
    get_vinted_parser()()
