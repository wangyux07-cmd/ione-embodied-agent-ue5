import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from train_ione_sft import use_native_bf16, precision_for_phase


class PrecisionPolicyTests(unittest.TestCase):
    def test_t4_emulated_bf16_is_not_selected(self):
        self.assertFalse(use_native_bf16((7, 5), True))

    def test_ampere_requires_native_support(self):
        self.assertTrue(use_native_bf16((8, 0), True))
        self.assertFalse(use_native_bf16((8, 0), False))

    def test_t4_pilot_does_not_use_fp16(self):
        self.assertEqual(precision_for_phase('pilot', False), 'fp32')
        self.assertEqual(precision_for_phase('smoke', False), 'fp16')
        self.assertEqual(precision_for_phase('pilot', True), 'bf16')

    def test_combined_batch_can_pin_fp32_on_any_gpu(self):
        self.assertEqual(precision_for_phase('pilot', True, forced='fp32'), 'fp32')
        self.assertEqual(precision_for_phase('pilot', False, forced='fp32'), 'fp32')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            precision_for_phase('pilot', True, forced='unknown')
