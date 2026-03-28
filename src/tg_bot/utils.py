"""
This module contains logic functions for telegram bot
"""
import asyncio
import os
import shutil
from decouple import config
from aiogram import types
from aiogram.types import ParseMode, InlineKeyboardMarkup

from .bot import bot, dp
from src.logger import logger
from src.data_structures import Item
from src.tg_bot.db_handler import get_unpublished_items, add_published_item


# Notification logic

async def send_new_items_to_user(user_id: int):
    """
    Sends all the unpublished
    :param user_id: telegram unique id
    """
    new_items = await get_unpublished_items(user_id)

    if not new_items:
        await bot.send_message(user_id, "There are no new items at the moment.")
    else:
        for item in new_items:
            await send_new_item(user_id, item)
            await asyncio.sleep(1)


async def send_new_item(user_id: int, item: Item) -> None:
    message_text = f"<b>{item.title}</b>\n" \
                   f"Brand: {item.brand_name}\n" \
                   f"Size: {item.size}\n" \
                   f"Price: {item.price}Zł\n" \
                   f"{item.url}"

    try:
        await bot.send_photo(
            chat_id=user_id,
            photo=item.image_url,
            caption=message_text,
            parse_mode=ParseMode.HTML,
        )
        await add_published_item(user_id, item.unique_id)
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")


async def edit_message_with_keyboard(message: types.Message, text: str, keyboard: InlineKeyboardMarkup):
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error editing message for chat_id {message.chat.id}: {e}")


def clear_data():
    vinted.clear_data()
    image_dir = os.path.join(
        BASE_DIR.parent,
        'images'
    )
    shutil.rmtree(image_dir)
    os.makedirs(image_dir)
