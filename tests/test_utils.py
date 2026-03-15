from pathlib import Path

from pylogkit import catch_exceptions, init_logging
from tests.conftest import wait_for_log_writes


def test_catch_exceptions_logs_traceback_to_main_log(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    @catch_exceptions(reraise=False)
    def broken():
        raise ValueError("boom")

    broken()
    wait_for_log_writes()

    log_files = sorted(tmp_path.glob("demo_*.log"))
    assert log_files

    content = log_files[0].read_text(encoding="utf-8")
    assert "Function broken raised an exception: boom" in content
    assert "ValueError: boom" in content


def test_catch_exceptions_supports_custom_logger():
    captured = []

    @catch_exceptions(reraise=False, logger_func=captured.append, message="custom")
    def broken():
        raise RuntimeError("fail")

    broken()

    assert captured == ["custom: fail"]

