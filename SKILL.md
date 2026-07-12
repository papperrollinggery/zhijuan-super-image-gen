---
name: zhijuan-super-image-gen
description: Image-generation director workflow for Codex. Use when a request involves generating or refining images, posters, portraits, storyboards, concept art, UI mockups, product shots, character design, scene design, thumbnails, banners, style references, visual direction, Codex image_gen prompt isolation, prompt compression or expansion, identity locks, hard constraints, draft renders, or ChatGPT Images handoff prompts.
---

# Zhijuan Super Image Gen

Use this skill to prepare image-generation work without polluting the main Codex session with long prompts. This skill improves planning, prompt quality, isolation, versioning, handoff discipline, and art direction; it cannot change the underlying `image_gen` model or guarantee ChatGPT-equivalent rendering.

## Workflow

1. Treat the main Codex session as a clean orchestrator.
2. Delegate visual planning to `subagents/image_director.md`. If subagent tools are unavailable, run the same isolated workflow in a fresh `imageops/runs/` directory.
3. Pass only task-relevant visual context, user constraints, and reference paths.
4. Create run artifacts with:

```bash
python3 scripts/create_run.py --task "$TASK" --slug "$SLUG"
```

5. Stop before generation when feasibility returns `NEEDS_REFERENCES`, `NEEDS_USER_INPUT`, `NOT_USEFUL`, or `BLOCKED`. Set `BLOCKED` only through the explicit runtime/API flag; never infer it from user copy.
6. For one-sentence requests, build `task_card.json`, `art_direction.json`, and `visual_plan.json` first. Do not let presets directly decide the hero object or scene template.
7. In `visual_plan.json`, keep a fixed visual breakdown: subject, action/pose, details/appearance, environment/background, lighting/atmosphere, composition/framing, style/camera, colors, materials, aspect ratio, quality/finish, and generation intent.
8. For non-trivial tasks, create internal `concept_candidates` and select one `selected_concept_id`. These candidates are planning evidence, not a request for multiple renders.
9. Preserve user-supplied literal copy and labeled `Constraints:` / `Avoid:` directives in the compiled prompt; never invent replacement copy.
10. Render `codex.draft.txt` as a short natural-language director brief plus only load-bearing text, preserve, and constraint lines.
11. Also save `prompt_core.txt` and `recreation_prompt.txt` as reusable prompt layers; treat `negative.txt` as compact hard constraints.
12. For optional handoff, use `chatgpt.final.txt`; do not imply Codex must hand off for final quality.
13. If the first render needs revision, use issue tags with `scripts/rewrite_prompt_from_review.py`; rewrite one or two causes only.
14. Validate a persisted run with `python3 scripts/validate_run.py imageops/runs/{run}` before recommending its prompt.
15. Return only status, file paths, and recommendation.

## Feasibility Status

- `PROCEED`: visual target is useful and specific enough.
- `PROCEED_WITH_ASSUMPTIONS`: usable with explicit assumptions.
- `NEEDS_REFERENCES`: identity, product, brand, or style preservation needs references.
- `NEEDS_USER_INPUT`: target is too vague to direct safely.
- `NOT_USEFUL`: image generation does not help the task.
- `BLOCKED`: request cannot be handled within available tools or policy.

Treat HTTP(S) URLs as remote-reference metadata validated only by URL shape; record that their content is not fetched or decoded, and never let them satisfy identity/style gating or become a Codex `image_gen` source of truth. A usable reference must be a local path that exists, is readable, and has a recognized PNG, JPEG, GIF, or WebP signature. Omit invalid or empty local paths from provided-reference artifacts and keep `NEEDS_REFERENCES` until exact preservation has a usable local reference.

## Prompt Discipline

For Codex `image_gen`, preserve native strengths:

- Use compact prompts with clear subject, scene, camera, lighting, style, preservation, and avoid rules.
- Add art-direction defaults when the user gives only a short request: visual thesis, emotional read, focal hierarchy, layout grammar, lighting motivation, tactile materials, expensive cues, cheap cues, and clean crop margins.
- Use type-aware planning for portraits, product images, posters, UI, illustration, 3D, and photography. Keep the type logic inside artifacts and the final brief, not as a long checklist.
- Use director cards as bias, not fixed scene templates. Director cards can influence tone, lighting, materials, hierarchy, and cheap/expensive cues, but must not force fixed objects such as specific pedestals, feature-chip layouts, or trust-strip sections.
- Let the model infer natural visual detail.
- Include only relevant hard constraints. Avoid generic negative prompt dumps.
- Use concrete visible finish cues instead of filler such as `masterpiece`, `highly detailed`, or repeated generic quality words.
- Do not invent hidden brands, exact text, precise locations, tools, claims, or off-frame details unless the user or references provide them.
- Avoid repeated quality words, conflicting styles, long negative dumps, exact camera physics, and rigid composition rules.
- Do not default to multi-image generation. Variants are opt-in.
- Keep output artifacts in English by default. Do not add multilingual prompt fields unless a downstream UI or user request needs them.
- The default Codex prompt renderer is the V2 short director brief. It should stay around 5-7 lines for ordinary tasks and should not be rendered as a schema checklist.
- Keep `prompt.codex.txt` at or below 190 lexical units. Count each CJK character as one unit and each Latin-script word/number as one unit. Preserve every explicit `Constraints:` / `Avoid:` item; if they exceed the deterministic constraint budget, return `NEEDS_USER_INPUT` and fail run validation with a prioritization message instead of truncating them.

When expanding short prompts, use `references/craft_rules.md` and the matching file under `references/directors/` if you need more detail than `SKILL.md` provides.

For ChatGPT Images 2.0 handoff:

- Expand material, composition, preservation, and constraint detail.
- Keep language precise and non-repetitive.
- Mark the file `FINAL_RENDER_HANDOFF`.

## Identity Lock

Create `identity_lock.json` only for recurring people, characters, mascots, products, UI systems, or brand styles. Use scope-specific anchors; do not apply face anchors to products or style references. Use references as the source of truth when available. Do not use identity lock for generic scenes.

## Follow-Up Issue Tags

Use these tags after a human review finds a specific problem:

- `wrong_visual_family`
- `text_unreadable`
- `too_generic`
- `overconstrained`
- `weak_composition`
- `weak_materials`
- `reference_drift`
- `fake_claims`

Use `reference_drift` only when the run has valid references and an `identity_lock.json` whose source is `provided_references`; otherwise reject the follow-up before writing drafts.
Allow any follow-up only when the persisted feasibility status is `PROCEED` or `PROCEED_WITH_ASSUMPTIONS`. Before writing, require the resulting prompt to remain 5-7 non-empty lines and at most 190 lexical units.

Run:

```bash
python3 scripts/rewrite_prompt_from_review.py imageops/runs/{run} --tag too_generic --tag weak_composition
```

To persist a deterministic blocked run after an upstream policy/tool decision, use `python3 scripts/create_run.py --blocked ...`. Do not encode or scan for sentinel words in the user's task.

Treat metadata hashes as a deterministic content-integrity receipt. They detect accidental or post-run content changes when revalidated; without a secret signing key they do not authenticate an entire run against a malicious party that can rewrite every artifact and receipt.

Release readiness for delegation requires an external real Codex Thread forward-test performed by the parent orchestrator, including the actual thread id, dispatch record, worker receipt, adoption decision, and cleanup evidence. Local scripts must not fabricate or substitute for that evidence.

## Main Session Return

Return exactly this shape:

```text
Image task status: PROCEED_WITH_ASSUMPTIONS

Files created:
- imageops/runs/{timestamp}-{slug}/feasibility.md
- imageops/runs/{timestamp}-{slug}/request.json
- imageops/runs/{timestamp}-{slug}/brief.json
- imageops/runs/{timestamp}-{slug}/task_card.json
- imageops/runs/{timestamp}-{slug}/art_direction.json
- imageops/runs/{timestamp}-{slug}/visual_plan.json
- imageops/runs/{timestamp}-{slug}/negative.txt
- imageops/runs/{timestamp}-{slug}/codex.draft.txt
- imageops/runs/{timestamp}-{slug}/chatgpt.final.txt
- imageops/runs/{timestamp}-{slug}/prompt.codex.txt
- imageops/runs/{timestamp}-{slug}/prompt.chatgpt.txt
- imageops/runs/{timestamp}-{slug}/prompt_core.txt
- imageops/runs/{timestamp}-{slug}/recreation_prompt.txt
- imageops/runs/{timestamp}-{slug}/human_checklist.md
- imageops/runs/{timestamp}-{slug}/review.md
- imageops/runs/{timestamp}-{slug}/identity_lock.json (only when preservation is needed)
- imageops/runs/{timestamp}-{slug}/metadata.json

Recommendation:
Use prompt.codex.txt for one Codex image_gen render. Use prompt.chatgpt.txt only when a ChatGPT handoff is explicitly needed.
```
