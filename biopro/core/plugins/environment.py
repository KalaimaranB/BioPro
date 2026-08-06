"""Plugin environment path injection service."""

import importlib.metadata as metadata
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_DEP_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+")


class PluginEnvironmentInjector:
    """Manages the injection of isolated .venv paths into the global sys.path."""

    @staticmethod
    def inject_path(plugin_path: Path, internal_plugins_dir: Path) -> Path | None:  # noqa: C901
        """Inject a plugin's local packages and source directory into `sys.path`.

        Parameters:
            plugin_path (Path): Path to the plugin directory.
            internal_plugins_dir (Path): Directory used to position injected paths relative to
            application paths.

        Returns:
            Path | None: The plugin's site-packages directory that was injected, or `None`
            if no plugin environment was found.
        """
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidate_paths = [
            # Unix/macOS layout: lib/pythonX.Y/site-packages
            plugin_path / ".venv" / "lib" / py_ver / "site-packages",
            plugin_path / ".venv" / "lib" / py_ver / "site-packages",
            # Windows layout: Lib/site-packages (no version subdirectory)
            plugin_path / ".venv" / "Lib" / "site-packages",
            plugin_path / ".venv" / "Lib" / "site-packages",
        ]

        selected_path = None
        for candidate in candidate_paths:
            logger.debug(
                "Checking plugin site-packages candidate: %s exists=%s",
                candidate,
                candidate.exists(),
            )
            if candidate.exists():
                selected_path = candidate
                break

        if not selected_path:
            logger.warning(
                "No plugin Python environment found for %s. Checked: %s. "
                "This usually happens if the plugin was sideloaded locally without running the Store installer.",  # noqa: E501
                plugin_path,
                ", ".join(str(p) for p in candidate_paths),
            )
            return None

        # Insert the plugin site-packages before any application-bundle paths
        insert_index = 0
        try:
            app_root = str(internal_plugins_dir).split("biopro/plugins")[0]
            for idx, p in enumerate(sys.path):
                if p and str(p).startswith(app_root):
                    insert_index = idx
                    break
        except Exception as e:
            logger.debug(f"Failed to find insert index in sys.path: {e}")
            insert_index = 0

        if str(selected_path) in sys.path:
            current_idx = sys.path.index(str(selected_path))
            if current_idx > insert_index:
                # Move existing entry earlier to take precedence
                sys.path.pop(current_idx)
                sys.path.insert(insert_index, str(selected_path))
                logger.info(
                    "Moved existing plugin path earlier in sys.path: %s (to index %d)",
                    selected_path,
                    insert_index,
                )
        else:
            sys.path.insert(insert_index, str(selected_path))

        # V3 Architecture: Also inject the plugin's src directory if it exists
        src_dir = plugin_path / "src"
        if src_dir.exists() and src_dir.is_dir() and str(src_dir) not in sys.path:
            sys.path.insert(insert_index, str(src_dir))
            logger.info(
                "Dynamically injected plugin src path to sys.path at index %d: %s",
                insert_index,
                src_dir,
            )

        if selected_path:
            logger.info(
                "Dynamically injected plugin path to sys.path at index %d: %s",
                insert_index,
                selected_path,
            )
            PluginEnvironmentInjector._log_plugin_environment(plugin_path, selected_path)

        return selected_path

    @staticmethod
    def _installed_names(site_packages: Path) -> list[str]:
        """Enumerate importable module names actually installed in a site-packages dir.

        Deliberately based on what's *installed*, not just the plugin's own declared
        top-level dependencies (`pyproject.toml [project].dependencies`) — a plugin's
        manifest lists `flowkit`, not `bokeh`, yet bokeh is exactly the package that
        needs isolating, because it arrives transitively (flowkit depends on it). Any
        transitively-installed package is just as capable of colliding with a
        core-bundled copy, so all of them need to be covered here.

        Parameters:
            site_packages (Path): The plugin's own site-packages directory.

        Returns:
            list[str]: Best-effort importable names (falls back to the distribution
            name, hyphens normalized to underscores, for wheels without a
            top_level.txt — distribution name and import name can still differ, e.g.
            "pillow" imports as "PIL", but this is a defensive check, not a source of
            truth).
        """
        names: set[str] = set()
        try:
            for dist in metadata.distributions(path=[str(site_packages)]):
                top_level = None
                try:
                    top_level = dist.read_text("top_level.txt")
                except Exception:
                    top_level = None

                if top_level:
                    names.update(line.strip() for line in top_level.splitlines() if line.strip())
                else:
                    dist_name = dist.metadata.get("Name") or dist.name
                    if dist_name:
                        match = _DEP_NAME_RE.match(dist_name.strip())
                        if match:
                            names.add(match.group(0).replace("-", "_"))
        except Exception as e:
            logger.debug("Failed to enumerate installed packages in %s: %s", site_packages, e)

        return sorted(names)

    @staticmethod
    def enforce_priority(plugin_path: Path, site_packages: Path) -> list[str]:
        """Force the plugin's installed dependencies to resolve from its own environment.

        `sys.path` ordering (see `inject_path`) cannot override a module name that is
        already resolved in `sys.modules` — for example a partial copy claimed by a
        frozen PyInstaller build's importer, or a copy left behind by an earlier-loaded
        plugin. For each package actually installed in this plugin's own site-packages
        that is already present in `sys.modules` but not resolving from there, this
        purges it (and its submodules) so the next import re-resolves — now correctly
        finding the plugin's own copy via the path `inject_path` just placed first on
        `sys.path`.

        Parameters:
            plugin_path (Path): Path to the plugin directory (used only for logging).
            site_packages (Path): The plugin's own site-packages directory, as selected by
            `inject_path`.

        Returns:
            list[str]: Names that were purged and forced to re-resolve.
        """
        purged: list[str] = []
        site_packages_str = str(site_packages)

        for name in PluginEnvironmentInjector._installed_names(site_packages):
            mod = sys.modules.get(name)
            if mod is None:
                continue

            origin = getattr(mod, "__file__", None)
            if not origin:
                path_entries = list(getattr(mod, "__path__", []) or [])
                origin = path_entries[0] if path_entries else None

            if origin and str(origin).startswith(site_packages_str):
                continue  # Already resolving from the plugin's own environment.

            keys_to_remove = [k for k in sys.modules if k == name or k.startswith(f"{name}.")]
            for k in keys_to_remove:
                del sys.modules[k]

            purged.append(name)
            logger.warning(
                "Purged shadow copy of '%s' (was resolving from %s) so plugin %s can "
                "re-resolve its own copy from %s.",
                name,
                origin or "<unknown>",
                plugin_path.name,
                site_packages,
            )

        return purged

    @staticmethod
    def verify_isolation(names: list[str], site_packages: Path) -> list[str]:
        """Check whether previously-purged dependency names now resolve from the plugin's env.

        Call this after the plugin has actually imported (so `sys.modules` has been
        repopulated). A name still resolving outside `site_packages` means something
        claimed it again before `sys.path`/`PathFinder` could be consulted — most likely a
        frozen bundle's `sys.meta_path` importer. `enforce_priority`'s `sys.modules` purge
        cannot fix that case; the module simply must not be bundled into the core app.

        Parameters:
            names (list[str]): Dependency names to re-check (typically the list returned by
            a prior `enforce_priority` call).
            site_packages (Path): The plugin's own site-packages directory.

        Returns:
            list[str]: Names still resolving outside the plugin's site-packages.
        """
        site_packages_str = str(site_packages)
        still_shadowed = []
        for name in names:
            mod = sys.modules.get(name)
            if mod is None:
                continue

            origin = getattr(mod, "__file__", None)
            if not origin:
                path_entries = list(getattr(mod, "__path__", []) or [])
                origin = path_entries[0] if path_entries else None

            if not origin or not str(origin).startswith(site_packages_str):
                still_shadowed.append(name)

        return still_shadowed

    @staticmethod
    def _log_plugin_environment(plugin_path: Path, site_packages: Path) -> None:
        """Log the installed packages for a plugin environment when available.

        Parameters:
            plugin_path (Path): Path identifying the plugin.
            site_packages (Path): Site-packages directory to inspect.
        """
        try:
            distributions = list(metadata.distributions(path=[str(site_packages)]))
            packages = sorted(
                [(dist.metadata.get("Name", dist.name), dist.version) for dist in distributions],
                key=lambda item: item[0].lower() if item[0] else "",
            )
            if packages:
                package_list = ", ".join(f"{name}=={version}" for name, version in packages)
                logger.info(
                    "Plugin environment packages for %s: %s", plugin_path.name, package_list
                )  # noqa: E501
        except Exception as exc:
            logger.warning(
                "Failed to enumerate plugin environment packages for %s: %s",
                site_packages,
                exc,
            )

    @staticmethod
    def cleanup_paths() -> None:
        """Remove plugin virtual-environment site-packages entries from sys.path."""
        target_marker = str(Path(".biopro") / "plugins")
        for path in list(sys.path):
            norm_path = str(Path(path))
            if (
                target_marker in norm_path
                and (".venv" in norm_path or ".venv" in norm_path)
                and ("site-packages" in norm_path)
            ):
                sys.path.remove(path)
                logger.info(f"Cleaned up dynamic plugin path from sys.path: {path}")
