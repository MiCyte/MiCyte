"""Where an instance keeps what the hosted service handed it: the base URL, its alias and
the key. One file per binding, 0600, under the instance's own utilities tree; never a
line in a config an operator edits by hand, because the key is a secret and the file is
the one place it may be."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "micyte.hosted_service.credential.v1"
CREDENTIAL_DIRNAME = ("utilities", "tools", "hosted_service")
_FORBIDDEN_MODE_BITS = stat.S_IRWXG | stat.S_IRWXO


class HostedCredentialError(RuntimeError):
    """The credential is missing, unreadable, or readable by too many."""


@dataclass(frozen=True)
class HostedServiceCredential:
    binding_id: str
    base_url: str
    alias: str
    api_key: str

    def public_facts(self) -> dict[str, str]:
        return {"base_url": self.base_url, "alias": self.alias,
                "key_fingerprint": f"…{self.api_key[-4:]}" if len(self.api_key) >= 4 else ""}


def credential_path(private_dir: Any, binding_id: str) -> Path:
    token = str(binding_id or "").strip()
    if not token or "/" in token or token in {".", ".."}:
        raise HostedCredentialError("a credential is addressed by a binding id, not a path")
    return Path(private_dir).joinpath(*CREDENTIAL_DIRNAME) / f"{token}.json"


def read_hosted_credential(private_dir: Any, binding_id: str) -> HostedServiceCredential:
    path = credential_path(private_dir, binding_id)
    if not path.is_file():
        raise HostedCredentialError(f"no hosted-service credential on file for {binding_id!r}")
    mode = path.stat().st_mode
    if mode & _FORBIDDEN_MODE_BITS:
        raise HostedCredentialError(
            f"{path.name} is readable beyond its owner (mode {stat.filemode(mode)}); refusing it")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostedCredentialError(f"{path.name} could not be read: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise HostedCredentialError(f"{path.name} is not a {SCHEMA} record")
    fields = {k: str(raw.get(k) or "").strip() for k in ("base_url", "alias", "api_key")}
    if not all(fields.values()):
        raise HostedCredentialError(f"{path.name} lacks a base url, an alias or a key")
    return HostedServiceCredential(binding_id=str(binding_id).strip(), **fields)


def write_hosted_credential(private_dir: Any, *, binding_id: str, base_url: str, alias: str,
                            api_key: str, replace: bool = False) -> Path:
    fields = {"base_url": str(base_url or "").strip().rstrip("/"),
              "alias": str(alias or "").strip(), "api_key": str(api_key or "").strip()}
    if not all(fields.values()):
        raise HostedCredentialError("a base url, an alias and the key are all required")
    path = credential_path(private_dir, binding_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if path.exists():
        if not replace:
            raise HostedCredentialError(f"a credential is already on file for {binding_id!r}; name replace=True")
        path.unlink()
    record = {"schema": SCHEMA, "binding_id": str(binding_id).strip(), **fields}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(record, indent=1) + "\n").encode("utf-8"))
    finally:
        os.close(descriptor)
    return path


__all__ = ["SCHEMA", "HostedCredentialError", "HostedServiceCredential", "credential_path",
           "read_hosted_credential", "write_hosted_credential"]
