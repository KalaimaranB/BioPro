"""Centralized HTTP client for BioPro."""

import logging

import certifi
import requests

logger = logging.getLogger(__name__)


class NetworkClient:
    """A centralized HTTP client with standardized headers, timeouts, and SSL handling."""

    DEFAULT_TIMEOUT = 15
    DEFAULT_HEADERS = {
        "User-Agent": "BioPro-App",
        "Cache-Control": "no-cache, no-store",
        "Pragma": "no-cache",
    }

    @classmethod
    def get(
        cls,
        url: str,
        stream: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        extra_headers: dict | None = None,
    ) -> requests.Response:  # noqa: E501
        """Perform a GET request with standard BioPro settings."""
        headers = cls.DEFAULT_HEADERS.copy()
        if extra_headers:
            headers.update(extra_headers)

        return requests.get(
            url, stream=stream, timeout=timeout, headers=headers, verify=certifi.where()
        )
