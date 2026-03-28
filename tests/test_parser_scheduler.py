import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def load_parser_scheduler():
    for module_name in [
        "parser_scheduler",
        "settings",
        "logger",
        "db_client.models",
        "tg_bot.db_handler",
        "parsers.parser_vinted",
    ]:
        sys.modules.pop(module_name, None)

    settings_module = ModuleType("settings")
    settings_module.PARSER_UPDATE_INTERVAL = 5
    settings_module.DEBUG = True

    logger_module = ModuleType("logger")
    logger_module.logger = SimpleNamespace(info=Mock(), error=Mock())

    models_module = ModuleType("db_client.models")
    models_module.UserPublishedItem = object()
    models_module.VintedItem = object()

    db_handler_module = ModuleType("tg_bot.db_handler")
    db_handler_module.clear_table = Mock(return_value="clear-task")

    parser_vinted_module = ModuleType("parsers.parser_vinted")
    parser_vinted_module.vinted_parser = Mock(name="vinted_parser")
    parser_vinted_module.get_vinted_parser = Mock(return_value=parser_vinted_module.vinted_parser)

    sys.modules["settings"] = settings_module
    sys.modules["logger"] = logger_module
    sys.modules["db_client.models"] = models_module
    sys.modules["tg_bot.db_handler"] = db_handler_module
    sys.modules["parsers.parser_vinted"] = parser_vinted_module

    module = importlib.import_module("parser_scheduler")
    return module, db_handler_module, parser_vinted_module


def test_start_parser_creates_background_thread(monkeypatch):
    module, _, parser_vinted_module = load_parser_scheduler()
    thread_calls = []

    class FakeThread:
        def __init__(self, target=None, daemon=None):
            thread_calls.append({"target": target, "daemon": daemon, "started": False})
            self._record = thread_calls[-1]

        def start(self):
            self._record["started"] = True

    monkeypatch.setattr(module.threading, "Thread", FakeThread)

    module.start_parser()

    assert len(thread_calls) == 1
    parser_vinted_module.get_vinted_parser.assert_called_once_with()
    assert thread_calls[0]["target"] is parser_vinted_module.vinted_parser
    assert thread_calls[0]["daemon"] is True
    assert thread_calls[0]["started"] is True
    parser_vinted_module.vinted_parser.assert_not_called()


def test_scheduler_runs_midnight_cleanup_via_asyncio(monkeypatch):
    module, db_handler_module, _ = load_parser_scheduler()
    every_calls = []
    run_mock = Mock()
    sleep_mock = Mock()

    class FakeNow:
        hour = 0

    class FakeDateTime:
        @staticmethod
        def now():
            return FakeNow()

    class FakeEvery:
        @property
        def minutes(self):
            return self

        def do(self, callback):
            every_calls.append(callback)

    monkeypatch.setattr(module.datetime, "datetime", FakeDateTime)
    monkeypatch.setattr(module.asyncio, "run", run_mock)
    monkeypatch.setattr(module.time, "sleep", sleep_mock)
    monkeypatch.setattr(module.schedule, "every", lambda interval: FakeEvery())

    module.scheduler()

    db_handler_module.clear_table.assert_called_once_with()
    run_mock.assert_called_once_with("clear-task")
    assert every_calls == [module.start_parser]
    sleep_mock.assert_any_call(360 * 5)
    sleep_mock.assert_any_call(10)
