import datetime
import threading
import time
import asyncio
import schedule
from settings import PARSER_UPDATE_INTERVAL, DEBUG
from logger import logger
from db_client.models import UserPublishedItem, VintedItem
from tg_bot.db_handler import clear_table
from parsers.parser_vinted import get_vinted_parser


def start_parser():
    try:
        threading.Thread(target=get_vinted_parser(), daemon=True).start()
        logger.info(f'Successfully started parser thread for vinted')
    except Exception as e:
        logger.error(f'Failed to start parser thread for vinted: {e}', exc_info=True)


def scheduler():
    if datetime.datetime.now().hour == 0:
        asyncio.run(clear_table())
        time.sleep(360 * 5)  # Pause for 5 hours

    schedule.every(PARSER_UPDATE_INTERVAL).minutes.do(start_parser)
    time.sleep(10)


def main():
    scheduler()
    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == '__main__':
    main()
