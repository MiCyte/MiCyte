# MiCyte

**MiCyte** is a standard for keeping records and building applications, made so that
people can organize themselves and connect without asking anyone's permission. An
**instance** holds its own records at its own address and is the unit of identity on the
network; applications written by anyone and hosted by anyone cooperate through it,
because the way data is kept and the way applications reach it is one standard rather
than one vendor's. Nobody has to rent the program to use it, or to take part.

In the software's own terms: MiCyte is the MOS-centric portal shell and datum operating
environment — Mycelial Ontological Schema. An instance holds its own corpus, draws it
through archetypes it carries, declares the seams it would use, and does nothing it has
not been granted.

This repository is MiCyte's canonical source and its authoritative documentation
tree. The `micyte/` package is what the public cut publishes
(`scripts/publish_micyte.py`).

> The package directory, the wire schemas (`mycite.v2.*`) and some runtime paths
> still carry the pre-rebrand `mycite` spelling. Those are protocol and
> infrastructure identifiers whose rename is a separate migration, not a brand
> fix.

## What an instance is

- **One corpus.** Documents live in MOS — a per-instance authority store — never
  as files somebody edits. `docs/contracts/mos_authority_enforcement.md` is the
  rule, and a CI job enforces it.
- **Shapes, not screens.** A document's ARCHETYPE says what it is and a
  VIEWSCOPE draws it, so a new kind of record needs no new renderer.
- **Addresses carry arity.** An MSS address says what level it names, and the
  engine refuses one that does not —
  `docs/contracts/mss_engine_invariants.md`.
- **Nothing is permitted by being installed.** Installing a gadget exposes its
  tools and provisions the blank documents they need. What a tool may WRITE is
  `datum_write_grants`; what a seam may CALL is `external_call_grants`; both deny
  on an empty grant set. `docs/contracts/port_binding_store.md`.

## Gadgets

A gadget is a package of tools that ship together. `micyte/tools/_packages.py`
declares what this build offers, and `docs/wiki/93-the-marketplace.md` states the
whole chain from that declaration to the cards on micyte.com. An **app** is a
package with a hub — a tabbed composite over its own tools; an **extension** is a
package that FILLS a port an app employs.

Declaring, binding and granting are three separate acts, on purpose. An adapter
that arrived able to act because it was merely installed is the shape of a
supply-chain problem.

A DEPLOYMENT may contribute packages of its own beyond the ones MiCyte ships
(`register_host_package`). Those are the host's, are never locked into this
package and are never published —
`fnd_app/instances/_shared/grantor/__init__.py` is this repository's own example
and says why at length.

## The portal

- one shell; canonical entry `/portal` → `/portal/system`
- root surfaces `SYSTEM`, `NETWORK`, `UTILITIES`
- one runtime envelope family; canonical shell endpoint `POST /portal/api/v2/shell`
- tool pages at `/portal/system/tools/<tool_slug>`
- `SYSTEM` is SQL-authoritative and **fail-closed** when the authority store is
  missing or uninitialized
- a tool's posture comes from the capabilities it requires and the ports it
  employs, never from portal identity

The shell contract is `micyte/state_machine/portal_shell/shell.py`.

## Running it

MiCyte is not on PyPI yet. Download the wheel from the
[latest release](https://github.com/MiCyte/MiCyte/releases/latest)
(Python 3.13; it needs only `pyyaml` and `shapely`) and install the file:

```bash
pip install ./micyte-<version>-py3-none-any.whl
```

There is no installer, no desktop application and no `micyte` command yet; you get
the database and its tools as a library. [micyte.com/get](https://micyte.com/get)
states, per platform, what installs today and what does not.

[`docs/wiki/00-overview-and-glossary.md`](docs/wiki/00-overview-and-glossary.md) is the way in: what an
instance is, how one is bootstrapped, and what each surface answers.

## Canonical docs

- [`docs/README.md`](docs/README.md) — the index
- [`docs/wiki/00-overview-and-glossary.md`](docs/wiki/00-overview-and-glossary.md)
- [`docs/contracts/portal_shell_contract.md`](docs/contracts/portal_shell_contract.md)
- [`docs/contracts/route_model.md`](docs/contracts/route_model.md)
- [`docs/contracts/surface_catalog.md`](docs/contracts/surface_catalog.md)
- [`docs/contracts/portal_vocabulary_glossary.md`](docs/contracts/portal_vocabulary_glossary.md)
- [`docs/standards/release_and_versioning.md`](docs/standards/release_and_versioning.md)
- [`docs/standards/development_process.md`](docs/standards/development_process.md)

## License

See [`LICENSE`](LICENSE).
