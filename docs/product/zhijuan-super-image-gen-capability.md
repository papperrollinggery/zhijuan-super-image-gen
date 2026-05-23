# Zhijuan Super Image Gen Capability Contract

## CAPABILITY

`zhijuan-super-image-gen` gives Codex an image-director lane for visual generation requests: the main session stays a clean orchestrator, the skill converts a short user image request into durable planning artifacts, and the final Codex `image_gen` call receives one compact art-directed prompt instead of a long field checklist. The capability improves context hygiene, prompt structure, repeatability, and art-direction consistency; it does not change the underlying image model or guarantee ChatGPT-equivalent rendering.

## CONSTRAINTS

- Default render count is one. Multi-image variants are opt-in only.
- Automatic regeneration is off by default. Human issue tags should drive follow-up renders.
- `image_gen` must remain the native draft renderer. The skill must not replace it with an API fallback unless explicitly requested.
- ChatGPT Images handoff is optional and artifact-only; it is not the default final-render route.
- Director cards guide thesis, tone, hierarchy, light, material, and cheap/expensive cues. They must not force fixed objects, layout widgets, feature chips, trust strips, pedestals, or fake brand marks.
- Final Codex prompts must be short natural-language director briefs with only load-bearing `Text`, `Preserve`, and `Constraints` lines.
- Do not invent copy, metrics, prices, awards, ratings, user counts, publication names, or official logos unless literal copy or references are provided.
- Identity locks are only for recurring people, characters, mascots, products, UI systems, or brand styles.
- Reference handling is currently text-path aware only. True visual anchor extraction remains open.
- Real subagent execution is a context-isolation feature, not a direct image-quality feature.

## IMPLEMENTATION CONTRACT

### Actors

- Main Codex session: detects image work, delegates visual planning, optionally calls `image_gen`, and returns only status, paths, and recommendation.
- Image director workflow: converts task context into feasibility, `TaskCard`, `ArtDirection`, `VisualPlan`, prompts, review checklist, metadata, and optional identity lock.
- Human reviewer: decides whether the single render is acceptable and supplies issue tags for any follow-up.

### Surfaces

- Skill entry: `SKILL.md`
- Delegation policy: `AGENTS.md`
- Director spec: `subagents/image_director.md`
- Runtime planner/renderer: `scripts/imageops_core.py`
- Run creator: `scripts/create_run.py`
- Schemas: `schemas/task_card.schema.json`, `schemas/art_direction.schema.json`, `schemas/visual_plan.schema.json`
- Director references: `references/directors/*.md`
- Run outputs: `imageops/runs/{timestamp}-{slug}/`

### States And Transitions

- `NOT_USEFUL`: visual generation does not help the request. Do not render.
- `NEEDS_USER_INPUT`: target is too vague. Do not render until clarified.
- `NEEDS_REFERENCES`: exact identity, product, brand, or style preservation needs references. Do not render unless user accepts assumptions.
- `PROCEED_WITH_ASSUMPTIONS`: render is allowed; assumptions must be recorded.
- `PROCEED`: render is allowed.

Run lifecycle:

1. User request enters main session.
2. Main session creates a run with `scripts/create_run.py`.
3. Feasibility determines whether generation may continue.
4. Runtime writes `request.json`, `task_card.json`, `art_direction.json`, `visual_plan.json`, `brief.json`, prompts, review checklist, and metadata.
5. Main session uses `prompt.codex.txt` for one Codex `image_gen` render only if status allows.
6. Human feedback drives any second pass.

### Interface And Data Implications

- `TaskCard` owns product-facing intent: use case, deliverable, hero subject, aspect ratio, text mode, must-show, must-not-show, constraints, references, render count, and auto-regeneration policy.
- `ArtDirection` owns quality-facing direction: director id, visual thesis, emotional read, focal hierarchy, layout grammar, lighting motivation, material specificity, taste anchors, expensive cues, cheap cues, and text policy.
- `VisualPlan` owns execution-facing scene structure: scene concept, shot family, spatial layers, composition, lighting, materials, text strategy, constraints, reference anchors, and human checklist.
- `brief.json` remains a compatibility aggregate, not the primary source of truth.
- `negative.txt` is a legacy file name for compact hard constraints, not a generic negative prompt dump.
- `metadata.json` must include director id, visual thesis, text mode, focal hierarchy, renderer recommendation, references, and run paths.

## NON-GOALS

- Do not promise ChatGPT Images parity.
- Do not create a default multi-image A/B workflow.
- Do not add automatic image QA as a replacement for human taste.
- Do not make director cards into new rigid house templates.
- Do not force real subagent execution for every request.
- Do not implement true reference-image analysis until the visual input and extraction interface are explicit.
- Do not add external paid API dependencies by default.

## OPEN QUESTIONS

- Should `isolated-agent` become an explicit mode beside the current file-isolated standard mode?
- What issue-tag vocabulary should drive second-pass regeneration?
- How should visual reference images be passed into the skill and summarized into anchors?
- Should accepted prompts be stored in memory, and what similarity threshold prevents overfitting?
- Should the legacy `references/presets/` files be deleted, migrated, or kept as backward-compatible reference material?
- Should `scripts/imageops_core.py` be split into parser, selector, planner, renderer, and memory modules now, or after one more validation pass?

## HANDOFF

Status: ready for direct implementation of phase 2, with one architecture decision still open: whether to add a real `isolated-agent` mode now or keep it as an explicit future capability.

Recommended next lane: `tdd-workflow` for focused tests around `TaskCard`, `ArtDirection`, `VisualPlan`, renderer output, and feasibility transitions.

Next implementation tasks:

1. Add issue-tag based follow-up prompt rewriting.
2. Add tests for Codex poster, fashion cover, UI mockup, product poster, and cinematic portrait.
3. Decide whether to migrate or delete `references/presets/`.
4. Split `scripts/imageops_core.py` only after tests cover current behavior.
5. Add reference-anchor extraction once the image/reference interface is clear.
