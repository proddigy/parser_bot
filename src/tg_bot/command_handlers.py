from aiogram import types
from aiogram.dispatcher import filters, FSMContext

from .bot import dp, bot
from .keyboards import menu_keyboard
from .db_handler import create_user, is_active, deactivate_user_by_id_async, activate_user_by_id_async,\
    get_user_by_username_async, create_category, add_category_to_user, get_user_by_id_async
from .states import NewCategory
from src.logger import logger


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = message.from_user
    existing_user = await get_user_by_id_async(user.id)
    if existing_user:
        await bot.send_message(text="Welcome back!", chat_id=user.id)
        await message.answer("Here is menu:", reply_markup=menu_keyboard())
        return
    logger.info(f"New user: {user.id} - {user.username}")
    try:
        await create_user(user)
        await message.reply("Welcome to the bot!\n Here is menu:", reply_markup=menu_keyboard())
    except Exception as e:
        logger.warning(f"Failed to create user: {e}")
        await message.reply("An error occurred. Please try again later.")


@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    user = message.from_user
    if await is_active(user):
        await deactivate_user_by_id_async(user.id)
        await message.answer(f"Unsubscribed from Vinted notifications.")
    else:
        await message.answer(f"You are already unsubscribed from Vinted notifications.")


@dp.message_handler(is_admin=True, commands=["activate"])
async def cmd_activate(message: types.Message):
    user_id_or_username = message.get_args()
    if user_id_or_username.isdigit():
        user_id = int(user_id_or_username)
        await activate_user_by_id_async(user_id)
        await message.reply(f"User {user_id} has been activated.")
    else:
        user = await get_user_by_username_async(user_id_or_username)
        if user:
            await activate_user_by_id_async(user.id)
            await message.reply(f"User {user.username} has been activated.")
        else:
            await message.reply(f"User {user_id_or_username} not found.")


@dp.message_handler(is_admin=True, commands=["deactivate"])
async def cmd_deactivate(message: types.Message):
    user_id_or_username = message.get_args()
    if user_id_or_username.isdigit():
        user_id = int(user_id_or_username)
        await deactivate_user_by_id_async(user_id)
        await message.reply(f"User {user_id} has been deactivated.")
    else:
        user = await get_user_by_username_async(user_id_or_username)
        if user:
            await deactivate_user_by_id_async(user.id)
            await message.reply(f"User {user.username} has been deactivated.")
        else:
            await message.reply(f"User {user_id_or_username} not found.")


@dp.message_handler(commands=["menu"])
async def menu(message: types.Message):
    keyboard = menu_keyboard()
    await message.answer("Menu:", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text, state=NewCategory.InputCategoryName)
async def new_category_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    category_name = message.text

    # Create the new category and save the relationship
    new_category = await create_category(category_name)
    await add_category_to_user(user_id, new_category.id)

    # Send a confirmation message to the user
    await bot.send_message(chat_id=user_id, text=f"New category '{category_name}' has been added.")

    # Finish the state
    await state.finish()
