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
        """Perform an HTTP GET request using BioPro's standard headers and TLS verification.

        Parameters:
                url (str): The URL to request.
                stream (bool): Whether to stream the response content.
                timeout (int): Maximum time in seconds to wait for the request.
                extra_headers (dict | None): Optional headers that override the standard headers.

        Returns:
                requests.Response: The HTTP response.
        """
        headers = cls.DEFAULT_HEADERS.copy()
        if extra_headers:
            headers.update(extra_headers)

        return requests.get(
            url, stream=stream, timeout=timeout, headers=headers, verify=certifi.where()
        )
