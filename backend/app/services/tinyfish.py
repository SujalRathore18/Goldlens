import os
from typing import Any

import httpx


class TinyFishConfigurationError(RuntimeError):
    """Raised when TinyFish is not configured for the backend."""


class TinyFishRequestError(RuntimeError):
    """Raised when TinyFish rejects or cannot complete a request."""


class TinyFishClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TINYFISH_API_KEY")
        self.base_url = (base_url or os.getenv("TINYFISH_BASE_URL") or "https://agent.tinyfish.ai").rstrip("/")
        self.timeout = timeout

    def run(self, *, url: str, goal: str) -> dict[str, Any]:
        if not self.api_key:
            raise TinyFishConfigurationError("TINYFISH_API_KEY is not configured")
        try:
            response = httpx.post(
                f"{self.base_url}/v1/automation/run",
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                json={"url": url, "goal": goal},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TinyFishRequestError(
                f"TinyFish returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise TinyFishRequestError("TinyFish request failed") from exc
        payload = response.json()
        if not isinstance(payload, dict):
            raise TinyFishRequestError("TinyFish returned an unexpected response")
        return payload
