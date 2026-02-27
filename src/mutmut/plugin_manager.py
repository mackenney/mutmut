import os
import warnings

import pluggy

from mutmut.hookspecs import MutmutHookSpec

_pm = None


def get_plugin_manager() -> pluggy.PluginManager:
    global _pm
    if _pm is not None:
        return _pm
    _pm = pluggy.PluginManager("mutmut")
    _pm.add_hookspecs(MutmutHookSpec)
    if not os.environ.get("MUTMUT_DISABLE_PLUGIN_AUTOLOAD"):
        try:
            _pm.load_setuptools_entrypoints("mutmut")
        except Exception as e:
            warnings.warn(f"Failed to load mutmut plugins: {e}")
    return _pm


def reset_plugin_manager():
    """For testing: reset singleton so plugins can be re-registered."""
    global _pm
    _pm = None
