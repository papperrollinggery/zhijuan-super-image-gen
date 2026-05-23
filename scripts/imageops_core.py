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

DIRECTOR_CARDS: dict[str, dict[str, Any]] = {
    "ecommerce_product_poster": {
        "tone": "premium technology campaign, physically grounded, expensive but not sterile",
        "visual_thesis": "a premium commercial hero image where the product or concept feels tangible, desirable, and physically grounded",
        "emotional_read": "expensive, confident, precise, grounded",
        "focal_hierarchy": ["hero product or concept", "supporting use context", "quiet commercial background"],
        "layout_grammar": "one dominant hero with headline-safe negative space and clean crop margins",
        "light": "soft directional studio key, cool edge rim, controlled reflections, crisp contact shadows",
        "materials": ["brushed aluminum", "smoked glass", "matte plastic", "subtle dust", "slight wear", "believable reflections"],
        "taste_anchors": ["premium commercial still life", "restrained technology campaign", "physically grounded product photography"],
        "expensive_cues": ["contact shadows", "controlled reflections", "clear silhouette", "quiet background", "specific surface texture"],
        "cheap_cues": ["random floating widgets", "unmotivated neon", "same-gloss surfaces", "fake badges", "flat poster lighting"],
    },
    "developer_tool_campaign": {
        "tone": "credible editorial photo of real work happening, polished but lived-in",
        "visual_thesis": "a believable premium developer-tool campaign image, not a generic SaaS mockup or sci-fi command center",
        "emotional_read": "intelligent, precise, expensive, useful, grounded",
        "focal_hierarchy": ["hero coding artifact", "supporting developer context", "quiet technical atmosphere"],
        "layout_grammar": "clear hero read with enough negative space for a headline, but no invented feature labels",
        "light": "soft studio key from one side, cool monitor glow, crisp contact shadows, natural falloff",
        "materials": ["keyboard texture", "desk surface", "fingerprints", "glass", "cables", "notebooks", "tool marks"],
        "taste_anchors": ["premium developer tooling", "editorial workplace realism", "commercial still life restraint"],
        "expensive_cues": ["real desk evidence", "screen glow interacting with objects", "controlled reflections", "edge rolloff", "quiet background"],
        "cheap_cues": ["floating UI shards", "fake metrics", "generic chrome orb", "unmotivated neon", "flat dashboard collage"],
    },
    "ui_marketing_mockup": {
        "tone": "interface becomes a tangible product object, clean and dimensional",
        "visual_thesis": "a polished interface marketing image where UI hierarchy is readable and spatially credible",
        "emotional_read": "clear, modern, product-led, trustworthy",
        "focal_hierarchy": ["primary interface surface", "secondary supporting panels", "quiet depth layer"],
        "layout_grammar": "interface hero with restrained supporting panels and readable spacing",
        "light": "studio key light plus interface glow, controlled reflections, visible bevels",
        "materials": ["glass cards", "edge-lit panels", "thin metal frames", "soft shadows", "fine borders"],
        "taste_anchors": ["clean product hierarchy", "premium UI mockup", "disciplined spacing"],
        "expensive_cues": ["stable grid", "consistent spacing", "subtle shadow depth", "few readable labels"],
        "cheap_cues": ["dense fake dashboard clutter", "tiny unreadable text", "misaligned widgets", "nested card mess"],
    },
    "graphic_poster_minimal": {
        "tone": "sharp graphic campaign poster, minimal but not empty",
        "visual_thesis": "a sharp graphic poster with one symbolic image and disciplined whitespace",
        "emotional_read": "bold, restrained, clear, memorable",
        "focal_hierarchy": ["single symbolic image", "headline-safe area", "supporting negative space"],
        "layout_grammar": "large typography-safe area, one visual idea, minimal supporting copy",
        "light": "flat graphic clarity with subtle dimensional highlight only where useful",
        "materials": ["clean vector-like surfaces", "simple dimensional forms", "crisp edges"],
        "taste_anchors": ["graphic campaign poster", "disciplined whitespace", "strong contrast"],
        "expensive_cues": ["one strong idea", "intentional emptiness", "crisp edge control"],
        "cheap_cues": ["clip-art symbols", "busy decoration", "generic gradient blob", "too many slogans"],
    },
    "fashion_editorial_cover": {
        "tone": "tasteful fashion magazine cover, confident, polished, sunlit, non-explicit",
        "visual_thesis": "an adult resort editorial cover that feels confident and fashion-led, not pin-up or exploitative",
        "emotional_read": "sunlit, elegant, relaxed, confident, tasteful",
        "focal_hierarchy": ["adult fashion model", "coastal atmosphere", "cover-layout negative space"],
        "layout_grammar": "model as cover hero, masthead-safe top area, clean side space for short cover lines",
        "light": "golden coastal sunlight with soft fill, clean catchlights, natural skin shadow transitions",
        "materials": ["swimwear fabric texture", "wind-shaped hair", "sunscreen sheen", "sand", "water reflection", "magazine paper grain"],
        "taste_anchors": ["fashion editorial cover", "adult resort photography", "tasteful commercial portrait"],
        "expensive_cues": ["natural skin shadow transitions", "wind and fabric movement", "clean cover crop", "specific coastal light"],
        "cheap_cues": ["pin-up posing", "plastic skin", "over-retouched gloss", "fake cover clutter", "sensational text"],
    },
    "cinematic_portrait": {
        "tone": "cinematic portrait with character presence and believable atmosphere",
        "visual_thesis": "a character-led cinematic portrait with readable identity, motivated light, and tactile world detail",
        "emotional_read": "present, atmospheric, human, cinematic",
        "focal_hierarchy": ["face or silhouette", "pose language", "environmental depth"],
        "layout_grammar": "one readable focal subject with layered foreground, middle ground, and background",
        "light": "motivated directional light, soft bounce, rim separation, consistent shadows",
        "materials": ["skin texture", "fabric weave", "hair detail", "environmental surfaces", "dust or moisture where appropriate"],
        "taste_anchors": ["cinematic portrait", "editorial realism", "production still"],
        "expensive_cues": ["natural catchlights", "consistent shadow direction", "specific fabric texture", "controlled background detail"],
        "cheap_cues": ["waxy skin", "over-sharpened eyes", "random bokeh", "unmotivated colored rim light"],
    },
}
DIRECTION_CARDS = DIRECTOR_CARDS


@dataclass
class TaskCard:
    use_case: str
    deliverable: str
    user_intent: str
    hero_subject: str
    aspect_ratio: str
    wants_text: bool
    text_mode: str
    must_show: list[str]
    must_not_show: list[str]
    hard_constraints: list[str]
    factual_risk: list[str]
    references: list[str]
    render_count: int
    auto_regen: bool


@dataclass
class ArtDirection:
    director_id: str
    visual_thesis: str
    emotional_read: str
    focal_hierarchy: list[str]
    layout_grammar: str
    lighting_motivation: str
    material_specificity: list[str]
    taste_anchors: list[str]
    expensive_cues: list[str]
    cheap_cues: list[str]
    text_policy: str


@dataclass
class VisualPlan:
    direction_family: str
    concept: str
    scene: str
    scene_concept: str
    shot_family: str
    spatial_layers: dict[str, str]
    composition: str
    lighting: str
    materials: str
    text_rule: str
    text_strategy: str
    hard_constraints: list[str]
    constraint_pack: list[str]
    reference_anchors: dict[str, list[str]]
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
        ("magazine cover", {"magazine cover", "fashion cover", "editorial cover", "杂志封面"}),
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
    if contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"magazine cover", "poster", "ui mockup", "thumbnail"}:
        flags.append("text_risk")
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        flags.append("fake_claims_risk")
    if contains_any(task, identity_terms):
        flags.append("identity_drift_risk")
    if use_case in {"ui mockup", "poster"}:
        flags.append("layout_precision_risk")
    if direction_family in {"ecommerce_product_poster", "ui_marketing_mockup"}:
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
    if contains_any(task, NO_FAKE_CLAIMS_TERMS) or any(phrase in lower for phrase in ["不要虚构", "no fake", "do not invent"]):
        add(["do not invent numbers, ratings, prices, awards, certifications, or user counts"])
    if contains_any(task, {"swimwear", "swimsuit", "bikini", "泳装", "泳衣"}):
        add(["adult model only", "tasteful non-explicit swimwear editorial, no nudity"])
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
    if use_case in {"magazine cover", "poster", "portrait", "product image"}:
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
    if contains_any(task, {"swimwear", "swimsuit", "bikini", "泳装", "泳衣"}) and contains_any(task, {"magazine", "cover", "杂志", "封面"}):
        return "an adult fashion model in tasteful swimwear for a summer magazine cover"
    return first[:180] or text[:180]


def infer_text_mode(task: str, use_case: str, wants_text: bool) -> str:
    if not wants_text:
        return "avoid_text"
    if contains_any(task, {"literal text", "exact text", "标题：", "文案：", "copy:"}):
        return "literal_copy"
    if use_case in {"magazine cover", "poster", "thumbnail"}:
        return "headline_safe_only"
    return "short_readable_labels"


def extract_task_terms(task: str) -> tuple[list[str], list[str]]:
    must_show: list[str] = []
    must_not_show: list[str] = []

    def add_unique(target: list[str], values: list[str]) -> None:
        for value in values:
            if value and value not in target:
                target.append(value)

    if "Codex" in task or "codex" in task.lower():
        add_unique(must_show, ["Codex as an AI coding agent", "credible software work context"])
    if contains_any(task, {"swimwear", "swimsuit", "bikini", "泳装", "泳衣"}):
        add_unique(must_show, ["adult fashion model", "tasteful swimwear editorial"])
        add_unique(must_not_show, ["nudity", "pin-up posing", "underage subject"])
    if contains_any(task, {"高级", "premium", "luxury", "质感"}):
        add_unique(must_show, ["premium finish", "specific tactile materials", "motivated light"])
    if contains_any(task, {"不要 logo", "不要logo", "no logo", "without logo"}):
        add_unique(must_not_show, ["official logos", "brand marks"])
    if "不要虚构" in task or "do not invent" in task.lower():
        add_unique(must_not_show, ["fabricated numbers", "fake claims"])
    return must_show[:8], must_not_show[:8]


def parse_task_card(task: str, use_case: str, references: list[str]) -> TaskCard:
    deliverable = {
        "magazine cover": "fashion magazine cover",
        "poster": "e-commerce hero poster",
        "ui mockup": "polished UI mockup image",
        "product image": "premium product image",
        "portrait": "editorial portrait",
        "scene design": "cinematic scene image",
        "thumbnail": "thumbnail image",
    }.get(use_case, "image")
    wants_text = contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"magazine cover", "poster", "thumbnail"}
    text_mode = infer_text_mode(task, use_case, wants_text)
    must_show, must_not_show = extract_task_terms(task)
    hard_constraints = build_hard_constraints(task)
    factual_risk = []
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        factual_risk.extend(["invented_metrics", "fake_badges", "fake_claims"])
    return TaskCard(
        use_case=use_case,
        deliverable=deliverable,
        user_intent=re.sub(r"\s+", " ", task).strip(),
        hero_subject=strip_constraints_from_subject(task),
        aspect_ratio=infer_aspect_ratio(task, use_case),
        wants_text=wants_text,
        text_mode=text_mode,
        must_show=must_show,
        must_not_show=must_not_show,
        hard_constraints=hard_constraints,
        factual_risk=factual_risk,
        references=references,
        render_count=1,
        auto_regen=False,
    )


def choose_direction_family(task: str, card: TaskCard) -> str:
    if card.use_case == "magazine cover" or contains_any(task, {"fashion", "editorial", "swimwear", "泳装", "时尚", "模特"}):
        return "fashion_editorial_cover"
    if card.use_case == "poster" and contains_any(task, {"codex", "developer", "ai coding agent", "软件", "开发者", "工具"}):
        return "developer_tool_campaign"
    if card.use_case == "poster":
        return "ecommerce_product_poster"
    if card.use_case == "ui mockup":
        return "ui_marketing_mockup"
    if card.use_case in {"product image", "thumbnail"}:
        return "ecommerce_product_poster"
    if contains_any(task, {"minimal", "极简"}):
        return "graphic_poster_minimal"
    return "cinematic_portrait"


def build_art_direction(task: str, card: TaskCard) -> ArtDirection:
    family = choose_direction_family(task, card)
    direction = DIRECTOR_CARDS[family]
    visual_thesis = direction["visual_thesis"]
    if "Codex" in task or "codex" in task.lower():
        visual_thesis = "a believable premium developer-tool campaign image that introduces Codex as an AI coding agent through real software work, not a generic SaaS template"
    elif family == "fashion_editorial_cover":
        visual_thesis = "an adult resort editorial magazine cover that feels confident, sunlit, fashion-led, and non-explicit"
    return ArtDirection(
        director_id=family,
        visual_thesis=visual_thesis,
        emotional_read=direction["emotional_read"],
        focal_hierarchy=list(direction["focal_hierarchy"]),
        layout_grammar=direction["layout_grammar"],
        lighting_motivation=direction["light"],
        material_specificity=list(direction["materials"]),
        taste_anchors=list(direction["taste_anchors"]),
        expensive_cues=list(direction["expensive_cues"]),
        cheap_cues=list(direction["cheap_cues"]),
        text_policy="leave text-safe space but do not invent copy unless literal copy is provided",
    )


def build_visual_plan(task: str, card: TaskCard, art_direction: ArtDirection | None = None) -> VisualPlan:
    art = art_direction or build_art_direction(task, card)
    family = art.director_id
    if "Codex" in task or "codex" in task.lower():
        concept = art.visual_thesis
        scene = "a layered developer workspace or studio productized coding environment with one dominant coding artifact in action, subtle evidence of reasoning and iteration, and a calm technical background"
    elif family == "fashion_editorial_cover":
        concept = art.visual_thesis
        scene = "a summer coastline with ocean air, warm sand, natural movement, and clean cover-layout negative space"
    elif card.use_case == "product image":
        concept = art.visual_thesis
        scene = "a controlled commercial setup with enough environment to show scale and use"
    elif card.use_case == "ui mockup":
        concept = art.visual_thesis
        scene = "a focused interface scene with spatial depth, readable primary panels, and restrained supporting details"
    else:
        concept = art.visual_thesis
        scene = "a coherent scene that makes the subject feel physically present and visually motivated"
    if card.text_mode == "avoid_text":
        text_rule = "Avoid text unless it is explicitly necessary."
    elif card.text_mode == "headline_safe_only":
        text_rule = "Leave headline-safe negative space, but do not invent cover lines, slogans, metrics, or feature labels."
    else:
        text_rule = "If any text appears, keep it very short, large, and fully legible."
    spatial_layers = {
        "foreground": "one subtle depth cue that supports the subject",
        "midground": card.hero_subject,
        "background": "quiet atmosphere that adds depth without clutter",
    }
    checklist = [
        "Main subject is clear in the first second.",
        "Light direction, contact shadows, and screen glow feel coherent.",
        "Materials feel physical, not flat or generic.",
        "The image avoids cheap cues such as " + ", ".join(art.cheap_cues[:3]) + ".",
    ]
    if card.wants_text:
        checklist.append("Visible text is short, readable, and not fabricated.")
    if card.aspect_ratio in {"4:5", "9:16"}:
        checklist.append("Composition still reads at mobile thumbnail size.")
    return VisualPlan(
        direction_family=family,
        concept=concept,
        scene=scene,
        scene_concept=scene,
        shot_family=art.taste_anchors[0],
        spatial_layers=spatial_layers,
        composition=f"{art.layout_grammar}; keep one dominant focal subject and enough negative space for the requested {card.aspect_ratio} crop",
        lighting=art.lighting_motivation,
        materials=", ".join(art.material_specificity),
        text_rule=text_rule,
        text_strategy=text_rule,
        hard_constraints=card.hard_constraints,
        constraint_pack=card.hard_constraints,
        reference_anchors={"identity": [], "palette": [], "lighting": [], "composition": [], "material": [], "forbidden_drift": []},
        human_checklist=checklist,
    )


def build_brief(task: str, status: str, references: list[str] | None = None) -> dict[str, Any]:
    references = references or []
    labels = parse_labeled_sections(task)
    use_case = labels.get("use_case") or infer_use_case(task)
    style = labels.get("style") or infer_style(task)
    task_card = parse_task_card(task, use_case, references)
    art_direction = build_art_direction(task, task_card)
    visual_plan = build_visual_plan(task, task_card, art_direction)
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
        "art_direction": asdict(art_direction),
        "visual_plan": asdict(visual_plan),
    }
    brief["craft_expansion"] = {
        "taste_preset": art_direction.director_id,
        "visual_thesis": art_direction.visual_thesis,
        "aspect_ratio": task_card.aspect_ratio,
        "composition": visual_plan.composition,
        "lighting": visual_plan.lighting,
        "materials": visual_plan.materials,
        "craft": visual_plan.scene,
        "text_strategy": visual_plan.text_rule,
        "positive_constraints": [],
        "preset_avoid": [],
        "risk_flags": detect_risk_flags(task, use_case, art_direction.director_id),
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
    art = brief.get("art_direction") or {}
    plan = brief.get("visual_plan") or {}
    text_rule = plan.get("text_rule", "Keep any text short and readable.")
    constraints = plan.get("hard_constraints") or brief.get("negative") or []
    constraints = [
        item for item in constraints
        if not (item == "keep visible text short, large, and legible" and "legible" in text_rule.lower())
    ]
    text_line = f"Text: {text_rule}" if text_rule else ""
    constraint_line = f"Constraints: {'; '.join(constraints)}" if constraints else ""
    preserve = brief.get("preserve") or []
    preserve_line = f"Preserve: {'; '.join(preserve)}" if preserve else ""
    focal = art.get("focal_hierarchy") or []
    second_read = ", ".join(focal[1:]) if len(focal) > 1 else "supporting scene evidence"
    material_specificity = art.get("material_specificity") or plan.get("materials") or brief.get("materials") or ["believable physical surfaces"]
    if isinstance(material_specificity, str):
        material_text = material_specificity
    else:
        material_text = ", ".join(material_specificity)
    cheap_cues = art.get("cheap_cues") or []
    cheap_text = ", ".join(cheap_cues[:4]) if cheap_cues else "generic AI gloss"
    prompt = f"""\
Create a {card.get("aspect_ratio", "well-composed")} {card.get("deliverable", brief.get("use_case", "image"))}.
Build the image around {art.get("visual_thesis") or plan.get("concept") or "one clear visual idea"}.
Show {plan.get("scene_concept") or plan.get("scene") or brief.get("scene")}, with {card.get("hero_subject", brief.get("subject"))} as the first read and {second_read} as the second read.
Use {art.get("lighting_motivation") or plan.get("lighting") or brief.get("lighting")}. Materials should feel specific and tactile: {material_text}.
Keep the composition {art.get("layout_grammar") or plan.get("composition") or brief.get("composition")}.
The image should feel {art.get("emotional_read") or brief.get("style")}, not {cheap_text}.
{text_line}
{preserve_line}
{constraint_line}
"""
    return compress_prompt(prompt, max_words=260)


def make_chatgpt_prompt(brief: dict[str, Any]) -> str:
    card = brief.get("task_card") or {}
    art = brief.get("art_direction") or {}
    plan = brief.get("visual_plan") or {}
    text_rule = plan.get("text_rule", "")
    constraints = plan.get("hard_constraints") or brief.get("negative") or []
    constraints = [
        item for item in constraints
        if not (item == "keep visible text short, large, and legible" and "legible" in text_rule.lower())
    ]
    text = f"""\
FINAL_RENDER_HANDOFF
Use case: {card.get("aspect_ratio", "")} {card.get("deliverable", brief.get("use_case", "image"))}.
Visual thesis: {art.get("visual_thesis") or plan.get("concept") or brief.get("style")}.
Scene: {plan.get("scene_concept") or plan.get("scene") or brief.get("scene")}.
Subject: {card.get("hero_subject", brief.get("subject"))}.
Lighting: {art.get("lighting_motivation") or plan.get("lighting") or brief.get("lighting")}.
Materials: {", ".join(art.get("material_specificity") or []) or plan.get("materials") or brief.get("materials") or "believable tactile surfaces"}.
Composition: {art.get("layout_grammar") or plan.get("composition") or brief.get("composition")}. Focal hierarchy: {", ".join(art.get("focal_hierarchy") or [])}.
Taste anchors: {", ".join(art.get("taste_anchors") or [])}.
Text: {text_rule}
Avoid cheap cues: {", ".join((art.get("cheap_cues") or [])[:5])}.
Constraints: {"; ".join(constraints)}
"""
    return compress_prompt(text, max_words=360)


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
