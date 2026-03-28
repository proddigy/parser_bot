import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock


class FakeDispatcher:
    def message_handler(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


def load_command_handlers(existing_user):
    for module_name in [
        "tg_bot.command_handlers",
        "tg_bot.bot",
        "tg_bot.db_handler",
        "tg_bot.keyboards",
        "src.logger",
    ]:
        sys.modules.pop(module_name, None)

    fake_bot = SimpleNamespace(send_message=AsyncMock())

    bot_module = ModuleType("tg_bot.bot")
    bot_module.bot = fake_bot
    bot_module.dp = FakeDispatcher()

    db_handler_module = ModuleType("tg_bot.db_handler")
    db_handler_module.create_user = AsyncMock()
    db_handler_module.is_active = AsyncMock(return_value=True)
    db_handler_module.deactivate_user_by_id_async = AsyncMock()
    db_handler_module.activate_user_by_id_async = AsyncMock()
    db_handler_module.get_user_by_username_async = AsyncMock(return_value=None)
    db_handler_module.create_category = AsyncMock()
    db_handler_module.add_category_to_user = AsyncMock()
    db_handler_module.get_user_by_id_async = AsyncMock(return_value=existing_user)

    keyboards_module = ModuleType("tg_bot.keyboards")
    keyboards_module.menu_keyboard = Mock(return_value="menu-keyboard")

    logger_module = ModuleType("src.logger")
    logger_module.logger = SimpleNamespace(info=Mock(), warning=Mock(), error=Mock(), debug=Mock())

    sys.modules["tg_bot.bot"] = bot_module
    sys.modules["tg_bot.db_handler"] = db_handler_module
    sys.modules["tg_bot.keyboards"] = keyboards_module
    sys.modules["src.logger"] = logger_module

    module = importlib.import_module("tg_bot.command_handlers")
    return module, fake_bot, db_handler_module


def make_message():
    user = SimpleNamespace(id=123, username="tester", first_name="Test")
    return SimpleNamespace(from_user=user, answer=AsyncMock(), reply=AsyncMock())


def test_cmd_start_existing_user_shows_menu():
    module, fake_bot, db_handler_module = load_command_handlers(existing_user=object())
    message = make_message()

    asyncio.run(module.cmd_start(message))

    db_handler_module.get_user_by_id_async.assert_awaited_once_with(123)
    db_handler_module.create_user.assert_not_awaited()
    fake_bot.send_message.assert_awaited_once_with(text="Welcome back!", chat_id=123)
    message.answer.assert_awaited_once_with("Here is menu:", reply_markup="menu-keyboard")
    message.reply.assert_not_awaited()


def test_cmd_start_new_user_creates_user():
    module, fake_bot, db_handler_module = load_command_handlers(existing_user=None)
    message = make_message()

    asyncio.run(module.cmd_start(message))

    db_handler_module.get_user_by_id_async.assert_awaited_once_with(123)
    db_handler_module.create_user.assert_awaited_once_with(message.from_user)
    fake_bot.send_message.assert_not_awaited()
    message.reply.assert_awaited_once_with(
        "Welcome to the bot!\n Here is menu:",
        reply_markup="menu-keyboard",
    )
