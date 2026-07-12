#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from imageops_core import CODEX_PROMPT_MAX_WORDS, analyze_feasibility, build_brief, count_prompt_words, make_codex_prompt, make_identity_lock


def evaluate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    task = fixture["task"]
    references = fixture.get("references", [])
    feasibility = analyze_feasibility(task, references)
    brief = build_brief(task, feasibility["status"], references)
    card = brief["task_card"]
    art = brief["art_direction"]
    plan = brief["visual_plan"]
    prompt = make_codex_prompt(brief)
    result = {
        "id": fixture["id"],
        "status": feasibility["status"],
        "use_case": card["use_case"],
        "director_id": art["director_id"],
        "prompt_lexical_units": count_prompt_words(prompt),
        "hard_constraints": plan.get("hard_constraints", []),
        "risk_flags": brief.get("craft_expansion", {}).get("risk_flags", []),
        "references_required": feasibility["references_required"],
        "identity_lock": bool(make_identity_lock(task, references)),
        "selected_concept_id": plan.get("selected_concept_id"),
        "concept_candidate_count": len(plan.get("concept_candidates", [])),
        "checks": {},
    }
    checks = {
        "status": result["status"] == fixture["expected_status"],
        "use_case": result["use_case"] == fixture["expected_use_case"],
        "director_id": result["director_id"] == fixture["expected_director"],
        "references_required": result["references_required"] == fixture["references_required"],
        "identity_lock": result["identity_lock"] == fixture["identity_lock"],
        "prompt_lexical_units": result["prompt_lexical_units"] <= min(fixture["max_prompt_lexical_units"], CODEX_PROMPT_MAX_WORDS),
        "concept_candidates": result["concept_candidate_count"] >= 1 and bool(result["selected_concept_id"]),
    }
    result["checks"] = checks
    result["passed"] = all(checks.values())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate planner behavior against image task fixtures.")
    parser.add_argument("--fixtures", required=True, help="Path to fixture JSON.")
    parser.add_argument("--json", action="store_true", help="Emit JSON results instead of a compact table.")
    args = parser.parse_args()

    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    results = [evaluate_fixture(fixture) for fixture in fixtures]
    if args.json:
        print(json.dumps({"results": results, "passed": all(item["passed"] for item in results)}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            status = "PASS" if item["passed"] else "FAIL"
            print(
                f"{status} {item['id']}: status={item['status']} use_case={item['use_case']} "
                f"director={item['director_id']} units={item['prompt_lexical_units']} "
                f"refs={item['references_required']} lock={item['identity_lock']} concept={item['selected_concept_id']}"
            )
            if not item["passed"]:
                failed = [name for name, passed in item["checks"].items() if not passed]
                print(f"  failed_checks={','.join(failed)}")
        print(f"SUMMARY: {sum(1 for item in results if item['passed'])}/{len(results)} passed")
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
