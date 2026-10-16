"""The mail seam, spoken to a host's key door.

Implements :class:`micyte.ports.email_provider.EmailProviderPort` over
:class:`HostedServiceClient`: reading and answering the alias's mail (the host's ``mail``
port) and administering its addresses (the host's ``mailbox`` port). Every method
authorizes under the port's own operation name.
"""

from __future__ import annotations

from typing import Any

from micyte.ports.email_provider import (
    OPERATION_ALIAS_CREATE,
    OPERATION_ALIAS_LIST,
    OPERATION_ALIAS_REMOVE,
    OPERATION_FORWARDING_SET,
    OPERATION_IDENTITY_REMIND,
    OPERATION_IDENTITY_VERIFY_REQUEST,
    OPERATION_MAILBOX_LIST,
    OPERATION_MESSAGE_FETCH,
    OPERATION_MESSAGE_FORWARD,
    OPERATION_MESSAGE_SEND,
    EmailMessage,
    EmailProviderError,
    InboundMessage,
    InboundPart,
    MailboxEntry,
)

from .transport import HostedServiceClient, HostedServiceRefused


def _row(cls: Any, row: dict[str, Any]) -> Any:
    names = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
    # JSON carries a tuple field as a list; the contract's dataclasses hold tuples.
    return cls(**{k: tuple(v) if isinstance(v, list) else v
                  for k, v in row.items() if k in names})


class HostedEmailAdapter:
    """The alias's mail on the host, read and answered from here."""

    provider_id = "hosted_service"
    adapter_id = "hosted_email"

    def __init__(self, *, client: HostedServiceClient) -> None:
        if not isinstance(client, HostedServiceClient):
            raise TypeError("HostedEmailAdapter requires a HostedServiceClient")
        self._client = client

    @classmethod
    def from_credential(cls, credential: Any, *, authorize: Any,
                        opener: Any = None) -> HostedEmailAdapter:
        """Built from what the host handed over (``read_hosted_credential``)."""
        return cls(client=HostedServiceClient(
            base_url=credential.base_url, alias=credential.alias,
            api_key=credential.api_key, authorize=authorize, opener=opener))

    def _call(self, operation: str, port: str, action: str,
              payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._client.call(operation, port, action, payload)
        except HostedServiceRefused as exc:
            if exc.code in ("call_not_permitted", "key_refused", "mailbox_not_permitted"):
                raise PermissionError(str(exc)) from exc
            raise EmailProviderError(f"{exc.code}: {exc}") from exc

    def list_inbound(
        self, *, mailbox: str = "", limit: int = 0, offset: int = 0,
    ) -> tuple[MailboxEntry, ...]:
        answer = self._call(OPERATION_MAILBOX_LIST, "mail", "list",
                            {"mailbox": mailbox, "limit": int(limit or 0),
                             "cursor": str(max(0, int(offset or 0)))})
        return tuple(_row(MailboxEntry, r) for r in answer.get("messages") or [] if isinstance(r, dict))

    def fetch_inbound(self, message_key: str) -> InboundMessage:
        answer = self._call(OPERATION_MESSAGE_FETCH, "mail", "message", {"message_key": message_key})
        message = answer.get("message")
        if not isinstance(message, dict):
            raise EmailProviderError("the hosted service answered without a message")
        return _row(InboundMessage, message)

    def fetch_attachment(
        self, message_key: str, *, part: int | None = None, content_id: str = "",
    ) -> InboundPart:
        # REFUSED HERE, before anything is authorized or sent. The key door answers in
        # JSON and carries no message's bytes but its text; an attachment needs a binary
        # answer that door does not have yet. The message's `attachments` rows still
        # arrive, so the reader can see what is there and fetch it on the host's portal.
        raise EmailProviderError(
            "attachments are not carried across the key door yet; open this message on "
            "the hosting portal to download its parts")

    def send_message(self, message: EmailMessage) -> str:
        answer = self._call(OPERATION_MESSAGE_SEND, "mail", "send", {
            "to": message.to, "subject": message.subject, "body": message.body,
            "in_reply_to": message.in_reply_to, "references": list(message.references)})
        return str(answer.get("message_id") or "")

    def forward_message(self, message: InboundMessage, *, to: str, note: str = "") -> str:
        answer = self._call(OPERATION_MESSAGE_FORWARD, "mail", "forward",
                            {"message_key": message.message_key, "to": to, "note": note})
        return str(answer.get("message_id") or "")

    def list_aliases(self, *, domain: str = "") -> tuple[dict[str, str], ...]:
        answer = self._call(OPERATION_ALIAS_LIST, "mailbox", "list", {"domain": domain})
        return tuple({str(k): str(v) for k, v in r.items()} for r in answer.get("aliases") or []
                     if isinstance(r, dict))

    def create_alias(self, *, domain: str, local_part: str, forward_to: str) -> dict[str, str]:
        # REFUSED HERE, before anything is authorized or sent: the door holds a key to
        # the client door's words, and adding or deleting an address on a domain the
        # host answers for is the host operator's. Saying so locally names the act
        # nothing on this side can perform, rather than spending a request to learn it.
        raise PermissionError(
            f"{OPERATION_ALIAS_CREATE} is the hosting operator's; ask them for the address")

    def remove_alias(self, *, domain: str, local_part: str) -> dict[str, str]:
        raise PermissionError(
            f"{OPERATION_ALIAS_REMOVE} is the hosting operator's; ask them to remove it")

    def set_forwarding(self, *, domain: str, local_part: str, forward_to: str) -> dict[str, str]:
        return self._str_dict(self._call(OPERATION_FORWARDING_SET, "mailbox", "forwarding", {
            "domain": domain, "local_part": local_part, "forward_to": forward_to,
            "confirm": f"{local_part}@{domain}"}))

    def request_identity_verification(self, *, domain: str, local_part: str) -> dict[str, str]:
        return self._str_dict(self._call(OPERATION_IDENTITY_VERIFY_REQUEST, "mailbox", "verify-request", {
            "domain": domain, "local_part": local_part, "confirm": f"{local_part}@{domain}"}))

    def remind_identity_verification(self, *, domain: str, local_part: str) -> dict[str, str]:
        return self._str_dict(self._call(OPERATION_IDENTITY_REMIND, "mailbox", "remind", {
            "domain": domain, "local_part": local_part, "confirm": f"{local_part}@{domain}"}))

    @staticmethod
    def _str_dict(answer: dict[str, Any]) -> dict[str, str]:
        return {str(k): str(v) for k, v in answer.items() if k != "ok"}


__all__ = ["HostedEmailAdapter"]
