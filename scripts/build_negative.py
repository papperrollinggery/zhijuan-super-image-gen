#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from imageops_core import build_negative, read_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact negative constraints for image generation.")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--brief", help="Optional brief.json. Uses subject and scene.")
    parser.add_argument("--output")
    args = parser.parse_args()

    task = read_task(args.task, args.task_file)
    if args.brief:
        brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
        task = " ".join(str(brief.get(key, "")) for key in ("subject", "scene", "use_case", "style"))
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Missing task or brief.", file=sys.stderr)
        return 2

    negative = build_negative(task)
    text = "\n".join(negative) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

