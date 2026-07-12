#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m py_compile scripts/*.py
python3 scripts/validate_skill_package.py
python3 -m unittest discover -s tests
python3 scripts/eval_planner.py --fixtures tests/fixtures/image_tasks.json
python3 scripts/forward_test.py --inputs tests/fixtures/forward_image_tasks.json

validate_create_stdout() {
  local expected_status="$1"
  local expected_recommendation="$2"
  local expected_files="$3"
  python3 -c '
import os, sys
status, recommendation, expected_csv = sys.argv[1:4]
lines = sys.stdin.read().splitlines()
if len(lines) < 7 or lines[0] != f"Image task status: {status}" or lines[1] != "" or lines[2] != "Files created:":
    raise SystemExit("invalid create_run status/header stdout")
try:
    marker = lines.index("Recommendation:")
except ValueError:
    raise SystemExit("missing Recommendation marker")
if marker < 4 or lines[marker - 1] != "" or lines[marker + 1:] != [recommendation]:
    raise SystemExit("invalid create_run recommendation or extra stdout")
file_lines = lines[3:marker - 1]
if any(not line.startswith("- ") for line in file_lines):
    raise SystemExit("invalid create_run file line")
actual = sorted(os.path.basename(line[2:]) for line in file_lines)
expected = sorted(expected_csv.split(","))
if actual != expected:
    raise SystemExit(f"incomplete create_run file set: {actual!r}")
' "$expected_status" "$expected_recommendation" "$expected_files"
}

tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
smoke_output="$(python3 scripts/create_run.py \
  --task $'Create a 16:9 product poster. Headline: QUIET SIGNAL.\nSubject: a matte radio on a walnut desk.\nConstraints: no price. Avoid: floating badges.' \
  --slug release-smoke \
  --output-root "$tmp_root")"
common_files='feasibility.md,request.json,brief.json,task_card.json,art_direction.json,visual_plan.json,negative.txt,codex.draft.txt,chatgpt.final.txt,prompt.codex.txt,prompt.chatgpt.txt,prompt_core.txt,recreation_prompt.txt,human_checklist.md,review.md,metadata.json'
validate_create_stdout \
  'PROCEED' \
  'Use prompt.codex.txt for a single Codex image_gen render. Export prompt.chatgpt.txt only when a ChatGPT handoff is explicitly needed.' \
  "$common_files" <<<"$smoke_output"
run_dir="$(find "$tmp_root" -mindepth 1 -maxdepth 1 -type d -print -quit)"
python3 scripts/validate_run.py "$run_dir"

non_proceed_output="$(python3 scripts/create_run.py \
  --task 'Create a portrait and keep her face, hairstyle, and proportions unchanged from the attachment.' \
  --slug release-needs-reference \
  --output-root "$tmp_root")"
validate_create_stdout \
  'NEEDS_REFERENCES' \
  'Do not render yet. Resolve feasibility status first.' \
  "$common_files,identity_lock.json" <<<"$non_proceed_output"

budget_task='Create a poster. Constraints:'
for index in $(seq 1 30); do
  budget_task+=" constraint ${index} must remain exactly as specified;"
done
if python3 scripts/create_run.py --task "$budget_task" --slug release-budget --output-root "$tmp_root" >"$tmp_root/budget.out" 2>"$tmp_root/budget.err"; then
  echo 'Expected prompt budget validation failure' >&2
  exit 1
fi
rg -Fq 'lexical-unit budget' "$tmp_root/budget.err"
git diff --check
