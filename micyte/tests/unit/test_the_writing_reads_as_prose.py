"""The writing on a piece's page is set as PROSE, and a partial date reads as the part known.

TASK-2026-10-07-001. The operator's client: *"can you adjust the font and background font
color on the dashboard authoring page?"* The editor's two fields and the version preview
declare `prose`, which the renderer turns into a reading face at a reading size; the card
and the facts bar stop printing the pool's `2024-00-00` as if it were a day.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from micyte.ports.site_hosting import PublishedArticle
from micyte.tools.pim_design import NEW_PIECE, PIECE_QUERY, PimDesign, _pretty_date


class _Site:
    def __init__(self, pieces=()):
        self._pieces = pieces

    def list_articles(self, *, site=""):
        return self._pieces

    def list_subtopics(self, *, site=""):
        return ("writing",)

    def list_pages(self, *, site=""):
        return ()

    def list_site_content(self, *, site=""):
        return {"enabled": True, "pages": [], "gallery": {}}


def _writing(site, **query):
    payload = PimDesign().build_panel_payload(
        sandbox_id="pim", host_context={"private_dir": None, "port": lambda _p: site}, extra_query=query or None)
    return {t["id"]: t["panel_payload"] for t in payload["tabs"]}["writing"]


PIECE = PublishedArticle(slug="fall_2024_newsletter", title="Fall 2024 newsletter", date="2024-00-00",
                         subtopic="writing", hidden=False, url="https://x.test/article/fall_2024_newsletter.html",
                         extra={"body": "# Fall 2024 newsletter\n\nNever fear.", "excerpt": "Never fear."})


class TheWritingIsProse(unittest.TestCase):
    def test_a_new_piece_s_title_and_writing_are_prose(self) -> None:
        form = _writing(_Site(()), **{PIECE_QUERY: NEW_PIECE})["panes"][1]["panel_payload"]
        self.assertEqual([(f["key"], f.get("prose")) for f in form["fields"]], [("title", True), ("content", True)])

    def test_the_editor_and_the_version_preview_are_prose(self) -> None:
        page = _writing(_Site((PIECE,)), **{PIECE_QUERY: "fall_2024_newsletter"})
        editor = page["panes"][1]["panel_payload"]
        self.assertTrue(all(f.get("prose") for f in editor["fields"]))
        self.assertTrue(page["panes"][2]["panel_payload"]["detail_prose"], "the reveal IS the preview; it reads as prose")


class APartialDateReadsAsWhatIsKnown(unittest.TestCase):
    def test_the_formula(self) -> None:
        self.assertEqual(_pretty_date("2026-10-05"), "2026-10-05")
        self.assertEqual(_pretty_date("2024-00-00"), "2024")
        self.assertEqual(_pretty_date("2024-10-00"), "2024-10")
        self.assertEqual(_pretty_date("0000-00-00"), "")
        self.assertEqual(_pretty_date("2026-10-05T19:07:00Z"), "2026-10-05")
        self.assertEqual(_pretty_date(""), "")

    def test_on_the_card_and_in_the_facts(self) -> None:
        gallery = _writing(_Site((PIECE,)))
        self.assertEqual(gallery["projects"][0]["meta"], "on the site · 2024")
        page = _writing(_Site((PIECE,)), **{PIECE_QUERY: "fall_2024_newsletter"})
        facts = {r["fact"]: r["value"] for r in page["panes"][0]["panel_payload"]["rows"]}
        self.assertEqual(facts["date"], "2024")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
