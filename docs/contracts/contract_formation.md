# Contract formation

## Status

Canonical, as built (LIVE since 2026-08-02; page written 2026-09-17, TASK-2026-09-16-002 P5).
Pinned by `fnd_app/tests/architecture/test_contract_pages_are_pinned.py` (every path here
exists) and by the handshake, negotiation and store tests under `fnd_app/tests/`.

## Purpose

State, in one place, how two instances form a contract on the msn network — so that
micyte.com can be the standardizing reference for it and an instance built from the
public package speaks the same handshake as FND's. The wiki page
`docs/wiki/90-network-contract-architecture.md` is the narrative; this is the contract.

## Identity comes from the contact card, never from the contract

An instance is identified by its msn contact card (`msn_profile_and_contact_card/`): the
card carries `public_signature` and `instance_endpoint`. A contract never introduces an
identity; it binds two identities that already exist.

## The handshake

`fnd_app/instances/_shared/runtime/contract_handshake.py`

| step | function | carries |
|---|---|---|
| request | `build_request` | signed with the card's key; a fresh X25519 ephemeral |
| verify | `verify_request` | checked against the requester's CARD signature |
| offer | `build_offer` | the responder mints the contract's symmetric key and seals it to the ECDH |
| open | `open_offer` | the requester unseals it |
| traffic | `seal_traffic` | every later message sealed with that key |
| expiry | `key_is_expired` | epoch + `key_period_seconds` (default 30 days; a parameter so rotation is testable) |

Schemas: `mycite.v2.network.contract.request.v1`, `.offer.v1`, `.sealed.v1`. Skew
tolerance `HANDSHAKE_SKEW_SECONDS = 120`. A signature key SIGNS; it does not agree —
signing the ephemeral is what stops a machine in the middle, which is why both are
present and neither is enough.

## Replay protection is a sequence

`fnd_app/instances/_shared/runtime/contract_sequence_store.py` — one SQLite store
(`contract_transport.sqlite3`) both gunicorn workers write, with an atomic
`UPDATE … WHERE last_seq < ?`. A sequence beats a nonce: bounded state, and it carries
ordering.

## Lifecycle

`fnd_app/instances/_shared/runtime/contract_negotiation.py` — `open_request`,
`receive_request`, `accept_request`, `answer_request`, `refuse_request`,
`revoke_contract`; the legal moves are derived from the record's state, so an illegal move
raises rather than being written. Records persist as `mycite.portal.contract.v2` under
`<private>/contracts/` (`contract_store.py`). Revoking destroys the key.

## Key material

`fnd_app/instances/_shared/runtime/instance_keys.py` — a vault at `<private>/keys/`, 0600
inside 0700, which refuses to re-mint and refuses wide permissions; `vault://` references
resolve through `resolve_vault_ref`. An epoch is minted once: re-minting the same bytes is
idempotent, different bytes raises. Key material never enters the local audit log.

## The declaration: the contract every instance holds with its registrar

Every instance, free, hosted or run by somebody else, holds one default contract with the
registrar, and its payload is the instance's own `msn_profile`. The instance reports the
contact card projected from it as a **declaration** (`mycite.v2.network.declaration.v1`):
`msn_id`, the registrar it is addressed to, the card (`lcl_id`, `dns`, `public_signature`,
`instance_endpoint`, and its title for a new row), a timestamp, and an Ed25519 signature by
the key the card declares.

    POST <registrar instance_endpoint>/__instance/registry/declaration

The registrar keeps the registry's card for that msn in step with it, adding the row if
there is none (`fnd_app/instances/_shared/runtime/registry_declaration.py`,
`registry_card_writer.py`; the projection is `micyte/domains/registry/card_projection.py`).
It applies a declaration at once only under a key it can check: the one the card already
publishes, or the one it holds itself for an instance it hosts. A first declaration from an
instance it does not host, or one signed by a key other than the published one, waits for
the registrar's operator. A declaration that is malformed, stale (five minutes), addressed
to another registrar, or not signed by the key it declares gets the stranger's 404.

A declaration owns only those cells. Email, website and every cell the registrar keeps for
its own reasons are left as they are, and a declared empty cell erases nothing. A card that
gains a cell changes its pair count, so its row moves to that family; nothing cites a card
by address.

Instance keys are derived from the instance's root and its msn (`instance_keys`), so the key
a card publishes is the same one every time for that root and address. The grantee profile
is the additional item a HOSTED account's contract carries; it is not part of the
declaration.

## What is public without a contract

`/__mss/public/stills` and `/__mss/public/stills/<name>.mss` serve published stills to an
unidentified requester; `/__mss/public/stills/registry.mss` serves the registrar's registry still (published 2026-10-11 through the contact card's allowlist, `fnd_app/scripts/export_registry_still.py`, `network_surfaces.apply_publication`).
A closed or unpublished resource answers 404, never 403. Discovery cannot require a
contract — a contract is not how you learn to form one.

## Not yet standardized (proposals in wiki 90)

Resolving a `hy.<msn>.<sandbox>.<document>.<hash>.<addr>` magnet against a remote
instance; rotation cadence; what an open session may offer toward joining.
