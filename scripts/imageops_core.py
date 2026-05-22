#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
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

TASTE_PRESETS: dict[str, dict[str, Any]] = {
    "premium_saas_poster": {
        "triggers": {"codex", "developer", "saas", "software", "app", "ai agent", "电商", "海报", "开发者", "软件", "工具", "主图"},
        "visual_thesis": "premium SaaS commerce poster staged like a high-end product photograph: abstract AI command center as the hero object, restrained dark interface surfaces, precise developer-tool credibility",
        "composition": "vertical 4:5 poster, large headline zone, centered 3D command-center hero on a black satin pedestal, three short floating feature chips, clean bottom trust strip, generous negative space",
        "lighting": "large softbox key light, cool rim highlights, subtle volumetric screen glow, controlled glass reflections, realistic contact shadows, no harsh neon wash",
        "materials": "smoked glass panels, anodized aluminum bevels, frosted acrylic cards, OLED screen glow, satin black pedestal, micro-scratches, fine dust, crisp shadow gradients",
        "craft": "strong foreground-background separation, readable focal hierarchy, tactile interface cards, visible bevels and edge highlights, micro-detail around the hero object, quiet premium background",
        "text_strategy": "short readable title and 3-4 short feature labels only; no fabricated metrics, ratings, prices, certifications, awards, or user counts",
        "positive": ["clean readable typography", "stable commercial layout", "premium developer-tool visual language", "photorealistic product staging", "short factual copy"],
        "avoid": ["official logo recreation", "invented numbers", "tiny unreadable text", "cluttered dashboard", "flat vector look"],
    },
    "cinematic_realism": {
        "triggers": {"cinematic", "film", "realistic", "photo", "电影", "真实", "照片", "写实"},
        "visual_thesis": "cinematic realistic image with natural atmosphere, tactile materials, and believable imperfections",
        "composition": "single clear focal subject, cinematic framing, layered depth from foreground to background",
        "lighting": "motivated directional light, soft bounce, controlled highlights, consistent shadows",
        "materials": "skin, fabric, glass, metal, dust, moisture, and surface wear rendered with natural texture",
        "craft": "subtle lens depth, environmental detail that supports the subject, no decorative overloading",
        "text_strategy": "avoid text unless explicitly requested",
        "positive": ["photographic realism", "natural material texture", "coherent light direction", "believable depth"],
        "avoid": ["plastic skin", "over-sharpening", "AI gloss", "flat lighting"],
    },
    "luxury_product_photo": {
        "triggers": {"product", "packaging", "bottle", "device", "shoe", "产品", "包装", "瓶", "设备", "手机", "鞋"},
        "visual_thesis": "luxury product photograph with precise geometry, tactile surfaces, and high-end commercial restraint",
        "composition": "hero product centered or slightly off-center, clean horizon, controlled props, safe crop margins",
        "lighting": "large softbox reflection, rim light for silhouette, subtle contact shadow",
        "materials": "accurate product geometry, crisp edges, believable metal, glass, plastic, paper, or fabric textures",
        "craft": "surface detail visible without noise, background quiet enough to make the product expensive",
        "text_strategy": "only include label text if provided; no fake certifications or claims",
        "positive": ["premium product hero", "accurate geometry", "clean edges", "tactile material detail"],
        "avoid": ["warped product shape", "incorrect logo", "busy props", "cheap stock-photo look"],
    },
    "editorial_portrait": {
        "triggers": {"portrait", "headshot", "person", "fashion", "肖像", "头像", "人物", "人像", "时尚"},
        "visual_thesis": "editorial portrait with character presence, skin realism, and controlled fashion-magazine lighting",
        "composition": "face and silhouette as the primary read, clean pose language, uncluttered background",
        "lighting": "large soft key light, gentle fill, catchlights in the eyes, natural skin shadow transitions",
        "materials": "real skin pores, fabric weave, hair strands, subtle makeup or styling when appropriate",
        "craft": "identity-preserving facial structure, natural hands if visible, clear separation from background",
        "text_strategy": "no text unless explicitly requested",
        "positive": ["natural skin texture", "consistent facial structure", "editorial lighting", "clean silhouette"],
        "avoid": ["waxy skin", "distorted face", "extra fingers", "uncanny expression"],
    },
    "clean_ui_mockup": {
        "triggers": {"ui", "dashboard", "mockup", "interface", "website", "app", "界面", "仪表盘", "网页", "应用"},
        "visual_thesis": "clean UI mockup with believable product hierarchy and polished interface materials",
        "composition": "straight-on or slight perspective device/interface hero, clear spacing, organized panels, readable large labels",
        "lighting": "soft studio glow, restrained reflections, subtle depth around cards and controls",
        "materials": "crisp glass panels, matte surfaces, fine borders, realistic shadows, no ornamental clutter",
        "craft": "stable grid, consistent spacing, recognizable controls, no nested-card mess",
        "text_strategy": "use short placeholder labels only; avoid paragraphs and small unreadable text",
        "positive": ["stable grid layout", "clear hierarchy", "readable large labels", "professional UI spacing"],
        "avoid": ["broken layout", "misaligned elements", "fake dense spreadsheet", "unreadable microcopy"],
    },
    "anime_key_visual": {
        "triggers": {"anime", "manga", "key visual", "二次元", "动漫", "漫画", "角色"},
        "visual_thesis": "anime key visual with strong silhouette, expressive pose, and polished production-art finish",
        "composition": "single hero character or group hierarchy, dynamic but readable pose, clean background shape language",
        "lighting": "stylized rim light, controlled color contrast, readable face and costume details",
        "materials": "clean linework, controlled gradients, crisp outfit detail, expressive hair and eye design",
        "craft": "character identity stays stable, costume anchors remain clear, background supports the pose",
        "text_strategy": "no text unless explicitly requested",
        "positive": ["clean linework", "expressive silhouette", "polished anime key art", "controlled color palette"],
        "avoid": ["extra limbs", "muddy linework", "overcrowded effects", "identity drift"],
    },
    "concept_art": {
        "triggers": {"concept art", "worldbuilding", "environment", "scene", "概念图", "设定", "世界观", "场景"},
        "visual_thesis": "concept art with strong atmosphere, readable design language, and production-ready visual logic",
        "composition": "clear scale cues, one main focal structure or subject, layered environment depth",
        "lighting": "atmospheric light with clear source, volumetric depth when useful, coherent color temperature",
        "materials": "environmental surfaces with age, weathering, construction logic, and believable texture",
        "craft": "every detail supports world logic and silhouette readability",
        "text_strategy": "avoid text unless explicitly requested",
        "positive": ["atmospheric depth", "believable environment texture", "strong silhouette", "production concept finish"],
        "avoid": ["random kitbash detail", "muddy focal point", "flat atmosphere", "overcrowded composition"],
    },
}


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


def score_terms(task: str, terms: set[str]) -> int:
    return sum(1 for term in terms if contains_any(task, {term}))


def select_taste_preset(task: str, use_case: str) -> str:
    scores: dict[str, int] = {}
    for name, preset in TASTE_PRESETS.items():
        score = score_terms(task, set(preset["triggers"]))
        if use_case in {"poster", "ui mockup", "product image", "portrait", "character design", "scene design"}:
            if use_case == "poster" and name == "premium_saas_poster":
                score += 3
            elif use_case == "ui mockup" and name == "clean_ui_mockup":
                score += 3
            elif use_case == "product image" and name == "luxury_product_photo":
                score += 3
            elif use_case == "portrait" and name == "editorial_portrait":
                score += 3
            elif use_case == "character design" and name == "anime_key_visual":
                score += 2
            elif use_case == "scene design" and name == "concept_art":
                score += 3
        scores[name] = score
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "cinematic_realism"
    return best


def detect_risk_flags(task: str, use_case: str, preset_name: str) -> list[str]:
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
    if preset_name in {"luxury_product_photo", "clean_ui_mockup"}:
        flags.append("geometry_risk")
    return flags


def craft_expansion(task: str, brief: dict[str, Any]) -> dict[str, Any]:
    preset_name = select_taste_preset(task, brief["use_case"])
    preset = TASTE_PRESETS[preset_name]
    risk_flags = detect_risk_flags(task, brief["use_case"], preset_name)
    aspect_ratio = "4:5" if brief["use_case"] in {"poster", "portrait", "product image"} else "16:9" if brief["use_case"] in {"scene design", "ui mockup"} else "1:1"
    if "9:16" in task or "竖版" in task:
        aspect_ratio = "4:5" if "4:5" in task else "9:16"
    if "1:1" in task or "方图" in task:
        aspect_ratio = "1:1"
    if "16:9" in task or "横版" in task:
        aspect_ratio = "16:9"
    return {
        "taste_preset": preset_name,
        "visual_thesis": preset["visual_thesis"],
        "aspect_ratio": aspect_ratio,
        "composition": preset["composition"],
        "lighting": preset["lighting"],
        "materials": preset["materials"],
        "craft": preset["craft"],
        "text_strategy": preset["text_strategy"],
        "positive_constraints": preset["positive"],
        "preset_avoid": preset["avoid"],
        "risk_flags": risk_flags,
        "human_checklist": human_checklist_for(risk_flags, preset_name),
    }


def human_checklist_for(risk_flags: list[str], preset_name: str) -> list[str]:
    checklist = [
        "Is the main subject immediately clear?",
        "Does the image feel tactile rather than flat or plastic?",
        "Is the lighting direction consistent?",
    ]
    if "text_risk" in risk_flags:
        checklist.append("Is every visible word short, readable, and intentional?")
    if "fake_claims_risk" in risk_flags:
        checklist.append("Did the image avoid invented numbers, ratings, prices, certifications, awards, and user counts?")
    if "layout_precision_risk" in risk_flags:
        checklist.append("Does the layout read cleanly at thumbnail size?")
    if "identity_drift_risk" in risk_flags:
        checklist.append("Does the identity or style anchor still match the reference or description?")
    if preset_name == "luxury_product_photo":
        checklist.append("Is the product geometry clean and believable?")
    return checklist


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


def build_negative(task: str, max_items: int = 9) -> list[str]:
    items: list[str] = []

    def add(values: list[str]) -> None:
        for value in values:
            if value not in items:
                items.append(value)

    if contains_any(task, PERSON_TERMS):
        add(["distorted face", "identity drift", "extra fingers", "broken hands", "duplicate limbs", "bad anatomy", "plastic skin"])
    if contains_any(task, PRODUCT_TERMS):
        add(["warped product geometry", "incorrect logo", "malformed text", "waxy texture", "over-sharpening"])
    if contains_any(task, UI_TERMS):
        add(["unreadable text", "broken layout", "inconsistent spacing", "misaligned interface elements"])
    if contains_any(task, SCENE_TERMS):
        add(["warped perspective", "noisy background", "inconsistent lighting"])
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        add(["invented metrics", "fake certifications", "fake ratings", "fake prices"])
    return items[:max_items]


def list_from_text(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    parts = re.split(r"[,;；\n]+", value)
    return [part.strip() for part in parts if part.strip()]


def build_brief(task: str, status: str, references: list[str] | None = None) -> dict[str, Any]:
    references = references or []
    labels = parse_labeled_sections(task)
    use_case = labels.get("use_case") or infer_use_case(task)
    style = labels.get("style") or infer_style(task)
    brief = {
        "task_id": slugify(task, limit=36),
        "status": status,
        "use_case": use_case,
        "scene": labels.get("scene") or infer_scene(task),
        "subject": labels.get("subject") or infer_subject(task),
        "camera": labels.get("camera") or infer_camera(task),
        "lighting": labels.get("lighting") or infer_lighting(task),
        "materials": labels.get("materials") or infer_materials(task),
        "composition": labels.get("composition") or infer_composition(use_case),
        "style": style,
        "preserve": list_from_text(labels.get("preserve")) or infer_preserve(task, references),
        "constraints": list_from_text(labels.get("constraints")),
        "negative": build_negative(task),
        "references": references,
    }
    brief["craft_expansion"] = craft_expansion(task, brief)
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
        if sep:
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
    craft = brief.get("craft_expansion") or {}
    avoid = list(dict.fromkeys((craft.get("preset_avoid") or []) + (brief.get("negative") or [])))[:8]
    positives = ", ".join((craft.get("positive_constraints") or [])[:5])
    sections = [
        ("Subject", brief.get("subject")),
        ("Visual direction", craft.get("visual_thesis") or brief.get("style")),
        ("Aspect ratio", craft.get("aspect_ratio")),
        ("Composition", craft.get("composition") or brief.get("composition")),
        ("Light and texture", f"{craft.get('lighting') or brief.get('lighting')}; {craft.get('materials') or brief.get('materials')}; {craft.get('craft') or ''}".strip("; ")),
        ("Camera", brief.get("camera")),
        ("Positive constraints", positives),
        ("Text handling", craft.get("text_strategy")),
        ("Preserve", "; ".join(brief.get("preserve") or [])),
        ("Avoid", ", ".join(avoid)),
    ]
    text = "\n".join(f"{label}: {value}" for label, value in sections if value)
    return compress_prompt(text, max_words=300)


def make_chatgpt_prompt(brief: dict[str, Any]) -> str:
    craft = brief.get("craft_expansion") or {}
    preserve = "; ".join(brief.get("preserve") or [])
    constraints = "; ".join(brief.get("constraints") or [])
    negative = ", ".join(list(dict.fromkeys((craft.get("preset_avoid") or []) + (brief.get("negative") or [])))[:10])
    materials = craft.get("materials") or brief.get("materials") or "Use believable surfaces, natural texture, and material behavior appropriate to the subject."
    constraints = constraints or "Do not add unrelated props, logos, text, characters, or style shifts."
    preserve = preserve or "Preserve the requested subject, silhouette, visual hierarchy, and stated style anchors."
    visual_thesis = craft.get("visual_thesis") or brief.get("style")
    composition = craft.get("composition") or brief.get("composition")
    lighting = craft.get("lighting") or brief.get("lighting")
    text_strategy = craft.get("text_strategy") or "Include text only when requested; keep it short and readable."

    text = f"""\
FINAL_RENDER_HANDOFF
Use case: Create a final-quality image for {brief.get("use_case")}.
Visual thesis: {visual_thesis}
Aspect ratio: {craft.get("aspect_ratio") or "auto"}
Scene: {brief.get("scene")} Extend only the environmental details that support the subject and keep the background coherent, readable, and visually quiet where the subject needs attention.
Subject: {brief.get("subject")} Keep the core subject recognizable and stable across the whole image. Do not reinterpret the subject into a different character, product, interface, or visual category.
Camera: {brief.get("camera")}. Use a natural lens feel and avoid distracting perspective tricks unless they are explicitly requested.
Lighting: {lighting}. Keep light direction consistent across the subject, background, shadows, and reflective surfaces.
Materials: {materials}
Composition: {composition}. Keep one clear focal priority, strong silhouette readability, and clean separation between subject and environment.
Style: {brief.get("style")}. Apply the style consistently without stacking unrelated aesthetics.
Craft: {craft.get("craft") or "Use tactile visual details, controlled contrast, and restrained background complexity."}
Preserve: {preserve}
Reference handling: If references are available, match enduring identity, silhouette, proportions, palette, outfit anchors, product geometry, or interface language. Ignore accidental reference artifacts such as compression noise, bad cropping, watermark fragments, or lighting mistakes unless the user explicitly asks to keep them.
Detail level: Add specific visual detail where it clarifies the subject, materials, or environment. Keep micro-detail subordinate to the main read, and avoid decorative clutter that competes with the focal subject.
Text handling: {text_strategy}
Constraints: {constraints}
Avoid: {negative}
"""
    return compress_prompt(text, max_words=700)


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
