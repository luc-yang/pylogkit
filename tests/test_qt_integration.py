import warnings
from pathlib import Path

import pytest

import pylogkit.qt_integration as qt_module
from pylogkit import LoggingNotInitializedError, attach_qt, init_logging, log
from pylogkit.qt_integration import QtLogHandler
from tests.conftest import wait_for_log_writes


def test_attach_qt_requires_initialization():
    with pytest.raises(LoggingNotInitializedError):
        attach_qt()


def test_attach_qt_requires_pyqt(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    with pytest.raises(RuntimeError, match="PyQt support is not available"):
        attach_qt()


def test_attach_qt_forwards_messages(monkeypatch, tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    class FakeQtHandler:
        def __init__(self, emitter=None, format_string=None):
            self.emitter = emitter
            self.format_string = format_string
            self.records = []
            self.buffer = []

        def emit(self, record):
            self.records.append(record)
            self.buffer.append(record["message"])

        def get_buffer(self):
            return list(self.buffer)

    monkeypatch.setattr(qt_module, "has_pyqt", lambda: True)
    monkeypatch.setattr(qt_module, "QtLogHandler", FakeQtHandler)

    handler = attach_qt(format_string="{level}::{message}")
    log.info("qt message")
    wait_for_log_writes()

    assert handler.records
    assert handler.records[0]["message"] == "qt message"
    assert handler.get_buffer() == ["qt message"]


def test_qt_log_handler_uses_format_string():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        handler = QtLogHandler(format_string="{level}::{message}")
    formatted = handler._format_message(
        {
            "time": "2026-03-15 10:00:00.000",
            "level": "INFO",
            "message": "hello",
            "name": "demo",
            "function": "test",
            "line": 1,
        }
    )

    assert formatted == "INFO::hello"
