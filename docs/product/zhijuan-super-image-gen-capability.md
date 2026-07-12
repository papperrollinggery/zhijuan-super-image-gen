# Zhijuan Super Image Gen Capability Contract

## CAPABILITY

`zhijuan-super-image-gen` gives Codex an image-director lane for visual generation requests: the main session stays a clean orchestrator, the skill converts a short user image request into durable planning artifacts, and the final Codex `image_gen` call receives one compact art-directed prompt instead of a long field checklist. The V2 workflow adds task fixtures, safer reference gating, internal visual concept candidates, a short director prompt renderer, issue-tag follow-up rewrites, and an eval harness. The capability improves context hygiene, prompt structure, repeatability, and art-direction consistency; it does not change the underlying image model or guarantee ChatGPT-equivalent rendering.

## CONSTRAINTS

- Default render count is one. Multi-image variants are opt-in only.
- Automatic regeneration is off by default. Human issue tags should drive follow-up renders.
- `image_gen` must remain the native draft renderer. The skill must not replace it with an API fallback unless explicitly requested.
- ChatGPT Images handoff is optional and artifact-only; it is not the default final-render route.
- Director cards guide thesis, tone, hierarchy, light, material, and cheap/expensive cues. They must not force fixed objects, layout widgets, feature chips, trust strips, pedestals, or fake brand marks.
- Final Codex prompts must be short natural-language director briefs with only load-bearing `Text`, `Preserve`, and `Constraints` lines.
- `visual_plan.json` carries the fixed structured breakdown: subject, action/pose, details/appearance, environment/background, lighting/atmosphere, composition/framing, style/camera, colors, materials, aspect ratio, quality/finish, and generation intent.
- `visual_plan.json` also carries `concept_candidates` and `selected_concept_id`. Candidates are internal planning evidence; they do not imply multi-render output.
- `prompt_core.txt` and `recreation_prompt.txt` are reusable prompt layers. `prompt.codex.txt` remains the default render input.
- Multilingual prompt fields are not part of the default workflow; add them only for UI/export needs.
- Style tags are compact metadata for indexing and review, not a replacement for the director brief.
- Do not invent copy, metrics, prices, awards, ratings, user counts, publication names, or official logos unless literal copy or references are provided.
- Identity locks are only for exact preservation or reference-dependent recurring people, characters, mascots, products, UI systems, or brand styles. Ordinary brand/product mentions and no-logo explanatory graphics must not trigger a reference gate.
- Reference handling is currently text-path aware only. True visual anchor extraction remains open.
- Real subagent execution is a context-isolation feature, not a direct image-quality feature.
- Human review follow-up uses issue tags and writes `drafts/followup.codex.txt`; it rewrites one or two causes, not the entire task.
- Literal copy plus labeled `Constraints:` and `Avoid:` directives are load-bearing and must survive prompt compilation.
- Literal-copy values end only at the next known label or newline; punctuation and letter case are content, not delimiters.
- Keep the Codex prompt at or below 190 lexical units: each CJK character counts as one unit and each Latin-script word/number counts as one unit. If explicit constraints exceed their deterministic budget, preserve them in artifacts, return `NEEDS_USER_INPUT`, and reject persisted-run validation until the user prioritizes them.
- Persisted runs must pass `scripts/validate_run.py`; release checks also exercise answer-free forward inputs and a temporary on-disk smoke run.

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
- `BLOCKED`: an upstream tool or policy decision explicitly prevents rendering. Enter this state only with `create_run.py --blocked` or the equivalent API flag; never infer it from user text.

HTTP(S) references are recorded separately and receive URL-shape validation only; because remote content is not fetched or decoded, URLs cannot satisfy identity/style gating or become `provided_references`. Local reference paths must exist, be readable, and carry a recognized PNG, JPEG, GIF, or WebP signature before they can satisfy reference gating or become a Codex `image_gen` source of truth.
Treat natural-language combinations of a preservation action plus an attachment/reference source as exact preservation requests, including identity details and brand visual systems.

Run lifecycle:

1. User request enters main session.
2. Main session creates a run with `scripts/create_run.py`.
3. Feasibility determines whether generation may continue.
4. Runtime writes `request.json`, `task_card.json`, `art_direction.json`, `visual_plan.json`, `brief.json`, prompts, review checklist, and metadata.
5. Main session uses `prompt.codex.txt` for one Codex `image_gen` render only if status allows.
6. Human feedback uses issue tags such as `too_generic`, `weak_composition`, or `text_unreadable` to create `drafts/followup.codex.txt`.

### Interface And Data Implications

- `TaskCard` owns product-facing intent: use case, deliverable, hero subject, aspect ratio, text mode, must-show, must-not-show, constraints, references, render count, and auto-regeneration policy.
- `ArtDirection` owns quality-facing direction: director id, visual thesis, emotional read, focal hierarchy, layout grammar, lighting motivation, material specificity, taste anchors, expensive cues, cheap cues, and text policy.
- `VisualPlan` owns execution-facing scene structure: scene concept, candidate visual solutions, selected concept, shot family, spatial layers, composition, lighting, materials, text strategy, constraints, reference anchors, and human checklist.
- `VisualPlan` also owns type-aware visual breakdown, compact style tags, quality target, generation intent, and reusable prompt layers.
- `brief.json` remains a compatibility aggregate, not the primary source of truth.
- `negative.txt` is a legacy file name for compact hard constraints, not a generic negative prompt dump.
- `metadata.json` must include runtime/schema versions, canonical input SHA-256, a versioned SHA-256 artifact receipt, director id, visual thesis, text mode, focal hierarchy, renderer recommendation, references, and run paths.
- The hash receipt is for deterministic content-integrity checking. It detects accidental or post-run changes when the validator recomputes it; without key-based signing it does not claim malicious whole-run authenticity.
- Run validation recomputes feasibility, task id, brief, identity lock, metadata projections, and both render prompts from `request.json`; synchronized edits to stored artifacts are invalid unless they match deterministic recompilation.
- `reference_drift` follow-ups require both valid references and an identity lock sourced from `provided_references`.
- All follow-ups require `PROCEED` or `PROCEED_WITH_ASSUMPTIONS` and must remain 5-7 non-empty lines and at most 190 lexical units.
- Release delegation evidence must come from a real external Codex Thread forward-test by the parent orchestrator, with thread id, dispatch, receipt, adoption, and cleanup evidence. Local scripts do not simulate that proof.

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
- How should visual reference images be passed into the skill and summarized into anchors?
- Should accepted prompts be stored in memory, and what similarity threshold prevents overfitting?
- Should the legacy `references/presets/` files be deleted, migrated, or kept as backward-compatible reference material?
- Should `scripts/imageops_core.py` be split into parser, selector, planner, renderer, and memory modules now, or after one more validation pass?

## HANDOFF

Status: V2 runtime implemented with tests and an eval harness. One architecture decision remains open: whether to split `scripts/imageops_core.py` into parser, selector, planner, renderer, and memory modules after the current behavior is covered.

Recommended next lane: run the release check and then consider a focused refactor only if `scripts/imageops_core.py` becomes too hard to reason about.

Next implementation tasks:

1. Decide whether to migrate or delete `references/presets/`.
2. Split `scripts/imageops_core.py` only after tests cover current behavior well enough for refactoring.
3. Add reference-anchor extraction once the image/reference interface is clear.
4. Add accepted-image memory after the eval harness has enough examples.
