#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from imageops_core import build_hard_constraints, read_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact hard constraints for image generation.")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--output")
    args = parser.parse_args()

    task = read_task(args.task, args.task_file)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Missing task.", file=sys.stderr)
        return 2

    text = "\n".join(build_hard_constraints(task)) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

