import time

import pytest

from pylogkit import shutdown_logging


@pytest.fixture(autouse=True)
def reset_logging_runtime():
    shutdown_logging()
    yield
    shutdown_logging()


def wait_for_log_writes() -> None:
    time.sleep(0.25)

