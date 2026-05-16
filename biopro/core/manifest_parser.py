import json
from typing import Any


class ManifestValidationError(Exception):
    """Raised when a manifest fails validation."""

    pass


class ManifestParser:
    """Parses and validates plugin manifest.json files (V2 Schema)."""

    REQUIRED_V2_KEYS = ["id", "name", "version", "description", "signed_by", "authors"]

    def parse(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate manifest dictionary."""
        # Check for legacy author field (Hard Migration to V2)
        if "author" in manifest_data:
            raise ManifestValidationError(
                "Legacy 'author' field is no longer supported. Please migrate to 'authors' array and 'signed_by' block."
            )

        # Ensure it specifies V2
        if manifest_data.get("manifest_version") != 2:
            raise ManifestValidationError("Only manifest_version: 2 is supported.")

        # Check required fields
        for key in self.REQUIRED_V2_KEYS:
            if key not in manifest_data:
                raise ManifestValidationError(f"Missing required field: '{key}'")

        # Validate authors is a non-empty array
        authors = manifest_data["authors"]
        if not isinstance(authors, list) or len(authors) == 0:
            raise ManifestValidationError("'authors' must be a non-empty array.")

        # Validate signed_by structure
        signed_by = manifest_data["signed_by"]
        if not isinstance(signed_by, dict):
            raise ManifestValidationError("'signed_by' must be an object.")
        if "entity_type" not in signed_by or "entity_id" not in signed_by:
            raise ManifestValidationError("'signed_by' must contain 'entity_type' and 'entity_id'.")

        return manifest_data

    def parse_file(self, filepath: str) -> dict[str, Any]:
        """Read and parse a manifest.json file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return self.parse(data)
        except json.JSONDecodeError as e:
            raise ManifestValidationError(f"Invalid JSON format: {e}") from e
        except FileNotFoundError as e:
            raise ManifestValidationError(f"Manifest file not found: {filepath}") from e
