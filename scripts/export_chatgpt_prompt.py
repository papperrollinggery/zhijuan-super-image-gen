#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from imageops_core import make_chatgpt_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a ChatGPT Images final handoff prompt from brief.json.")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--negative", help="Optional negative.txt override.")
    parser.add_argument("--output")
    args = parser.parse_args()

    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    if args.negative:
        brief["negative"] = [line.strip() for line in Path(args.negative).read_text(encoding="utf-8").splitlines() if line.strip()]
    prompt = make_chatgpt_prompt(brief)
    if args.output:
        Path(args.output).write_text(prompt + "\n", encoding="utf-8")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

