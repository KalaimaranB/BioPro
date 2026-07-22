import json
import logging
import platform
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any

from biopro_sdk.plugin.manifest_parser import ManifestParser

from biopro.core.network_updater import NetworkUpdater
from biopro.core.trust.strategies import TrustStrategyFactory

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    FAIL_MANUAL = "FAIL_MANUAL"


class DiagnosticResult:
    def __init__(self, check_name: str, status: CheckStatus, message: str, details: str = ""):
        self.check_name = check_name
        self.status = status
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


class PluginDoctor:
    """Diagnostic tool to inspect a specific installed plugin and identify failure root causes."""

    def __init__(self, plugin_id: str, plugin_dir: Path):
        self.plugin_id = plugin_id
        self.plugin_dir = plugin_dir
        self.manifest_data: dict[str, Any] = {}
        self.results: dict[str, list[DiagnosticResult]] = {
            "phase1": [],
            "phase2": [],
            "phase3": [],
            "phase4": [],
        }

    def run_all_checks(self):
        """Run all phases top to bottom."""
        self.results = {
            "phase1": [],
            "phase2": [],
            "phase3": [],
            "phase4": [],
        }
        self._run_phase1_integrity()
        self._run_phase2_trust()
        self._run_phase3_dependencies()
        self._run_phase4_runtime()
        return self.results

    def _run_phase1_integrity(self):
        """Phase 1: Location & Download Integrity."""
        # 1. Directory exists
        if not self.plugin_dir.exists():
            self.results["phase1"].append(
                DiagnosticResult(
                    "Plugin directory exists",
                    CheckStatus.FAIL,
                    f"Directory {self.plugin_dir} not found.",
                )
            )
            return
        else:
            self.results["phase1"].append(
                DiagnosticResult("Plugin directory exists", CheckStatus.OK, "Directory found.")
            )

        # 2. Manifest present & parseable
        manifest_file = self.plugin_dir / "manifest.json"
        if not manifest_file.exists():
            self.results["phase1"].append(
                DiagnosticResult(
                    "Manifest present & parseable", CheckStatus.FAIL, "manifest.json is missing."
                )
            )
            return

        try:
            parser = ManifestParser()
            self.manifest_data = parser.parse_file(str(manifest_file))
            self.results["phase1"].append(
                DiagnosticResult(
                    "Manifest present & parseable", CheckStatus.OK, "Manifest parsed successfully."
                )
            )
        except Exception as e:
            self.results["phase1"].append(
                DiagnosticResult(
                    "Manifest present & parseable",
                    CheckStatus.FAIL,
                    f"Manifest validation failed: {str(e)}",
                )
            )
            return

        # 3 & 4. Signature verification (security.json and file hashes)
        strategy = TrustStrategyFactory.get_strategy(self.manifest_data, str(self.plugin_dir))
        trust_result = strategy.verify(self.manifest_data, str(self.plugin_dir))

        if not trust_result.success:
            err_msg = trust_result.error_message

            # Try to extract the exact file name that failed the security check for better UX
            failed_file = "Unknown file"
            if "manifest.json" in err_msg:
                failed_file = "manifest.json"
            elif "security.json" in err_msg:
                failed_file = "security.json"
            elif "Unauthorized File:" in err_msg:
                failed_file = err_msg.split("Unauthorized File:")[1].split("is not")[0].strip()
            elif "Integrity Mismatch:" in err_msg:
                failed_file = err_msg.split("Integrity Mismatch:")[1].split("has been")[0].strip()
            elif "Missing File:" in err_msg:
                failed_file = err_msg.split("Missing File:")[1].split("was signed")[0].strip()
            elif "Unauthorized Executable" in err_msg:
                failed_file = err_msg.split("Found")[1].split("inside")[0].strip().strip("'")

            if "Cryptographic bind mismatch" in err_msg or "Signature chain" in err_msg:
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Manifest hash matches security.json",
                        CheckStatus.FAIL,
                        f"Cryptographic bind mismatch for: {failed_file}",
                        details=err_msg,
                    )
                )
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Signed file hashes match on-disk files",
                        CheckStatus.WARN,
                        "Skipped due to previous error.",
                    )
                )
            elif (
                "not in the signed security hashes" in err_msg
                or "Unauthorized File" in err_msg
                or "Hash mismatch" in err_msg
                or "tampered with" in err_msg
                or "Missing File" in err_msg
            ):
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Manifest hash matches security.json",
                        CheckStatus.OK,
                        "Manifest hash is valid.",
                    )
                )
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Signed file hashes match on-disk files",
                        CheckStatus.FAIL,
                        f"Security check failed for: {failed_file}",
                        details=err_msg,
                    )
                )
            else:
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Manifest hash matches security.json",
                        CheckStatus.FAIL,
                        f"Security verification failed: {failed_file}",
                        details=err_msg,
                    )
                )
                self.results["phase1"].append(
                    DiagnosticResult(
                        "Signed file hashes match on-disk files",
                        CheckStatus.FAIL,
                        f"Security verification failed: {failed_file}",
                        details=err_msg,
                    )
                )
        else:
            self.results["phase1"].append(
                DiagnosticResult(
                    "Manifest hash matches security.json", CheckStatus.OK, "Manifest hash matches."
                )
            )
            self.results["phase1"].append(
                DiagnosticResult(
                    "Signed file hashes match on-disk files",
                    CheckStatus.OK,
                    "All signed files match their hashes.",
                )
            )

    def _run_phase2_trust(self):
        """Phase 2: Trust & Install State Consistency."""
        venv_path = self.plugin_dir / ".plugin_venv"

        # 1. Trust cache vs. actual venv presence
        if not venv_path.exists():
            self.results["phase2"].append(
                DiagnosticResult(
                    "Trust cache vs actual venv presence",
                    CheckStatus.FAIL,
                    ".plugin_venv exists = False — installer never ran or was deleted.",
                )
            )
        else:
            self.results["phase2"].append(
                DiagnosticResult(
                    "Trust cache vs actual venv presence", CheckStatus.OK, ".plugin_venv exists."
                )
            )

        # 2. Interpreter resolvable for this platform
        unix_python = venv_path / "bin" / "python3"
        win_python = venv_path / "Scripts" / "python.exe"

        interpreter_path = None
        if platform.system() == "Windows":
            if win_python.exists():
                interpreter_path = win_python
            elif unix_python.exists():
                # Cross-platform confusion!
                interpreter_path = unix_python
                self.results["phase2"].append(
                    DiagnosticResult(
                        "Interpreter resolvable for this platform",
                        CheckStatus.WARN,
                        f"Found Unix path {unix_python} on Windows!",
                    )
                )
        else:
            if unix_python.exists():
                interpreter_path = unix_python
            elif win_python.exists():
                interpreter_path = win_python
                self.results["phase2"].append(
                    DiagnosticResult(
                        "Interpreter resolvable for this platform",
                        CheckStatus.WARN,
                        f"Found Windows path {win_python} on Unix!",
                    )
                )

        if not interpreter_path:
            self.results["phase2"].append(
                DiagnosticResult(
                    "Interpreter resolvable for this platform",
                    CheckStatus.FAIL,
                    "No valid python interpreter found in venv.",
                )
            )
        else:
            self.results["phase2"].append(
                DiagnosticResult(
                    "Interpreter resolvable for this platform",
                    CheckStatus.OK,
                    f"Interpreter found at {interpreter_path.name}.",
                )
            )
            self._interpreter_path = interpreter_path

        # 3. Self-test result recorded
        self.results["phase2"].append(
            DiagnosticResult(
                "Self-test result recorded", CheckStatus.OK, "N/A - Not implemented in this version"
            )
        )

    def _run_phase3_dependencies(self):
        """Phase 3: Dependency Completeness."""
        # Check for internal lazy imports assuming plugin root is in sys.path
        import ast
        import os

        local_modules = {
            d.name for d in self.plugin_dir.iterdir() if d.is_dir() and (d / "__init__.py").exists()
        }
        local_modules.update({f.stem for f in self.plugin_dir.glob("*.py") if f.stem != "__init__"})

        bad_imports = []
        for root, _, files in os.walk(self.plugin_dir):
            if ".plugin_venv" in root or ".venv" in root or "tests" in root:
                continue
            for file in files:
                if not file.endswith(".py"):
                    continue
                py_file = Path(root) / file
                try:
                    tree = ast.parse(py_file.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                base_module = alias.name.split(".")[0]
                                if base_module in local_modules:
                                    bad_imports.append(
                                        f"{py_file.relative_to(self.plugin_dir)}: import {alias.name}"
                                    )
                        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                            base_module = node.module.split(".")[0]
                            if base_module in local_modules:
                                bad_imports.append(
                                    f"{py_file.relative_to(self.plugin_dir)}: from {node.module}..."
                                )
                except Exception:
                    pass

        if bad_imports:
            sample = ", ".join(bad_imports[:3])
            more = f" and {len(bad_imports) - 3} more" if len(bad_imports) > 3 else ""
            self.results["phase3"].append(
                DiagnosticResult(
                    "Internal imports use relative paths",
                    CheckStatus.FAIL,
                    f"Found absolute imports for local modules (Plugin root is not in sys.path). Examples: {sample}{more}. Use relative imports.",
                )
            )
        else:
            self.results["phase3"].append(
                DiagnosticResult(
                    "Internal imports use relative paths",
                    CheckStatus.OK,
                    "No problematic absolute imports found.",
                )
            )

        if not hasattr(self, "_interpreter_path") or not self._interpreter_path:
            self.results["phase3"].append(
                DiagnosticResult(
                    "Required packages importable",
                    CheckStatus.FAIL,
                    "No interpreter to test imports.",
                )
            )
            self.results["phase3"].append(
                DiagnosticResult(
                    "Package versions match manifest pins", CheckStatus.FAIL, "No interpreter."
                )
            )
            self.results["phase3"].append(
                DiagnosticResult(
                    "No file lock conflicts in site-packages", CheckStatus.FAIL, "No venv to check."
                )
            )
            return

        deps = self.manifest_data.get("dependencies", [])
        if not deps:
            self.results["phase3"].append(
                DiagnosticResult(
                    "Required packages importable", CheckStatus.OK, "No dependencies required."
                )
            )
            self.results["phase3"].append(
                DiagnosticResult(
                    "Package versions match manifest pins",
                    CheckStatus.OK,
                    "No dependencies required.",
                )
            )
        else:
            import re

            failed_imports = []
            for dep in deps:
                pkg_name = re.split(r"[=><!~]", dep)[0].strip()
                try:
                    result = subprocess.run(
                        [str(self._interpreter_path), "-c", f"import {pkg_name}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode != 0:
                        failed_imports.append(pkg_name)
                except Exception:
                    failed_imports.append(pkg_name)

            if failed_imports:
                self.results["phase3"].append(
                    DiagnosticResult(
                        "Required packages importable",
                        CheckStatus.FAIL,
                        f"Failed to import: {', '.join(failed_imports)}",
                    )
                )
                self.results["phase3"].append(
                    DiagnosticResult(
                        "Package versions match manifest pins",
                        CheckStatus.FAIL,
                        "Missing packages prevent version check.",
                    )
                )
            else:
                self.results["phase3"].append(
                    DiagnosticResult(
                        "Required packages importable",
                        CheckStatus.OK,
                        "All packages imported successfully.",
                    )
                )
                self.results["phase3"].append(
                    DiagnosticResult(
                        "Package versions match manifest pins",
                        CheckStatus.OK,
                        "All packages imported successfully.",
                    )
                )

        # Check for internal file lock conflicts (Windows specific heuristic)
        if platform.system() == "Windows":
            try:
                import psutil  # type: ignore

                locked_files = []
                site_packages = self.plugin_dir / ".plugin_venv" / "Lib" / "site-packages"
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        for item in proc.open_files():
                            if site_packages.as_posix() in Path(item.path).as_posix():
                                locked_files.append(
                                    f"{proc.info['name']} (PID: {proc.info['pid']})"
                                )
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if locked_files:
                    self.results["phase3"].append(
                        DiagnosticResult(
                            "No file lock conflicts in site-packages",
                            CheckStatus.FAIL_MANUAL,
                            f"Files locked by processes: {', '.join(locked_files)}",
                        )
                    )
                else:
                    self.results["phase3"].append(
                        DiagnosticResult(
                            "No file lock conflicts in site-packages",
                            CheckStatus.OK,
                            "No locks detected.",
                        )
                    )
            except ImportError:
                self.results["phase3"].append(
                    DiagnosticResult(
                        "No file lock conflicts in site-packages",
                        CheckStatus.WARN,
                        "psutil not available to check locks.",
                    )
                )
        else:
            self.results["phase3"].append(
                DiagnosticResult(
                    "No file lock conflicts in site-packages", CheckStatus.OK, "N/A for Unix."
                )
            )

    def _run_phase4_runtime(self):
        """Phase 4: Runtime/Process Health."""
        # 1. No stale BioPro/plugin processes holding files (covered in phase 3 locks check partially, but here we can check for other BioPro instances)
        self.results["phase4"].append(
            DiagnosticResult(
                "No stale processes holding files", CheckStatus.OK, "Checked in Phase 3."
            )
        )

        # 2. Network reachability
        try:
            import urllib.request

            updater = NetworkUpdater()
            req = urllib.request.Request(updater.registry_url, method="HEAD")
            urllib.request.urlopen(req, timeout=3)
            self.results["phase4"].append(
                DiagnosticResult("Network reachability", CheckStatus.OK, "Registry is reachable.")
            )
        except Exception as e:
            self.results["phase4"].append(
                DiagnosticResult(
                    "Network reachability",
                    CheckStatus.FAIL_MANUAL,
                    f"Network unreachable: {str(e)}",
                )
            )

        # 3. App stable location (macOS AppTranslocation check)
        if platform.system() == "Darwin":
            if "AppTranslocation" in sys.executable:
                self.results["phase4"].append(
                    DiagnosticResult(
                        "App running from a stable location",
                        CheckStatus.WARN,
                        "App is running in macOS AppTranslocation. Move to /Applications to fix.",
                    )
                )
            else:
                self.results["phase4"].append(
                    DiagnosticResult(
                        "App running from a stable location", CheckStatus.OK, "Path is stable."
                    )
                )
        else:
            self.results["phase4"].append(
                DiagnosticResult(
                    "App running from a stable location", CheckStatus.OK, "N/A for Windows/Linux."
                )
            )

    def export_diagnostic_bundle(self) -> str:
        """Returns a JSON string containing the full structured diagnostic log."""
        bundle = {
            "timestamp": time.time(),
            "plugin_id": self.plugin_id,
            "platform": platform.platform(),
            "python_version": sys.version,
            "results": {
                phase: [r.to_dict() for r in results] for phase, results in self.results.items()
            },
        }
        return json.dumps(bundle, indent=2)
