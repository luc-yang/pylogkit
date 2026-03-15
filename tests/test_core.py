import inspect
import json
import logging
from pathlib import Path

import pytest

from pylogkit import (
    LoggingNotInitializedError,
    audit,
    init_logging,
    log,
    shutdown_logging,
)
from tests.conftest import wait_for_log_writes


def _read_main_log(log_dir: Path, app_name: str) -> str:
    log_files = sorted(log_dir.glob(f"{app_name}_*.log"))
    assert log_files, "expected main log file to exist"
    return log_files[0].read_text(encoding="utf-8")


def _read_audit_lines(log_dir: Path) -> list[str]:
    audit_files = sorted((log_dir / "audit").glob("audit_*.jsonl"))
    assert audit_files, "expected audit log file to exist"
    return [line for line in audit_files[0].read_text(encoding="utf-8").splitlines() if line]


def test_log_requires_initialization():
    with pytest.raises(LoggingNotInitializedError):
        log.info("not ready")


def test_init_logging_writes_main_and_audit_logs(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    log.info("hello {}", "world")
    audit.info("user_login", user="alice")
    wait_for_log_writes()

    main_content = _read_main_log(tmp_path, "demo")
    audit_lines = _read_audit_lines(tmp_path)

    assert "hello world" in main_content
    assert len(audit_lines) == 1
    assert json.loads(audit_lines[0])["action"] == "user_login"


def test_reinitialization_replaces_previous_runtime(tmp_path: Path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    init_logging("demo", log_dir=first_dir, console_output=False)
    log.info("first run")
    wait_for_log_writes()

    init_logging("demo", log_dir=second_dir, console_output=False)
    log.info("second run")
    wait_for_log_writes()

    first_content = _read_main_log(first_dir, "demo")
    second_content = _read_main_log(second_dir, "demo")

    assert "first run" in first_content
    assert "second run" not in first_content
    assert "second run" in second_content


def test_log_caller_points_to_business_code(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    def business_call():
        line_no = inspect.currentframe().f_lineno + 1
        log.info("caller check")
        return line_no

    line_no = business_call()
    wait_for_log_writes()

    content = _read_main_log(tmp_path, "demo")
    assert f"business_call:{line_no}" in content


def test_bind_and_opt_keep_caller_context(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    def business_call():
        bind_line = inspect.currentframe().f_lineno + 1
        log.bind(user="alice").warning("bound")
        opt_line = inspect.currentframe().f_lineno + 1
        log.opt(depth=0).error("opted")
        return bind_line, opt_line

    bind_line, opt_line = business_call()
    wait_for_log_writes()

    content = _read_main_log(tmp_path, "demo")
    assert f"business_call:{bind_line}" in content
    assert f"business_call:{opt_line}" in content
    assert "bound" in content
    assert "opted" in content


def test_stdlib_logging_is_captured_once(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    logging.getLogger("stdlib.demo").warning("stdlib warning")
    wait_for_log_writes()

    content = _read_main_log(tmp_path, "demo")
    assert content.count("stdlib warning") == 1


def test_audit_logs_are_isolated_from_main_logs(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)

    log.info("plain log")
    audit.info("user_login", user="bob")
    wait_for_log_writes()

    main_content = _read_main_log(tmp_path, "demo")
    audit_lines = _read_audit_lines(tmp_path)

    assert "plain log" in main_content
    assert "\"action\": \"user_login\"" not in main_content

    parsed = json.loads(audit_lines[0])
    assert parsed["action"] == "user_login"
    assert parsed["data"]["user"] == "bob"
    assert "plain log" not in audit_lines[0]


def test_shutdown_blocks_future_logging(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False)
    shutdown_logging()

    with pytest.raises(LoggingNotInitializedError):
        log.info("after shutdown")

    with pytest.raises(LoggingNotInitializedError):
        audit.info("after_shutdown")


def test_audit_disabled_raises_when_used(tmp_path: Path):
    init_logging("demo", log_dir=tmp_path, console_output=False, audit_enabled=False)

    with pytest.raises(RuntimeError, match="Audit logging is disabled"):
        audit.info("user_login")
