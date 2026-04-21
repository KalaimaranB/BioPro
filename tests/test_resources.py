import unittest
from pathlib import Path
import sys

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from biopro.core.resource_manager import resource_path

class TestBioProResources(unittest.TestCase):
    """Verifies that all critical assets and themes are present and solvable."""

    def test_core_icon_exists(self):
        """Verify the main application icon is in the correct location."""
        # Our updated .spec and __main__.py expect icon.icns at the root (or MEIPASS root)
        path = resource_path("icon.icns")
        self.assertTrue(path.exists(), f"CRITICAL: Application icon missing at {path}")

    def test_themes_exist(self):
        """Verify that the default and supplemental themes are present."""
        themes = ["themes/default.json", "themes/star_wars.json"]
        for t in themes:
            path = resource_path(t)
            self.assertTrue(path.exists(), f"CRITICAL: Theme file missing: {t}")

    def test_path_resolution_integrity(self):
        """Ensure resource_path isn't returning 'phantom' paths in biopro/ subfolders."""
        # Test a known internal file
        path = resource_path("biopro/core/config.py")
        self.assertTrue(path.exists(), "resource_path failed to resolve an internal core module")

if __name__ == "__main__":
    unittest.main()
