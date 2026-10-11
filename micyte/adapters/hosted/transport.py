"""One authorized request to a hosted service's key door.

``authorize(operation)`` is judged in THIS function, before anything is sent — the
egress sweep's unit of audit, and the same posture every adapter in this tree keeps. The
key rides as a bearer header and the alias beside it; a refusal from the door comes back
as :class:`HostedServiceRefused` carrying the door's own code and sentence, so a surface
can show "key refused" or "not permitted" rather than "unavailable".
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

ALIAS_HEADER = "X-MiCyte-Alias"
_TIMEOUT_SECONDS = 30


class HostedServiceRefused(RuntimeError):
    """The door answered with a refusal; ``code`` is its word for why."""

    def __init__(self, code: str, message: str, *, status: int = 0) -> None:
        super().__init__(message or code)
        self.code = code
        self.status = status


def refusal_of(detail: Any, status: int) -> tuple[str, str]:
    """``(code, sentence)`` from a refusal body, in each of the shapes the host answers.

    The portal's error envelope nests ``{"error": {"code", "message"}}``; the key door
    answers ``{"error": code, "message": ...}``; a gate refusal answers ``{"error":
    "<the gate's sentence>"}``. A sentence is not a code, so a 403 carrying one is
    named ``call_not_permitted`` (the gate is the only thing that answers 403 that way)
    and the sentence is kept as the message.
    """
    if not isinstance(detail, dict):
        return f"http_{status}", ""
    error = detail.get("error")
    if isinstance(error, dict):
        return (str(error.get("code") or f"http_{status}"), str(error.get("message") or ""))
    text = str(error or "").strip()
    if text and " " not in text:
        return text, str(detail.get("message") or "")
    return ("call_not_permitted" if status == 403 else f"http_{status}"), text


class HostedServiceClient:
    def __init__(self, *, base_url: str, alias: str, api_key: str,
                 authorize: Callable[[str], None],
                 opener: Callable[..., Any] | None = None) -> None:
        if not callable(authorize):
            raise TypeError("HostedServiceClient requires an authorize(operation) callable")
        self._base = str(base_url or "").strip().rstrip("/")
        self._alias = str(alias or "").strip()
        self._key = str(api_key or "").strip()
        if not (self._base.startswith("https://") or self._base.startswith("http://127.0.0.1")
                or self._base.startswith("http://localhost")):
            raise ValueError("a hosted service is reached over https (or loopback for a test)")
        if not self._alias or not self._key:
            raise ValueError("a hosted service needs an alias and the key minted for it")
        self._authorize = authorize
        self._open = opener or urllib.request.urlopen

    @property
    def alias(self) -> str:
        return self._alias

    def call(self, operation: str, port: str, action: str,
             payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """``POST <base>/<port>/<action>``, authorized under ``operation`` first."""
        self._authorize(operation)
        request = urllib.request.Request(
            f"{self._base}/{port}/{action}", method="POST",
            data=json.dumps(payload or {}).encode(),
            headers={"Authorization": f"Bearer {self._key}", ALIAS_HEADER: self._alias,
                     "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self._open(request, timeout=_TIMEOUT_SECONDS) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail: dict[str, Any] = {}
            try:
                detail = json.loads(exc.read().decode() or "{}")
            except (ValueError, OSError):
                detail = {}
            code, message = refusal_of(detail, int(exc.code))
            raise HostedServiceRefused(code, message, status=int(exc.code)) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise HostedServiceRefused("unreachable", f"the hosted service could not be reached: {exc}") from exc
        try:
            parsed = json.loads(raw.decode() or "{}")
        except ValueError as exc:
            raise HostedServiceRefused("bad_answer", "the hosted service answered with something that is not JSON") from exc
        if not isinstance(parsed, dict):
            raise HostedServiceRefused("bad_answer", "the hosted service answered with something that is not an object")
        if parsed.get("ok") is False:
            raise HostedServiceRefused(str(parsed.get("error") or "refused"),
                                       str(parsed.get("message") or parsed.get("error") or ""))
        return parsed


__all__ = ["ALIAS_HEADER", "HostedServiceClient", "HostedServiceRefused"]
