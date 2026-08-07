from __future__ import annotations

import json
import unittest
from pathlib import Path


class EvalSchemaTests(unittest.TestCase):
    def test_eval_cases_have_required_fields_and_unique_ids(self) -> None:
        path = Path(__file__).parents[1] / "evals" / "evals.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["skill"], "vln-innovation-study")
        self.assertGreaterEqual(len(data["cases"]), 8)
        identifiers = [case["id"] for case in data["cases"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for case in data["cases"]:
            self.assertTrue(case["prompt"])
            self.assertTrue(case["expected"])
            self.assertTrue(case["forbidden"])


if __name__ == "__main__":
    unittest.main()
