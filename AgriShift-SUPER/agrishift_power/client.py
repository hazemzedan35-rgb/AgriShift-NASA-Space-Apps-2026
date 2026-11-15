"""Single request with defensive network errors, bounded retries and timeout."""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import PowerRequest


class PowerAPIError(RuntimeError):
    """NASA POWER request or response failed."""


def fetch_daily(request: PowerRequest, *, timeout: int = 45, attempts: int = 3,
                pause=time.sleep, opener=urlopen) -> dict:
    """Download JSON from POWER, respecting retries for transient errors only.

    `opener` and `pause` may be substituted in tests; no external dependencies.
    """
    if timeout <= 0 or attempts < 1:
        raise ValueError("timeout must be positive and attempts >= 1")
    url = request.url()
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "AgriShift-Student-Research/0.1 (NASA POWER data client)",
    })
    for attempt in range(attempts):
        try:
            with opener(req, timeout=timeout) as response:
                raw = response.read()
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PowerAPIError("NASA returned a non-JSON or invalid JSON body") from exc
            if not isinstance(data, dict):
                raise PowerAPIError("NASA JSON top level was not an object")
            if data.get("messages") and "properties" not in data:
                raise PowerAPIError(f"NASA reported: {data['messages']!r}")
            return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise PowerAPIError(f"NASA POWER HTTP {exc.code}. URL: {url}") from exc
        except (URLError, TimeoutError, ConnectionError) as exc:
            if attempt == attempts - 1:
                raise PowerAPIError(
                    "Could not reach NASA POWER after retries. Check internet/DNS and try again."
                ) from exc
        pause(min(2 ** attempt, 8))
    raise AssertionError("unreachable")
