"""
This module contains telegram bot
"""
from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from src.tg_bot.filter import IsAdminFilter
from src.logger import logger
from src.tg_bot.db_handler import init_engine
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from src.settings import API_TOKEN

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
dp.filters_factory.bind(IsAdminFilter)


async def on_startup(_):
    global async_session
    async_session = await init_engine()
    logger.info("Bot has been started")


async def on_shutdown(_):
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Bot has been stopped")
