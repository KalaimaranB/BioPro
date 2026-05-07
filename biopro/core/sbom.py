"""SBOM (Software Bill of Materials) Generator for BioPro Core & Plugins.

Supports CycloneDX JSON and human-readable Markdown outputs.
"""

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any


class SBOMGenerator:
    """Compiles software supply chain inventory for the BioPro core and active plugins."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.biopro_dir = Path.home() / ".biopro"

    def compile_sbom(self) -> dict[str, Any]:
        """Gathers system, core python library, and active plugin metadata."""
        components_list: list[dict[str, Any]] = []
        plugins_list: list[dict[str, Any]] = []

        sbom: dict[str, Any] = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{hashlib.sha256(str(platform.node()).encode()).hexdigest()[:32]}",
            "version": 1,
            "metadata": {
                "timestamp": importlib.metadata.version("biopro")
                if "biopro" in sys.modules
                else "2026-05-06T16:40:00Z",
                "tools": [
                    {
                        "vendor": "BioPro Authority",
                        "name": "BioPro SBOM Generator",
                        "version": "1.0.0",
                    }
                ],
                "component": {
                    "type": "application",
                    "name": "BioPro Core",
                    "version": self._get_core_version(),
                    "description": "Sleek, high-performance modular desktop scientific suite.",
                    "properties": [
                        {"name": "os_name", "value": platform.system()},
                        {"name": "os_release", "value": platform.release()},
                        {"name": "python_version", "value": platform.python_version()},
                    ],
                },
            },
            "components": components_list,
            "plugins": plugins_list,
        }

        # 1. Gather Core Pip Dependencies (from requirements.txt)
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            with open(req_file) as f:
                for line in f:
                    name = (
                        line.strip().split("[")[0].split("=")[0].split("<")[0].split(">")[0].strip()
                    )
                    if not name or name.startswith("#"):
                        continue

                    try:
                        version = importlib.metadata.version(name)
                    except Exception:
                        version = "Installed (Version Unknown)"

                    components_list.append(
                        {
                            "type": "library",
                            "name": name,
                            "version": version,
                            "purl": f"pkg:pypi/{name}@{version}",
                        }
                    )

        # 2. Gather Active Plugins Profile
        try:
            from biopro_sdk.core.trust_manager import TrustManager

            from biopro.core.module_manager import ModuleManager

            manager = ModuleManager()
            trust = TrustManager()

            for manifest in manager.get_available_modules():
                mod_id = manifest.get("id", "unknown")
                plugin_path = manager.user_plugins_dir / mod_id
                if not plugin_path.exists():
                    plugin_path = manager.internal_plugins_dir / mod_id

                # Verify and calculate integrity hashes
                v_res = trust.verify_plugin(plugin_path) if plugin_path.exists() else None
                status = "Verified" if v_res and v_res.success else "Unverified"
                if v_res and v_res.trust_level != "untrusted":
                    status = f"Trusted ({v_res.trust_level.capitalize()})"

                plugin_info = {
                    "id": mod_id,
                    "name": manifest.get("name", mod_id),
                    "version": manifest.get("version", "0.0.0"),
                    "author": manifest.get("author", "Unknown"),
                    "description": manifest.get("description", ""),
                    "trust_status": status,
                    "file_count": len(manifest.get("integrity", {}).get("hashes", {})),
                }
                plugins_list.append(plugin_info)
        except Exception as e:
            # Fallback if UI/core imports fail in headless contexts
            sbom["plugins_error"] = str(e)

        return sbom

    def to_json(self) -> str:
        """Returns the SBOM as a formatted CycloneDX JSON string."""
        return json.dumps(self.compile_sbom(), indent=4)

    def to_markdown(self) -> str:
        """Returns the SBOM as a beautifully formatted Markdown report."""
        data = self.compile_sbom()
        md = []
        md.append("# Software Bill of Materials (SBOM) — BioPro\n")

        # Metadata
        md.append("## 🖥️ System & Application Profile\n")
        md.append("| Property | Value |")
        md.append("| :--- | :--- |")
        md.append(
            f"| **Application** | BioPro Core (v{data['metadata']['component']['version']}) |"
        )
        md.append(f"| **Python Version** | {platform.python_version()} |")
        md.append(f"| **Operating System** | {platform.system()} ({platform.release()}) |")
        md.append(f"| **Architecture** | {platform.machine()} |")
        md.append("\n")

        # Plugins
        md.append("## 🔌 Installed Plugins & Security Audits\n")
        if data.get("plugins"):
            md.append("| Plugin ID | Name | Version | Author | Files Checked | Trust Status |")
            md.append("| :--- | :--- | :--- | :--- | :---: | :--- |")
            for p in data["plugins"]:
                md.append(
                    f"| `{p['id']}` | {p['name']} | v{p['version']} | {p['author']} | {p['file_count']} | **{p['trust_status']}** |"
                )
        else:
            md.append("*No plugins currently installed or loaded.*")
        md.append("\n")

        # Pip Components
        md.append("## 📦 Third-Party Python Dependencies\n")
        md.append("| Library Name | Version Installed | Pypi Package Link |")
        md.append("| :--- | :--- | :--- |")
        for comp in data["components"]:
            md.append(
                f"| `{comp['name']}` | {comp['version']} | [Pypi Page](https://pypi.org/project/{comp['name']}/{comp['version']}/) |"
            )

        return "\n".join(md)

    def _get_core_version(self) -> str:
        try:
            from biopro import __version__

            return __version__
        except Exception:
            return "1.0.0"
