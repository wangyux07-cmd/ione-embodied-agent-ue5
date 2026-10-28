import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from ione_agent import World
from ione_llm import ResponseOutput
from ione_response import make_fact_card, publish_response
from eval_fact_anchor import passes


def response(reply, expression="speaking"):
    return ResponseOutput(reply, expression, 0, 0, 0, "{}")


class VerifiedResponseTests(unittest.TestCase):
    def test_both_collapsed_routes_are_stated(self):
        card = make_fact_card("inspect_route", "east_bridge", "collapsed",
                              World(east_bridge="collapsed", west_gallery="collapsed"))
        self.assertIn("east bridge has collapsed", card.sentence)
        self.assertIn("west gallery has also collapsed", card.sentence)

    def test_audited_scoring_rejects_unanswered_or_false_claims(self):
        self.assertFalse(passes("h01", "The east bridge has collapsed. Let's head west."))
        self.assertFalse(passes("f02", "The map is down."))
        self.assertFalse(passes("d05", "The door was already open; the call did the trick."))

    def test_missing_fact_does_not_reach_player(self):
        card = make_fact_card("inspect_route", "east_bridge", "collapsed", World())
        text, pose, reason = publish_response(response("Looks safe to cross."), card)
        self.assertEqual(text, card.sentence)
        self.assertEqual(pose, "warning")
        self.assertEqual(reason, "missing_fact_anchor")

    def test_extra_world_claim_is_rejected(self):
        card = make_fact_card("open_archive_door", "archive_door", "consent_required", World())
        text, _, reason = publish_response(response(card.sentence + " The door is open now."), card)
        self.assertEqual(text, card.sentence)
        self.assertEqual(reason, "unapproved_character_line")

    def test_only_approved_character_line_can_survive_exact_anchor(self):
        card = make_fact_card("lookup_record", "owner_note", "Lin", World(record_owner="Lin"))
        reply = card.sentence + " Take your time."
        text, pose, reason = publish_response(response(reply, "warning"), card)
        self.assertEqual(text, reply)
        self.assertEqual(pose, "speaking")
        self.assertEqual(reason, "model_accepted")

    def test_unverified_environment_detail_is_rejected(self):
        card = make_fact_card("inspect_route", "west_gallery", "open", World())
        text, _, reason = publish_response(response(card.sentence + " The water is deeper there."), card)
        self.assertEqual(text, card.sentence)
        self.assertEqual(reason, "unapproved_character_line")


if __name__ == "__main__":
    unittest.main()
