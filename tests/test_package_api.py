import pylogkit

EXPECTED_EXPORTS = {
    "__version__",
    "LogConfig",
    "LoggingNotInitializedError",
    "attach_qt",
    "audit",
    "catch_exceptions",
    "init_logging",
    "log",
    "shutdown_logging",
}


def test_public_exports_are_available():
    assert set(pylogkit.__all__) == EXPECTED_EXPORTS

    for name in EXPECTED_EXPORTS:
        assert hasattr(pylogkit, name)
