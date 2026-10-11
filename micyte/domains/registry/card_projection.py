"""An instance's contact card, projected from its own ``msn_profile``.

Operator, 2026-10-09: the contract every instance holds with the registrar carries "a simple
payload that exists as their MSN profile datum doc; they report this as their declaration
and the registrar sandbox holds that profile and then also uses that to maintain the
registry datum doc by updating or adding … their contact card entry".

This module is the PURE half: which cells an instance may declare about itself, how they
are read out of its profile, and how a declared card merges into the registry row the
registrar already keeps. No store, no network, no key.

## Which numbering a profile is written in

Every instance's core sandbox is called ``system`` and the namespaces disagree about where
a field sits (``msn_id`` is 3-1-3 under system and 3-1-2 under registrar). Live, on
2026-10-09, one profile of eight is written in registrar numbering while its claimed
namespace says system: read under the claim, its ``msn_id`` cell holds title bits. So the
projection is SELF-CHECKING rather than trusting the claim: it reads the profile under each
candidate numbering and accepts only the one in which the profile's own ``msn_id`` cell
names the msn the document is filed under. None agreeing is a refusal, never a guess.

## What a declaration owns

``DECLARED_FIELDS``: the cells an instance states about ITSELF — its local domain, its
website domain, where it answers contract traffic, and the key that proves its messages.
Everything else on the registry row (email, website, social, the registrar's own marks)
is the registrar's record and is kept as it is. A declared empty value leaves the
registrar's cell alone; a declaration does not erase.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

#: The cells an instance declares about itself, in the order a card head carries them.
DECLARED_FIELDS: tuple[str, ...] = ("lcl_id", "dns", "public_signature", "instance_endpoint")
#: The registrar's canonical head order. A merged head is written in this order, so two
#: registrars merging the same declaration write the same bytes.
CARD_ORDER: tuple[str, ...] = (
    "msn_id", "lcl_id", "dns", "email", "website", "public_signature", "instance_endpoint")
#: The card's babelettes hold 64 characters.
CELL_LIMIT = 64


class CardProjectionError(ValueError):
    """The profile cannot be read as this instance's own, or a declared cell is unusable."""


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def profile_fields(rows: Iterable[Any], *, msn_id: str,
                   namespaces: Sequence[str]) -> tuple[str, dict[str, str]]:
    """``(namespace, {field: value})`` for the numbering under which the profile names
    ITSELF. ``rows`` are the profile's rows (objects with ``raw`` or dicts)."""
    from micyte.core.datum_ops import archetype_shape as _ash
    from micyte.core.datum_ops.datum_resolve import as_text, decode_label, iter_marker_pairs

    heads: list[tuple[list[Any], list[Any]]] = []
    for row in rows:
        raw = row.get("raw") if isinstance(row, dict) else getattr(row, "raw", None)
        head = _ash._row_head(raw)
        label = raw[1] if isinstance(raw, list) and len(raw) > 1 and isinstance(raw[1], list) else []
        if head:
            heads.append((head, label))
    msn = _text(msn_id)
    for namespace in dict.fromkeys(n for n in namespaces if n):
        fields: dict[str, str] = {}
        for head, label in heads:
            for marker, magnitude in iter_marker_pairs(head):
                name = _ash._field_name(as_text(marker), sandbox=namespace)
                if not name or name.startswith("<"):
                    continue
                # EVERY cell, not only the title: a profile may hold its dns as a
                # bit-encoded babelette (live 2026-10-11: one profile's dns was 512 bits
                # spelling "masonlenehan.com"). decode_label returns a plain value as is.
                value = decode_label(magnitude)
                fields.setdefault(name, _text(value))
            if label and "label" not in fields:
                fields["label"] = _text(label[0])
        if fields.get("msn_id") == msn:
            return namespace, fields
    raise CardProjectionError(
        f"the msn_profile filed under {msn} does not name {msn} under any numbering "
        f"tried ({', '.join(namespaces)}); the profile has to say whose it is before it "
        "can be declared")


def project_card(fields: dict[str, str], *, msn_id: str, public_signature: str = "") -> dict[str, str]:
    """The card an instance declares: its msn, its title, and ``DECLARED_FIELDS``."""
    card = {"msn_id": _text(msn_id), "title": _text(fields.get("label") or fields.get("title"))}
    for name in DECLARED_FIELDS:
        card[name] = _text(fields.get(name))
    if public_signature:
        card["public_signature"] = _text(public_signature)
    return validate_card(card)


def validate_card(card: dict[str, Any]) -> dict[str, str]:
    clean = {key: _text(card.get(key)) for key in ("msn_id", "title", *DECLARED_FIELDS)}
    if not clean["msn_id"]:
        raise CardProjectionError("a card names the msn it is about")
    for name in DECLARED_FIELDS:
        if len(clean[name]) > CELL_LIMIT:
            raise CardProjectionError(f"{name} is {len(clean[name])} characters; a card cell holds {CELL_LIMIT}")
    endpoint = clean["instance_endpoint"]
    if endpoint and not endpoint.startswith("https://"):
        raise CardProjectionError("an instance endpoint is an https origin")
    return clean


def head_pairs(head: Sequence[Any]) -> list[tuple[str, str]]:
    """``[(marker, value), …]`` from a registry row head ``[address, m, v, m, v, …]``."""
    return [(str(head[i]), str(head[i + 1])) for i in range(1, len(head) - 1, 2)]


def merge_card(pairs: Sequence[tuple[str, str]], card: dict[str, str], *,
               marker_of: Any) -> list[tuple[str, str]]:
    """The registry row's pairs with the declared cells written in.

    ``marker_of(field) -> "rf.3-1-N"`` is the registrar namespace's marker. Pairs the
    declaration does not own are kept verbatim — including markers this module has never
    heard of — and the result is in ``CARD_ORDER`` with unknown markers after it, in their
    original order. A declared empty cell leaves the registrar's value.
    """
    by_marker = dict(pairs)
    order = [marker_of(name) for name in CARD_ORDER]
    by_marker[marker_of("msn_id")] = card["msn_id"]
    for name in DECLARED_FIELDS:
        value = _text(card.get(name))
        if value:
            by_marker[marker_of(name)] = value
    known = [(m, by_marker[m]) for m in order if by_marker.get(m)]
    rest = [(m, v) for m, v in pairs if m not in order and v]
    return known + rest


def card_changes(before: Sequence[tuple[str, str]], after: Sequence[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """``{marker: (was, now)}`` for every cell the merge changed."""
    b, a = dict(before), dict(after)
    return {m: (b.get(m, ""), a.get(m, "")) for m in dict.fromkeys([*b, *a]) if b.get(m, "") != a.get(m, "")}


__all__ = ["CARD_ORDER", "CELL_LIMIT", "DECLARED_FIELDS", "CardProjectionError", "card_changes",
           "head_pairs", "merge_card", "profile_fields", "project_card", "validate_card"]
