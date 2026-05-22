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

## Prompt Shape

```text
Subject:
Visual direction:
Aspect ratio:
Composition:
Light and texture:
Camera:
Positive constraints:
Text handling:
Preserve:
Avoid:
```

## Default Stance

Generate one image by default. Do not produce multiple rendered variants unless the user explicitly asks for variants.

