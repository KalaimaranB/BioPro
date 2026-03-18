"""Basic sanity checks to ensure the test suite is configured correctly."""

def test_environment_is_sane():
    """If this fails, the universe is broken."""
    assert 1 + 1 == 2

def test_imports_work():
    """Ensures our test suite can 'see' the biopro core package."""
    import biopro.core.config
    assert biopro.core.config.AppConfig is not None