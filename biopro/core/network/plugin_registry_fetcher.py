"""Decentralized plugin registry fetcher.

Fetches each plugin's own ``pyproject.toml`` from its GitHub repository,
reads the ``[tool.biopro.plugin]`` section for store-display metadata
(icon, tags, homepage, rich author info), caches the result locally, and
enriches the store inventory built from the slim Distribution index.
"""

from __future__ import annotations

import contextlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from biopro.core.config import AppConfig
from biopro.core.network.client import NetworkClient

logger = logging.getLogger(__name__)

# Raw-content URL template: github.com → raw.githubusercontent.com/<branch>/pyproject.toml
_RAW_TEMPLATE = "https://raw.githubusercontent.com/{owner}/{repo}/main/pyproject.toml"


class PluginRegistryFetcher:
    """Fetches, caches, and enriches plugin metadata from each plugin's own pyproject.toml."""

    # ── URL derivation ──────────────────────────────────────────────────────

    @staticmethod
    def derive_manifest_url(repo_url: str) -> str | None:
        """Derive the raw ``pyproject.toml`` URL from a GitHub repository URL.

        Parameters:
            repo_url (str): GitHub repository URL, e.g.
                ``https://github.com/KalaimaranB/BioPro-flow-cytometry``.

        Returns:
            str | None: The raw-content URL, or ``None`` if the URL cannot be parsed.
        """
        try:
            parsed = urlparse(repo_url.rstrip("/"))
            parts = parsed.path.strip("/").split("/")
            if len(parts) < 2:
                logger.warning(
                    "Cannot derive manifest URL — repo_url has no owner/repo: %s",
                    repo_url,
                )  # noqa: E501
                return None
            owner, repo = parts[0], parts[1]
            return _RAW_TEMPLATE.format(owner=owner, repo=repo)
        except Exception:
            logger.warning("Failed to parse repo_url: %s", repo_url, exc_info=True)
            return None

    # ── Cache helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _cache_path(plugin_id: str) -> Path:
        return AppConfig.PLUGIN_REGISTRY_CACHE_DIR / f"{plugin_id}.toml"

    @staticmethod
    def _timestamp_path(plugin_id: str) -> Path:
        return AppConfig.PLUGIN_REGISTRY_CACHE_DIR / f"{plugin_id}.timestamp"

    @classmethod
    def is_cache_valid(cls, plugin_id: str) -> bool:
        """Return ``True`` when a fresh cached ``pyproject.toml`` exists for *plugin_id*."""
        ts_file = cls._timestamp_path(plugin_id)
        if not ts_file.exists():
            return False
        try:
            ts = float(ts_file.read_text().strip())
            return (time.time() - ts) < AppConfig.PLUGIN_REGISTRY_CACHE_TTL_SECONDS
        except Exception:
            return False

    @classmethod
    def _write_cache(cls, plugin_id: str, raw_toml: str) -> None:
        AppConfig.PLUGIN_REGISTRY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls._cache_path(plugin_id).write_text(raw_toml, encoding="utf-8")
        cls._timestamp_path(plugin_id).write_text(str(time.time()), encoding="utf-8")

    @classmethod
    def _read_cache(cls, plugin_id: str) -> dict[str, Any] | None:
        try:
            import tomllib

            raw = cls._cache_path(plugin_id).read_bytes()
            return tomllib.loads(raw.decode("utf-8"))
        except Exception:
            return None

    @classmethod
    def invalidate_cache(cls) -> None:
        """Delete all cached plugin manifests (called by the manual Refresh button)."""
        cache_dir = AppConfig.PLUGIN_REGISTRY_CACHE_DIR
        if not cache_dir.exists():
            return
        for f in cache_dir.iterdir():
            if f.suffix in {".toml", ".timestamp"}:
                with contextlib.suppress(Exception):
                    f.unlink()
        logger.info("Plugin registry cache cleared.")

    # ── Fetch ───────────────────────────────────────────────────────────────

    @classmethod
    def fetch(cls, plugin_id: str, repo_url: str) -> dict[str, Any] | None:
        """Fetch the full ``pyproject.toml`` manifest from a plugin's repository.

        Uses the local disk cache when it is still within the TTL, otherwise
        performs a live HTTP GET and refreshes the cache.

        Parameters:
            plugin_id (str): Plugin identifier used as the cache key.
            repo_url (str): GitHub repository URL to derive the manifest URL from.

        Returns:
            dict | None: The parsed TOML dict, or ``None`` on failure.
        """
        if cls.is_cache_valid(plugin_id):
            cached = cls._read_cache(plugin_id)
            if cached is not None:
                logger.debug("Plugin registry cache hit for '%s'.", plugin_id)
                return cached

        manifest_url = cls.derive_manifest_url(repo_url)
        if not manifest_url:
            return None

        try:
            response = NetworkClient.get(manifest_url, timeout=10)
            if response.status_code == 404:
                logger.debug(
                    "No pyproject.toml found at %s (404) — skipping enrichment.",
                    manifest_url,
                )
                return None
            response.raise_for_status()

            raw_toml = response.text
            cls._write_cache(plugin_id, raw_toml)

            import tomllib

            return tomllib.loads(raw_toml)
        except Exception:
            logger.warning(
                "Failed to fetch plugin manifest for '%s' from %s "
                "— using cached data if available.",
                plugin_id,
                manifest_url,
                exc_info=True,
            )
            # Attempt stale cache as graceful fallback
            return cls._read_cache(plugin_id)

    # ── Enrichment ──────────────────────────────────────────────────────────

    @staticmethod
    def enrich_entry(  # noqa: E501
        store_entry: dict[str, Any], plugin_manifest: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge ``[tool.biopro.plugin]`` fields into a store inventory entry.

        Parameters:
            store_entry (dict): An entry from the store inventory (the ``info`` sub-dict).
            plugin_manifest (dict): The full parsed ``pyproject.toml`` table.

        Returns:
            dict: The enriched ``store_entry["info"]`` dict (mutated in place and returned).
        """
        info = store_entry.get("info", store_entry)

        plugin_table = plugin_manifest.get("tool", {}).get("biopro", {}).get("plugin", {})
        project_table = plugin_manifest.get("project", {})

        # 1. Use display_name for the name in store
        display_name = plugin_table.get("display_name")
        if display_name:
            info["name"] = display_name
        elif "name" in project_table:
            info["name"] = project_table["name"]

        # 4. Parse version and min_core_version parameters correctly
        if "version" in project_table:
            info["version"] = project_table["version"]

        if "min_core_version" in plugin_table:
            info["min_core_version"] = plugin_table["min_core_version"]

        # Standard metadata mapping
        for field in ("description", "icon", "tags", "homepage", "is_beta", "beta"):
            value = plugin_table.get(field)
            if value is not None:
                info[field] = value

        # Map authors and contributors
        authors = plugin_table.get("authors")
        if authors and isinstance(authors, list):
            info["authors"] = authors

        # 5. Extract contributors as well
        contributors = plugin_table.get("contributors")
        if contributors and isinstance(contributors, list):
            info["contributors"] = contributors

        return info

    # ── Batch fetch ─────────────────────────────────────────────────────────

    @classmethod
    def fetch_all(cls, store_inventory: dict[str, Any]) -> dict[str, Any]:
        """Eagerly fetch and enrich all plugins in *store_inventory* in parallel.

        For each entry that contains a ``repo_url``, derives the ``pyproject.toml``
        URL, fetches it (with cache), and merges the metadata into the entry.
        Plugins without a ``repo_url`` or that fail parsing are removed from the store inventory.

        Parameters:
            store_inventory (dict): Mapping of plugin_id → store entry dict.

        Returns:
            dict: The same *store_inventory* dict, enriched in place (invalid plugins removed).
        """
        to_fetch: list[tuple[str, str]] = []
        for plugin_id, entry in store_inventory.items():
            repo_url = entry.get("info", {}).get("repo_url")
            if repo_url:
                to_fetch.append((plugin_id, repo_url))

        if not to_fetch:
            return store_inventory

        successful_plugins = set()

        def _fetch_one(args: tuple[str, str]) -> tuple[str, dict[str, Any] | None]:
            pid, url = args
            return pid, cls.fetch(pid, url)

        with ThreadPoolExecutor(max_workers=min(8, len(to_fetch))) as executor:
            futures = {executor.submit(_fetch_one, args): args[0] for args in to_fetch}
            for future in as_completed(futures):
                plugin_id = futures[future]
                try:
                    pid, manifest = future.result()
                    if manifest:
                        cls.enrich_entry(store_inventory[pid], manifest)
                        successful_plugins.add(pid)
                        logger.debug("Enriched store entry for '%s' from plugin manifest.", pid)
                except Exception:
                    logger.warning(
                        "Failed to enrich store entry for '%s'.",
                        plugin_id,
                        exc_info=True,
                    )

        # 3. If a module's toml can not be fully parsed, it should not be rendered.
        fetch_pids = [p[0] for p in to_fetch]
        for pid in list(store_inventory.keys()):
            if pid in fetch_pids and pid not in successful_plugins:
                del store_inventory[pid]

        return store_inventory
