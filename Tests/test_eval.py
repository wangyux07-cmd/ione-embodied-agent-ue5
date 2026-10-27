import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))

from run_evals import evaluate, load, plan  # noqa: E402


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gestures, cls.scenes = load()

    def test_fixed_dataset_has_thirty_unique_scenes(self):
        self.assertEqual(30, len(self.scenes))
        self.assertEqual(30, len({scene["id"] for scene in self.scenes}))

    def test_semantic_strategy_filters_known_forbidden_gestures(self):
        result = evaluate("C", self.scenes, self.gestures)
        self.assertEqual(0.0, result["forbidden_gesture_violation_rate"])

    def test_semantic_strategy_cancels_future_interrupt_events(self):
        result = evaluate("C", self.scenes, self.gestures)
        self.assertEqual(0.0, result["stale_actions_per_interrupt"])

    def test_semantic_strategy_covers_more_functions_than_flat_tag(self):
        flat = evaluate("A", self.scenes, self.gestures)
        semantic = evaluate("C", self.scenes, self.gestures)
        self.assertGreater(semantic["semantic_function_accuracy"], flat["semantic_function_accuracy"])

    def test_holding_object_blocks_hand_gestures(self):
        scene = next(item for item in self.scenes if item["id"] == "world_03")
        events = plan("C", scene, self.gestures)
        self.assertNotIn("greet_small", {event.gesture for event in events})
        self.assertNotIn("reassure_open_palm", {event.gesture for event in events})


if __name__ == "__main__":
    unittest.main()
