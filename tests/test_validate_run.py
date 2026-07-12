from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_run import validate_run_directory  # noqa: E402
from imageops_core import count_prompt_words  # noqa: E402


class ValidateRunTest(unittest.TestCase):
    DEFAULT_TASK = (
        "Create a 16:9 developer poster. Headline: BUILD. SHIP. WIN.\n"
        "Constraints: no price; no awards. Avoid: floating badges."
    )

    def invoke_create(
        self,
        root: Path,
        *,
        task: str | None = None,
        blocked: bool = False,
        reference: str | None = None,
        check: bool = True,
    ) -> tuple[Path, subprocess.CompletedProcess[str]]:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "create_run.py"),
            "--task",
            task or self.DEFAULT_TASK,
            "--slug",
            "validator-test",
            "--output-root",
            str(root),
        ]
        if blocked:
            command.append("--blocked")
        if reference:
            command.extend(["--reference", reference])
        result = subprocess.run(command, cwd=ROOT, check=check, capture_output=True, text=True)
        return next(path for path in root.iterdir() if path.is_dir()), result

    def create_run(self, root: Path, **kwargs: object) -> Path:
        return self.invoke_create(root, **kwargs)[0]

    def test_valid_run_and_explicit_blocked_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.create_run(Path(tmp), blocked=True)
            self.assertEqual(validate_run_directory(run_dir), [])
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["feasibility_status"], "BLOCKED")
            self.assertEqual(metadata["runtime_version"], "2.1.0")
            self.assertEqual(metadata["schema_version"], "2.1.0")
            self.assertEqual(len(metadata["input_sha256"]), 64)
            self.assertEqual(metadata["artifact_receipt"]["algorithm"], "sha256")
            self.assertIn("prompt.codex.txt", metadata["artifact_receipt"]["hashes"])

    def test_create_run_stdout_and_non_proceed_recommendation_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = "Create a portrait and keep her face, hairstyle, and proportions unchanged from the attachment."
            run_dir, result = self.invoke_create(Path(tmp), task=task)

            self.assertEqual(result.returncode, 0)
            self.assertIn("Image task status: NEEDS_REFERENCES", result.stdout)
            self.assertIn("Files created:\n- ", result.stdout)
            self.assertIn("Recommendation:\nDo not render yet.", result.stdout)
            self.assertEqual(validate_run_directory(run_dir), [])

    def test_missing_reference_stays_unprovided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "missing.png")
            run_dir = self.create_run(Path(tmp) / "runs", reference=missing)
            request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(request["references"], [])
            self.assertEqual(metadata["references"], [])
            self.assertEqual(request["invalid_references"], [missing])

    def test_non_image_reference_stays_unprovided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "not-image.txt"
            reference.write_text("not an image", encoding="utf-8")
            task = "Recreate the exact product from the reference image as a 4:5 product poster."
            run_dir, result = self.invoke_create(Path(tmp) / "runs", task=task, reference=str(reference))
            request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0)
            self.assertEqual(metadata["feasibility_status"], "NEEDS_REFERENCES")
            self.assertEqual(request["references"], [])
            self.assertEqual(request["invalid_references"], [str(reference)])

    def test_remote_url_is_recorded_but_does_not_unlock_identity_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            remote = "https://example.com/404.png"
            task = "Recreate the exact product from the reference image as a 4:5 product poster."
            run_dir, result = self.invoke_create(Path(tmp) / "runs", task=task, reference=remote)
            request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            identity_lock = json.loads((run_dir / "identity_lock.json").read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0)
            self.assertEqual(metadata["feasibility_status"], "NEEDS_REFERENCES")
            self.assertEqual(request["references"], [])
            self.assertEqual(request["reference_urls"], [remote])
            self.assertTrue(metadata["identity_lock_used"])
            self.assertEqual(identity_lock["source_of_truth"], "explicit_user_description")
            self.assertEqual(identity_lock["references"], [])
            self.assertNotIn("Image task status: PROCEED", result.stdout)

    def test_remote_url_tampering_invalidates_input_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = "Recreate the exact product from the reference image as a 4:5 product poster."
            run_dir, _ = self.invoke_create(
                Path(tmp) / "runs",
                task=task,
                reference="https://example.com/original.png",
            )
            request_path = run_dir / "request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["reference_urls"] = ["https://example.com/replaced.png"]
            request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")

            errors = validate_run_directory(run_dir)

            self.assertTrue(any("input_sha256" in error for error in errors))

    def test_192_unit_exact_product_request_compacts_before_proceed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = "Create a 4:5 exact product poster using the reference image with a red dial and walnut base."
            details: list[str] = []
            while count_prompt_words(base + " " + " ".join(details)) < 192:
                details.append(f"detail{len(details)}")
            task = base + " " + " ".join(details)
            self.assertEqual(count_prompt_words(task), 192)
            reference = Path(tmp) / "product.png"
            reference.write_bytes(b"\x89PNG\r\n\x1a\nextra")
            run_dir, result = self.invoke_create(
                Path(tmp) / "runs", task=task, reference=str(reference)
            )
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            prompt = (run_dir / "prompt.codex.txt").read_text(encoding="utf-8")

            self.assertEqual(result.returncode, 0)
            self.assertEqual(metadata["feasibility_status"], "PROCEED")
            self.assertLessEqual(count_prompt_words(prompt), 190)
            self.assertIn("red dial", prompt)
            self.assertIn("walnut base", prompt)

    def test_irreducible_prompt_overflow_is_non_proceed_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            literal = " ".join(f"word{index}" for index in range(205))
            task = (
                "Create a 4:5 exact product poster using the reference image. "
                f'Headline: "{literal}".'
            )
            reference = Path(tmp) / "product.png"
            reference.write_bytes(b"\x89PNG\r\n\x1a\nextra")
            run_dir, result = self.invoke_create(
                Path(tmp) / "runs", task=task, reference=str(reference), check=False
            )
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 1)
            self.assertEqual(metadata["feasibility_status"], "NEEDS_USER_INPUT")
            self.assertNotIn("Image task status: PROCEED", result.stdout)

    def test_schema_and_metadata_path_tampering_fail(self) -> None:
        mutations = [
            ("brief.json", lambda payload: payload.__setitem__("subject", 7)),
            ("visual_plan.json", lambda payload: payload.__setitem__("concept", ["wrong"])),
            ("metadata.json", lambda payload: payload.__setitem__("run_path", "/tmp")),
            ("metadata.json", lambda payload: payload.__setitem__("draft_prompt_path", "/etc/hosts")),
        ]
        for filename, mutate in mutations:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                run_dir = self.create_run(Path(tmp))
                path = run_dir / filename
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                self.assertTrue(validate_run_directory(run_dir))

    def test_cross_artifact_reference_and_prompt_tampering_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.create_run(Path(tmp))
            metadata_path = run_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["references"] = ["https://example.com/other.png"]
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            (run_dir / "prompt_core.txt").write_text("tampered\n", encoding="utf-8")

            errors = validate_run_directory(run_dir)
            self.assertTrue(any("references do not match" in error for error in errors))
            self.assertTrue(any("prompt_core.txt does not match" in error for error in errors))

    def test_synchronized_request_metadata_and_prompt_tampering_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.create_run(Path(tmp))
            request_path = run_dir / "request.json"
            metadata_path = run_dir / "metadata.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            request["task"] = "Create a different 1:1 portrait with soft window light."
            metadata["task_id"] = "create-a-different-1-1-portrait"
            metadata["director_id"] = "cinematic_portrait"
            request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            for filename in ("prompt.codex.txt", "codex.draft.txt"):
                path = run_dir / filename
                lines = path.read_text(encoding="utf-8").splitlines()
                path.write_text("\n".join(["tampered"] * 4 + lines[4:]) + "\n", encoding="utf-8")

            errors = validate_run_directory(run_dir)
            self.assertTrue(any("brief.json does not match" in error for error in errors))
            self.assertTrue(any("prompt recompiled" in error for error in errors))
            self.assertTrue(any("director_id does not match" in error for error in errors))

    def test_synchronized_chatgpt_prompt_tampering_fails_recompile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.create_run(Path(tmp))
            for filename in ("prompt.chatgpt.txt", "chatgpt.final.txt"):
                (run_dir / filename).write_text("synchronized tamper\n", encoding="utf-8")
            self.assertTrue(any("prompt.chatgpt.txt does not match prompt recompiled" in error for error in validate_run_directory(run_dir)))

    def test_version_input_hash_and_artifact_receipt_tampering_fail(self) -> None:
        mutations = [
            ("runtime_version", "0.0.0", "runtime_version"),
            ("schema_version", "0.0.0", "schema_version"),
            ("input_sha256", "0" * 64, "input_sha256"),
        ]
        for key, value, expected_error in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                run_dir = self.create_run(Path(tmp))
                metadata_path = run_dir / "metadata.json"
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata[key] = value
                metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
                self.assertTrue(any(expected_error in error for error in validate_run_directory(run_dir)))

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.create_run(Path(tmp))
            (run_dir / "prompt_core.txt").write_text("content changed after receipt\n", encoding="utf-8")
            self.assertTrue(any("artifact hashes" in error for error in validate_run_directory(run_dir)))

    def test_excessive_constraints_return_non_proceed_and_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            constraints = "; ".join(f"constraint {index} must remain exactly as specified" for index in range(30))
            task = f"Create a 16:9 poster.\nConstraints: {constraints}."
            run_dir, result = self.invoke_create(Path(tmp), task=task, check=False)

            self.assertEqual(result.returncode, 1)
            self.assertIn("lexical-unit budget", result.stderr)
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["feasibility_status"], "NEEDS_USER_INPUT")
            self.assertTrue(any("lexical-unit budget" in error for error in validate_run_directory(run_dir)))


if __name__ == "__main__":
    unittest.main()
