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
