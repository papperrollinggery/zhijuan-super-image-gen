from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from rewrite_prompt_from_review import ISSUE_REWRITES, rewrite_prompt, rewrite_run  # noqa: E402
from imageops_core import count_prompt_words  # noqa: E402


class ReviewRewriteTest(unittest.TestCase):
    BASE_PROMPT = (
        "Create a 1:1 image.\n"
        "Show one clear subject with visible action.\n"
        "Compose with one focal path and clean spacing.\n"
        "Use motivated light and tactile materials.\n"
        "Text: avoid text unless requested.\n"
        "Constraints: no fake claims.\n"
    )

    def make_eligible_run(self, run_dir: Path, status: str = "PROCEED") -> None:
        (run_dir / "prompt.codex.txt").write_text(self.BASE_PROMPT, encoding="utf-8")
        (run_dir / "brief.json").write_text(f'{{"status": "{status}"}}\n', encoding="utf-8")

    def test_issue_tags_add_targeted_revision_lines(self) -> None:
        prompt = "Create a 16:9 image.\nText: keep labels large.\nConstraints: no fake claims.\n"
        followup = rewrite_prompt(prompt, ["too_generic", "weak_composition"])

        self.assertIn(ISSUE_REWRITES["too_generic"], followup)
        self.assertIn(ISSUE_REWRITES["weak_composition"], followup)
        self.assertIn("no fake claims", followup)
        self.assertNotIn(ISSUE_REWRITES["fake_claims"], followup)

    def test_two_issue_followup_keeps_short_shape_and_literal_invariants(self) -> None:
        prompt = (
            "Create a 16:9 poster.\n"
            "Show a grounded developer workbench.\n"
            "Compose with one focal path.\n"
            "Use motivated studio light.\n"
            "Text: Render only this literal text exactly: \"BUILD. SHIP. WIN.\".\n"
            "Constraints: user constraint: no price; avoid: official logos.\n"
        )
        followup = rewrite_prompt(prompt, ["too_generic", "weak_composition"])

        self.assertGreaterEqual(len(followup.splitlines()), 5)
        self.assertLessEqual(len(followup.splitlines()), 7)
        self.assertIn("BUILD. SHIP. WIN.", followup)
        self.assertIn("user constraint: no price", followup)
        self.assertIn("avoid: official logos", followup)
        self.assertIn(ISSUE_REWRITES["too_generic"], followup)
        self.assertIn(ISSUE_REWRITES["weak_composition"], followup)

    def test_unknown_issue_tag_fails_fast(self) -> None:
        with self.assertRaises(ValueError):
            rewrite_prompt("Create an image.", ["unknown_tag"])

    def test_first_two_tags_drive_rewrite(self) -> None:
        prompt = "Create a 4:5 image.\n"
        followup = rewrite_prompt(prompt, ["text_unreadable", "weak_materials", "fake_claims"])

        self.assertIn(ISSUE_REWRITES["text_unreadable"], followup)
        self.assertIn(ISSUE_REWRITES["weak_materials"], followup)
        self.assertNotIn(ISSUE_REWRITES["fake_claims"], followup)

    def test_rewrite_run_writes_followup_and_review_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.make_eligible_run(run_dir)
            (run_dir / "review.md").write_text("# Human Review\n", encoding="utf-8")

            followup_path = rewrite_run(run_dir, ["wrong_visual_family", "overconstrained"])

            self.assertTrue(followup_path.exists())
            self.assertIn("wrong_visual_family", (run_dir / "review.md").read_text(encoding="utf-8"))
            self.assertIn(ISSUE_REWRITES["overconstrained"], followup_path.read_text(encoding="utf-8"))
            self.assertTrue((run_dir / "drafts" / "followup.json").exists())

    def test_duplicate_tags_are_normalized_in_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.make_eligible_run(run_dir)

            rewrite_run(run_dir, ["too_generic", "too_generic", "fake_claims"])

            receipt = (run_dir / "drafts" / "followup.json").read_text(encoding="utf-8")
            self.assertEqual(receipt.count("too_generic"), 1)
            self.assertIn("fake_claims", receipt)

    def test_reference_drift_rejects_run_without_valid_reference_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.make_eligible_run(run_dir)
            (run_dir / "request.json").write_text('{"references": []}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requires valid references"):
                rewrite_run(run_dir, ["reference_drift"])

            self.assertFalse((run_dir / "drafts").exists())

    def test_reference_drift_accepts_valid_reference_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            reference_path = run_dir / "person.png"
            reference_path.write_bytes(b"\x89PNG\r\n\x1a\nextra")
            reference = str(reference_path.resolve())
            self.make_eligible_run(run_dir)
            (run_dir / "request.json").write_text(
                json.dumps({"references": [reference]}) + "\n", encoding="utf-8"
            )
            (run_dir / "identity_lock.json").write_text(
                json.dumps({"source_of_truth": "provided_references", "references": [reference]}) + "\n",
                encoding="utf-8",
            )

            followup = rewrite_run(run_dir, ["reference_drift"])
            self.assertTrue(followup.exists())
            self.assertIn(reference, (run_dir / "request.json").read_text(encoding="utf-8"))

    def test_followup_rejects_non_proceed_status_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.make_eligible_run(run_dir, "NEEDS_REFERENCES")
            with self.assertRaisesRegex(ValueError, "requires PROCEED"):
                rewrite_run(run_dir, ["too_generic"])
            self.assertFalse((run_dir / "drafts").exists())

    def test_followup_rejects_lexical_budget_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            long_line = " ".join(f"detail{i}" for i in range(185))
            prompt = (
                "Create a 1:1 image.\n"
                f"Show {long_line}.\n"
                "Compose with one focal path.\n"
                "Use motivated light.\n"
                "Text: avoid text.\n"
                "Constraints: no fake claims.\n"
            )
            (run_dir / "prompt.codex.txt").write_text(prompt, encoding="utf-8")
            (run_dir / "brief.json").write_text('{"status": "PROCEED"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lexical units"):
                rewrite_run(run_dir, ["too_generic"])
            self.assertFalse((run_dir / "drafts").exists())

    def test_near_limit_single_tag_followup_compacts_non_load_bearing_lines(self) -> None:
        filler = " ".join(f"detail{i}" for i in range(131))
        prompt = (
            "Create a 1:1 image with carefully directed commercial polish.\n"
            f"Show the requested product clearly with {filler}.\n"
            "Compose with one focal path and generous spacing.\n"
            "Use motivated light and tactile materials.\n"
            "Text: Render only this literal text exactly: \"KEEP ME\".\n"
            "Constraints: user constraint: no price; avoid: official logos.\n"
        )
        self.assertEqual(count_prompt_words(prompt), 178)

        followup = rewrite_prompt(prompt, ["too_generic"])

        self.assertLessEqual(count_prompt_words(followup), 190)
        self.assertGreaterEqual(len(followup.splitlines()), 5)
        self.assertLessEqual(len(followup.splitlines()), 7)
        self.assertIn("KEEP ME", followup)
        self.assertIn("user constraint: no price", followup)
        self.assertIn("avoid: official logos", followup)
        self.assertIn("detail0", followup)
        self.assertIn("detail130", followup)
        self.assertIn("1:1", followup)

    def test_near_limit_two_tag_followup_preserves_literal_and_constraints(self) -> None:
        filler = " ".join(f"detail{i}" for i in range(130))
        prompt = (
            "Create a 4:5 campaign image with carefully directed commercial polish.\n"
            f"Show the requested product clearly with {filler}.\n"
            "Compose with one focal path and generous spacing.\n"
            "Use motivated light and tactile materials.\n"
            "Text: Render only this literal text exactly: \"KEEP ME\".\n"
            "Constraints: user constraint: no price; avoid: official logos.\n"
        )

        self.assertEqual(count_prompt_words(prompt), 178)
        followup = rewrite_prompt(prompt, ["too_generic", "weak_composition"])

        self.assertLessEqual(count_prompt_words(followup), 190)
        self.assertGreaterEqual(len(followup.splitlines()), 5)
        self.assertLessEqual(len(followup.splitlines()), 7)
        self.assertIn("KEEP ME", followup)
        self.assertIn("user constraint: no price", followup)
        self.assertIn("avoid: official logos", followup)
        self.assertIn("detail0", followup)
        self.assertIn("detail129", followup)
        self.assertIn("4:5", followup)
        self.assertIn("campaign image", followup)


if __name__ == "__main__":
    unittest.main()
