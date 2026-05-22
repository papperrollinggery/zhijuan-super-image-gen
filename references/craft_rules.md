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
9. Direction cards guide tone, palette, lighting, materials, and composition family only. They must not force fixed scene objects or fixed layout widgets.

## Prompt Shape

Prefer a short natural-language director brief:

```text
Create a [aspect ratio] [deliverable].
Show [hero subject] through [visual concept], with [scene evidence].
Compose it with [focal order, crop, negative space].
Use [lighting behavior], with tactile materials such as [material family] so the image feels spatially real rather than like a flat template.
[Text rule.] Constraints: [1-4 hard constraints].
```

## Default Stance

Generate one image by default. Do not produce multiple rendered variants unless the user explicitly asks for variants.

Do not render the final Codex prompt as a long field checklist. Field data belongs in `task_card.json`, `visual_plan.json`, and `brief.json`.
