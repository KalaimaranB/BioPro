import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from biopro.core.sbom import SBOMGenerator


@pytest.fixture
def mock_project_root(tmp_path):
    # Create a fake requirements.txt
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("requests==2.31.0\n# comment\npytest>=7.0.0\n")
    return tmp_path


class TestSBOMGenerator:
    def test_compile_sbom_basic(self, mock_project_root):
        generator = SBOMGenerator(project_root=mock_project_root)

        with patch("importlib.metadata.version", return_value="1.2.3"):
            sbom = generator.compile_sbom()

        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["metadata"]["component"]["name"] == "BioPro Core"

        # Check components from requirements.txt
        components = sbom["components"]
        assert any(c["name"] == "requests" and c["version"] == "1.2.3" for c in components)
        assert any(c["name"] == "pytest" and c["version"] == "1.2.3" for c in components)

    def test_compile_sbom_with_plugins(self, mock_project_root):
        generator = SBOMGenerator(project_root=mock_project_root)

        mock_manifests = [
            {"id": "test_p", "name": "Test Plugin", "version": "1.0.0", "author": "Dev"}
        ]

        with (
            patch(
                "biopro.core.module_manager.ModuleManager.get_available_modules",
                return_value=mock_manifests,
            ),
            patch("biopro_sdk.host.TrustManager.verify_plugin") as mock_verify,
            patch(
                "biopro.core.module_manager.ModuleManager.user_plugins_dir",
                Path("/tmp/plugins"),
                create=True,
            ),
            patch(
                "biopro.core.module_manager.ModuleManager.internal_plugins_dir",
                Path("/tmp/internal"),
                create=True,
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_verify.return_value = MagicMock(success=True, trust_level="verified")

            sbom = generator.compile_sbom()

            assert len(sbom["plugins"]) == 1
            plugin = sbom["plugins"][0]
            assert plugin["id"] == "test_p"
            assert plugin["trust_status"] == "Trusted (Verified)"

    def test_to_json(self, mock_project_root):
        generator = SBOMGenerator(project_root=mock_project_root)
        with patch.object(generator, "compile_sbom", return_value={"test": "data"}):
            json_str = generator.to_json()
            assert json.loads(json_str) == {"test": "data"}

    def test_to_markdown(self, mock_project_root):
        generator = SBOMGenerator(project_root=mock_project_root)
        mock_data = {
            "metadata": {"component": {"version": "1.0.0"}},
            "plugins": [
                {
                    "id": "p1",
                    "name": "P1",
                    "version": "1.1",
                    "author": "A",
                    "file_count": 5,
                    "trust_status": "Verified",
                }
            ],
            "components": [{"name": "lib1", "version": "2.0"}],
        }
        with (
            patch.object(generator, "compile_sbom", return_value=mock_data),
            patch("platform.system", return_value="Darwin"),
            patch("platform.release", return_value="20.0.0"),
            patch("platform.python_version", return_value="3.14"),
            patch("platform.machine", return_value="arm64"),
        ):
            md = generator.to_markdown()
            assert "# Software Bill of Materials" in md
            assert "BioPro Core (v1.0.0)" in md
            assert "P1" in md
            assert "lib1" in md

    def test_get_core_version_fallback(self, mock_project_root):
        generator = SBOMGenerator(project_root=mock_project_root)
        import sys

        with patch.dict(sys.modules, {"biopro": None}):
            assert generator._get_core_version() == "1.0.0"
