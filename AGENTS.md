# Image Delegation Policy

Keep the main Codex session as a clean orchestrator.

When an image-related requirement appears, delegate to the Zhijuan Super Image Gen workflow in `subagents/image_director.md`.

The image director must:

1. Analyze feasibility.
2. Extract only relevant visual context.
3. Build a structured image brief.
4. Build preservation rules when needed.
5. Build compact hard constraints.
6. Generate Codex draft prompt.
7. Generate ChatGPT final render prompt.
8. Save files under `imageops/runs/`.
9. Return only status, paths, and recommendation.

Do not paste long prompt bodies into the main session unless explicitly requested.

Use Codex `image_gen` for the default single render.

Use ChatGPT Images 2.0 handoff prompts only when explicitly needed.
