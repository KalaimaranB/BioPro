"""Trust and developer syncing for BioPro network updates."""

import contextlib
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from biopro_sdk.host import BIOPRO_ROOT_PUBLIC_KEY_HEX
from cryptography.hazmat.primitives.asymmetric import ed25519

from biopro.core.config import AppConfig
from biopro.core.network.client import NetworkClient
from biopro.core.utils import sanitize_identifier

logger = logging.getLogger(__name__)


class TrustSync:
    """Handles syncing cryptographic keys and developer profiles."""

    @staticmethod
    def sync_keys(trusted_list: list[dict[str, Any]], prefix: str = "network_") -> None:
        """Persist trusted public keys locally and remove stale keys for the specified prefix.

        Parameters:
                trusted_list (list): Trusted entities containing an identifier and hexadecimal
                public key.
                prefix (str): Filename prefix used to group the synchronized keys.
        """
        roots_dir = Path.home() / ".biopro" / "trusted_roots"
        roots_dir.mkdir(parents=True, exist_ok=True)

        # 1. Identify current network keys for this prefix
        existing_keys = list(roots_dir.glob(f"{prefix}*.pub"))
        new_filenames = []

        for entity in trusted_list:
            entity_id = entity.get("id") or entity.get("developer_id")
            pub_hex = entity.get("public_key")

            if not entity_id or not pub_hex:
                continue

            # Sanitize the entity_id to prevent path traversal
            sanitized_id = sanitize_identifier(entity_id)
            if not sanitized_id:
                logger.warning("Skipping invalid entity_id (redacted)")
                continue

            filename = roots_dir / f"{prefix}{sanitized_id}.pub"

            # Verify the resolved filename is within roots_dir
            try:
                resolved = filename.resolve()
                roots_resolved = roots_dir.resolve()
                if not str(resolved).startswith(str(roots_resolved) + os.sep):
                    logger.warning("Path traversal detected for entity_id (redacted)")
                    continue
            except Exception:
                logger.warning("Failed to resolve path for entity_id (redacted)")
                continue

            try:
                # Decode first to avoid leaving an empty temp file on error
                pub_bytes = bytes.fromhex(pub_hex)

                # Save raw bytes atomically
                with tempfile.NamedTemporaryFile("wb", delete=False, dir=roots_dir) as f:
                    f.write(pub_bytes)
                    tmp_name = f.name
                shutil.move(tmp_name, filename)
                new_filenames.append(filename)
            except Exception:
                logger.error("Failed to sync trusted key entry", exc_info=True)
                if "tmp_name" in locals() and os.path.exists(tmp_name):
                    os.unlink(tmp_name)

        # 2. Cleanup old keys that were revoked/removed from registry
        for old_key in existing_keys:
            if old_key not in new_filenames:
                with contextlib.suppress(Exception):
                    old_key.unlink()

    @staticmethod
    def fetch_and_sync_authorities(authority_url: str) -> None:
        """Fetch, verify, and locally synchronize authorities from a registry URL.

        Parameters:
            authority_url (str): URL of the authorities registry. Empty URLs are ignored.

        The registry is synchronized only after its signature is verified with the
        built-in root public key. Missing or invalid registries are skipped.
        """  # noqa: E501
        if not authority_url:
            return

        try:
            import time
            from http import HTTPStatus
            from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

            parsed = urlparse(authority_url)
            query = parse_qsl(parsed.query)
            query.append(("t", str(int(time.time()))))
            busted_url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    urlencode(query),
                    parsed.fragment,
                )
            )

            response = NetworkClient.get(busted_url)

            if response.status_code == HTTPStatus.NOT_FOUND:
                return

            response.raise_for_status()
            remote_data = response.json()
            authorities = remote_data.get("authorities", [])

            if authorities:
                sig_hex = remote_data.get("signature")
                if not sig_hex:
                    logger.error("Signature missing from authorities registry! Skipping sync.")
                    return

                # Canonicalize the authorities list matching the signature generation
                canonical_bytes = json.dumps(authorities, sort_keys=True).encode()

                # Load root public key
                root_pub_bytes = bytes.fromhex(BIOPRO_ROOT_PUBLIC_KEY_HEX)
                root_public_key = ed25519.Ed25519PublicKey.from_public_bytes(root_pub_bytes)

                # Verify signature
                try:
                    root_public_key.verify(bytes.fromhex(sig_hex), canonical_bytes)
                    logger.info("Successfully verified authorities registry signature ✅")
                except Exception:
                    logger.error(
                        "CRITICAL SECURITY ALERT: Authorities registry signature verification failed!",  # noqa: E501
                        exc_info=True,
                    )
                    return

                TrustSync.sync_keys(authorities, prefix="auth_")
        except Exception as e:
            # Only log actual network failures, not 404s
            logger.debug(f"Optional authority registry not available: {e}")

    @staticmethod
    def sync_trusted_developers(trusted_list: list[dict[str, Any]]) -> None:
        """Synchronize trusted developer keys and associated profile data.

        Parameters:
            trusted_list (list[dict[str, Any]]): Developer records containing public keys
            and optional profile or avatar information.
        """
        TrustSync.sync_keys(trusted_list, prefix="network_")

        # Integrate centralized profile caching and image download
        try:
            from biopro.core.developer_database import AvatarManager, DeveloperProfileDatabase

            db = DeveloperProfileDatabase()
            db.save_profiles(trusted_list)

            # Asynchronously download/cache avatars in background
            avatar_mgr = AvatarManager()
        except Exception as e:
            logger.warning(f"Could not sync developer profile database: {e}")
            return

        allowed_hosts = AppConfig.AVATAR_ALLOWED_HOSTS

        for dev in trusted_list:
            try:
                dev_id = dev.get("developer_id")
                avatar_url = dev.get("avatar_url")

                if not dev_id or not avatar_url:
                    continue
                if not isinstance(dev_id, str) or not isinstance(avatar_url, str):
                    continue

                sanitized_id = sanitize_identifier(dev_id)
                if not sanitized_id:
                    logger.warning("Skipping avatar sync for record with invalid developer_id")
                    continue

                parsed_url = urlparse(avatar_url)
                if parsed_url.scheme != "https" or parsed_url.hostname not in allowed_hosts:
                    logger.warning("Blocked unauthorized avatar URL")
                    continue

                avatar_mgr.fetch_and_cache_avatar(sanitized_id, avatar_url)
            except Exception as e:
                logger.warning(f"Failed to fetch avatar for developer: {e}")
