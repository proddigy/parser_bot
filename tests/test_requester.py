import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self._payload = payload or {}
        self._error = error

    def raise_for_status(self):
        if self._error is not None:
            raise self._error

    def json(self):
        return self._payload


def load_requester_module(import_post_response=None):
    for module_name in ["requester", "requests", "src.logger"]:
        sys.modules.pop(module_name, None)

    logger_module = ModuleType("src.logger")
    logger_module.logger = SimpleNamespace(info=Mock(), error=Mock())

    requests_module = ModuleType("requests")

    class ImportSession:
        def __init__(self):
            self.headers = {}

        def post(self, url, params=None):
            return import_post_response or FakeResponse()

        def get(self, url, params=None):
            return FakeResponse()

    requests_module.Session = ImportSession

    sys.modules["src.logger"] = logger_module
    sys.modules["requests"] = requests_module

    module = importlib.import_module("requester")
    return module, logger_module.logger


def test_import_does_not_initialize_requester():
    module, _ = load_requester_module()

    assert module._requester is None


def test_get_returns_json_after_transient_failures():
    module, logger = load_requester_module()
    requester = module.VintedRequester()
    responses = [
        FakeResponse(error=RuntimeError("boom-1")),
        FakeResponse(error=RuntimeError("boom-2")),
        FakeResponse(payload={"items": [1, 2, 3]}),
    ]

    requester.session = SimpleNamespace(
        get=Mock(side_effect=lambda url, params=None: responses.pop(0)),
        post=Mock(return_value=FakeResponse()),
    )

    result = requester.get("https://example.com")

    assert result == {"items": [1, 2, 3]}
    assert requester.session.get.call_count == 3
    assert requester.session.post.call_count == 3
    assert logger.error.call_count == 2


def test_get_raises_after_three_failed_attempts():
    module, logger = load_requester_module()
    requester = module.VintedRequester()

    requester.session = SimpleNamespace(
        get=Mock(return_value=FakeResponse(error=RuntimeError("still failing"))),
        post=Mock(return_value=FakeResponse()),
    )

    with pytest.raises(RuntimeError, match="Failed to fetch https://example.com after 3 attempts"):
        requester.get("https://example.com")

    assert requester.session.get.call_count == 3
    assert requester.session.post.call_count == 4
    assert logger.error.call_count == 3
