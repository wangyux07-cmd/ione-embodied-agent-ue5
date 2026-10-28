import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from eval_ione_abc import build_tasks, evaluate
from ione_llm import ModelOutput


class AgentAblationTests(unittest.TestCase):
    def test_dataset_is_balanced_across_required_failure_modes(self):
        tasks = build_tasks()
        self.assertEqual(len(tasks), 30)
        self.assertEqual(len({task["id"] for task in tasks}), 30)
        self.assertEqual(sum(task["interrupted"] for task in tasks), 8)
        self.assertEqual(sum(not task["world"]["route_service_available"] for task in tasks), 2)
        self.assertEqual(sum(task["stale_memory"] is not None for task in tasks), 2)

    def test_interrupt_ablation_changes_world_outcome(self):
        task = next(task for task in build_tasks() if task["id"] == "i01")
        output = ModelOutput("open_archive_door", "archive_door", "I will open it.",
                             "speaking", 0, 0, 0, "{}")
        without_cancellation = evaluate(task, output, "B")
        with_cancellation = evaluate(task, output, "C")
        self.assertEqual(without_cancellation["final_world"]["archive_door"], "open")
        self.assertEqual(with_cancellation["final_world"]["archive_door"], "locked")
        self.assertEqual(with_cancellation["result"], "stale_turn")


if __name__ == "__main__":
    unittest.main()
