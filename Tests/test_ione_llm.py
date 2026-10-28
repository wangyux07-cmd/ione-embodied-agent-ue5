import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from ione_agent import IoneHarness, World
from ione_llm import ModelOutput, apply_model_output, begin_model_request


class LocalModelBoundaryTests(unittest.TestCase):
    def output(self, intent, target, reply="Done"):
        return ModelOutput(intent, target, reply, "speaking", 0, 0, 0, "{}")

    def test_model_cannot_open_without_consent(self):
        agent = IoneHarness()
        turn, result = apply_model_output(agent, self.output("open_archive_door", "archive_door", "Opened."))
        self.assertEqual(result, "consent_required")
        self.assertEqual(agent.world.archive_door, "locked")
        self.assertIn("sealed", turn.proposal.dialogue)

    def test_model_cannot_invent_route_result(self):
        agent = IoneHarness()
        turn, result = apply_model_output(agent, self.output("inspect_route", "east_bridge", "Safe."))
        self.assertEqual(result, "collapsed")
        self.assertIn("collapsed", turn.proposal.dialogue)

    def test_authorized_door_mutates_world(self):
        agent = IoneHarness(World(owner_consent=True))
        _, result = apply_model_output(agent, self.output("open_archive_door", "archive_door"))
        self.assertEqual(result, "opened")
        self.assertEqual(agent.world.archive_door, "open")

    def test_interrupted_inference_cannot_commit_late_result(self):
        agent = IoneHarness(World(owner_consent=True))
        generation = begin_model_request(agent)
        agent.interrupt()
        _, result = apply_model_output(agent, self.output("open_archive_door", "archive_door"),
                                       expected_generation=generation)
        self.assertEqual(result, "stale_turn")
        self.assertEqual(agent.world.archive_door, "locked")

    def test_tool_failure_does_not_invent_route(self):
        agent = IoneHarness(World(route_service_available=False))
        turn, result = apply_model_output(agent, self.output("inspect_route", "east_bridge", "Safe."))
        self.assertEqual(result, "tool_unavailable")
        self.assertIn("cannot verify", turn.proposal.dialogue)

    def test_authoritative_record_beats_stale_memory(self):
        agent = IoneHarness(World(record_owner="Lin"))
        agent.memory.append("old_owner:Mara")
        turn, result = apply_model_output(agent, self.output("lookup_record", "owner_note", "Mara owns it."))
        self.assertEqual(result, "Lin")
        self.assertIn("Lin", turn.proposal.dialogue)
        self.assertNotIn("Mara", turn.proposal.dialogue)


if __name__ == "__main__":
    unittest.main()
