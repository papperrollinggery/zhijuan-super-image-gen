#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from imageops_core import analyze_feasibility, feasibility_markdown, read_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Score image-generation feasibility.")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    task = read_task(args.task, args.task_file)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Missing task.", file=sys.stderr)
        return 2

    result = analyze_feasibility(task, args.reference)
    if args.markdown:
        print(feasibility_markdown(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

