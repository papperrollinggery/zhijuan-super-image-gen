# V2 Goal Runbook

Use this runbook to verify the V2 visual director workflow.

## Objective

Upgrade `zhijuan-super-image-gen` so the default Codex `image_gen` path has a tested V2 visual director workflow that improves task classification, reduces false reference blocking, renders shorter natural-language prompts, supports issue-tag follow-up prompts, and proves behavior with representative sample runs.

## Non-Negotiables

- Keep Codex `image_gen` as the default renderer.
- Do not promise ChatGPT-equivalent rendering.
- Do not add paid API dependencies.
- Do not default to multi-image generation.
- Preserve the existing run artifacts: `task_card.json`, `art_direction.json`, `visual_plan.json`, `brief.json`, `prompt.codex.txt`, `prompt.chatgpt.txt`, `prompt_core.txt`, `recreation_prompt.txt`, `negative.txt`, `review.md`, and `metadata.json`.

## What V2 Adds

- `infographic` is a first-class use case.
- Exact preservation is separated from ordinary brand/product mentions.
- `visual_plan.json` includes `concept_candidates` and `selected_concept_id`.
- `prompt.codex.txt` uses the short V2 director brief.
- Human review can produce a targeted follow-up with `scripts/rewrite_prompt_from_review.py`.
- `scripts/eval_planner.py` checks representative planner behavior.

## Commands

```bash
cd /path/to/zhijuan-super-image-gen
python3 -m py_compile scripts/*.py
python3 scripts/validate_skill_package.py
python3 -m unittest discover -s tests
python3 scripts/eval_planner.py --fixtures tests/fixtures/image_tasks.json
python3 scripts/forward_test.py --inputs tests/fixtures/forward_image_tasks.json
git diff --check
```

Or run the combined gate:

```bash
bash scripts/release_check.sh
```

## Follow-Up Rewrite

```bash
python3 scripts/rewrite_prompt_from_review.py imageops/runs/<run-dir> --tag too_generic --tag weak_composition
```

Supported tags:

- `wrong_visual_family`
- `text_unreadable`
- `too_generic`
- `overconstrained`
- `weak_composition`
- `weak_materials`
- `reference_drift`
- `fake_claims`

## Expected Regression Fixes

- Chinese infographic requests no longer become `NEEDS_REFERENCES`.
- Chinese portrait requests no longer become `NOT_USEFUL`.
- No-logo explanatory brand mentions do not create `identity_lock.json`.
- Exact identity or exact product preservation without references still returns `NEEDS_REFERENCES`.
- Default prompts are short natural-language director briefs, not schema dumps.
- Literal copy and labeled constraints survive prompt compilation.
- Identity locks use person, product, UI, brand, or visual-style anchors instead of one face-centric template.
- A temporary persisted run passes schema, metadata, prompt-shape, and artifact validation.
