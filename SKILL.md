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

5. Stop before generation when feasibility returns `NEEDS_REFERENCES`, `NEEDS_USER_INPUT`, `NOT_USEFUL`, or `BLOCKED`.
6. For one-sentence requests, build `task_card.json`, `art_direction.json`, and `visual_plan.json` first. Do not let presets directly decide the hero object or scene template.
7. Render `codex.draft.txt` as a short natural-language director brief plus only load-bearing text, preserve, and constraint lines.
8. For optional handoff, use `chatgpt.final.txt`; do not imply Codex must hand off for final quality.
9. Return only status, file paths, and recommendation.

## Feasibility Status

- `PROCEED`: visual target is useful and specific enough.
- `PROCEED_WITH_ASSUMPTIONS`: usable with explicit assumptions.
- `NEEDS_REFERENCES`: identity, product, brand, or style preservation needs references.
- `NEEDS_USER_INPUT`: target is too vague to direct safely.
- `NOT_USEFUL`: image generation does not help the task.
- `BLOCKED`: request cannot be handled within available tools or policy.

## Prompt Discipline

For Codex `image_gen`, preserve native strengths:

- Use compact prompts with clear subject, scene, camera, lighting, style, preservation, and avoid rules.
- Add art-direction defaults when the user gives only a short request: visual thesis, emotional read, focal hierarchy, layout grammar, lighting motivation, tactile materials, expensive cues, cheap cues, and clean crop margins.
- Use director cards as bias, not fixed scene templates. Director cards can influence tone, lighting, materials, hierarchy, and cheap/expensive cues, but must not force fixed objects such as specific pedestals, feature-chip layouts, or trust-strip sections.
- Let the model infer natural visual detail.
- Include only relevant hard constraints. Avoid generic negative prompt dumps.
- Avoid repeated quality words, conflicting styles, long negative dumps, exact camera physics, and rigid composition rules.
- Do not default to multi-image generation. Variants are opt-in.

When expanding short prompts, use `references/craft_rules.md` and the matching file under `references/directors/` if you need more detail than `SKILL.md` provides.

For ChatGPT Images 2.0 handoff:

- Expand material, composition, preservation, and constraint detail.
- Keep language precise and non-repetitive.
- Mark the file `FINAL_RENDER_HANDOFF`.

## Identity Lock

Create `identity_lock.json` only for recurring people, characters, mascots, products, UI systems, or brand styles. Use references as the source of truth when available. Do not use identity lock for generic scenes.

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
- imageops/runs/{timestamp}-{slug}/human_checklist.md
- imageops/runs/{timestamp}-{slug}/review.md
- imageops/runs/{timestamp}-{slug}/metadata.json

Recommendation:
Use prompt.codex.txt for one Codex image_gen render. Use prompt.chatgpt.txt only when a ChatGPT handoff is explicitly needed.
```
