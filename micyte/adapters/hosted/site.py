"""The site-hosting seam, spoken to a host's key door.

Implements the authoring subset and the two content writes of
:class:`micyte.ports.site_hosting.SiteHostingPort` over :class:`HostedServiceClient`. Each
method authorizes under the port's own operation name — the same word the host's grant
names — so a refusal on either side reads the same.
"""

from __future__ import annotations

import base64
from typing import Any

from micyte.ports.site_hosting import (
    OPERATION_ANALYTICS_READ,
    OPERATION_ARTICLE_PUBLISH,
    OPERATION_ARTICLE_RETIRE,
    OPERATION_ASSET_UPLOAD,
    OPERATION_CONTENT_REPLACE,
    OPERATION_PAGE_LIST,
    ArticleDraft,
    ContentEdit,
    EditablePage,
    PublishedArticle,
    SiteHostingError,
)

from .transport import HostedServiceClient, HostedServiceRefused


def _row(cls: Any, row: dict[str, Any]) -> Any:
    names = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
    return cls(**{k: v for k, v in row.items() if k in names})


class HostedSiteAdapter:
    """A site the host runs for this alias, authored from here."""

    adapter_id = "hosted_site"

    def __init__(self, *, client: HostedServiceClient) -> None:
        if not isinstance(client, HostedServiceClient):
            raise TypeError("HostedSiteAdapter requires a HostedServiceClient")
        self._client = client

    @classmethod
    def from_credential(cls, credential: Any, *, authorize: Any,
                        opener: Any = None) -> HostedSiteAdapter:
        """Built from what the host handed over (``read_hosted_credential``)."""
        return cls(client=HostedServiceClient(
            base_url=credential.base_url, alias=credential.alias,
            api_key=credential.api_key, authorize=authorize, opener=opener))

    def _call(self, operation: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return self._client.call(operation, "site", action, payload)
        except HostedServiceRefused as exc:
            if exc.code in ("call_not_permitted", "key_refused", "mailbox_not_permitted"):
                raise PermissionError(str(exc)) from exc
            raise SiteHostingError(f"{exc.code}: {exc}") from exc

    def list_pages(self, *, site: str = "") -> tuple[EditablePage, ...]:
        answer = self._call(OPERATION_PAGE_LIST, "pages")
        return tuple(_row(EditablePage, r) for r in answer.get("rows") or [] if isinstance(r, dict))

    def list_articles(self, *, site: str = "") -> tuple[PublishedArticle, ...]:
        answer = self._call(OPERATION_PAGE_LIST, "articles")
        return tuple(_row(PublishedArticle, r) for r in answer.get("rows") or [] if isinstance(r, dict))

    def read_analytics(self, *, site: str = "") -> tuple[dict[str, str], ...]:
        answer = self._call(OPERATION_ANALYTICS_READ, "analytics")
        return tuple({str(k): str(v) for k, v in r.items()} for r in answer.get("rows") or []
                     if isinstance(r, dict))

    def publish_article(self, *, site: str = "", draft: ArticleDraft,
                        fork_of: str = "") -> PublishedArticle:
        answer = self._call(OPERATION_ARTICLE_PUBLISH, "publish", {
            "body": draft.body, "date": draft.date, "subtopic": draft.subtopic,
            "summary": draft.summary, "hidden": bool(draft.hidden),
            "prior_slug": draft.prior_slug, "fork_of": fork_of})
        return PublishedArticle(slug=str(answer.get("slug") or ""), title=str(answer.get("title") or ""),
                                hidden=bool(draft.hidden), url=str(answer.get("url") or ""))

    def retire_article(self, *, site: str = "", slug: str) -> dict[str, Any]:
        return self._call(OPERATION_ARTICLE_RETIRE, "retire", {"slug": slug, "confirm": "retire"})

    def replace_content(self, *, site: str = "", edit: ContentEdit | None = None) -> dict[str, Any]:
        if edit is None:
            raise SiteHostingError("a content replacement needs an edit")
        return self._call(OPERATION_CONTENT_REPLACE, "content.replace",
                          {"page": edit.page, "old": edit.old, "new": edit.new})

    def upload_asset(self, *, site: str = "", name: str, payload: bytes) -> dict[str, Any]:
        if not payload:
            raise SiteHostingError("an upload needs bytes")
        return self._call(OPERATION_ASSET_UPLOAD, "asset.upload",
                          {"name": name, "data": base64.b64encode(payload).decode()})


__all__ = ["HostedSiteAdapter"]
