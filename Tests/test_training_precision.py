import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
from train_ione_sft import use_native_bf16


class PrecisionPolicyTests(unittest.TestCase):
    def test_t4_emulated_bf16_is_not_selected(self):
        self.assertFalse(use_native_bf16((7, 5), True))

    def test_ampere_requires_native_support(self):
        self.assertTrue(use_native_bf16((8, 0), True))
        self.assertFalse(use_native_bf16((8, 0), False))
