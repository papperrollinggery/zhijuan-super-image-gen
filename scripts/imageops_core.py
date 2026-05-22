#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


VISUAL_TRIGGERS = {
    "image", "generate image", "poster", "portrait", "storyboard", "concept art",
    "ui mockup", "mockup", "character design", "scene design", "thumbnail",
    "banner", "style reference", "visual direction", "product shot", "render",
    "logo", "illustration", "生图", "图片", "海报", "头像", "分镜", "概念图",
    "角色", "场景", "缩略图", "横幅", "视觉", "风格参考", "产品图",
}

IDENTITY_TERMS = {
    "same person", "same character", "recurring", "mascot", "brand", "logo",
    "product", "identity", "consistent", "preserve", "reference", "同一个",
    "角色一致", "身份", "品牌", "产品", "保持", "参考图", "一致",
}

REFERENCE_REQUIRED_TERMS = {
    "same person", "same character", "real person", "celebrity", "brand",
    "logo", "product", "reference image", "exact", "同一个人", "真人",
    "明星", "品牌", "logo", "产品", "参考图", "一模一样",
}

PERSON_TERMS = {
    "person", "portrait", "face", "hands", "character", "model", "actor",
    "woman", "man", "girl", "boy", "人物", "肖像", "脸", "手", "角色",
    "男人", "女人", "女孩", "男孩",
}

UI_TERMS = {"ui", "app", "website", "dashboard", "mockup", "界面", "应用", "网页", "小程序"}
PRODUCT_TERMS = {"product", "packaging", "device", "shoe", "phone", "bottle", "产品", "包装", "设备", "手机"}
SCENE_TERMS = {"room", "street", "city", "landscape", "architecture", "interior", "场景", "街道", "城市", "建筑", "室内"}

TEXT_HEAVY_TERMS = {"text", "typography", "copy", "headline", "poster", "banner", "label", "logo", "文字", "排版", "标题", "海报", "横幅", "标签", "卖点"}
NO_FAKE_CLAIMS_TERMS = {"ecommerce", "poster", "ad", "landing", "marketing", "电商", "海报", "广告", "营销", "主图", "卖点"}

DIRECTION_CARDS: dict[str, dict[str, str]] = {
    "commercial_tech_still_life": {
        "tone": "premium technology campaign, physically grounded, expensive but not sterile",
        "palette": "deep charcoal, graphite, glass highlights, restrained blue-green accents",
        "light": "soft directional studio light, cool edge rim, screen glow, crisp contact shadows",
        "materials": "brushed aluminum, smoked glass, matte plastic, subtle dust, slight wear, believable reflections",
        "composition": "one dominant hero subject, clear negative space for a short headline, readable crop",
    },
    "editorial_workplace_realism": {
        "tone": "credible editorial photo of real work happening, polished but lived-in",
        "palette": "dark workstation neutrals, natural screen light, restrained accent color",
        "light": "motivated desk light, screen glow, soft falloff, real shadow depth",
        "materials": "keyboard texture, desk surface, fingerprints, glass, cables, notebooks, tool marks",
        "composition": "workspace context with a clear focal moment, foreground depth, non-random props",
    },
    "ui_object_hybrid": {
        "tone": "interface becomes a tangible product object, clean and dimensional",
        "palette": "dark UI surfaces, subtle glow, restrained product-photography accents",
        "light": "studio key light plus interface glow, controlled reflections, visible bevels",
        "materials": "glass cards, edge-lit panels, thin metal frames, soft shadows",
        "composition": "interface hero with supporting panels, spatial hierarchy instead of dense dashboard clutter",
    },
    "graphic_poster_minimal": {
        "tone": "sharp graphic campaign poster, minimal but not empty",
        "palette": "strong contrast, one accent family, disciplined whitespace",
        "light": "flat graphic clarity with subtle dimensional highlight only where useful",
        "materials": "clean vector-like surfaces and simple dimensional forms",
        "composition": "large typography area, one symbolic image, minimal supporting copy",
    },
    "cinematic_scene": {
        "tone": "cinematic scene with atmosphere, narrative tension, and believable world detail",
        "palette": "coherent color grade, natural contrast, environmental depth",
        "light": "motivated directional light, bounce, rim, consistent shadows",
        "materials": "surfaces with texture, age, moisture, dust, fabric, skin, metal, or glass as appropriate",
        "composition": "one readable focal subject with layered foreground, middle ground, background",
    },
}


@dataclass
class TaskCard:
    use_case: str
    deliverable: str
    hero_subject: str
    aspect_ratio: str
    wants_text: bool
    hard_constraints: list[str]
    factual_risk: list[str]
    references: list[str]


@dataclass
class VisualPlan:
    direction_family: str
    concept: str
    scene: str
    composition: str
    lighting: str
    materials: str
    text_rule: str
    hard_constraints: list[str]
    human_checklist: list[str]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_task(task: str | None = None, task_file: str | None = None) -> str:
    if task:
        return task.strip()
    if task_file:
        return Path(task_file).read_text(encoding="utf-8").strip()
    return ""


def slugify(value: str, fallback: str = "image-task", limit: int = 48) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        value = fallback
    return value[:limit].strip("-") or fallback


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def contains_any(text: str, terms: set[str]) -> bool:
    lower = text.lower()
    for term in terms:
        normalized = term.lower()
        if re.search(r"[\u4e00-\u9fff]", normalized):
            if normalized in lower:
                return True
        elif " " in normalized or "-" in normalized:
            if normalized in lower:
                return True
        elif re.search(rf"\b{re.escape(normalized)}\b", lower):
            return True
    return False


def infer_use_case(task: str) -> str:
    lower = task.lower()
    cases = [
        ("ui mockup", {"ui mockup", "dashboard", "app", "website", "界面", "网页", "应用"}),
        ("portrait", {"portrait", "headshot", "avatar", "肖像", "头像"}),
        ("poster", {"poster", "海报"}),
        ("storyboard", {"storyboard", "分镜"}),
        ("character design", {"character", "mascot", "角色", "吉祥物"}),
        ("product image", {"product", "packaging", "产品", "包装"}),
        ("scene design", {"scene", "environment", "场景", "环境"}),
        ("thumbnail", {"thumbnail", "缩略图", "封面"}),
    ]
    for label, terms in cases:
        if any(term in lower for term in terms):
            return label
    return "image generation"


def detect_risk_flags(task: str, use_case: str, direction_family: str) -> list[str]:
    flags = []
    lower = task.lower()
    no_official_mark = any(phrase in lower for phrase in ["no logo", "without logo", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"])
    identity_terms = IDENTITY_TERMS - {"brand", "logo", "品牌"} if no_official_mark else IDENTITY_TERMS
    if contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"poster", "ui mockup", "thumbnail"}:
        flags.append("text_risk")
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        flags.append("fake_claims_risk")
    if contains_any(task, identity_terms):
        flags.append("identity_drift_risk")
    if use_case in {"ui mockup", "poster"}:
        flags.append("layout_precision_risk")
    if direction_family in {"commercial_tech_still_life", "ui_object_hybrid"}:
        flags.append("geometry_risk")
    return flags


def parse_labeled_sections(task: str) -> dict[str, str]:
    labels = {
        "use case": "use_case",
        "scene": "scene",
        "subject": "subject",
        "camera": "camera",
        "lighting": "lighting",
        "materials": "materials",
        "composition": "composition",
        "style": "style",
        "preserve": "preserve",
        "constraints": "constraints",
        "avoid": "avoid",
    }
    found: dict[str, str] = {}
    pattern = re.compile(r"(?im)^\s*([a-zA-Z ]{3,18}|场景|主体|镜头|光线|风格|保留|避免)\s*[:：]\s*(.+)$")
    zh = {
        "场景": "scene",
        "主体": "subject",
        "镜头": "camera",
        "光线": "lighting",
        "风格": "style",
        "保留": "preserve",
        "避免": "avoid",
    }
    for match in pattern.finditer(task):
        raw = match.group(1).strip().lower()
        key = labels.get(raw) or zh.get(match.group(1).strip())
        if key:
            found[key] = match.group(2).strip()
    return found


def analyze_feasibility(task: str, references: list[str] | None = None) -> dict[str, Any]:
    references = references or []
    lower = task.lower()
    image_useful = contains_any(task, VISUAL_TRIGGERS)
    vague = len(re.findall(r"[\w\u4e00-\u9fff]+", task)) < 4 or lower.strip() in {"make image", "generate image", "生图", "画图"}
    no_official_mark = any(phrase in lower for phrase in ["no logo", "without logo", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"])
    identity_needed = contains_any(task, IDENTITY_TERMS)
    if no_official_mark:
        identity_needed = contains_any(task, IDENTITY_TERMS - {"brand", "logo", "品牌"})
    exact_preservation = contains_any(task, {"same person", "same character", "real person", "celebrity", "reference image", "exact", "同一个人", "真人", "明星", "参考图", "一模一样"})
    brand_or_product_exact = contains_any(task, {"brand", "logo", "product", "品牌", "logo", "产品"}) and not no_official_mark
    references_required = (exact_preservation or brand_or_product_exact) and not references

    if not image_useful:
        status = "NOT_USEFUL"
    elif references_required:
        status = "NEEDS_REFERENCES"
    elif vague:
        status = "NEEDS_USER_INPUT"
    elif "blocked" in lower:
        status = "BLOCKED"
    elif len(task) < 80:
        status = "PROCEED_WITH_ASSUMPTIONS"
    else:
        status = "PROCEED"

    assumptions = []
    if status == "PROCEED_WITH_ASSUMPTIONS":
        assumptions.append("Visual target is usable but underspecified; fill only obvious scene, style, and composition gaps.")
    if identity_needed and references:
        assumptions.append("Use provided references as identity or style source of truth.")
    if not references:
        assumptions.append("No external reference images were provided.")

    return {
        "status": status,
        "image_generation_useful": image_useful,
        "target_specific_enough": not vague,
        "references_required": references_required,
        "identity_or_style_preservation_needed": identity_needed,
        "use_codex_image_gen_directly": status in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"},
        "use_chatgpt_images_for_final": status in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"} and (identity_needed or len(task) > 160),
        "assumptions": assumptions,
    }


def build_hard_constraints(task: str, max_items: int = 4) -> list[str]:
    items: list[str] = []

    def add(values: list[str]) -> None:
        for value in values:
            if value not in items:
                items.append(value)

    lower = task.lower()
    if any(phrase in lower for phrase in ["no logo", "without logo", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"]):
        add(["do not use official logos or recreate official brand marks"])
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        add(["do not invent numbers, ratings, prices, awards, certifications, or user counts"])
    if contains_any(task, TEXT_HEAVY_TERMS):
        add(["keep visible text short, large, and legible"])
    if contains_any(task, {"screenshot", "真实截图", "ui screenshot", "官方界面"}):
        add(["do not fake an official product screenshot"])
    return items[:max_items]


def build_negative(task: str, max_items: int = 4) -> list[str]:
    return build_hard_constraints(task, max_items=max_items)


def list_from_text(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    parts = re.split(r"[,;；\n]+", value)
    return [part.strip() for part in parts if part.strip()]


def infer_aspect_ratio(task: str, use_case: str) -> str:
    lower = task.lower()
    if "4:5" in lower:
        return "4:5"
    if "9:16" in lower or "竖版" in task:
        return "9:16"
    if "16:9" in lower or "横版" in task:
        return "16:9"
    if "1:1" in lower or "方图" in task:
        return "1:1"
    if use_case in {"poster", "portrait", "product image"}:
        return "4:5"
    if use_case in {"ui mockup", "scene design"}:
        return "16:9"
    return "1:1"


def strip_constraints_from_subject(task: str) -> str:
    text = re.sub(r"\s+", " ", task).strip()
    splitters = ["。", ". ", "；", ";"]
    first = text
    for splitter in splitters:
        if splitter in first:
            first = first.split(splitter)[0].strip()
            break
    for phrase in ["不要官方 logo", "不要官方logo", "不要虚构数字", "不使用官方 logo", "不要使用官方 logo"]:
        first = first.replace(phrase, "").strip(" ，,。.")
    first = re.sub(r"生成一张|生成一个|create an?|make an?|generate an?", "", first, flags=re.I).strip(" ，,。.")
    if "Codex" in task and "AI coding agent" in task:
        return "Codex presented as an AI coding agent"
    return first[:180] or text[:180]


def parse_task_card(task: str, use_case: str, references: list[str]) -> TaskCard:
    deliverable = {
        "poster": "e-commerce hero poster",
        "ui mockup": "polished UI mockup image",
        "product image": "premium product image",
        "portrait": "editorial portrait",
        "scene design": "cinematic scene image",
        "thumbnail": "thumbnail image",
    }.get(use_case, "image")
    wants_text = contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"poster", "thumbnail"}
    hard_constraints = build_hard_constraints(task)
    factual_risk = []
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        factual_risk.extend(["invented_metrics", "fake_badges", "fake_claims"])
    return TaskCard(
        use_case=use_case,
        deliverable=deliverable,
        hero_subject=strip_constraints_from_subject(task),
        aspect_ratio=infer_aspect_ratio(task, use_case),
        wants_text=wants_text,
        hard_constraints=hard_constraints,
        factual_risk=factual_risk,
        references=references,
    )


def choose_direction_family(task: str, card: TaskCard) -> str:
    if card.use_case == "poster" and contains_any(task, {"codex", "developer", "ai coding agent", "软件", "开发者", "工具"}):
        return "editorial_workplace_realism"
    if card.use_case == "poster":
        return "commercial_tech_still_life"
    if card.use_case == "ui mockup":
        return "ui_object_hybrid"
    if card.use_case in {"product image", "thumbnail"}:
        return "commercial_tech_still_life"
    if contains_any(task, {"minimal", "极简"}):
        return "graphic_poster_minimal"
    return "cinematic_scene"


def build_visual_plan(task: str, card: TaskCard) -> VisualPlan:
    family = choose_direction_family(task, card)
    direction = DIRECTION_CARDS[family]
    if "Codex" in task or "codex" in task.lower():
        concept = "a believable high-end developer workspace at the moment of active problem solving, where Codex feels present through the workflow rather than as a generic sci-fi trophy"
        scene = "a luminous coding interface, terminal output, structured code panels, and subtle signs of reasoning and iteration inside a real workspace"
    elif card.use_case == "product image":
        concept = f"{card.hero_subject} treated as the clear product hero, physically grounded and desirable"
        scene = "a controlled commercial setup with enough environment to show scale and use"
    elif card.use_case == "ui mockup":
        concept = f"{card.hero_subject} presented as a tangible interface experience with clean product hierarchy"
        scene = "a focused interface scene with spatial depth, readable primary panels, and restrained supporting details"
    else:
        concept = f"{card.hero_subject} with one clear visual idea, not a generic template"
        scene = "a coherent scene that makes the subject feel physically present and visually motivated"
    text_rule = "If any text appears, keep it very short, large, and fully legible."
    if not card.wants_text:
        text_rule = "Avoid text unless it is explicitly necessary."
    checklist = [
        "Main subject is clear in the first second.",
        "Light direction, contact shadows, and screen glow feel coherent.",
        "Materials feel physical, not flat or generic.",
    ]
    if card.wants_text:
        checklist.append("Visible text is short, readable, and not fabricated.")
    if card.aspect_ratio in {"4:5", "9:16"}:
        checklist.append("Composition still reads at mobile thumbnail size.")
    return VisualPlan(
        direction_family=family,
        concept=concept,
        scene=scene,
        composition=f"{direction['composition']}; keep one dominant focal subject and enough negative space for the requested {card.aspect_ratio} crop",
        lighting=direction["light"],
        materials=direction["materials"],
        text_rule=text_rule,
        hard_constraints=card.hard_constraints,
        human_checklist=checklist,
    )


def build_brief(task: str, status: str, references: list[str] | None = None) -> dict[str, Any]:
    references = references or []
    labels = parse_labeled_sections(task)
    use_case = labels.get("use_case") or infer_use_case(task)
    style = labels.get("style") or infer_style(task)
    task_card = parse_task_card(task, use_case, references)
    visual_plan = build_visual_plan(task, task_card)
    brief = {
        "task_id": slugify(task, limit=36),
        "status": status,
        "use_case": use_case,
        "scene": labels.get("scene") or infer_scene(task),
        "subject": labels.get("subject") or task_card.hero_subject,
        "camera": labels.get("camera") or infer_camera(task),
        "lighting": labels.get("lighting") or infer_lighting(task),
        "materials": labels.get("materials") or infer_materials(task),
        "composition": labels.get("composition") or infer_composition(use_case),
        "style": style,
        "preserve": list_from_text(labels.get("preserve")) or infer_preserve(task, references),
        "constraints": list_from_text(labels.get("constraints")),
        "negative": task_card.hard_constraints,
        "references": references,
        "task_card": asdict(task_card),
        "visual_plan": asdict(visual_plan),
    }
    brief["craft_expansion"] = {
        "taste_preset": visual_plan.direction_family,
        "visual_thesis": visual_plan.concept,
        "aspect_ratio": task_card.aspect_ratio,
        "composition": visual_plan.composition,
        "lighting": visual_plan.lighting,
        "materials": visual_plan.materials,
        "craft": visual_plan.scene,
        "text_strategy": visual_plan.text_rule,
        "positive_constraints": [],
        "preset_avoid": [],
        "risk_flags": detect_risk_flags(task, use_case, visual_plan.direction_family),
        "human_checklist": visual_plan.human_checklist,
    }
    return brief


def infer_subject(task: str) -> str:
    return re.sub(r"\s+", " ", task).strip()[:500]


def infer_scene(task: str) -> str:
    if contains_any(task, UI_TERMS):
        return "A focused digital interface context with clear hierarchy and realistic product framing."
    if contains_any(task, PRODUCT_TERMS):
        return "A clean product-focused setup with enough environment to support scale and use."
    if contains_any(task, SCENE_TERMS):
        return "A coherent environment matching the requested setting."
    return "A visually clear scene centered on the requested subject."


def infer_camera(task: str) -> str:
    lower = task.lower()
    if "close" in lower or "特写" in task:
        return "close-up view"
    if "wide" in lower or "全景" in task:
        return "wide composition"
    if "top" in lower or "overhead" in lower or "俯视" in task:
        return "overhead view"
    if contains_any(task, UI_TERMS):
        return "straight-on product mockup view"
    return "natural eye-level framing"


def infer_lighting(task: str) -> str:
    lower = task.lower()
    if "neon" in lower or "霓虹" in task:
        return "controlled neon lighting"
    if "cinematic" in lower or "电影" in task:
        return "cinematic directional lighting"
    if "soft" in lower or "柔和" in task:
        return "soft diffused lighting"
    return "clean natural lighting"


def infer_materials(task: str) -> str:
    lower = task.lower()
    hits = []
    for term in ["glass", "metal", "paper", "fabric", "plastic", "wood", "skin", "玻璃", "金属", "纸", "布料", "木质", "皮肤"]:
        if term in lower or term in task:
            hits.append(term)
    return ", ".join(hits)


def infer_style(task: str) -> str:
    lower = task.lower()
    styles = [
        ("photorealistic", {"photo", "photoreal", "realistic", "真实", "照片"}),
        ("cinematic", {"cinematic", "film", "电影"}),
        ("editorial", {"editorial", "magazine", "杂志"}),
        ("minimal product design", {"minimal", "clean", "极简", "干净"}),
        ("anime illustration", {"anime", "manga", "二次元", "动漫"}),
        ("3D render", {"3d", "render", "渲染"}),
        ("watercolor illustration", {"watercolor", "水彩"}),
    ]
    for label, terms in styles:
        if any(term in lower for term in terms):
            return label
    return "visually polished, coherent, and natural"


def infer_composition(use_case: str) -> str:
    if use_case == "ui mockup":
        return "stable grid, clear hierarchy, readable spacing, no decorative clutter"
    if use_case == "thumbnail":
        return "strong focal point, simple silhouette, readable at small size"
    if use_case == "poster":
        return "strong central subject with enough negative space for optional title placement"
    if use_case == "product image":
        return "product-led composition with clean edges and believable scale"
    return "balanced composition with one clear focal subject"


def infer_preserve(task: str, references: list[str]) -> list[str]:
    preserve = []
    lower = task.lower()
    no_official_mark = any(phrase in lower for phrase in ["no logo", "without logo", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"])
    identity_terms = IDENTITY_TERMS - {"brand", "logo", "品牌"} if no_official_mark else IDENTITY_TERMS
    if contains_any(task, identity_terms):
        preserve.append("preserve identity, silhouette, proportions, and style from references or user description")
    if references:
        preserve.append("use reference files as visual source of truth")
    return preserve


def compress_prompt(text: str, max_words: int = 300) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned: list[str] = []
    seen_lines: set[str] = set()
    for line in lines:
        label, sep, body = line.partition(":")
        if sep and re.match(r"^[A-Za-z][A-Za-z ]{1,24}$", label.strip()):
            phrases = [p.strip() for p in re.split(r",|;", body) if p.strip()]
            deduped = []
            seen_phrases = set()
            for phrase in phrases:
                key = phrase.lower()
                if key not in seen_phrases:
                    deduped.append(phrase)
                    seen_phrases.add(key)
            line = f"{label}: {', '.join(deduped)}" if deduped else f"{label}:"
        key = line.lower()
        if key not in seen_lines:
            cleaned.append(line)
            seen_lines.add(key)
    words = " ".join(cleaned).split()
    if len(words) <= max_words:
        return "\n".join(cleaned)
    clipped = " ".join(words[:max_words]).rstrip(",.;")
    return clipped + "."


def make_codex_prompt(brief: dict[str, Any]) -> str:
    card = brief.get("task_card") or {}
    plan = brief.get("visual_plan") or {}
    text_rule = plan.get("text_rule", "Keep any text short and readable.")
    constraints = plan.get("hard_constraints") or brief.get("negative") or []
    constraints = [
        item for item in constraints
        if not (item == "keep visible text short, large, and legible" and "legible" in text_rule.lower())
    ]
    constraint_sentence = f" Constraints: {'; '.join(constraints)}." if constraints else ""
    prompt = f"""\
Create a {card.get("aspect_ratio", "well-composed")} {card.get("deliverable", brief.get("use_case", "image"))}.
Show {card.get("hero_subject", brief.get("subject"))} through {plan.get("concept", "one clear visual idea")}, with {plan.get("scene", brief.get("scene"))}.
Compose it with {plan.get("composition", brief.get("composition"))}.
Use {plan.get("lighting", brief.get("lighting"))}, with tactile materials such as {plan.get("materials", brief.get("materials") or "believable physical surfaces")} so the image feels spatially real rather than like a flat template.
{text_rule}{constraint_sentence}
"""
    return compress_prompt(prompt, max_words=230)


def make_chatgpt_prompt(brief: dict[str, Any]) -> str:
    card = brief.get("task_card") or {}
    plan = brief.get("visual_plan") or {}
    text_rule = plan.get("text_rule", "")
    constraints = plan.get("hard_constraints") or brief.get("negative") or []
    constraints = [
        item for item in constraints
        if not (item == "keep visible text short, large, and legible" and "legible" in text_rule.lower())
    ]
    constraint_text = f" Avoid: {', '.join(constraints)}." if constraints else ""
    text = (
        f"Make a polished {card.get('aspect_ratio', '')} image for {card.get('deliverable', brief.get('use_case', 'image'))}. "
        f"It should show {card.get('hero_subject', brief.get('subject'))} in {plan.get('scene', brief.get('scene'))}, "
        f"with {plan.get('lighting', brief.get('lighting'))}, tactile materials like {plan.get('materials', brief.get('materials') or 'believable surfaces')}, "
        f"and a composition built around {plan.get('composition', brief.get('composition'))}. "
        f"{text_rule}{constraint_text}"
    )
    return compress_prompt("FINAL_RENDER_HANDOFF\n" + text, max_words=220)


def make_identity_lock(task: str, references: list[str]) -> dict[str, Any] | None:
    lower = task.lower()
    no_official_mark = any(phrase in lower for phrase in ["no logo", "without logo", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"])
    identity_terms = IDENTITY_TERMS - {"brand", "logo", "品牌"} if no_official_mark else IDENTITY_TERMS
    if not contains_any(task, identity_terms):
        return None
    ref_note = "Use provided references as source of truth." if references else "Use only explicit user description; request references for exact preservation."
    return {
        "face_structure": ref_note,
        "eye_structure": ref_note,
        "hair_silhouette": ref_note,
        "body_proportion": ref_note,
        "clothing_anchor": ref_note,
        "pose_language": "Preserve recurring pose language only when specified.",
        "style_anchor": ref_note,
        "forbidden_drift": ["identity drift", "changed proportions", "changed logo or brand marks", "unrequested style change"],
    }


def feasibility_markdown(feasibility: dict[str, Any]) -> str:
    yes = lambda value: "Yes" if value else "No"
    assumptions = feasibility.get("assumptions") or ["None."]
    assumption_text = "\n".join(f"- {item}" for item in assumptions)
    return textwrap.dedent(f"""\
    # Feasibility

    Status: {feasibility["status"]}

    1. Is image generation useful here? {yes(feasibility["image_generation_useful"])}
    2. Is the visual target specific enough? {yes(feasibility["target_specific_enough"])}
    3. Are reference images required? {yes(feasibility["references_required"])}
    4. Is identity/style preservation needed? {yes(feasibility["identity_or_style_preservation_needed"])}
    5. Should Codex image_gen be used directly? {yes(feasibility["use_codex_image_gen_directly"])}
    6. Should ChatGPT Images 2.0 be used for final render? {yes(feasibility["use_chatgpt_images_for_final"])}
    7. What assumptions are being made?
    {assumption_text}
    """)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_to_root(path: Path, root: Path | None = None) -> str:
    root = root or skill_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
