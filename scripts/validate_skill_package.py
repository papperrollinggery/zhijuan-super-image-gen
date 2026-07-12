#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", skill_text, flags=re.S)
    if not match:
        errors.append("SKILL.md: missing YAML frontmatter")
    else:
        keys = [line.split(":", 1)[0].strip() for line in match.group(1).splitlines() if ":" in line]
        if keys != ["name", "description"]:
            errors.append(f"SKILL.md: frontmatter keys must be name, description; got {keys}")
        name_match = re.search(r"^name:\s*(.+)$", match.group(1), flags=re.M)
        if not name_match or name_match.group(1).strip() != root.name:
            errors.append("SKILL.md: skill name must match folder name")

    for linked_path in sorted(set(re.findall(r"`((?:scripts|schemas|references|subagents)/[^`\s{}]+)`", skill_text))):
        if not (root / linked_path).exists():
            errors.append(f"SKILL.md: missing linked resource {linked_path}")

    agent_text = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if f"${root.name}" not in agent_text:
        errors.append("agents/openai.yaml: default_prompt does not invoke this skill")
    for field in ("display_name", "short_description", "default_prompt"):
        if not re.search(rf"^\s*{field}:\s*.+$", agent_text, flags=re.M):
            errors.append(f"agents/openai.yaml: missing {field}")

    for schema_path in sorted((root / "schemas").glob("*.json")):
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{schema_path.name}: invalid JSON schema: {error}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("VALID: skill package metadata, resource links, and schema JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
