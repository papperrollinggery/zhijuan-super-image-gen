#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from imageops_core import compress_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Compress an image prompt for Codex image_gen.")
    parser.add_argument("--input", help="Prompt text file. Defaults to stdin.")
    parser.add_argument("--max-words", type=int, default=300)
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    print(compress_prompt(text, max_words=args.max_words))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

