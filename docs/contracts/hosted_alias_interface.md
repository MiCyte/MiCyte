# Hosted alias interfaces

## Status

Canonical, as built (channels LIVE since 2026-08-02, alias documents since 2026-08-21;
page written 2026-09-17, TASK-2026-09-16-002 P5). Pinned by
`fnd_app/tests/architecture/test_contract_pages_are_pinned.py`.

## Purpose

A channel is a relationship with two halves: the HOST keeps one roster row per member,
and each MEMBER keeps an alias document whose rows are references to datums it already
holds. This page fixes the names, the addresses and the postures so an instance built
from the public package hosts and joins channels the way FND's does.

## A channel is a base msn-profile value

The host's registrar `channels` document carries one row per channel at `4-1-N`:
`rf.3-1-2` the channel's msn, `rf.3-1-3` its id, `rf.3-1-14` its access — `public` or
`private`. `build_profile` picks it up with no code change; the channel register
(`micyte/channels/`) is the third register beside tools and automation, mutually
exclusive with them, and declares no routes and no writes.

## The alias document

`lv.<member_msn>.system.<channel>-<host_msn>.<hash>`, minted header-first. A
declared-empty alias is a real answer: the profile page's alias gallery is a data fact,
not a hardcode.

**The pairing rule is the channel's, and a channel must state which it takes.** A roster
keyed by INSTANCE msn pairs directly. A roster keyed by some OTHER address of the same
party does not, and resolving it is a join the channel owns — which is the load-bearing
case, because a party may hold more than one address in this stack and the two are not
the same number.

> **Where the mechanics are.** Minting the documents, and the join a specific channel's
> roster needs, are a HOST's business: a host knows its own parties and what it calls
> them. This page is the INTERFACE — what an alias document is, what the postures mean,
> and what a channel may and may not do. A deployment's own channels, its minting script
> and its roster join live on that deployment's side (in this repository,
> `fnd_app/`), and `docs/contracts/` carries the contract rather than the roster.

## Postures

* **Open routes are read-only by construction.** `/__channel/` is GET-only; no write
  route exists under it, because a header-less request resolves to the operator identity
  with an every-sandbox grant, and "no write path exists" cannot be wrong the way
  "authorize then deny" can.
* A closed or disabled channel answers 404, not 403.
* `/portal/api/channels` is the authenticated twin for the operator's own portal.
* **Private** channels are visible on the host's page grayed for the host (the host has
  no alias of its own) and readable by members through their contract; **public**
  channels serve their session payload to anyone.

## Implementations

`micyte/channels/agnet.py` (the network's own channel) and
`micyte/channels/convention.py` (the cooperation convention). Both are MiCyte's, and both
are registered by importing `micyte.channels`.

A DEPLOYMENT may register channels of its own through the same `register()`, and they are
not listed here: a channel serving one host's clients is that host's, and naming it on
this page would put one deployment's client relationship in the published contract. In
this repository that channel is in `fnd_app/instances/_shared/grantor/channel.py`, which
says at length why it is there and not in `micyte/channels/` (it was, until
2026-10-04).
