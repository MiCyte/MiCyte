"""KEY PASS — what this instance holds on behalf of an alias, and what may be done with it.

The operator, 2026-08-24:

    "The utilities page should feature a key pass wallet tab. For the most part this will
    only be used for API keys, but also for the FND instance I will use this to see, and
    implement from, for AWS verification info for the FND service module and more
    important for the Grantor Application to charge clients with their provided payment
    information held under the respective docs."

THE RULE, stated without naming a screen:

    A HELD INSTRUMENT is something this instance possesses on behalf of an alias, which
    has a purpose, a state, and a declared reading of what may be done with it.

    ``held_instruments`` returns enough to RECOGNISE one -- which alias, what kind, when
    it arrived, whether it is usable -- and NEVER enough to USE one.

That last sentence is a property of THIS MODULE, not of a renderer. A surface that
receives a secret and chooses not to draw it has already put the secret in a payload, a
log, and a browser's memory. So the secret never leaves here.

## The one deliberate exception, named so it cannot be called by accident

``service_key_for_handover`` DOES return the key in full, because that is what a service
key is FOR: the operator copies it and gives it to the client, who pastes it where their
extension's binding asks. The grantor channel has always shown it
(``grantor.py:_service_key`` -- "the KEY IS SHOWN, exposing a copyable key is the
depiction's point").

Two readings of one file, and the names say which is which. See the memory note
"two denotations or none": the failure is one function serving both, where the caller
that wanted an inventory quietly gets a credential.

## Record vs instrument

The operator's phrase "held under the respective docs" reads like a collision with the
rule that credentials never enter MOS. It is not one:

    the RECORD     -- which services an alias opted into, and their state
                   -- MOS, ``grantor.grantee-<msn>`` documents
    the INSTRUMENT -- the PayPal client_secret, the SES config, the service key
                   -- instance FILES, 0600, never MOS

This module reads instruments only. Joining them to the record is the surface's job, and
joining is not moving: ``fnd_app/docs/contracts/instance_payment_storage.md`` stays true.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The three families an instance can hold. Keys are universal; the other two exist only
#: where the operator's own trees do, which is why a client instance shows keys and
#: nothing else without any permission rule being involved.
KEYPASS_FAMILIES: tuple[str, ...] = (
    "service_key",
    "aws_verification",
    # TWO FAMILIES THIS MODULE NO LONGER READS, and still names (2026-10-04,
    # TASK-2026-10-02-002 P4). Their READERS moved to
    # `fnd_app/instances/_shared/grantor/instruments.py`, because both read a tree only
    # the operator's own host has — the ENV-configured grantee secrets tree, and the
    # folder the grantor keeps vault references in. A published package that knew how to
    # walk one deployment's private client secrets is the mixing the repo split exists to
    # prevent, and `micyte/__init__.py` already said so: "This package must import
    # nothing of FND's grantee services." It did not import them; it read their files.
    #
    # The NAMES stay here because the family taxonomy is the contract — a host
    # contributing a reader must name a family this list knows, so the wallet's columns
    # and `instruments_by_family`'s every-family-present rule hold for a host reader
    # exactly as for a built-in one. The taxonomy is where it was; only the walkers moved.
    #
    # `merchant_account` is the client's own MERCHANT credential, the account their
    # site takes money INTO. `charging_instrument` is the processor's vault reference for
    # the card the client put on file at signup — what FND charges them WITH. Two
    # families and not one reading of one, because they point opposite ways: one family
    # for both would let "this alias can be charged" mean "this alias can take payment",
    # which is in fact what the third family's purpose string said until 2026-09-16.
    # RENAMED from `payment_instrument` on 2026-10-09 (side-2026-10-08-0005): that is the
    # name of the PORT FND charges through, and a fill now makes the port's name
    # load-bearing — one name, one denotation.
    "merchant_account",
    "charging_instrument",
)

STATE_PRESENT = "present"
STATE_ABSENT = "absent"
STATE_UNVERIFIED = "unverified"
STATE_ERROR = "error"

_KEY_DIRNAME = ("utilities", "tools", "fnd_service", "keys")
_AWS_DIRNAME = ("utilities", "tools", "aws-csm")

#: Extra instrument readers a HOST contributes, by family.
#:
#: WHY THIS SEAM EXISTS (2026-10-04). Two of the four families were read HERE, out of
#: trees only the operator's own host has: the ENV-configured grantee secrets tree
#: (`MYCITE_GRANTEE_ROOT`) and the folder the grantor keeps vault references in. This
#: module's own docstring is careful that "this module does not read the environment, so
#: it cannot quietly reach a tree its caller did not name" — and it knew the LAYOUT of
#: both trees, which is the same knowledge one step removed.
#:
#: So a reader is a callable the host registers, taking the paths the caller named and
#: returning :class:`HeldInstrument` values. The RULE this module owns is unchanged and
#: applies to a host reader exactly as to a built-in one: a reader returns enough to
#: RECOGNISE an instrument and never enough to USE one.
_HOST_READERS: dict[str, Any] = {}


def register_instrument_reader(family: str, reader: Any) -> None:
    """A host contributes a reader for one instrument family.

    ``family`` must be one this module's taxonomy names. A reader for a family nobody
    declared would return instruments the wallet has no column for and
    `instruments_by_family`'s every-family-present rule could not account for — so it is
    refused by name rather than grouped under a heading that does not exist.

    ``reader(private_dir, grantee_root)`` returns an iterable of `HeldInstrument`. Both
    paths are passed because a reader may need either and neither is discovered here.
    """
    token = str(family or "").strip()
    if token not in KEYPASS_FAMILIES:
        raise ValueError(
            f"{token!r} is not an instrument family this taxonomy names "
            f"({', '.join(KEYPASS_FAMILIES)}). A reader for an undeclared family would "
            "return instruments the wallet has no column for.")
    if not callable(reader):
        raise TypeError(f"the {token!r} instrument reader must be callable")
    _HOST_READERS[token] = reader


@dataclass(frozen=True)
class HeldInstrument:
    """One thing this instance holds for one alias.

    ``fingerprint`` is a RECOGNISER and never a value. Enough to tell two apart in a
    list; never enough to reconstruct one. What that means differs per family and each
    builder below says so at the point it decides.
    """

    family: str
    alias: str
    purpose: str
    state: str
    fingerprint: str = ""
    arrived_at: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "alias": self.alias,
            "purpose": self.purpose,
            "state": self.state,
            "fingerprint": self.fingerprint,
            "arrived_at": self.arrived_at,
            "note": self.note,
        }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load(path: Path) -> tuple[dict[str, Any] | None, str]:
    """``(record, error)``. An unreadable file is a row in state=error, never a skip.

    A swallowed row reads as "this alias holds nothing", which is the same shape as an
    alias who genuinely holds nothing -- and the operator cannot tell them apart. Say
    which.
    """
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}"
    if not isinstance(loaded, dict):
        return None, "not a JSON object"
    return loaded, ""


def _service_keys(private_dir: Path) -> list[HeldInstrument]:
    folder = private_dir.joinpath(*_KEY_DIRNAME)
    if not folder.is_dir():
        # NOT an error. On the live host this directory does not exist, because no
        # service key has ever been minted -- so "no keys" is the honest answer and the
        # surface must say "none minted" rather than look broken.
        return []
    out: list[HeldInstrument] = []
    for path in sorted(folder.glob("*.json")):
        alias = path.stem
        record, error = _load(path)
        if record is None:
            out.append(HeldInstrument(
                family="service_key", alias=alias,
                purpose="Enables an FND port on this alias's own instance.",
                state=STATE_ERROR,
                note=f"The key file could not be read ({error}).",
            ))
            continue
        key = _text(record.get("key"))
        out.append(HeldInstrument(
            family="service_key",
            alias=_text(record.get("grantee_msn_id")) or alias,
            purpose="Enables an FND port on this alias's own instance.",
            state=STATE_PRESENT if key else STATE_ABSENT,
            # Last four plus the mint date. The operator has to tell two apart when
            # handing one over; four characters of a 48-hex token does that and
            # reconstructs nothing. The full key is service_key_for_handover's job.
            fingerprint=f"…{key[-4:]}" if len(key) >= 4 else "",
            arrived_at=_text(record.get("minted_at")),
            note="" if key else "The record carries no key.",
        ))
    return out


def _aws_verifications(private_dir: Path) -> list[HeldInstrument]:
    folder = private_dir.joinpath(*_AWS_DIRNAME)
    if not folder.is_dir():
        return []
    out: list[HeldInstrument] = []
    for path in sorted(folder.glob("aws-csm.*.json")):
        record, error = _load(path)
        if record is None:
            out.append(HeldInstrument(
                family="aws_verification", alias=path.stem,
                purpose="AWS SES identity backing the FND service module.",
                state=STATE_ERROR, note=f"Unreadable ({error}).",
            ))
            continue
        identity = record.get("identity")
        identity = identity if isinstance(identity, dict) else {}
        workflow = record.get("workflow")
        workflow = workflow if isinstance(workflow, dict) else {}
        lifecycle = _text(workflow.get("lifecycle_state"))
        out.append(HeldInstrument(
            family="aws_verification",
            alias=_text(identity.get("tenant_id")) or path.stem,
            purpose="AWS SES identity backing the FND service module.",
            # "operational" is the only state that means the identity is usable. Every
            # other value is a stage on the way there, and calling it present would let
            # a half-onboarded identity read as ready.
            state=STATE_PRESENT if lifecycle == "operational" else STATE_UNVERIFIED,
            # The identity itself, which is a public fact -- it is the address mail
            # arrives at. Not a secret, and the operator needs to see WHICH one.
            fingerprint=_text(identity.get("send_as_email"))
            or _text(identity.get("domain")),
            arrived_at=_text(workflow.get("onboarded_at")),
            note=lifecycle or "no lifecycle state recorded",
        ))
    return out


def held_instruments(
    private_dir: Path | str | None,
    *,
    grantee_root: Path | str | None = None,
) -> tuple[HeldInstrument, ...]:
    """Everything this instance holds, as recognisers.

    ``grantee_root`` is optional and separate because it is an ENV-configured tree
    (``MYCITE_GRANTEE_ROOT``) that only the operator's instance has. Passing it is the
    caller's decision; this module does not read the environment, so it cannot quietly
    reach a tree its caller did not name.

    Returns ``()`` for an unreadable tree. An instance whose private directory cannot be
    resolved holds an UNKNOWN number of instruments, not zero -- but the surface's job
    then is to say the tree is unreadable, which it can tell from the config it already
    has. Returning a fabricated empty inventory here would be the worse lie.
    """
    if private_dir is None:
        return ()
    root = Path(private_dir)
    if not root.is_dir():
        return ()
    found: list[HeldInstrument] = []
    found.extend(_service_keys(root))
    found.extend(_aws_verifications(root))
    # THE HOST'S OWN FAMILIES. Empty in a public build, by construction — nothing
    # registers a reader there, and the wallet then draws the two families this module
    # reads with the other two present and empty, which is exactly what
    # `instruments_by_family` promises.
    for family in KEYPASS_FAMILIES:
        reader = _HOST_READERS.get(family)
        if reader is None:
            continue
        try:
            found.extend(reader(
                root, Path(grantee_root) if grantee_root is not None else None))
        except Exception:  # pragma: no cover — a host reader must not blank the wallet
            # SILENT here and not swallowed everywhere: each reader already reports an
            # unreadable FILE as a `STATE_ERROR` instrument, which is the honest answer.
            # This catches a reader that fails wholesale, and the family then renders
            # empty rather than taking the three families beside it down with it.
            continue
    return tuple(found)


def instruments_by_family(
    instruments: tuple[HeldInstrument, ...],
) -> dict[str, list[HeldInstrument]]:
    """Grouped, with EVERY family present even when empty.

    An absent family and an empty one look identical to a renderer that only iterates
    what it was given, and they mean different things: "this instance holds no keys" is
    a fact worth drawing, and it is currently the true one on the live host.
    """
    grouped: dict[str, list[HeldInstrument]] = {name: [] for name in KEYPASS_FAMILIES}
    for held in instruments:
        grouped.setdefault(held.family, []).append(held)
    return grouped


def service_key_for_handover(
    private_dir: Path | str | None, *, alias_msn: str
) -> dict[str, Any]:
    """THE FULL KEY. The one function here that returns a secret, named so that calling
    it is a decision rather than an accident.

    This is what a service key is for: the operator copies it and gives it to the client,
    who pastes it where their extension's binding asks. ``grantor.py`` has always done
    this and continues to; the wallet does NOT call this.

    Returns the same shape grantor's ``_service_key`` has always returned, so the channel
    payload is unchanged by moving the read here.
    """
    if private_dir is None:
        return {"present": False, "note": "No private directory configured."}
    path = Path(private_dir).joinpath(*_KEY_DIRNAME) / f"{alias_msn}.json"
    if not path.is_file():
        return {"present": False, "note": "No service key minted for this alias yet."}
    record, _error = _load(path)
    if record is None:
        return {"present": False, "note": "The key file could not be read."}
    return {
        "present": True,
        "key": _text(record.get("key")),
        "minted_at": _text(record.get("minted_at")),
        "note": "Copy this key into the FND email extension's binding to enable the "
                "port. Every port works this way: add the extension, enable it with "
                "a key.",
    }
