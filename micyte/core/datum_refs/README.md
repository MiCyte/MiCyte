# Datum Refs

Authority: [../../../docs/wiki/separation_and_responsibility.md](../../../docs/wiki/separation_and_responsibility.md)

`micyte/core/datum_refs/` owns the phase-02 MVP datum-ref surface.

Implemented in this phase:

- pure datum-ref parsing
- pure datum-ref validation
- pure datum-ref normalization into canonical local, dot, or hyphen text

Not implemented in this phase:

- identity logic
- MSS resolution
- HOPS or SAMRAS structures
- runtime path helpers
- port, adapter, tool, sandbox, or state-machine concerns
