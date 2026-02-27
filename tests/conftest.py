import os

import pytest

from mutmut.plugin_manager import reset_plugin_manager


@pytest.fixture(autouse=True, scope="session")
def _disable_plugin_autoload():
    """Prevent third-party plugins from loading during core tests."""
    os.environ["MUTMUT_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    reset_plugin_manager()
    yield
    os.environ.pop("MUTMUT_DISABLE_PLUGIN_AUTOLOAD", None)
    reset_plugin_manager()
