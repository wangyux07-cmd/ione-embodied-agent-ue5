import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from ione_agent import IoneHarness, World


class AgentContractTests(unittest.TestCase):
    def test_world_grounding_changes_route_answer(self):
        agent = IoneHarness()
        turn = agent.propose("Can I cross the east bridge?", "tool")
        self.assertEqual(agent.execute(turn), "collapsed")
        self.assertIn("west gallery", turn.proposal.dialogue)

    def test_consent_gate_prevents_world_mutation(self):
        agent = IoneHarness()
        turn = agent.propose("Open the sealed record", "embodied")
        self.assertEqual(agent.execute(turn), "consent_required")
        self.assertEqual(agent.world.archive_door, "locked")

    def test_interrupt_rejects_old_tool_call(self):
        agent = IoneHarness(World(owner_consent=True))
        old = agent.propose("Open the record", "embodied")
        agent.interrupt()
        self.assertEqual(agent.execute(old), "stale_turn")
        self.assertEqual(agent.world.archive_door, "locked")
        self.assertEqual(old.proposal.fork_state, "listening")

    def test_committed_action_is_recorded(self):
        agent = IoneHarness(World(owner_consent=True))
        turn = agent.propose("Open the record", "embodied")
        self.assertEqual(agent.execute(turn), "opened")
        self.assertEqual(agent.world.archive_door, "open")
        self.assertEqual(agent.memory, ["archive_door_opened_with_consent"])


if __name__ == "__main__":
    unittest.main()
