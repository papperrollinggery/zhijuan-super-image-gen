# Craft Rules

Use these rules when expanding a short image request before calling Codex `image_gen`.

## Default Priorities

1. One clear subject.
2. Strong foreground/background separation.
3. Consistent light direction.
4. Tactile material description.
5. Controlled color palette.
6. Background detail that supports the subject.
7. Short, readable text only when needed.
8. No invented claims, metrics, ratings, certifications, awards, prices, or user counts.
9. Director cards guide tone, lighting, materials, focal hierarchy, layout grammar, expensive cues, and cheap cues only. They must not force fixed scene objects or fixed layout widgets.
10. Plan with visible evidence only. Do not invent hidden objects, exact brands, exact copy, precise locations, tools, or off-frame facts.
11. Use concrete finish targets instead of generic quality filler.
12. Choose type-aware emphasis:
    - Portrait: pose, gaze, expression, skin texture, hair, clothing, motivated catchlight.
    - Product: silhouette, scale, contact shadow, surface finish, reflection behavior.
    - Poster: visual hierarchy, headline-safe negative space, crop, symbolic clarity.
    - UI: primary screen state, readable grid, spacing, few large labels.
    - Illustration: silhouette, line or paint finish, controlled palette, world detail.
    - 3D: scale, bevels, material roughness, grounded shadows.
    - Photography: lens-consistent depth, foreground/midground/background, natural light behavior.

## Structured Planning

Keep these fields in `visual_plan.json`, not as a final prompt checklist:

```json
{
  "visual_type": "portrait | product | poster | ui | illustration | 3d | photography",
  "visual_breakdown": {
    "subject": "...",
    "action_pose": "...",
    "details_appearance": "...",
    "environment_background": "...",
    "lighting_atmosphere": "...",
    "composition_framing": "...",
    "style_camera": "...",
    "colors": ["..."],
    "materials": ["..."],
    "aspect_ratio": "...",
    "quality_finish": "...",
    "generation_intent": "..."
  },
  "style_tags": ["tag 1", "tag 2", "tag 3", "tag 4"],
  "concept_candidates": [
    {
      "concept_id": "...",
      "visual_solution": "...",
      "why_it_fits": "...",
      "first_read": "...",
      "second_read": "...",
      "text_risk": "low | medium | high",
      "reference_risk": "low | medium | high",
      "thumbnail_readability": "low | medium | high",
      "selected": true
    }
  ],
  "selected_concept_id": "...",
  "prompt_layers": {
    "prompt_core": "...",
    "recreation_prompt": "...",
    "negative_prompt": "..."
  }
}
```

Use English artifact fields by default. Multilingual prompts are an export concern, not the core Codex workflow. Concept candidates are internal planning evidence; they help choose one strong visual solution without defaulting to multiple renders.

## Prompt Shape

Prefer a short natural-language director brief:

```text
Create a [aspect ratio] [deliverable].
Build the image around [visual thesis].
Show [scene concept], with [hero subject] as the first read and [supporting evidence] as the second read.
Use [lighting motivation]. Materials should feel specific and tactile: [material specificity].
Keep the composition [layout grammar].
The image should feel [emotional read], not [cheap cues].
Text: [only when useful]
Preserve: [only when references or identity anchors exist]
Constraints: [1-4 hard constraints only]
```

## Default Stance

Generate one image by default. Do not produce multiple rendered variants unless the user explicitly asks for variants.

Do not render the final Codex prompt as a long field checklist. Field data belongs in `task_card.json`, `art_direction.json`, `visual_plan.json`, and `brief.json`.
