from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_vln_source.py"
SPEC = importlib.util.spec_from_file_location("prepare_vln_source", SCRIPT)
assert SPEC and SPEC.loader
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class PrepareVlnSourceTests(unittest.TestCase):
    def make_pdf(self, root: Path, name: str, payload: bytes) -> Path:
        path = root / name
        path.write_bytes(b"%PDF-1.4\n" + payload)
        return path

    def test_prefers_original_over_compare(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = self.make_pdf(root, "paper.pdf", b"original")
            compare = self.make_pdf(root, "paper.compare.pdf", b"translated")
            candidates = prepare.inspect_candidates([compare, original])
            selected = prepare.choose_anchor(candidates)
            self.assertEqual(Path(selected["path"]), original.resolve())
            self.assertEqual(selected["role"], "original-candidate")

    def test_collapses_identical_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_pdf(root, "paper.pdf", b"same")
            second = self.make_pdf(root, "paper-copy.pdf", b"same")
            candidates = prepare.inspect_candidates([first, second])
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["duplicate_paths"], [str(second.resolve())])

    def test_identical_original_replaces_compare_as_primary_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compare = self.make_pdf(root, "paper.compare.pdf", b"same")
            original = self.make_pdf(root, "paper.pdf", b"same")
            candidates = prepare.inspect_candidates([compare, original])
            self.assertEqual(candidates[0]["path"], str(original.resolve()))
            self.assertEqual(candidates[0]["role"], "original-candidate")
            self.assertIn(str(compare.resolve()), candidates[0]["duplicate_paths"])

    def test_refuses_ambiguous_distinct_originals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_pdf(root, "paper-v1.pdf", b"one")
            second = self.make_pdf(root, "paper-v2.pdf", b"two")
            candidates = prepare.inspect_candidates([first, second])
            with self.assertRaises(prepare.SourcePreparationError):
                prepare.choose_anchor(candidates)

    def test_inventory_extracts_structural_anchors(self) -> None:
        pages = [
            "1 Introduction\nFigure 1: Pipeline\nTable 2 Results\nx = y (3)",
            "Conclusion",
        ]
        inventory = prepare.build_inventory(pages)
        self.assertIn(
            {"label": "Figure 1", "pdf_page": 1}, inventory["figures"]
        )
        self.assertIn({"label": "Table 2", "pdf_page": 1}, inventory["tables"])
        self.assertIn(
            {"label": "Equation 3", "pdf_page": 1}, inventory["equations"]
        )

    def test_transformed_source_cannot_be_page_grounded(self) -> None:
        selected = {"role": "reading-aid"}
        mode, warnings = prepare.determine_locator_mode(
            selected, ["x" * 300], 1, False
        )
        self.assertEqual(mode, "structure-grounded")
        self.assertTrue(warnings)

    def test_mismatched_page_boundaries_are_structure_grounded(self) -> None:
        selected = {"role": "original-candidate"}
        mode, warnings = prepare.determine_locator_mode(
            selected, ["x" * 300, "y" * 300], 3, False
        )
        self.assertEqual(mode, "structure-grounded")
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
