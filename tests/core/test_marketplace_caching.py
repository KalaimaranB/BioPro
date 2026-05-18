import hashlib
from pathlib import Path

import pytest
from biopro_sdk.host.marketplace_cache import (
    AssetVerificationError,
    AssetVerifier,
    MarketplaceQueryService,
    SandboxCacheService,
)


@pytest.fixture
def mock_sandbox_root(tmp_path):
    sandbox_root = tmp_path / "sandbox_cache"
    sandbox_root.mkdir()
    return sandbox_root


@pytest.fixture
def mock_remote_assets(tmp_path):
    """Simulates a remote marketplace endpoint with avatars and screenshots."""
    web_dir = tmp_path / "remote_web"
    web_dir.mkdir()

    # Write a mock developer avatar
    avatar_content = b"fake_avatar_png_data"
    avatar_hash = hashlib.sha256(avatar_content).hexdigest()
    avatar_file = web_dir / "alice.png"
    avatar_file.write_bytes(avatar_content)

    # Write a mock plugin screenshot
    screen_content = b"fake_screenshot_png_data"
    screen_hash = hashlib.sha256(screen_content).hexdigest()
    screen_file = web_dir / "screen1.png"
    screen_file.write_bytes(screen_content)

    return {
        "web_dir": web_dir,
        "avatar": {"path": avatar_file, "hash": avatar_hash, "content": avatar_content},
        "screenshot": {"path": screen_file, "hash": screen_hash, "content": screen_content},
    }


class TestMarketplaceCachingSuite:
    def test_sandbox_caching_security_and_path_generation(self, mock_sandbox_root):
        """Test Case A: Validate that cache paths reside strictly inside the sandbox cache boundary.
        Ensure traversal attempts raise ValueError.
        """
        cache_service = SandboxCacheService(base_dir=mock_sandbox_root)

        # Valid path generation
        safe_path = cache_service.get_cache_path("segmenter_plugin", "avatars", "alice.png")
        assert safe_path.name == "alice.png"
        assert "segmenter_plugin" in safe_path.parts
        assert "avatars" in safe_path.parts

        # Verify it resides inside the sandbox root
        assert safe_path.is_relative_to(mock_sandbox_root)

        # Malicious Directory Traversal attempt using '../../' in filename
        with pytest.raises(ValueError) as exc:
            cache_service.get_cache_path("segmenter_plugin", "avatars", "../../../etc/passwd")
        assert "Directory Traversal Attempt Blocked" in str(exc.value)

    def test_secure_download_and_hash_matching_success(self, mock_sandbox_root, mock_remote_assets):
        """Test Case B: Securely download avatar asset and assert that matching signed hash succeeds verification."""
        cache_service = SandboxCacheService(base_dir=mock_sandbox_root)

        # Mock Downloader that copies local mock files to target sandboxed directory
        def mock_downloader(url, target_file):
            source_path = mock_remote_assets["avatar"]["path"]
            Path(target_file).parent.mkdir(parents=True, exist_ok=True)
            Path(target_file).write_bytes(source_path.read_bytes())

        query_service = MarketplaceQueryService(downloader=mock_downloader)

        # Resolve target sandboxed path
        target_path = cache_service.get_cache_path("segmenter_plugin", "avatars", "alice.png")

        # Download
        query_service.download_asset("https://biopro.org/assets/alice.png", target_path)
        assert target_path.exists()
        assert target_path.read_bytes() == mock_remote_assets["avatar"]["content"]

        # Verify matching hash
        verifier = AssetVerifier()
        is_valid = verifier.verify_asset(target_path, mock_remote_assets["avatar"]["hash"])
        assert is_valid is True

    def test_asset_tampering_hash_mismatch_failure(self, mock_sandbox_root, mock_remote_assets):
        """Test Case C: Verify that mismatching or tampered asset hashes raise AssetVerificationError
        and trigger an asset-tampered event hook.
        """
        cache_service = SandboxCacheService(base_dir=mock_sandbox_root)

        # Copy simulated files to sandbox
        target_path = cache_service.get_cache_path("segmenter_plugin", "screenshots", "screen1.png")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(mock_remote_assets["screenshot"]["content"])

        tampered_events = []

        def on_tampered(file_path, calculated, expected):
            tampered_events.append((file_path, calculated, expected))

        verifier = AssetVerifier(on_tampered_callback=on_tampered)

        # Attempt to verify with a wrong/manipulated hash
        wrong_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        with pytest.raises(AssetVerificationError) as exc:
            verifier.verify_asset(target_path, wrong_hash)

        assert "Asset Cryptographic Tampering Detected" in str(exc.value)
        assert len(tampered_events) == 1
        assert tampered_events[0][0] == target_path
        assert tampered_events[0][2] == wrong_hash
