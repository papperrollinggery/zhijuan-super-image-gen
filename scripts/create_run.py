#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from imageops_core import (
    analyze_feasibility,
    build_brief,
    feasibility_markdown,
    make_chatgpt_prompt,
    make_codex_prompt,
    make_identity_lock,
    read_task,
    relative_to_root,
    skill_root,
    slugify,
    timestamp,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an isolated image-generation planning run.")
    parser.add_argument("--task", help="Raw delegated image task.")
    parser.add_argument("--task-file", help="File containing the delegated image task.")
    parser.add_argument("--slug", help="Run slug.")
    parser.add_argument("--reference", action="append", default=[], help="Reference file path or URL. Repeatable.")
    parser.add_argument("--source-context", default="delegated visual task", help="Short source context label.")
    args = parser.parse_args()

    task = read_task(args.task, args.task_file)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Missing task. Provide --task, --task-file, or stdin.", file=sys.stderr)
        return 2

    root = skill_root()
    run_slug = slugify(args.slug or task)
    run_dir = root / "imageops" / "runs" / f"{timestamp()}-{run_slug}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "drafts").mkdir()

    feasibility = analyze_feasibility(task, args.reference)
    brief = build_brief(task, feasibility["status"], args.reference)
    codex_prompt = make_codex_prompt(brief)
    chatgpt_prompt = make_chatgpt_prompt(brief)
    prompt_layers = (brief.get("visual_plan") or {}).get("prompt_layers") or {}
    identity_lock = make_identity_lock(task, args.reference)

    write_json(run_dir / "request.json", {"task": task, "references": args.reference, "source_context": args.source_context})
    (run_dir / "feasibility.md").write_text(feasibility_markdown(feasibility), encoding="utf-8")
    write_json(run_dir / "brief.json", brief)
    write_json(run_dir / "task_card.json", brief.get("task_card", {}))
    write_json(run_dir / "art_direction.json", brief.get("art_direction", {}))
    write_json(run_dir / "visual_plan.json", brief.get("visual_plan", {}))
    (run_dir / "negative.txt").write_text("\n".join(brief["negative"]) + "\n", encoding="utf-8")
    (run_dir / "codex.draft.txt").write_text(codex_prompt + "\n", encoding="utf-8")
    (run_dir / "chatgpt.final.txt").write_text(chatgpt_prompt + "\n", encoding="utf-8")
    (run_dir / "prompt.codex.txt").write_text(codex_prompt + "\n", encoding="utf-8")
    (run_dir / "prompt.chatgpt.txt").write_text(chatgpt_prompt + "\n", encoding="utf-8")
    if prompt_layers.get("prompt_core"):
        (run_dir / "prompt_core.txt").write_text(prompt_layers["prompt_core"] + "\n", encoding="utf-8")
    if prompt_layers.get("recreation_prompt"):
        (run_dir / "recreation_prompt.txt").write_text(prompt_layers["recreation_prompt"] + "\n", encoding="utf-8")
    checklist = (brief.get("visual_plan") or {}).get("human_checklist") or brief.get("craft_expansion", {}).get("human_checklist", [])
    if checklist:
        (run_dir / "human_checklist.md").write_text(
            "# Human Check\n\n" + "\n".join(f"- {item}" for item in checklist) + "\n",
            encoding="utf-8",
        )
        (run_dir / "review.md").write_text(
            "# Human Review\n\n" + "\n".join(f"- [ ] {item}" for item in checklist) + "\n",
            encoding="utf-8",
        )
    if identity_lock:
        write_json(run_dir / "identity_lock.json", identity_lock)

    metadata = {
        "task_id": brief["task_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_context": args.source_context,
        "feasibility_status": feasibility["status"],
        "run_path": relative_to_root(run_dir, root),
        "draft_prompt_path": relative_to_root(run_dir / "codex.draft.txt", root),
        "final_prompt_path": relative_to_root(run_dir / "chatgpt.final.txt", root),
        "negative_prompt_path": relative_to_root(run_dir / "negative.txt", root),
        "human_checklist_path": relative_to_root(run_dir / "human_checklist.md", root) if checklist else None,
        "references": args.reference,
        "identity_lock_used": bool(identity_lock),
        "director_id": (brief.get("art_direction") or {}).get("director_id"),
        "visual_thesis": (brief.get("art_direction") or {}).get("visual_thesis"),
        "direction_family": (brief.get("visual_plan") or {}).get("direction_family"),
        "aspect_ratio": (brief.get("task_card") or {}).get("aspect_ratio"),
        "text_mode": (brief.get("task_card") or {}).get("text_mode"),
        "focal_hierarchy": (brief.get("art_direction") or {}).get("focal_hierarchy", []),
        "visual_type": (brief.get("visual_plan") or {}).get("visual_type"),
        "style_tags": (brief.get("visual_plan") or {}).get("style_tags", []),
        "quality_target": (brief.get("visual_plan") or {}).get("quality_target"),
        "risk_flags": brief.get("craft_expansion", {}).get("risk_flags", []),
        "recommended_draft_renderer": "Codex image_gen",
        "recommended_final_renderer": "Optional ChatGPT Images handoff",
    }
    write_json(run_dir / "metadata.json", metadata)

    files = [
        "feasibility.md",
        "request.json",
        "brief.json",
        "task_card.json",
        "art_direction.json",
        "visual_plan.json",
        "negative.txt",
        "codex.draft.txt",
        "chatgpt.final.txt",
        "prompt.codex.txt",
        "prompt.chatgpt.txt",
        "prompt_core.txt",
        "recreation_prompt.txt",
        "human_checklist.md",
        "review.md",
        "metadata.json",
    ]
    if not checklist:
        files.remove("human_checklist.md")
        files.remove("review.md")
    if not prompt_layers.get("prompt_core"):
        files.remove("prompt_core.txt")
    if not prompt_layers.get("recreation_prompt"):
        files.remove("recreation_prompt.txt")
    if identity_lock:
        files.insert(-1, "identity_lock.json")

    print(f"Image task status: {feasibility['status']}\n")
    print("Files created:")
    for name in files:
        print(f"- {relative_to_root(run_dir / name, root)}")
    print("\nRecommendation:")
    if feasibility["status"] in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"}:
        print("Use prompt.codex.txt for a single Codex image_gen render. Export prompt.chatgpt.txt only when a ChatGPT handoff is explicitly needed.")
    else:
        print("Do not render yet. Resolve feasibility status first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
