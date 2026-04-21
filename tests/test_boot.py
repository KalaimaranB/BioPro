import os
import sys
from pathlib import Path
import unittest

# Add the project root to sys.path so we can import biopro
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from biopro.core.config import AppConfig
from biopro.core.module_manager import ModuleManager
from biopro.core.trust_manager import TrustManager

class TestBioProBoot(unittest.TestCase):
    """Smoke tests to verify the core application can boot without crashes."""

    def setUp(self):
        # We use the real AppConfig but it targets ~/.biopro which should be writable
        self.config = AppConfig()
        
    def test_trust_manager_write_access(self):
        """Verify TrustManager can write debug logs without OSError."""
        tm = TrustManager()
        # Create a dummy plugin path
        dummy_plugin = project_root / "biopro" / "plugins" / "sdk_utils.py" # Use an existing file as a path
        
        try:
            # This triggers the debug log write we just fixed
            tm.verify_plugin(dummy_plugin)
        except OSError as e:
            self.fail(f"TrustManager raised OSError during verification: {e}")
        except Exception as e:
            # We don't care if verification fails logically, as long as it doesn't crash
            pass

    def test_module_manager_discovery(self):
        """Verify ModuleManager can discover plugins without crashing."""
        try:
            mm = ModuleManager()
            # If we got here, __init__ succeeded (which includes _discover_modules)
            self.assertIsNotNone(mm.modules)
        except Exception as e:
            self.fail(f"ModuleManager failed to initialize: {e}")

if __name__ == "__main__":
    unittest.main()
