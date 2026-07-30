"""Trust and developer syncing for BioPro network updates."""

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

from biopro_sdk.host import BIOPRO_ROOT_PUBLIC_KEY_HEX
from cryptography.hazmat.primitives.asymmetric import ed25519

from biopro.core.network.client import NetworkClient

logger = logging.getLogger(__name__)


class TrustSync:
    """Handles syncing cryptographic keys and developer profiles."""

    @staticmethod
    def sync_keys(trusted_list: list, prefix: str = "network_") -> Any:
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

            filename = roots_dir / f"{prefix}{entity_id}.pub"
            new_filenames.append(filename)

            try:
                # Save raw bytes
                with open(filename, "wb") as f:
                    f.write(bytes.fromhex(pub_hex))
            except Exception:
                logger.error("Failed to sync trusted key entry", exc_info=True)

        # 2. Cleanup old keys that were revoked/removed from registry
        for old_key in existing_keys:
            if old_key not in new_filenames:
                with contextlib.suppress(Exception):
                    old_key.unlink()

    @staticmethod
    def fetch_and_sync_authorities(authority_url: str) -> Any:
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

            busted_url = f"{authority_url}?t={int(time.time())}"
            response = NetworkClient.get(busted_url)

            if response.status_code == 404:
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
    def sync_trusted_developers(trusted_list: list) -> Any:
        """Synchronize trusted developer keys and associated profile data.

        Parameters:
            trusted_list (list): Developer records containing public keys and optional profile or
            avatar information.
        """
        TrustSync.sync_keys(trusted_list, prefix="network_")

        # Integrate centralized profile caching and image download
        try:
            from biopro.core.developer_database import AvatarManager, DeveloperProfileDatabase

            db = DeveloperProfileDatabase()
            db.save_profiles(trusted_list)

            # Asynchronously download/cache avatars in background
            avatar_mgr = AvatarManager()
            for dev in trusted_list:
                dev_id = dev.get("developer_id")
                avatar_url = dev.get("avatar_url")
                if dev_id and avatar_url:
                    avatar_mgr.fetch_and_cache_avatar(dev_id, avatar_url)
        except Exception as e:
            logger.warning(f"Could not sync developer profile database/avatars: {e}")
