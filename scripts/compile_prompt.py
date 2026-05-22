#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from imageops_core import build_brief, read_task, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a raw image request into a structured brief JSON.")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--status", default="PROCEED_WITH_ASSUMPTIONS")
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args()

    task = read_task(args.task, args.task_file)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Missing task.", file=sys.stderr)
        return 2

    brief = build_brief(task, args.status, args.reference)
    if args.output:
        write_json(Path(args.output), brief)
    else:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

