"""PIM's Authoring tab: a gallery of writing, and one piece with its versions.

Restructured 2026-10-06 on the operator's instruction: *"a simple gallery of articles, where
the first gallery card is just a box with a '+' … so either someone can select an existing
article to see and edit it, or see prior changes, then on an article someone can select from
block buttons like 'send emailer' or 'post blog' where a specific version is used. The
workflow that would follow is like a 'check out' almost. Giving a preview of the version
being used. … The more form fields the less intuitive."*

What was there before (2026-09-14): three views of one article cut by destination —
Articles, Newsletter, Website — each offering the one act about it, plus a four-field form.
The destination is now a block button on the piece's own page, chosen with the version in
sight; a new piece asks for a title and the writing and nothing else.

These tests pin the parts a redesign is most likely to quietly lose.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from micyte.ports.site_hosting import PublishedArticle
from micyte.tools.pim_design import (
    DEFAULT_TAB,
    NEW_PIECE,
    PIECE_QUERY,
    TAB_QUERY,
    VERSION_QUERY,
    PimDesign,
)

BODY = "# On Playing the Light\n\nSome roles you build. Others you agree to stand inside."
OLDER = "# On Playing the Light\n\nAn earlier draft of the same thought."


def _vid(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]


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


def _piece(slug="on_playing_the_light", *, hidden=False, body=BODY, date="2026-07-02"):
    return PublishedArticle(
        slug=slug, title="On Playing the Light", date=date, subtopic="writing",
        hidden=hidden, url=f"https://masonlenehan.com/article/{slug}.html",
        extra={"body": body, "excerpt": "Some roles you build."})


def _panes(site, *, sent=None, subscribers=None, versions=None, **query):
    context = {"private_dir": None, "port": lambda _p: site}
    if sent is not None:
        context["sent_issues"] = sent
    if subscribers is not None:
        context["subscribers"] = subscribers
    if versions is not None:
        context["versions"] = versions
    payload = PimDesign().build_panel_payload(
        sandbox_id="pim", host_context=context, extra_query=query or None)
    return payload, {t["id"]: t["panel_payload"] for t in payload["tabs"]}


def _blocks(page):
    """The block buttons on a piece's page, by title."""
    return {p["panel_payload"].get("title"): p["panel_payload"]
            for p in page["panes"][3]["panel_payload"]["panes"]}


class TheTwoViews(unittest.TestCase):
    def test_writing_is_the_landing_and_contacts_is_beside_it(self) -> None:
        payload, _ = _panes(_Site())
        self.assertEqual([t["id"] for t in payload["tabs"]], ["writing", "contacts"])
        self.assertEqual(DEFAULT_TAB, "writing")
        self.assertEqual(payload["active_tab"], "writing")

    def test_the_old_destination_tabs_land_on_writing(self) -> None:
        for old in ("articles", "newsletter", "website", "posts", "drafts"):
            payload, _ = _panes(_Site(), **{TAB_QUERY: old})
            self.assertEqual(payload["active_tab"], "writing", old)


class TheGallery(unittest.TestCase):
    def test_it_is_a_card_gallery_whose_first_card_is_a_plus(self) -> None:
        _, panes = _panes(_Site((_piece(),)))
        gallery = panes["writing"]
        self.assertEqual(gallery["container"], "project_gallery")
        self.assertEqual(gallery["new_card"], {"label": "New piece", "value": NEW_PIECE})
        self.assertEqual(gallery["pick_param"], PIECE_QUERY)

    def test_a_card_carries_the_first_line_and_what_became_of_it(self) -> None:
        _, panes = _panes(_Site((_piece(), _piece("second", hidden=True, date="2026-08-01"))),
                          sent={"on_playing_the_light": {"sent_at": "2026-07-03T10:00:00Z"}})
        cards = {c["slug"]: c for c in panes["writing"]["projects"]}
        self.assertEqual(cards["on_playing_the_light"]["excerpt"], "Some roles you build.")
        self.assertEqual(cards["on_playing_the_light"]["meta"], "on the site · sent · 2026-07-02")
        self.assertEqual(cards["second"]["meta"], "draft · 2026-08-01")

    def test_newest_first(self) -> None:
        _, panes = _panes(_Site((_piece("old", date="2024-01-01"), _piece("new", date="2026-09-01"))))
        self.assertEqual([c["slug"] for c in panes["writing"]["projects"]], ["new", "old"])

    def test_an_issue_mailed_in_with_no_article_is_a_card_too(self) -> None:
        _, panes = _panes(_Site(()), sent={"mailed_in": {
            "subject": "Mailed In", "sent_at": "2026-06-01T00:00:00Z", "body_text": "Hello all,\nnews."}})
        [card] = panes["writing"]["projects"]
        self.assertEqual((card["slug"], card["name"], card["excerpt"]), ("mailed_in", "Mailed In", "Hello all,"))
        self.assertIn("not an article yet", card["meta"])

    def test_an_empty_gallery_still_has_the_plus(self) -> None:
        _, panes = _panes(_Site(()))
        self.assertEqual(panes["writing"]["projects"], [])
        self.assertTrue(panes["writing"]["new_card"])
        self.assertIn("+", panes["writing"]["empty_text"])


class ANewPiece(unittest.TestCase):
    def _form(self):
        _, panes = _panes(_Site(()), **{PIECE_QUERY: NEW_PIECE})
        page = panes["writing"]
        return page["panes"][1]["panel_payload"]

    def test_asks_for_a_title_and_the_writing_and_nothing_else(self) -> None:
        self.assertEqual([f["key"] for f in self._form()["fields"]], ["title", "content"])
        content = next(f for f in self._form()["fields"] if f["key"] == "content")
        self.assertEqual(content["type"], "textarea")

    def test_is_saved_as_a_draft_through_the_publish_door(self) -> None:
        action = self._form()["submit_action"]
        self.assertTrue(action["route"].endswith("/publish"))
        self.assertEqual(action["fixed"], {"visibility": "draft"})
        self.assertNotIn("confirm", action)

    def test_the_way_back_is_clearing_the_piece(self) -> None:
        _, panes = _panes(_Site(()), **{PIECE_QUERY: NEW_PIECE})
        back = panes["writing"]["panes"][0]["panel_payload"]["back"]
        self.assertEqual((back["param"], back["value"]), (PIECE_QUERY, ""))


class OpeningOnePiece(unittest.TestCase):
    def _page(self, site, **extra):
        _, panes = _panes(site, **extra)
        return panes["writing"]

    def test_the_editor_is_PREFILLED_with_title_and_content_only(self) -> None:
        page = self._page(_Site((_piece(),)), **{PIECE_QUERY: "on_playing_the_light"})
        editor = page["panes"][1]["panel_payload"]
        self.assertEqual([f["key"] for f in editor["fields"]], ["title", "content"])
        self.assertEqual(editor["fields"][0]["value"], "On Playing the Light")
        self.assertEqual(editor["fields"][1]["value"],
                         "Some roles you build. Others you agree to stand inside.")
        self.assertEqual(editor["submit_action"]["fixed"],
                         {"prior_slug": "on_playing_the_light", "visibility": "public"})

    def test_a_piece_the_host_has_no_versions_for_shows_its_current_text_as_one(self) -> None:
        page = self._page(_Site((_piece(),)), **{PIECE_QUERY: "on_playing_the_light"})
        table = page["panes"][2]["panel_payload"]
        self.assertEqual(table["row_count"], 1)
        self.assertEqual(table["rows"][0]["version"], _vid(BODY))
        self.assertIn("current", table["rows"][0]["status"])
        self.assertEqual(table["rows"][0]["details"]["text"], BODY, "the reveal IS the preview")
        self.assertIsNone(table["pick"], "one version: nothing to check out")

    def test_the_versions_the_host_kept_are_listed_newest_first_with_a_check_out(self) -> None:
        versions = {"on_playing_the_light": {"head": _vid(BODY), "on_site": _vid(BODY), "versions": [
            {"id": _vid(BODY), "saved_at": "2026-07-02T09:00:00+00:00", "title": "On Playing the Light",
             "hidden": False, "head": True, "on_site": True, "sent_at": "", "body": BODY},
            {"id": _vid(OLDER), "saved_at": "2026-07-01T09:00:00+00:00", "title": "On Playing the Light",
             "hidden": True, "head": False, "on_site": False, "sent_at": "2026-07-01T10:00:00+00:00", "body": OLDER},
        ]}}
        page = self._page(_Site((_piece(),)), versions=versions, **{PIECE_QUERY: "on_playing_the_light"})
        table = page["panes"][2]["panel_payload"]
        self.assertEqual([r["version"] for r in table["rows"]], [_vid(BODY), _vid(OLDER)])
        self.assertEqual(table["rows"][0]["status"], "current · on the site · checked out")
        self.assertEqual(table["rows"][1]["status"], "sent 2026-07-01")
        self.assertEqual(table["pick"]["param"], VERSION_QUERY)
        self.assertEqual([o["value"] for o in table["pick"]["options"]], [_vid(BODY), _vid(OLDER)])

    def test_CHECKING_OUT_an_older_version_puts_it_in_the_editor_and_under_every_button(self) -> None:
        versions = {"on_playing_the_light": {"head": _vid(BODY), "on_site": _vid(BODY), "versions": [
            {"id": _vid(BODY), "saved_at": "2026-07-02T09:00:00+00:00", "title": "On Playing the Light",
             "hidden": False, "head": True, "on_site": True, "sent_at": "", "body": BODY},
            {"id": _vid(OLDER), "saved_at": "2026-07-01T09:00:00+00:00", "title": "On Playing the Light",
             "hidden": True, "head": False, "on_site": False, "sent_at": "", "body": OLDER},
        ]}}
        page = self._page(_Site((_piece(),)), versions=versions,
                          subscribers={"count": 30, "list_address": "news@masonlenehan.com"},
                          **{PIECE_QUERY: "on_playing_the_light", VERSION_QUERY: _vid(OLDER)})
        editor = page["panes"][1]["panel_payload"]
        self.assertEqual(editor["fields"][1]["value"], "An earlier draft of the same thought.")
        facts = page["panes"][0]["panel_payload"]
        checked = next(r["value"] for r in facts["rows"] if r["fact"] == "checked out")
        self.assertIn(_vid(OLDER), checked)
        self.assertIn("not the current text", checked)
        blocks = _blocks(page)
        send = blocks["Send emailer"]
        self.assertEqual(send["submit_action"]["fixed"], {"slug": "on_playing_the_light", "version": _vid(OLDER)})
        self.assertIn(_vid(OLDER), send["submit_action"]["confirm"]["text"])
        self.assertIn("30 people", send["submit_note"], "the consequence is the line under the verb")
        post = blocks["Post blog"]
        self.assertEqual(post["submit_action"]["fixed"]["version"], _vid(OLDER))
        self.assertEqual(post["submit_action"]["fixed"]["visibility"], "public")
        self.assertTrue(post["submit_action"]["route"].endswith("/publish"))

    def test_an_unknown_version_falls_back_to_the_current_text(self) -> None:
        page = self._page(_Site((_piece(),)), **{PIECE_QUERY: "on_playing_the_light", VERSION_QUERY: "nope"})
        self.assertEqual(page["panes"][1]["panel_payload"]["fields"][1]["value"],
                         "Some roles you build. Others you agree to stand inside.")

    def test_the_block_buttons_follow_the_piece(self) -> None:
        subs = {"count": 2, "list_address": "news@x.test"}
        live = _blocks(self._page(_Site((_piece(),)), subscribers=subs, **{PIECE_QUERY: "on_playing_the_light"}))
        self.assertEqual(set(live), {"Send emailer", "Take off the site"})
        self.assertEqual(live["Take off the site"]["submit_action"]["fixed"],
                         {"slug": "on_playing_the_light", "visibility": "draft"})
        draft = _blocks(self._page(_Site((_piece(hidden=True),)), subscribers=subs, **{PIECE_QUERY: "on_playing_the_light"}))
        self.assertEqual(set(draft), {"Send emailer", "Post blog", "Delete this draft"})
        self.assertEqual(draft["Delete this draft"]["submit_action"]["confirm"]["expect"], "retire")
        self.assertTrue(draft["Delete this draft"]["submit_action"]["danger"])

    def test_with_nobody_subscribed_the_send_button_is_a_sentence_instead(self) -> None:
        blocks = _blocks(self._page(_Site((_piece(),)), subscribers={"count": 0}, **{PIECE_QUERY: "on_playing_the_light"}))
        self.assertIn("Nobody has subscribed", blocks["Send emailer"]["empty_text"])
        self.assertNotIn("submit_action", blocks["Send emailer"])

    def test_EDITING_A_SENT_PIECE_FORKS_IT(self) -> None:
        page = self._page(_Site((_piece(),)), sent={"on_playing_the_light": {"sent_at": "2026-07-03T00:00:00Z"}},
                          **{PIECE_QUERY: "on_playing_the_light"})
        editor = page["panes"][1]["panel_payload"]
        self.assertEqual(editor["submit_action"]["fixed"], {"fork_of": "on_playing_the_light", "visibility": "draft"})
        self.assertIn("new piece", editor["submit_label"])
        self.assertNotIn("Delete this draft", _blocks(page), "what went out is not deleted from here")

    def test_a_stale_address_falls_back_to_the_gallery(self) -> None:
        page = self._page(_Site((_piece(),)), **{PIECE_QUERY: "gone"})
        self.assertEqual(page["container"], "project_gallery")

    def test_an_issue_mailed_in_opens_its_own_page_with_post_blog(self) -> None:
        page = self._page(_Site(()), sent={"mailed_in": {
            "subject": "Mailed In", "sent_at": "2026-06-01T00:00:00Z", "body_text": "Hello all,\nnews.", "target_count": 23}},
            **{PIECE_QUERY: "mailed_in"})
        titles = [p["panel_payload"].get("title") for p in page["panes"]]
        self.assertEqual(titles, ["Mailed In", "What went out", "Post blog"])
        post = page["panes"][2]["panel_payload"]["submit_action"]
        self.assertTrue(post["route"].endswith("/newsletter.post"))
        self.assertEqual(post["fixed"], {"slug": "mailed_in"})


class TheContactsView(unittest.TestCase):
    def test_offers_one_act_a_reader_on_or_off_typed(self) -> None:
        _, panes = _panes(_Site(()))
        # The fixture carries no `contacts` fact → not configured → the roster pane alone.
        self.assertEqual(panes["contacts"]["container"], "record_table")
        payload = PimDesign().build_panel_payload(
            sandbox_id="pim",
            host_context={"private_dir": None, "port": lambda _p: _Site(()),
                          "contacts": {"rows": [], "subscribed": 0, "unsubscribed": 0, "why_not": ""}})
        view = {t["id"]: t["panel_payload"] for t in payload["tabs"]}["contacts"]
        self.assertEqual(view["container"], "composite")
        self.assertTrue(view["configured"])
        form = view["panes"][1]["panel_payload"]
        self.assertEqual([f["key"] for f in form["fields"]], ["email", "subscribed"])
        self.assertTrue(form["submit_action"]["route"].endswith("/contact.set_subscription"))
        self.assertEqual(form["submit_action"]["confirm"]["expect"], "change")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
