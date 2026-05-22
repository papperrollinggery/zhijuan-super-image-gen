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
    identity_lock = make_identity_lock(task, args.reference)

    (run_dir / "feasibility.md").write_text(feasibility_markdown(feasibility), encoding="utf-8")
    write_json(run_dir / "brief.json", brief)
    (run_dir / "negative.txt").write_text("\n".join(brief["negative"]) + "\n", encoding="utf-8")
    (run_dir / "codex.draft.txt").write_text(codex_prompt + "\n", encoding="utf-8")
    (run_dir / "chatgpt.final.txt").write_text(chatgpt_prompt + "\n", encoding="utf-8")
    checklist = brief.get("craft_expansion", {}).get("human_checklist", [])
    if checklist:
        (run_dir / "human_checklist.md").write_text(
            "# Human Check\n\n" + "\n".join(f"- {item}" for item in checklist) + "\n",
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
        "taste_preset": brief.get("craft_expansion", {}).get("taste_preset"),
        "aspect_ratio": brief.get("craft_expansion", {}).get("aspect_ratio"),
        "risk_flags": brief.get("craft_expansion", {}).get("risk_flags", []),
        "recommended_draft_renderer": "Codex image_gen",
        "recommended_final_renderer": "ChatGPT Images 2.0",
    }
    write_json(run_dir / "metadata.json", metadata)

    files = [
        "feasibility.md",
        "brief.json",
        "negative.txt",
        "codex.draft.txt",
        "chatgpt.final.txt",
        "human_checklist.md",
        "metadata.json",
    ]
    if not checklist:
        files.remove("human_checklist.md")
    if identity_lock:
        files.insert(-1, "identity_lock.json")

    print(f"Image task status: {feasibility['status']}\n")
    print("Files created:")
    for name in files:
        print(f"- {relative_to_root(run_dir / name, root)}")
    print("\nRecommendation:")
    if feasibility["status"] in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"}:
        print("Use Codex image_gen for drafts. Use ChatGPT Images 2.0 for final render if high fidelity is required.")
    else:
        print("Do not render yet. Resolve feasibility status first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
