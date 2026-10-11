"""What a hub composes, said once, by the hub, in a form a test can check.

## Why this primitive exists

Measured 2026-10-03 (TASK-2026-10-02-002): the `grantor` package declared five tools and
its hub composed none of them. `credit_ledger`, `subscription_book`, `grantor_tolling`
and `grantor_permissions` were built, tested, write-owning surfaces that no hub composed,
that were absent from `LIVE_TOOL_IDS`, and that were therefore reachable only by typing
`?tool=` into the address bar. `quiar_overview` and `project_manager` were in the same
state while the package manifest said "both are still reachable from the menubar".

Nothing caught it, and the reason is worth keeping: the claim lived as PROSE in a test
table — *"grantor's Credits tab"* — and prose asserts. Four claims, no implementation
behind any of them, and a green suite over all four.

So a hub now DECLARES what it composes, and the declaration is derived from the same
table the hub builds its tabs from. `fnd_app/tests/architecture/test_tool_registry_shape.py`
reads it, and a dark tool's entry must name a hub that actually composes it.

## The one-hop rule

Some tabs are filled by an intermediate composite that is not itself a registered tool —
`quiar`'s Jobs tab is `JobsPane`, which stacks `job_document_view` above `job_manager`,
and its own `tool_id` (`quiar_jobs`) names no registered tool. A composite like that
declares `composes` of its own, and :func:`composed_ids` flattens one level per hop until
it reaches ids that stand on their own. That is why the function recurses rather than
reading one attribute: the hub's claim must be about the tools an operator can reach, not
about the wrappers between.
"""

from __future__ import annotations

from typing import Any


def composed_ids(tools: Any) -> tuple[str, ...]:
    """The registered tool ids an iterable of tool INSTANCES stands for, in order.

    A tool that declares `composes` contributes what it composes, not itself: it is a
    wrapper, and naming the wrapper would make the claim unfollowable. One that does not
    contributes its own `tool_id`. Duplicates are dropped, keeping the first position —
    two tabs may legitimately draw the same tool (brevat's Sales tab and the grantor
    sandbox's `sales` document are one tool opening on two books).
    """
    out: list[str] = []
    for tool in tools:
        if tool is None:
            continue
        nested = getattr(tool, "composes", ())
        ids = tuple(nested) if nested else (getattr(tool, "tool_id", ""),)
        for tool_id in ids:
            if tool_id and tool_id not in out:
                out.append(tool_id)
    return tuple(out)
