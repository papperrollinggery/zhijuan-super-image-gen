# Deep Research Prompt

You are a senior AI image-generation product architect, visual director, and prompt systems designer.

Repository to analyze:

```text
zhijuan-super-image-gen
```

Goal:

Build a Codex Skill that makes one-sentence image requests in Codex produce stronger single-shot images through better visual understanding, art direction, lighting, material texture, composition, and prompt rendering. The skill must not pretend it changes the underlying Codex `image_gen` model, must not default to multi-image generation, and must not replace human taste with automated aesthetic QA.

Current situation:

The skill currently acts as a director layer before Codex `image_gen`. It creates:

```text
feasibility.md
brief.json
negative.txt
codex.draft.txt
chatgpt.final.txt
human_checklist.md
metadata.json
```

The current implementation has added taste presets and craft expansion, including:

```text
premium_saas_poster
cinematic_realism
luxury_product_photo
editorial_portrait
clean_ui_mockup
anime_key_visual
concept_art
```

Observed issue:

The skill can make outputs more structured and stable, but it may also reduce design vitality. It tends to become a polished SaaS template instead of capturing the deeper ChatGPT image-generation quality: strong visual concept, natural scene intelligence, lighting atmosphere, material richness, spatial storytelling, and coherent art direction.

Research and analyze:

1. What is the real difference between ChatGPT image generation and a direct Codex `image_gen` prompt?
   - language understanding
   - implicit visual completion
   - world knowledge
   - taste defaults
   - composition strategy
   - lighting strategy
   - material and texture strategy
   - detail density
   - prompt rewriting
   - multi-turn editing

2. Why can structured field prompts make images feel less alive?
   Compare:
   - field-style prompts
   - checklist prompts
   - negative-heavy prompts
   - natural-language director briefs
   - hybrid prompts

3. What should this skill actually learn from ChatGPT?
   Focus on:
   - visual concept generation
   - scene construction
   - art-direction selection
   - aesthetic tension
   - material specificity
   - lighting plausibility
   - composition intelligence
   - constraint restraint

4. Design a v2 workflow for this skill.
   Requirements:
   - one-sentence input should work well
   - default single image only
   - no default multi-image generation
   - no fake automated taste QA
   - no huge prompt
   - no generic negative prompt dump
   - preserve native Codex `image_gen` creativity
   - generate stronger light, material, space, details, and design sense
   - keep `chatgpt.final.txt` as a handoff artifact

5. Review the repository implementation directly.
   Identify:
   - what is good
   - what is overfit or too template-like
   - what should be removed
   - what should be added
   - what prompt renderer should output
   - what metadata should be saved
   - what scripts should exist

6. Use this concrete example:

```text
生成一张 Codex 的介绍电商海报，突出 AI coding agent，光影高级，质感强，细节丰富，适合 4:5 电商主图。不要官方 logo，不要虚构数字。
```

Show:

```text
current style prompt
better v2 prompt
why v2 is more likely to produce stronger image quality
```

Output format:

```text
1. Diagnosis
2. What to keep
3. What to remove or weaken
4. New v2 architecture
5. Prompt rendering rules
6. Concrete file/script changes
7. Example rewritten prompt
8. Risks and failure modes
9. Priority implementation plan
```

Do not give generic advice. Produce an implementation-ready critique of this repository.

