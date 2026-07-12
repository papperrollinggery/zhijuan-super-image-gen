#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from imageops_core import (
    CODEX_PROMPT_MAX_WORDS,
    analyze_feasibility,
    build_brief,
    count_prompt_words,
    make_codex_prompt,
    make_identity_lock,
)
from validate_run import load_json, validate_value


ALLOWED_STATUSES = {
    "PROCEED", "PROCEED_WITH_ASSUMPTIONS", "NEEDS_REFERENCES",
    "NEEDS_USER_INPUT", "NOT_USEFUL", "BLOCKED",
}


def evaluate_input(item: dict[str, Any], schema_dir: Path) -> dict[str, Any]:
    task = item["task"]
    references = item.get("references", [])
    feasibility = analyze_feasibility(task, references)
    brief = build_brief(task, feasibility["status"], references)
    prompt = make_codex_prompt(brief)
    plan = brief["visual_plan"]
    identity_lock = make_identity_lock(task, references)
    errors: list[str] = []

    for artifact, schema_name in [
        (brief["task_card"], "task_card.schema.json"),
        (brief["art_direction"], "art_direction.schema.json"),
        (plan, "visual_plan.schema.json"),
    ]:
        errors.extend(validate_value(artifact, load_json(schema_dir / schema_name)))
    if identity_lock:
        errors.extend(validate_value(identity_lock, load_json(schema_dir / "identity_lock.schema.json")))

    selected = [candidate for candidate in plan["concept_candidates"] if candidate.get("selected")]
    if len(selected) != 1 or selected[0]["concept_id"] != plan["selected_concept_id"]:
        errors.append("selected concept invariant failed")
    if feasibility["status"] not in ALLOWED_STATUSES:
        errors.append("unknown feasibility status")
    if feasibility["status"] not in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"} and feasibility["use_codex_image_gen_directly"]:
        errors.append("non-proceed status incorrectly allows generation")
    prompt_lexical_units = count_prompt_words(prompt)
    expected_budget_error = item.get("expect_constraint_budget_exceeded", False)
    if expected_budget_error:
        if feasibility["status"] != "NEEDS_USER_INPUT" or not feasibility.get("constraint_budget_exceeded"):
            errors.append("constraint budget overflow did not produce NEEDS_USER_INPUT")
        if prompt_lexical_units <= CODEX_PROMPT_MAX_WORDS:
            errors.append("constraint budget fixture did not exercise the persisted prompt rejection boundary")
    elif prompt_lexical_units > CODEX_PROMPT_MAX_WORDS:
        errors.append(f"Codex prompt exceeds {CODEX_PROMPT_MAX_WORDS} lexical units")
    if not (5 <= len(prompt.splitlines()) <= 7):
        errors.append("Codex prompt is not a 5-7 line director brief")
    for literal in brief["task_card"].get("literal_text", []):
        if literal not in prompt:
            errors.append(f"literal copy was dropped: {literal}")
    for constraint in plan.get("hard_constraints", []):
        if constraint not in prompt:
            errors.append(f"hard constraint was dropped: {constraint}")
    if item.get("expected_status") and feasibility["status"] != item["expected_status"]:
        errors.append(f"expected status {item['expected_status']}, got {feasibility['status']}")
    expected_literals = item.get("expected_literal_copy")
    if expected_literals is not None and brief["task_card"].get("literal_text") != expected_literals:
        errors.append("literal copy boundary mismatch")

    return {
        "id": item.get("id", "unnamed"),
        "status": feasibility["status"],
        "prompt_lexical_units": prompt_lexical_units,
        "selected_concept_id": plan["selected_concept_id"],
        "passed": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward-test planner invariants using answer-free task inputs.")
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    items = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    results = [evaluate_input(item, root / "schemas") for item in items]
    for result in results:
        label = "PASS" if result["passed"] else "FAIL"
        print(
            f"{label} {result['id']}: status={result['status']} "
            f"units={result['prompt_lexical_units']} concept={result['selected_concept_id']}"
        )
        for error in result["errors"]:
            print(f"  {error}")
    print(f"SUMMARY: {sum(result['passed'] for result in results)}/{len(results)} passed")
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
