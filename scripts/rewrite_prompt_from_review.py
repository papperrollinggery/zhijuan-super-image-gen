#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from imageops_core import CODEX_PROMPT_MAX_WORDS, artifact_hashes, classify_references, count_prompt_words


ISSUE_REWRITES: dict[str, str] = {
    "wrong_visual_family": "Revision focus: change the visual family to match the requested use case; keep the subject, constraints, and factual boundaries unchanged.",
    "text_unreadable": "Revision focus: reduce visible text to fewer, larger labels with generous spacing; avoid tiny paragraphs or dense UI copy.",
    "too_generic": "Revision focus: make the chosen concept more specific through visible action, concrete spatial layers, and tactile details implied by the request.",
    "overconstrained": "Revision focus: remove nonessential style pressure and keep only the constraints that protect facts, identity, text, or brand boundaries.",
    "weak_composition": "Revision focus: strengthen first-read hierarchy, crop discipline, negative space, and foreground-to-background separation.",
    "weak_materials": "Revision focus: make surface behavior visible through contact shadows, reflection roughness, texture, edge lighting, and scale cues.",
    "reference_drift": "Revision focus: anchor the image more tightly to provided references for identity, proportions, palette, composition, and forbidden drift.",
    "fake_claims": "Revision focus: remove any invented metrics, ratings, prices, awards, badges, certifications, publication names, or official marks.",
}

COMPACT_ISSUE_REWRITES: dict[str, str] = {
    "wrong_visual_family": "Revision: match the requested visual family; preserve subject, facts, and constraints.",
    "text_unreadable": "Revision: use fewer, larger, legible labels with generous spacing.",
    "too_generic": "Revision: add request-grounded action, spatial layers, and tactile detail.",
    "overconstrained": "Revision: remove nonessential style pressure; preserve factual, identity, text, and brand constraints.",
    "weak_composition": "Revision: strengthen hierarchy, crop, negative space, and depth separation.",
    "weak_materials": "Revision: clarify surfaces with shadows, roughness, texture, edge light, and scale cues.",
    "reference_drift": "Revision: match reference identity, proportions, palette, composition, and forbidden drift.",
    "fake_claims": "Revision: remove invented claims, metrics, prices, awards, badges, names, and marks.",
}


ASPECT_RATIO_PATTERN = re.compile(r"\b(?:1:1|4:5|9:16|16:9)\b")
DELIVERABLE_PATTERN = re.compile(
    r"(?i)^create\s+(?:a|an)\s+(.+?\b(?:image|poster|portrait|illustration|mockup|cover|infographic|storyboard|render|photo)\b)"
)


def compact_create_line(line: str) -> str:
    deliverable = DELIVERABLE_PATTERN.match(line)
    if deliverable:
        return f"Create a {deliverable.group(1).strip()}."
    ratio = ASPECT_RATIO_PATTERN.search(line)
    return f"Create a {ratio.group(0)} requested image." if ratio else "Create the requested image."


def compact_compose_line(line: str) -> str:
    ratio = ASPECT_RATIO_PATTERN.search(line)
    return f"Compose clearly for the {ratio.group(0)} crop." if ratio else "Compose with a clear focal path."


def normalize_issue_tags(issue_tags: list[str]) -> list[str]:
    clean_tags = []
    for tag in issue_tags:
        if tag not in ISSUE_REWRITES:
            raise ValueError(f"Unknown issue tag: {tag}")
        if tag not in clean_tags:
            clean_tags.append(tag)
    return clean_tags[:2]


def rewrite_prompt(prompt: str, issue_tags: list[str]) -> str:
    selected = normalize_issue_tags(issue_tags)
    additions = [ISSUE_REWRITES[tag] for tag in selected]
    lines = [line.rstrip() for line in prompt.strip().splitlines() if line.strip()]
    constraint_index = next((index for index, line in enumerate(lines) if line.startswith("Constraints:")), None)
    revision_text = " ".join(additions)
    if constraint_index is None:
        lines.append(f"Constraints: {revision_text}")
    else:
        lines[constraint_index] = f"{lines[constraint_index]} {revision_text}"
    rendered = "\n".join(lines) + "\n"
    if count_prompt_words(rendered) <= CODEX_PROMPT_MAX_WORDS:
        return rendered

    for index, line in enumerate(lines):
        lower = line.lower()
        if line.startswith(("Show ", "Text:", "Constraints:", "Preserve:", "Must show:")) or "visible details:" in lower:
            continue
        if lower.startswith("create "):
            lines[index] = compact_create_line(line)
        elif lower.startswith("compose "):
            lines[index] = compact_compose_line(line)
        elif lower.startswith("use "):
            lines[index] = "Use coherent light and tactile materials."
        else:
            lines[index] = "Keep the requested visual intent."
    rendered = "\n".join(lines) + "\n"
    if count_prompt_words(rendered) <= CODEX_PROMPT_MAX_WORDS:
        return rendered

    compact_revision = " ".join(COMPACT_ISSUE_REWRITES[tag] for tag in selected)
    if constraint_index is None:
        lines[-1] = f"Constraints: {compact_revision}"
    else:
        original_constraint = [line.rstrip() for line in prompt.strip().splitlines() if line.strip()][constraint_index]
        lines[constraint_index] = f"{original_constraint} {compact_revision}"
    return "\n".join(lines) + "\n"


def rewrite_run(run_dir: Path, issue_tags: list[str]) -> Path:
    prompt_path = run_dir / "prompt.codex.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Missing {prompt_path}")
    metadata_path = run_dir / "metadata.json"
    brief_path = run_dir / "brief.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.is_file() else {}
    status = metadata.get("feasibility_status") or brief.get("status")
    if status not in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"}:
        raise ValueError("follow-up requires PROCEED or PROCEED_WITH_ASSUMPTIONS status")
    selected_tags = normalize_issue_tags(issue_tags)
    if "reference_drift" in selected_tags:
        request_path = run_dir / "request.json"
        identity_path = run_dir / "identity_lock.json"
        request = json.loads(request_path.read_text(encoding="utf-8")) if request_path.is_file() else {}
        references = request.get("references") if isinstance(request.get("references"), list) else []
        reference_info = classify_references(references)
        identity_lock = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.is_file() else {}
        eligible = (
            bool(references)
            and reference_info["valid"] == references
            and not reference_info["invalid"]
            and identity_lock.get("source_of_truth") == "provided_references"
            and identity_lock.get("references") == references
        )
        if not eligible:
            raise ValueError("reference_drift requires valid references and an identity_lock sourced from provided_references")
    prompt = prompt_path.read_text(encoding="utf-8")
    followup = rewrite_prompt(prompt, selected_tags)
    followup_lines = [line for line in followup.splitlines() if line.strip()]
    if not 5 <= len(followup_lines) <= 7:
        raise ValueError(f"follow-up prompt must contain 5-7 non-empty lines, got {len(followup_lines)}")
    followup_units = count_prompt_words(followup)
    if followup_units > CODEX_PROMPT_MAX_WORDS:
        raise ValueError(
            f"follow-up prompt uses {followup_units} lexical units; limit is {CODEX_PROMPT_MAX_WORDS}"
        )
    drafts_dir = run_dir / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    followup_path = drafts_dir / "followup.codex.txt"
    followup_path.write_text(followup, encoding="utf-8")
    (drafts_dir / "followup.json").write_text(
        json.dumps(
            {
                "source_prompt": "prompt.codex.txt",
                "output_prompt": "drafts/followup.codex.txt",
                "issue_tags": selected_tags,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    review_path = run_dir / "review.md"
    tag_text = ", ".join(selected_tags)
    note = f"\n## Follow-up Rewrite\n\nIssue tags: {tag_text}\nOutput: drafts/followup.codex.txt\n"
    if review_path.exists():
        review_path.write_text(review_path.read_text(encoding="utf-8") + note, encoding="utf-8")
    else:
        review_path.write_text("# Human Review\n" + note, encoding="utf-8")
    if metadata_path.is_file():
        receipt = metadata.setdefault("artifact_receipt", {})
        receipt["version"] = 1
        receipt["algorithm"] = "sha256"
        receipt["hashes"] = artifact_hashes(run_dir)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return followup_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a follow-up Codex prompt from human review issue tags.")
    parser.add_argument("run_dir", help="Path to an imageops run directory containing prompt.codex.txt.")
    parser.add_argument("--tag", action="append", required=True, choices=sorted(ISSUE_REWRITES), help="Issue tag. Repeatable; the first two tags drive the rewrite.")
    args = parser.parse_args()
    followup_path = rewrite_run(Path(args.run_dir), args.tag)
    print(followup_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
