#!/usr/bin/env python3
"""Release-gate scan for the MiCyte doc set (Phase 5).

Two jobs, both a precondition for making the repo public:

1. CLASSIFY every file under ``docs/`` as public (ships with MiCyte) or private
   (FND's own domain — audits, personal notes, internal plans, and the FND-domain
   contract clusters). Private files must not exist in the published tree.

2. SCAN the public set for sensitive literals that must never leave the building:
   live registrar msns, absolute ``/srv`` paths, Route53 hosted-zone ids, the AWS
   account id / ARNs. A hit in a public file fails the gate.

Exit non-zero if any private file is still present OR any public file carries a
sensitive literal, so this can gate a release in CI. ``--list-private`` prints the
private paths (one per line) for a caller that wants to ``git rm`` them.

This exists because the repo once went public with the whole private tree in it;
this is the check that makes that a red build instead of an incident.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

# --- classification (path-based; the boundary is domain, not folder) ----------

# Whole private subtrees: FND's internal working docs, not part of the software.
PRIVATE_DIR_PREFIXES = (
    "docs/audits/",
    "docs/personal_notes/",
    "docs/plans/",
)

# Private FND-domain clusters that live INSIDE the otherwise-public contracts dir.
# Matched on the basename stem so a new cts_gis_* / fnd_* file is caught too.
PRIVATE_CONTRACT_PATTERNS = (
    re.compile(r"(^|/)cts_gis[_-]"),
    re.compile(r"(^|/)fnd_csm[_-]"),
    re.compile(r"(^|/)fnd_dcm[_-]"),
    re.compile(r"(^|/)fnd_newsletter[_-]"),
    re.compile(r"(^|/)analytics_event_schema\b"),
    re.compile(r"(^|/)agro_erp_workbench_contract\b"),
)


def is_private(rel_path: str) -> bool:
    if any(rel_path.startswith(p) for p in PRIVATE_DIR_PREFIXES):
        return True
    if rel_path.startswith("docs/contracts/"):
        return any(p.search(rel_path) for p in PRIVATE_CONTRACT_PATTERNS)
    return False


# --- sensitive literals (only ever checked against PUBLIC files) --------------

SENSITIVE = {
    "live_msn": re.compile(r"\b3-2-3-17-(?:66|77)(?:-\d+)*\b"),
    "srv_path": re.compile(r"/srv/[a-z]"),
    "route53_zone": re.compile(r"\bZ[A-Z0-9]{12,}\b"),
    "aws_account": re.compile(r"\b0659\d{8}\b"),
    "aws_arn": re.compile(r"\barn:aws:"),
}


#: Literals that ship today, each one measured and kept so the gate can refuse a NEW one.
#:
#: WHY A RATCHET AND NOT A REFUSAL. Until 2026-10-03 this gate read `git ls-files docs` and
#: judged 68 files, while `publish_micyte.py` exported 494 — all of `micyte/`, `README.md`,
#: `.gitignore` and six scripts, none of them scanned. Pointed at what actually ships it
#: finds hits. Refusing them all at once would simply stop the release, and a gate that
#: cannot be satisfied is a gate somebody switches off; admitting them silently is how they
#: got here. So each is named with the reason it is tolerated, a NEW one fails, and an entry
#: that stops hitting fails too — the list may only ever shrink.
#:
#: Keyed `(path, kind)`; the value is why it is tolerated. Everything here is debt against
#: TASK-2026-10-02-002 unless the reason says otherwise.
KNOWN_EXPORT_LITERAL_DEBT: dict[tuple[str, str], str] = {
    # --- not disclosure: the literal is this script's own scratch path -------------------
    ("scripts/publish_micyte.py", "srv_path"): "the publisher's own --out default, on this host",
    ("scripts/repair_mss_invariants.py", "srv_path"): "prose telling an operator to work on a copy",
    # --- the sentence is ABOUT the boundary, and names the path it forbids reaching ------
    ("micyte/tools/pim_overview.py", "srv_path"):
        "'a tool in the published package may reach neither' — the literal is the thing refused",
    # --- allowlisted elsewhere with its own reasoning -----------------------------------
    ("micyte/core/datum_ops/field_registry.py", "live_msn"):
        "the three live namespace bindings; see test_public_package_has_no_live_instances "
        "and the 2026-08-22 revert that restored them",
    # --- DEBT: worked examples in prose that disclose the operator's county/city prefix --
    #     Cheap to retire: the synthetic space the test fixtures already use (3-2-3-17-9x)
    #     says the same thing about the numbering without naming where this host operates.
    ("micyte/core/mss/document_adapter.py", "live_msn"): "worked example in a docstring",
    ("micyte/core/payment_instrument.py", "live_msn"): "worked example about address length",
    ("micyte/domains/registry/levels.py", "live_msn"): "the county row in a levels table",
    ("micyte/tools/_node_names.py", "live_msn"): "worked examples, incl. a measured collision",
    ("micyte/tools/_place.py", "live_msn"): "worked example: the prefix IS the filter value",
    ("micyte/tools/_record_view.py", "live_msn"): "worked examples of facet matching",
    ("micyte/tools/_row_map.py", "live_msn"): "worked example of a minted document's name",
    ("micyte/tools/contacts_manager.py", "live_msn"): "a before/after note on a drawn column",
    ("micyte/tools/job_manager.py", "live_msn"): "worked example of what a job row holds",
    ("micyte/tools/ledger_books.py", "live_msn"): "a live alias address in a worked example",
    ("micyte/tools/stock_ledger.py", "live_msn"): "a field placeholder",
    # --- DEBT: a live instance pinned in shipped code or shipped data --------------------
    ("micyte/data_templates/agro_erp_taxonomy_source.yaml", "live_msn"):
        "a live farm's msn as a TEMPLATE's default msn_id",
    ("micyte/data_templates/product_profile.yaml", "live_msn"):
        "a live farm's msn as a TEMPLATE's default msn_id",
    # --- DEBT: host paths in files the cut carries verbatim -----------------------------
    #
    # `README.md` LEFT this table on 2026-10-04 (TASK-2026-10-02-002 P4), and it is the
    # first entry to be paid off rather than re-explained. Its reason read: "the private
    # host's README is exported as the package's; it names the runtime roots" — four /srv
    # paths, one deployment's product named as the downstream application, and five
    # canonical-doc links to pages this very gate filters out of the cut, so a reader of
    # the published README followed them to nothing. There are now two READMEs: the
    # public package's at the root, and the host's in `fnd_app/`, which the cut does not
    # carry.
    ("micyte/domains/reference_exchange/README.md", "srv_path"): "cites a host knowledge path",
}


def tracked_docs(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "docs"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def scan_literals(repo: Path, rel_path: str) -> list[tuple[int, str, str]]:
    """(line_no, kind, snippet) for every sensitive literal in a text file."""
    path = repo / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []  # binary/unreadable public asset — nothing to leak as text
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for kind, pat in SENSITIVE.items():
            m = pat.search(line)
            if m:
                hits.append((lineno, kind, line.strip()[:120]))
    return hits


def _publish_module():
    """`publish_micyte.py`'s own lists, loaded by path rather than imported.

    It must be the one place that says what ships: a second copy here would be a list that
    drifts from the cut it is meant to judge. By path, because that module loads THIS one
    the same way, and an import in both directions is a cycle.
    """
    spec = importlib.util.spec_from_file_location(
        "publish_micyte_lists", Path(__file__).resolve().with_name("publish_micyte.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exported_paths(repo: Path) -> list[str]:
    """Every file the public cut would carry, repo-relative.

    The same four things `publish_micyte.export()` copies: `micyte/` minus caches, the
    public half of `docs/`, the top-level files, and the public scripts. The workflow it
    writes into the export is generated there and has no counterpart here.
    """
    publish = _publish_module()
    out: list[str] = []
    micyte_root = repo / "micyte"
    if micyte_root.is_dir():
        for path in sorted(micyte_root.rglob("*")):
            rel = path.relative_to(repo)
            if any(part in publish.EXCLUDED_DIRS for part in rel.parts):
                continue
            if path.is_file():
                out.append(str(rel))
    out.extend(f for f in tracked_docs(repo) if not is_private(f))
    out.extend(name for name in publish.TOP_LEVEL_FILES if (repo / name).exists())
    out.extend(f"scripts/{name}" for name in publish.PUBLIC_SCRIPTS
               if (repo / "scripts" / name).exists())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    ap.add_argument("--list-private", action="store_true",
                    help="print private tracked doc paths, one per line, and exit 0")
    ap.add_argument("--export", action="store_true",
                    help="scan EVERYTHING the cut ships (micyte/, the public docs, the top-level "
                         "files, the public scripts) and not only docs/")
    ap.add_argument("--debt", action="store_true",
                    help="with --export: print each hit as a debt entry, for seeding the list")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    files = tracked_docs(repo)
    private = [f for f in files if is_private(f)]
    public = [f for f in files if not is_private(f)]

    if args.list_private:
        print("\n".join(private))
        return 0

    scanned = exported_paths(repo) if args.export else public
    leaks: list[tuple[str, int, str, str]] = []
    tolerated: list[tuple[str, int, str, str]] = []
    for f in scanned:
        for lineno, kind, snippet in scan_literals(repo, f):
            if args.export and (f, kind) in KNOWN_EXPORT_LITERAL_DEBT:
                tolerated.append((f, lineno, kind, snippet))
            else:
                leaks.append((f, lineno, kind, snippet))

    if args.debt:
        for f, kind in sorted({(f, k) for f, _l, k, _s in leaks + tolerated}):
            print(f'    ("{f}", "{kind}"): "",')
        return 0

    if args.export:
        print(f"export scanned : {len(scanned)} file(s)")
        hit = {(f, k) for f, _l, k, _s in tolerated}
        stale = sorted(set(KNOWN_EXPORT_LITERAL_DEBT) - hit)
        if stale:
            print(f"\nDEBT ENTRIES THAT NO LONGER HIT ({len(stale)}) — this list may only "
                  "shrink, so remove them:")
            for f, kind in stale:
                print(f"  - {f} [{kind}]")
            leaks.extend((f, 0, kind, "(debt entry no longer hits)") for f, kind in stale)
        if tolerated:
            print(f"  tolerated    : {len(tolerated)} known literal(s) in "
                  f"{len({f for f, _l, _k, _s in tolerated})} file(s) — TASK-2026-10-02-002")

    print(f"docs tracked : {len(files)}")
    print(f"  public     : {len(public)}")
    print(f"  private    : {len(private)}")
    if private:
        print("\nPRIVATE still present (must be removed before publish):")
        for f in private:
            print(f"  - {f}")
    if leaks:
        print(f"\nSENSITIVE LITERALS in public docs ({len(leaks)}):")
        for f, lineno, kind, snippet in leaks:
            print(f"  {f}:{lineno} [{kind}] {snippet}")

    ok = not private and not leaks
    print("\nGATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
