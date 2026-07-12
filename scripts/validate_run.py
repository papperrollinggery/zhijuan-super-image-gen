#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from imageops_core import (
    CODEX_PROMPT_MAX_WORDS,
    RUNTIME_VERSION,
    SCHEMA_VERSION,
    analyze_feasibility,
    artifact_hashes,
    build_brief,
    canonical_input_sha256,
    classify_references,
    count_prompt_words,
    feasibility_markdown,
    make_chatgpt_prompt,
    make_codex_prompt,
    make_identity_lock,
    slugify,
)


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "boolean": bool,
}


def validate_value(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected in TYPE_MAP and (not isinstance(value, TYPE_MAP[expected]) or expected == "integer" and isinstance(value, bool)):
        return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                errors.extend(validate_value(child, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected key {key!r}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(validate_value(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: expected value >= {schema['minimum']}")
    return errors


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_run_directory(run_dir: Path, schema_dir: Path | None = None) -> list[str]:
    schema_dir = schema_dir or Path(__file__).resolve().parents[1] / "schemas"
    errors: list[str] = []
    required_files = [
        "request.json", "feasibility.md", "brief.json", "task_card.json",
        "art_direction.json", "visual_plan.json", "negative.txt", "codex.draft.txt",
        "chatgpt.final.txt", "prompt.codex.txt", "prompt.chatgpt.txt",
        "prompt_core.txt", "recreation_prompt.txt", "human_checklist.md", "review.md",
        "metadata.json",
    ]
    for name in required_files:
        if not (run_dir / name).is_file():
            errors.append(f"missing artifact: {name}")
    if errors:
        return errors

    for artifact, schema_name in [
        ("brief.json", "brief.schema.json"),
        ("task_card.json", "task_card.schema.json"),
        ("art_direction.json", "art_direction.schema.json"),
        ("visual_plan.json", "visual_plan.schema.json"),
        ("metadata.json", "metadata.schema.json"),
    ]:
        errors.extend(validate_value(load_json(run_dir / artifact), load_json(schema_dir / schema_name), artifact))

    identity_path = run_dir / "identity_lock.json"
    if identity_path.exists():
        errors.extend(validate_value(load_json(identity_path), load_json(schema_dir / "identity_lock.schema.json"), "identity_lock.json"))

    feasibility_text = (run_dir / "feasibility.md").read_text(encoding="utf-8")
    metadata = load_json(run_dir / "metadata.json")
    brief = load_json(run_dir / "brief.json")
    request = load_json(run_dir / "request.json")
    card = load_json(run_dir / "task_card.json")
    art = load_json(run_dir / "art_direction.json")
    plan = load_json(run_dir / "visual_plan.json")
    status = metadata.get("feasibility_status")
    if metadata.get("runtime_version") != RUNTIME_VERSION:
        errors.append("metadata.json: runtime_version does not match runtime")
    if metadata.get("schema_version") != SCHEMA_VERSION:
        errors.append("metadata.json: schema_version does not match runtime")
    if metadata.get("input_sha256") != canonical_input_sha256(request):
        errors.append("metadata.json: input_sha256 does not match request.json")
    receipt = metadata.get("artifact_receipt") or {}
    if receipt.get("version") != 1 or receipt.get("algorithm") != "sha256":
        errors.append("metadata.json: unsupported artifact receipt version or algorithm")
    if receipt.get("hashes") != artifact_hashes(run_dir):
        errors.append("metadata.json: artifact hashes do not match run contents")
    if f"Status: {status}" not in feasibility_text:
        errors.append("metadata.json: feasibility_status does not match feasibility.md")
    if brief.get("status") != status:
        errors.append("brief.json: status does not match metadata.json")
    if metadata.get("identity_lock_used") != identity_path.exists():
        errors.append("metadata.json: identity_lock_used does not match identity_lock.json")

    task = request.get("task")
    if not isinstance(task, str) or not task.strip():
        errors.append("request.json: task must be a non-empty string")
        expected_feasibility = None
        expected_brief = None
    else:
        expected_task_id = slugify(task, limit=36)
        if brief.get("task_id") != expected_task_id:
            errors.append("brief.json: task_id does not match request.task")
        if metadata.get("task_id") != expected_task_id:
            errors.append("metadata.json: task_id does not match request.task")
        submitted_references = (
            list(request.get("references") or [])
            + list(request.get("reference_urls") or [])
            + list(request.get("invalid_references") or [])
        )
        expected_feasibility = analyze_feasibility(
            task,
            submitted_references,
            blocked=request.get("blocked") is True,
        )
        if expected_feasibility.get("status") != status:
            errors.append("metadata.json: feasibility_status does not match recomputed request semantics")
        if feasibility_text != feasibility_markdown(expected_feasibility):
            errors.append("feasibility.md does not match recomputed request semantics")
        expected_brief = build_brief(task, expected_feasibility["status"], request.get("references") or [])
        if brief != expected_brief:
            errors.append("brief.json does not match the brief recomputed from request.json")

    for embedded_key, standalone, schema_name in [
        ("task_card", card, "task_card.schema.json"),
        ("art_direction", art, "art_direction.schema.json"),
        ("visual_plan", plan, "visual_plan.schema.json"),
    ]:
        embedded = brief.get(embedded_key)
        errors.extend(validate_value(embedded, load_json(schema_dir / schema_name), f"brief.json.{embedded_key}"))
        if embedded != standalone:
            errors.append(f"brief.json: {embedded_key} does not match {embedded_key}.json")

    selected_id = plan.get("selected_concept_id")
    selected = [item for item in plan.get("concept_candidates", []) if item.get("selected")]
    if len(selected) != 1 or selected[0].get("concept_id") != selected_id:
        errors.append("visual_plan.json: selected concept relationship is invalid")
    if metadata.get("selected_concept_id") != selected_id:
        errors.append("metadata.json: selected_concept_id does not match visual_plan.json")
    if metadata.get("concept_candidate_count") != len(plan.get("concept_candidates", [])):
        errors.append("metadata.json: concept_candidate_count does not match visual_plan.json")

    skill_root = schema_dir.parent.resolve()
    expected_paths = {
        "run_path": run_dir,
        "draft_prompt_path": run_dir / "codex.draft.txt",
        "final_prompt_path": run_dir / "chatgpt.final.txt",
        "negative_prompt_path": run_dir / "negative.txt",
    }
    if metadata.get("human_checklist_path") is not None:
        expected_paths["human_checklist_path"] = run_dir / "human_checklist.md"
    for key, expected_path in expected_paths.items():
        value = metadata.get(key)
        target = Path(value).expanduser() if isinstance(value, str) else Path("__invalid__")
        if not target.is_absolute():
            target = skill_root / target
        if target.resolve() != expected_path.resolve():
            errors.append(f"metadata.json: {key} must point to this run's {expected_path.name}")
        elif not target.exists():
            errors.append(f"metadata.json: {key} does not resolve to an existing path")

    reference_sets = {
        "request.json": request.get("references"),
        "brief.json": brief.get("references"),
        "task_card.json": card.get("references"),
        "metadata.json": metadata.get("references"),
    }
    canonical_references = request.get("references")
    for artifact, references in reference_sets.items():
        if references != canonical_references:
            errors.append(f"{artifact}: references do not match request.json")
    submitted_references = (
        list(canonical_references if isinstance(canonical_references, list) else [])
        + list(request.get("reference_urls") or [])
    )
    reference_info = classify_references(submitted_references)
    if reference_info["valid"] != canonical_references or reference_info["invalid"]:
        errors.append("request.json: references contain a missing, unreadable, or unsupported local reference")
    for artifact, payload in (("request.json", request), ("metadata.json", metadata)):
        if payload.get("local_references") != reference_info["local_files"]:
            errors.append(f"{artifact}: local_references do not match classified references")
        if payload.get("reference_urls") != reference_info["urls"]:
            errors.append(f"{artifact}: reference_urls do not match classified references")
    if metadata.get("invalid_references") != request.get("invalid_references"):
        errors.append("metadata.json: invalid_references do not match request.json")
    if identity_path.exists() and load_json(identity_path).get("references") != canonical_references:
        errors.append("identity_lock.json: references do not match request.json")
    if isinstance(task, str) and task.strip():
        expected_lock = make_identity_lock(task, canonical_references if isinstance(canonical_references, list) else [])
        actual_lock = load_json(identity_path) if identity_path.exists() else None
        if actual_lock != expected_lock:
            errors.append("identity_lock.json does not match recomputed preservation semantics")

    expected_metadata = {
        "task_id": brief.get("task_id"),
        "source_context": request.get("source_context"),
        "feasibility_status": brief.get("status"),
        "references": request.get("references"),
        "local_references": request.get("local_references"),
        "reference_urls": request.get("reference_urls"),
        "invalid_references": request.get("invalid_references"),
        "identity_lock_used": identity_path.exists(),
        "director_id": art.get("director_id"),
        "visual_thesis": art.get("visual_thesis"),
        "direction_family": plan.get("direction_family"),
        "aspect_ratio": card.get("aspect_ratio"),
        "text_mode": card.get("text_mode"),
        "focal_hierarchy": art.get("focal_hierarchy"),
        "visual_type": plan.get("visual_type"),
        "selected_concept_id": plan.get("selected_concept_id"),
        "concept_candidate_count": len(plan.get("concept_candidates", [])),
        "style_tags": plan.get("style_tags"),
        "quality_target": plan.get("quality_target"),
        "risk_flags": (brief.get("craft_expansion") or {}).get("risk_flags"),
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            errors.append(f"metadata.json: {key} does not match run artifacts")

    prompt = (run_dir / "prompt.codex.txt").read_text(encoding="utf-8").strip()
    prompt_lines = [line for line in prompt.splitlines() if line.strip()]
    if not 5 <= len(prompt_lines) <= 7:
        errors.append(f"prompt.codex.txt: expected 5-7 non-empty lines, got {len(prompt_lines)}")
    for required_label in ("Text:", "Constraints:"):
        if not any(line.startswith(required_label) for line in prompt_lines):
            errors.append(f"prompt.codex.txt: missing {required_label} line")
    if prompt != (run_dir / "codex.draft.txt").read_text(encoding="utf-8").strip():
        errors.append("codex.draft.txt does not match prompt.codex.txt")
    chatgpt_prompt = (run_dir / "prompt.chatgpt.txt").read_text(encoding="utf-8").strip()
    if chatgpt_prompt != (run_dir / "chatgpt.final.txt").read_text(encoding="utf-8").strip():
        errors.append("chatgpt.final.txt does not match prompt.chatgpt.txt")
    if prompt != make_codex_prompt(brief).strip():
        errors.append("prompt.codex.txt does not match prompt recompiled from brief.json")
    if chatgpt_prompt != make_chatgpt_prompt(brief).strip():
        errors.append("prompt.chatgpt.txt does not match prompt recompiled from brief.json")
    prompt_lexical_units = count_prompt_words(prompt)
    if prompt_lexical_units > CODEX_PROMPT_MAX_WORDS:
        errors.append(
            f"prompt.codex.txt: {prompt_lexical_units} lexical units exceeds the {CODEX_PROMPT_MAX_WORDS} lexical-unit budget; prioritize explicit constraints before rendering"
        )
    prompt_layers = plan.get("prompt_layers") or {}
    for artifact, key in (("prompt_core.txt", "prompt_core"), ("recreation_prompt.txt", "recreation_prompt")):
        if (run_dir / artifact).read_text(encoding="utf-8").strip() != str(prompt_layers.get(key, "")).strip():
            errors.append(f"{artifact} does not match visual_plan.json prompt_layers.{key}")
    negative_lines = [line for line in (run_dir / "negative.txt").read_text(encoding="utf-8").splitlines() if line]
    if negative_lines != plan.get("hard_constraints") or negative_lines != brief.get("negative"):
        errors.append("negative.txt, brief.json, and visual_plan.json constraints do not match")
    for literal in card.get("literal_text", []):
        if literal not in prompt:
            errors.append(f"prompt.codex.txt: literal copy was dropped: {literal}")
    for constraint in card.get("hard_constraints", []):
        if constraint not in prompt:
            errors.append(f"prompt.codex.txt: hard constraint was dropped: {constraint}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a persisted imageops run and its schema relationships.")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    errors = validate_run_directory(Path(args.run_dir))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID: {args.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
