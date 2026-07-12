#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import os
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


VISUAL_TRIGGERS = {
    "image", "generate image", "poster", "portrait", "storyboard", "concept art",
    "ui mockup", "mockup", "character design", "scene design", "thumbnail",
    "banner", "style reference", "visual direction", "product shot", "render",
    "logo", "illustration", "生图", "图片", "海报", "头像", "分镜", "概念图",
    "角色", "场景", "缩略图", "横幅", "视觉", "风格参考", "产品图",
    "信息图", "解释图", "视觉流程图", "流程图", "人物肖像", "肖像", "写真",
    "概念海报",
    "imagen", "cartel", "póster", "poster español", "retrato", "ilustración",
    "画像", "ポスター", "写真", "イラスト", "生成して", "描いて",
}

PRESERVATION_TERMS = {
    "same person", "same character", "recurring", "mascot", "identity",
    "consistent", "preserve", "reference", "style reference", "同一个",
    "角色一致", "身份", "保持", "参考图", "一致", "风格参考",
}

EXACT_REFERENCE_TERMS = {
    "same person", "same character", "real person", "celebrity",
    "reference image", "exact", "same product", "exact product",
    "same logo", "exact logo", "recreate logo", "同一个人", "真人",
    "明星", "参考图", "一模一样", "同款产品", "一模一样的产品",
    "复刻产品", "复刻 logo", "复刻logo", "完全一致", "同一个角色",
    "同一个吉祥物",
}

BRAND_MENTION_TERMS = {
    "brand", "logo", "product", "品牌", "logo", "产品",
}

IDENTITY_TERMS = PRESERVATION_TERMS | EXACT_REFERENCE_TERMS
REFERENCE_REQUIRED_TERMS = EXACT_REFERENCE_TERMS

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
NO_OFFICIAL_MARK_TERMS = ["no logo", "without logo", "no official logo", "no brand marks", "do not use official", "不要使用官方", "不使用官方", "不要官方", "不要 logo", "不要logo"]

REFERENCE_SOURCE_TERMS = {
    "attachment", "attached image", "attached photo", "attached file",
    "uploaded image", "uploaded photo", "provided image", "provided photo",
    "supplied image", "supplied photo", "source image", "source photo",
    "附件", "附件里", "附图", "上传图片", "上传照片", "提供的图片", "提供的照片", "参考附件",
}

REFERENCE_PRESERVATION_TERMS = {
    "keep", "unchanged", "do not change", "match", "matching", "same as",
    "严格保持", "保持不变", "不得改变", "完全沿用", "一致",
}

FIDELITY_TERMS = {
    "preserve identity", "preserve facial identity", "preserve face", "face fidelity",
    "product fidelity", "brand fidelity", "preserve product", "preserve brand",
    "keep the face", "keep her face", "keep his face", "keep its proportions",
    "保留人物", "保持人物", "保持人脸", "保持产品", "保持品牌", "保真", "还原",
}

CODEX_PROMPT_MAX_LEXICAL_UNITS = 190
# Backward-compatible import name for existing callers; the value is lexical units, not whitespace words.
CODEX_PROMPT_MAX_WORDS = CODEX_PROMPT_MAX_LEXICAL_UNITS
EXPLICIT_CONSTRAINT_WORD_LIMIT = 70
RUNTIME_VERSION = "2.1.0"
SCHEMA_VERSION = "2.1.0"

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
    literal_text: list[str]
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
class VisualConcept:
    concept_id: str
    visual_solution: str
    why_it_fits: str
    first_read: str
    second_read: str
    text_risk: str
    reference_risk: str
    thumbnail_readability: str
    score: int
    selected: bool = False


@dataclass
class VisualPlan:
    direction_family: str
    visual_type: str
    concept: str
    scene: str
    scene_concept: str
    visual_breakdown: dict[str, Any]
    shot_family: str
    spatial_layers: dict[str, str]
    composition: str
    lighting: str
    materials: str
    color_system: list[str]
    style_tags: list[str]
    quality_target: str
    generation_intent: str
    text_rule: str
    text_strategy: str
    hard_constraints: list[str]
    constraint_pack: list[str]
    prompt_layers: dict[str, str]
    concept_candidates: list[dict[str, Any]]
    selected_concept_id: str
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


def count_prompt_words(text: str) -> int:
    """Count lexical units, treating each CJK character as one budget unit."""
    return len(
        re.findall(
            r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*|[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]",
            text,
        )
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_hashes(run_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(run_dir).as_posix(): sha256_file(path)
        for path in sorted(run_dir.rglob("*"))
        if path.is_file() and path.name != "metadata.json"
    }


def canonical_input_sha256(request: dict[str, Any]) -> str:
    payload = {
        "task": request.get("task"),
        "references": request.get("references") or [],
        "reference_urls": request.get("reference_urls") or [],
        "invalid_references": request.get("invalid_references") or [],
        "source_context": request.get("source_context"),
        "blocked": request.get("blocked") is True,
    }
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def requests_reference_preservation(task: str) -> bool:
    return contains_any(task, REFERENCE_SOURCE_TERMS) and (
        contains_any(task, PRESERVATION_TERMS)
        or contains_any(task, REFERENCE_PRESERVATION_TERMS)
        or contains_any(task, FIDELITY_TERMS)
    )


def has_no_official_mark(task: str) -> bool:
    lower = task.lower()
    return any(phrase in lower for phrase in NO_OFFICIAL_MARK_TERMS) or bool(
        re.search(r"(?:不要|不使用|禁止|避免).{0,8}(?:官方|logo|品牌标志|品牌视觉)", task)
    )


def infer_use_case(task: str) -> str:
    lower = task.lower()
    cases = [
        ("infographic", {"infographic", "diagram", "comparison chart", "flowchart", "explainer", "信息图", "解释图", "视觉流程图", "流程图", "对比图", "架构图"}),
        ("magazine cover", {"magazine cover", "fashion cover", "editorial cover", "杂志封面"}),
        ("storyboard", {"storyboard", "分镜"}),
        ("thumbnail", {"thumbnail", "缩略图", "封面"}),
        ("poster", {"poster", "海报"}),
        ("ui mockup", {"ui mockup", "dashboard", "app", "website", "界面", "网页", "应用"}),
        ("portrait", {"portrait", "headshot", "avatar", "肖像", "头像", "人物肖像", "写真"}),
        ("character design", {"character", "mascot", "角色", "吉祥物"}),
        ("product image", {"product", "packaging", "产品", "包装"}),
        ("scene design", {"scene", "environment", "concept art", "场景", "环境", "概念图", "夜景"}),
    ]
    for label, terms in cases:
        if any(term in lower for term in terms):
            return label
    return "image generation"


def detect_risk_flags(task: str, use_case: str, direction_family: str) -> list[str]:
    flags = []
    exact_reference = contains_any(task, EXACT_REFERENCE_TERMS) or requests_reference_preservation(task)
    if contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"infographic", "magazine cover", "poster", "ui mockup", "thumbnail"}:
        flags.append("text_risk")
    if contains_any(task, NO_FAKE_CLAIMS_TERMS):
        flags.append("fake_claims_risk")
    if exact_reference or (contains_any(task, PRESERVATION_TERMS) and not has_no_official_mark(task)):
        flags.append("identity_drift_risk")
    if use_case in {"infographic", "ui mockup", "poster"}:
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


def classify_references(references: list[str] | None = None) -> dict[str, list[str]]:
    local_files: list[str] = []
    urls: list[str] = []
    invalid: list[str] = []
    for reference in references or []:
        value = str(reference).strip()
        if not value:
            invalid.append(value)
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            urls.append(value)
            continue
        path = Path(value).expanduser()
        if path.is_file() and os.access(path, os.R_OK) and local_image_format(path) is not None:
            local_files.append(str(path.resolve()))
        else:
            invalid.append(value)
    return {
        "local_files": local_files,
        "urls": urls,
        # Only decoded-local candidates can be passed to Codex image_gen or
        # serve as identity/style source of truth. Remote URLs are recorded
        # separately until a later fetch/decode/localization stage exists.
        "valid": local_files,
        "invalid": invalid,
    }


def local_image_format(path: Path) -> str | None:
    """Recognize supported local image containers by their file signature."""
    try:
        with path.open("rb") as handle:
            header = handle.read(12)
    except OSError:
        return None
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    return None


def analyze_feasibility(
    task: str,
    references: list[str] | None = None,
    *,
    blocked: bool = False,
) -> dict[str, Any]:
    reference_info = classify_references(references)
    valid_references = reference_info["valid"]
    lower = task.lower()
    use_case = infer_use_case(task)
    explicit_visual_signal = contains_any(task, VISUAL_TRIGGERS) or use_case != "image generation"
    unknown_script_present = any(
        char.isalpha()
        and ord(char) > 127
        and not (
            "\u3400" <= char <= "\u9fff"
            or "\u3040" <= char <= "\u30ff"
            or "\uac00" <= char <= "\ud7af"
            or "\u00c0" <= char <= "\u024f"
        )
        for char in task
    )
    potential_unknown_language_visual = bool(
        re.search(r"\b(?:1:1|4:5|9:16|16:9)\b", task)
        or re.search(r"[\u3040-\u30ff]", task)
        or re.search(r"\b(?:imagen|cartel|p[oó]ster|retrato|ilustraci[oó]n)\b", lower)
        or unknown_script_present
    )
    image_useful = explicit_visual_signal
    compact = re.sub(r"\s+", "", task)
    vague = len(compact) < 8 or lower.strip() in {"make image", "generate image", "生图", "画图"}
    no_official_mark = has_no_official_mark(task)
    exact_preservation = (
        contains_any(task, EXACT_REFERENCE_TERMS)
        or (contains_any(task, FIDELITY_TERMS) and not no_official_mark)
        or requests_reference_preservation(task)
    )
    preservation_requested = contains_any(task, PRESERVATION_TERMS) or requests_reference_preservation(task)
    brand_or_product_mentioned = contains_any(task, BRAND_MENTION_TERMS)
    identity_needed = exact_preservation or (preservation_requested and not no_official_mark)
    brand_or_product_exact = brand_or_product_mentioned and exact_preservation and not no_official_mark
    references_required = (exact_preservation or brand_or_product_exact) and not valid_references

    explicit_constraint_words = count_prompt_words("\n".join(build_hard_constraints(task, max_items=0)))
    constraint_budget_exceeded = explicit_constraint_words > EXPLICIT_CONSTRAINT_WORD_LIMIT

    if blocked:
        status = "BLOCKED"
    elif not image_useful and potential_unknown_language_visual:
        status = "NEEDS_USER_INPUT"
    elif not image_useful:
        status = "NOT_USEFUL"
    elif references_required:
        status = "NEEDS_REFERENCES"
    elif constraint_budget_exceeded:
        status = "NEEDS_USER_INPUT"
    elif vague:
        status = "NEEDS_USER_INPUT"
    elif len(task) < 80:
        status = "PROCEED_WITH_ASSUMPTIONS"
    else:
        status = "PROCEED"

    assumptions = []
    if status == "PROCEED_WITH_ASSUMPTIONS":
        assumptions.append("Visual target is usable but underspecified; fill only obvious scene, style, and composition gaps.")
    if identity_needed and valid_references:
        assumptions.append("Use provided references as identity or style source of truth.")
    if not valid_references:
        assumptions.append("No decoded local reference images were provided.")
    if reference_info["urls"]:
        assumptions.append(
            "Remote reference URLs passed format-level validation only; network content was not fetched or decoded, so they do not satisfy identity or style reference requirements."
        )
    if reference_info["invalid"]:
        assumptions.append("Ignore missing, unreadable, empty, or unrecognized local image paths until valid PNG, JPEG, GIF, or WebP files are provided.")
    if constraint_budget_exceeded:
        assumptions.append(
            f"Explicit constraints use {explicit_constraint_words} words; reduce or prioritize them to fit the {EXPLICIT_CONSTRAINT_WORD_LIMIT}-word constraint budget."
        )

    result = {
        "status": status,
        "image_generation_useful": image_useful,
        "target_specific_enough": not vague,
        "references_required": references_required,
        "identity_or_style_preservation_needed": identity_needed,
        "use_codex_image_gen_directly": status in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"},
        "use_chatgpt_images_for_final": False,
        "local_references": reference_info["local_files"],
        "reference_urls": reference_info["urls"],
        "invalid_references": reference_info["invalid"],
        "constraint_budget_exceeded": constraint_budget_exceeded,
        "constraint_word_count": explicit_constraint_words,
        "constraint_word_limit": EXPLICIT_CONSTRAINT_WORD_LIMIT,
        "assumptions": assumptions,
    }
    if status in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS"}:
        prompt = make_codex_prompt(build_brief(task, status, valid_references))
        prompt_units = count_prompt_words(prompt)
        if prompt_units > CODEX_PROMPT_MAX_LEXICAL_UNITS:
            result["status"] = "NEEDS_USER_INPUT"
            result["use_codex_image_gen_directly"] = False
            result["assumptions"].append(
                f"The load-bearing prompt uses {prompt_units} lexical units after compacting director language; prioritize copy, must-show details, or constraints to fit the {CODEX_PROMPT_MAX_LEXICAL_UNITS}-unit limit."
            )
    return result


def build_hard_constraints(task: str, max_items: int = 4) -> list[str]:
    explicit: list[str] = []
    derived: list[str] = []

    def add(target: list[str], values: list[str]) -> None:
        for value in values:
            if value not in explicit and value not in derived:
                target.append(value)

    lower = task.lower()
    if contains_any(task, {"swimwear", "swimsuit", "bikini", "泳装", "泳衣"}):
        add(derived, ["adult model only", "tasteful non-explicit swimwear editorial, no nudity"])
    directive_pattern = re.compile(
        r"(?:^|[.。;；,，\n])\s*(?P<label>constraints?|约束|avoid|避免)\s*[:：]\s*",
        flags=re.I,
    )
    directive_matches = list(directive_pattern.finditer(task))
    for index, match in enumerate(directive_matches):
        next_label = directive_matches[index + 1].start() if index + 1 < len(directive_matches) else len(task)
        newline = task.find("\n", match.end(), next_label)
        end = newline if newline >= 0 else next_label
        value = task[match.end():end].strip(" \t.;。")
        label = match.group("label").lower()
        prefix = "avoid" if label in {"avoid", "避免"} else "user constraint"
        add(explicit, [f"{prefix}: {item}" for item in list_from_text(value)])
    if any(phrase in lower for phrase in NO_OFFICIAL_MARK_TERMS):
        add(derived, ["do not use official logos or recreate official brand marks"])
    if contains_any(task, NO_FAKE_CLAIMS_TERMS) or any(phrase in lower for phrase in ["不要虚构", "no fake", "do not invent"]):
        add(derived, ["do not invent numbers, ratings, prices, awards, certifications, or user counts"])
    if contains_any(task, TEXT_HEAVY_TERMS):
        add(derived, ["keep visible text short, large, and legible"])
    if contains_any(task, {"screenshot", "真实截图", "ui screenshot", "官方界面"}):
        add(derived, ["do not fake an official product screenshot"])
    return explicit + derived[:max_items]


def build_negative(task: str, max_items: int = 4) -> list[str]:
    return build_hard_constraints(task, max_items=max_items)


def infer_visual_type(task: str, use_case: str, direction_family: str) -> str:
    if use_case == "infographic":
        return "infographic"
    if direction_family == "fashion_editorial_cover" or use_case == "portrait":
        return "portrait"
    if use_case in {"storyboard", "character design"}:
        return "illustration"
    if use_case == "product image" or direction_family == "ecommerce_product_poster":
        return "product"
    if use_case == "ui mockup" or direction_family == "ui_marketing_mockup":
        return "ui"
    if use_case in {"poster", "thumbnail"} or direction_family == "graphic_poster_minimal":
        return "poster"
    if contains_any(task, {"3d", "render", "渲染"}):
        return "3d"
    if contains_any(task, {"illustration", "anime", "manga", "插画", "二次元", "动漫"}):
        return "illustration"
    if contains_any(task, {"photo", "photoreal", "realistic", "真实", "照片"}):
        return "photography"
    return "photography"


def style_tags_for(visual_type: str, art: ArtDirection) -> list[str]:
    base = {
        "infographic": ["infographic", "visual hierarchy", "large labels", "clear connectors"],
        "portrait": ["editorial portrait", "skin texture", "motivated light", "clean crop"],
        "product": ["product hero", "tactile material", "contact shadow", "clean hierarchy"],
        "poster": ["graphic poster", "negative space", "strong focal", "controlled type"],
        "ui": ["ui mockup", "readable grid", "glass depth", "product led"],
        "illustration": ["illustration", "clear silhouette", "controlled palette", "layered scene"],
        "3d": ["3d render", "physical scale", "surface finish", "soft shadows"],
        "photography": ["photoreal", "natural lens", "motivated light", "physical detail"],
    }.get(visual_type, ["visual direction", "clear subject", "motivated light", "controlled palette"])
    anchors = [item for item in art.taste_anchors if item not in base]
    return (base + anchors)[:4]


def infer_color_system(task: str, visual_type: str, art: ArtDirection) -> list[str]:
    lower = task.lower()
    colors: list[str] = []
    candidates = [
        ("black", {"black", "黑"}),
        ("white", {"white", "白"}),
        ("red", {"red", "红"}),
        ("blue", {"blue", "蓝"}),
        ("green", {"green", "绿"}),
        ("gold", {"gold", "金"}),
        ("silver", {"silver", "银"}),
        ("warm sand", {"sand", "beach", "沙滩", "海滩"}),
    ]
    for label, terms in candidates:
        if any(term in lower or term in task for term in terms):
            colors.append(label)
    if colors:
        return colors[:4]
    if visual_type == "infographic":
        return ["warm white base", "dark readable type", "blue green red accents"]
    if visual_type == "ui":
        return ["deep neutral surfaces", "soft interface glow", "one restrained accent"]
    if visual_type == "portrait":
        return ["natural skin tones", "environmental neutrals", "warm light accents"]
    if visual_type == "poster":
        return ["controlled neutral base", "one high-contrast accent", "quiet background tones"]
    return ["controlled natural palette", "subject-led accents", "background restraint"]


def quality_target_for(visual_type: str, art: ArtDirection) -> str:
    targets = {
        "infographic": "large readable labels, clean visual hierarchy, restrained connectors, no tiny text",
        "portrait": "natural skin texture, believable catchlights, readable pose language, no waxy retouching",
        "product": "clear silhouette, contact shadows, specific surfaces, believable scale and reflections",
        "poster": "one strong visual idea, legible negative space, disciplined crop, no fake claims",
        "ui": "readable primary interface, stable spacing, few large labels, credible screen depth",
        "illustration": "clear silhouettes, coherent world detail, controlled palette, intentional line or paint finish",
        "3d": "consistent scale, surface variation, grounded shadows, motivated reflections",
        "photography": "motivated light, lens-consistent depth, tactile surfaces, coherent foreground to background",
    }
    return targets.get(visual_type, ", ".join(art.expensive_cues[:4]))


def build_visual_breakdown(card: TaskCard, art: ArtDirection, visual_type: str, scene: str, colors: list[str]) -> dict[str, Any]:
    spatial = {
        "foreground": "one subtle depth cue that supports the subject",
        "midground": card.hero_subject,
        "background": "quiet atmosphere that adds depth without clutter",
    }
    action_pose = {
        "infographic": "information flow, module grouping, connector direction, and label hierarchy",
        "portrait": "pose, gaze, gesture, expression, and body language must be visible when a person is present",
        "product": "object placement, scale cues, contact with surface, and use context",
        "poster": "symbolic subject placement and headline-safe visual rhythm",
        "ui": "primary screen state, panel hierarchy, hover or active state only if requested",
        "illustration": "character or object motion, silhouette, and readable staging",
        "3d": "object orientation, scale, bevels, supports, and shadow grounding",
        "photography": "natural subject placement and visible interaction with the environment",
    }.get(visual_type, "visible subject placement and staging")
    return {
        "subject": card.hero_subject,
        "action_pose": action_pose,
        "details_appearance": ", ".join(card.must_show) if card.must_show else "visible, prompt-relevant details only; avoid hidden or unverifiable specifics",
        "environment_background": scene,
        "lighting_atmosphere": art.lighting_motivation,
        "composition_framing": art.layout_grammar,
        "style_camera": ", ".join(art.taste_anchors[:2]),
        "colors": colors,
        "materials": art.material_specificity,
        "aspect_ratio": card.aspect_ratio,
        "quality_finish": quality_target_for(visual_type, art),
        "generation_intent": art.visual_thesis,
        "spatial_layers": spatial,
    }


def build_prompt_layers(card: TaskCard, art: ArtDirection, plan_seed: dict[str, Any], constraints: list[str]) -> dict[str, str]:
    core = (
        f"{card.aspect_ratio} {card.deliverable} centered on {card.hero_subject}; "
        f"{art.visual_thesis}; {plan_seed['lighting_atmosphere']}; "
        f"{plan_seed['composition_framing']}; palette: {', '.join(plan_seed['colors'])}; "
        f"materials: {', '.join(plan_seed['materials'][:5])}."
    )
    recreation = (
        f"Create a {core} Show foreground, midground, and background relationships clearly. "
        f"Quality target: {plan_seed['quality_finish']}. "
        f"Use only visually plausible details implied by the user request or references; avoid generic quality filler."
    )
    negative = "; ".join(constraints) if constraints else "avoid generic artifacts, fake text, fake claims, and unrequested brand marks"
    return {
        "prompt_core": core,
        "recreation_prompt": recreation,
        "negative_prompt": negative,
    }


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
    if use_case in {"infographic", "ui mockup", "scene design"}:
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
    subject_clauses = []
    for clause in re.split(r"[，,]+", first):
        cleaned = clause.strip(" ，,。.;；")
        lower = cleaned.lower()
        if not cleaned:
            continue
        if contains_any(cleaned, {"不要", "不使用", "不能", "禁止", "只用", "只使用", "避免"}):
            continue
        if any(phrase in lower for phrase in ["do not", "don't", "without", "avoid", "only use", "no logo", "no small text"]):
            continue
        if re.fullmatch(r"\d+\s*:\s*\d+", cleaned):
            continue
        subject_clauses.append(cleaned)
    first = "，".join(subject_clauses) if subject_clauses else first
    for phrase in ["不要官方 logo", "不要官方logo", "不要 logo", "不要logo", "不要小字", "不要虚构数字", "不使用官方 logo", "不要使用官方 logo"]:
        first = first.replace(phrase, "").strip(" ，,。.")
    first = re.sub(r"生成一张|生成一个|create an?|make an?|generate an?", "", first, flags=re.I).strip(" ，,。.")
    if infer_use_case(task) == "infographic":
        theme_match = re.search(r"(?:主题|topic)\s*[:：]\s*(.+)", task, flags=re.I)
        if theme_match:
            theme = re.split(r"[。.;；]", theme_match.group(1).strip(), maxsplit=1)[0]
            return theme.strip(" ，,。.")[:180]
        return "the requested visual explanation"
    if "Codex" in task and "AI coding agent" in task:
        return "Codex presented as an AI coding agent"
    if contains_any(task, {"swimwear", "swimsuit", "bikini", "泳装", "泳衣"}) and contains_any(task, {"magazine", "cover", "杂志", "封面"}):
        return "an adult fashion model in tasteful swimwear for a summer magazine cover"
    return first[:180] or text[:180]


def infer_text_mode(task: str, use_case: str, wants_text: bool) -> str:
    if not wants_text:
        return "avoid_text"
    if extract_literal_text(task) or contains_any(task, {"literal text", "exact text", "标题：", "文案：", "copy:"}):
        return "literal_copy"
    if use_case in {"magazine cover", "poster", "thumbnail"}:
        return "headline_safe_only"
    return "short_readable_labels"


def extract_literal_text(task: str) -> list[str]:
    literal_labels = {"标题", "文案", "准确文字", "精确文字", "literal text", "exact text", "headline", "copy"}
    known_labels = literal_labels | {
        "use case", "scene", "subject", "camera", "lighting", "materials", "composition",
        "style", "preserve", "constraints", "constraint", "avoid", "场景", "主体", "镜头",
        "光线", "材质", "构图", "风格", "保留", "约束", "避免",
    }
    label_pattern = re.compile(
        rf"(?i)(?P<label>{'|'.join(sorted((re.escape(label) for label in known_labels), key=len, reverse=True))})\s*[:：]\s*"
    )
    matches = list(label_pattern.finditer(task))
    values: list[str] = []
    for index, match in enumerate(matches):
        if match.group("label").strip().lower() not in literal_labels:
            continue
        next_label_start = matches[index + 1].start() if index + 1 < len(matches) else len(task)
        newline_start = task.find("\n", match.end(), next_label_start)
        end = newline_start if newline_start >= 0 else next_label_start
        value = task[match.end():end].strip(" \t，,；;\"'")
        if value and value not in values:
            values.append(value)
    return values


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
    if contains_any(task, {"不要 logo", "不要logo", "no logo", "without logo", "no official logo", "no brand marks"}):
        add_unique(must_not_show, ["official logos", "brand marks"])
    if "不要虚构" in task or "do not invent" in task.lower():
        add_unique(must_not_show, ["fabricated numbers", "fake claims"])
    add_unique(must_show, extract_visible_details(task))
    return must_show[:12], must_not_show[:8]


def extract_visible_details(task: str) -> list[str]:
    """Keep positive, visible natural-language details from every sentence."""
    details: list[str] = []
    literal_values = set(extract_literal_text(task))
    directive_prefix = re.compile(
        r"(?i)^\s*(?:constraints?|avoid|preserve|headline|copy|literal text|exact text|"
        r"约束|避免|保留|标题|文案)\s*[:：]"
    )
    command_prefix = re.compile(
        r"(?i)^\s*(?:create|make|generate|design|draw|"
        r"生成|制作|设计|画|作成|描いて|生成して)\s*"
    )
    negative_terms = {
        "do not", "don't", "without", "avoid", "no logo", "must not",
        "不要", "避免", "禁止", "不使用", "なし", "避けて",
    }
    for raw in re.split(r"[\n。！？!?]+|(?<=[a-z0-9])\.\s+", task):
        clause = raw.strip(" \t,;，；.")
        if not clause or directive_prefix.match(clause) or clause in literal_values:
            continue
        if contains_any(clause, negative_terms):
            continue
        clause = command_prefix.sub("", clause).strip(" \t,;，；.")
        clause = re.sub(
            r"(?i)^(?:an?|the)?\s*(?:1:1|4:5|9:16|16:9)?\s*"
            r"(?:image|poster|portrait|illustration|photo|render|mockup|"
            r"图片|海报|肖像|照片|画像|ポスター)\s*[:,-]?\s*",
            "",
            clause,
        ).strip()
        if len(clause) < 3 or re.fullmatch(r"\d+\s*:\s*\d+", clause):
            continue
        if clause not in details:
            details.append(clause[:240])
    return details[:10]


def parse_task_card(task: str, use_case: str, references: list[str]) -> TaskCard:
    deliverable = {
        "infographic": "premium visual explainer infographic",
        "magazine cover": "fashion magazine cover",
        "poster": "e-commerce hero poster",
        "ui mockup": "polished UI mockup image",
        "product image": "premium product image",
        "portrait": "editorial portrait",
        "scene design": "cinematic scene image",
        "thumbnail": "thumbnail image",
        "storyboard": "storyboard sheet",
        "character design": "character design image",
    }.get(use_case, "image")
    literal_text = extract_literal_text(task)
    wants_text = bool(literal_text) or contains_any(task, TEXT_HEAVY_TERMS) or use_case in {"infographic", "magazine cover", "poster", "thumbnail"}
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
        literal_text=literal_text,
        must_show=must_show,
        must_not_show=must_not_show,
        hard_constraints=hard_constraints,
        factual_risk=factual_risk,
        references=references,
        render_count=1,
        auto_regen=False,
    )


def choose_direction_family(task: str, card: TaskCard) -> str:
    if card.use_case == "infographic":
        return "graphic_poster_minimal"
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
    if card.use_case == "infographic":
        visual_thesis = "a clear premium visual explanation where the viewer understands the comparison through hierarchy, modules, and connectors"
    elif "Codex" in task or "codex" in task.lower():
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


def score_visual_concept(concept: VisualConcept) -> int:
    score = 0
    if "high" in concept.thumbnail_readability:
        score += 3
    if "low" in concept.text_risk:
        score += 2
    if "low" in concept.reference_risk:
        score += 2
    if concept.first_read and concept.second_read:
        score += 2
    # Task-fit is deliberately stronger than generic risk heuristics. Otherwise a
    # safer but less useful fallback can displace the primary concept.
    return concept.score * 3 + score


def concept_candidates_for(task: str, card: TaskCard, art: ArtDirection) -> list[VisualConcept]:
    lower = task.lower()
    candidates: list[VisualConcept] = []

    def add(
        concept_id: str,
        visual_solution: str,
        why_it_fits: str,
        first_read: str,
        second_read: str,
        text_risk: str = "low",
        reference_risk: str = "low",
        thumbnail_readability: str = "high",
        score: int = 0,
    ) -> None:
        candidates.append(VisualConcept(
            concept_id=concept_id,
            visual_solution=visual_solution,
            why_it_fits=why_it_fits,
            first_read=first_read,
            second_read=second_read,
            text_risk=text_risk,
            reference_risk=reference_risk,
            thumbnail_readability=thumbnail_readability,
            score=score,
        ))

    if card.use_case == "infographic":
        add(
            "modular_flow_explainer",
            "a premium three-module visual explainer with large labels, abstract icons, and a single left-to-right comparison flow",
            "The request needs explanation and readable Chinese labels more than simulated UI depth.",
            "large labeled comparison modules",
            "thin connector lines and a concise bottom takeaway",
            text_risk="medium",
            score=4,
        )
        add(
            "architecture_map",
            "a clean architecture map with three stacked layers: renderer, conversation intelligence, and Codex visual director workflow",
            "Layering makes the workflow difference clear without relying on official logos.",
            "layered architecture blocks",
            "short labels that show responsibility boundaries",
            text_risk="medium",
            score=3,
        )
        add(
            "poster_triad",
            "a graphic poster with three large symbolic panels and restrained color accents",
            "This keeps the image visually strong when text rendering is imperfect.",
            "three symbolic panels",
            "color-coded role labels",
            text_risk="medium",
            score=2,
        )
    elif "codex" in lower and card.use_case == "poster":
        add(
            "workbench_in_action",
            "a real developer workbench scene with one dominant coding artifact and quiet evidence of iteration",
            "It shows the AI coding agent through believable work, not a generic SaaS object.",
            "coding artifact in action",
            "developer context and reasoning traces",
            score=4,
        )
        add(
            "ui_object_hybrid",
            "a productized interface surface treated like a physical object with restrained technical depth",
            "It keeps the commercial poster read while avoiding fake metrics and crowded dashboards.",
            "interface-as-product hero",
            "tactile material cues and headline-safe space",
            score=3,
        )
        add(
            "symbolic_agent_poster",
            "a minimal symbolic campaign poster around a single abstract agent mark, with lots of negative space",
            "It is safer for thumbnail reading but less concrete than a work context.",
            "single symbolic agent form",
            "headline-safe whitespace",
            text_risk="low",
            score=2,
        )
    elif card.use_case == "magazine cover":
        add(
            "coastal_editorial_cover",
            "an adult fashion model in natural coastal motion with clean masthead space and restrained cover-line zones",
            "It gives the cover a specific editorial world while protecting tasteful framing and typography space.",
            "adult fashion model and confident pose",
            "coastal light, fabric movement, and cover-safe negative space",
            text_risk="medium",
            score=4,
        )
        add(
            "studio_resort_cover",
            "a controlled resort-inspired studio portrait with sculpted sunlight and minimal graphic background",
            "It is a cleaner fallback when the cover needs stronger type control than a location scene.",
            "model silhouette and swimwear styling",
            "sun-shaped shadows and masthead-safe background",
            text_risk="medium",
            score=3,
        )
    elif card.use_case == "storyboard":
        add(
            "sequential_story_beats",
            "a clearly ordered storyboard sheet with one panel per requested beat, consistent subject anchors, and readable action staging",
            "The sequence is the deliverable, so panel continuity and action clarity outrank decorative finish.",
            "ordered panel sequence",
            "consistent characters, props, eyelines, and transitions",
            text_risk="low",
            score=4,
        )
        add(
            "cinematic_keyframes",
            "a restrained row of cinematic keyframes with strong shot contrast and minimal annotations",
            "This works when mood and shot language matter more than diagram-like explanation.",
            "contrasting keyframe silhouettes",
            "continuity of light, location, and subject",
            score=3,
        )
    elif card.use_case == "thumbnail":
        add(
            "thumbnail_single_hook",
            "one high-contrast visual hook with a simple silhouette, one face or object scale cue, and a large title-safe zone",
            "Small-size readability needs one immediate idea instead of product-poster detail.",
            "single visual hook",
            "short title-safe space and one supporting cue",
            text_risk="medium",
            score=4,
        )
        add(
            "thumbnail_before_after",
            "a clean two-state contrast with a strong dividing gesture and minimal background detail",
            "A before-and-after structure can explain transformation without dense labels.",
            "two contrasting states",
            "single connective action or divider",
            text_risk="medium",
            score=3,
        )
    elif card.use_case == "ui mockup":
        add(
            "primary_screen_hero",
            "one readable primary interface surface with two restrained supporting panels",
            "It prioritizes hierarchy and avoids dense fake dashboard clutter.",
            "primary screen state",
            "secondary panels and spatial depth",
            text_risk="medium",
            score=4,
        )
        add(
            "interface_as_product",
            "a clean interface object floating in a believable product-marketing scene",
            "It gives the UI physical presence without pretending to be an official screenshot.",
            "interface object",
            "subtle surface depth and light",
            score=3,
        )
    elif card.use_case == "product image" or art.director_id == "ecommerce_product_poster":
        add(
            "grounded_product_hero",
            "a product-led commercial hero with clear silhouette, contact shadow, and scale cues",
            "It makes the product or commercial concept feel tangible without fake claims.",
            "product or concept silhouette",
            "surface material and use context",
            score=4,
        )
        add(
            "use_context_still_life",
            "a restrained still life that places the product in a credible use environment",
            "It can explain value without adding badges or invented labels.",
            "product in context",
            "quiet environment details",
            score=3,
        )
    elif card.use_case == "portrait":
        add(
            "character_presence_portrait",
            "a cinematic portrait with motivated light, readable pose language, and tactile environment detail",
            "It focuses on subject presence and avoids overproduced generic gloss.",
            "face or silhouette",
            "pose language and environmental depth",
            score=4,
        )
        add(
            "editorial_environmental_portrait",
            "an editorial portrait where the setting explains mood and scale around the person",
            "It adds story while keeping identity and pose readable.",
            "person in environment",
            "atmosphere and material cues",
            score=3,
        )
    else:
        add(
            "single_subject_scene",
            "one clear subject in a coherent scene with foreground, midground, and background relationships",
            "It keeps the first generated image focused and easy to review.",
            card.hero_subject,
            "supporting scene evidence",
            score=3,
        )
        add(
            "graphic_symbolic_read",
            "a simple symbolic composition with strong silhouette and disciplined negative space",
            "It protects thumbnail readability when the subject is abstract.",
            "symbolic subject",
            "negative space and supporting cues",
            score=2,
        )

    scored = []
    for concept in candidates:
        concept.score = score_visual_concept(concept)
        scored.append(concept)
    scored.sort(key=lambda item: item.score, reverse=True)
    for index, concept in enumerate(scored):
        concept.selected = index == 0
    return scored


def selected_visual_concept(concepts: list[VisualConcept]) -> VisualConcept:
    for concept in concepts:
        if concept.selected:
            return concept
    return concepts[0]


def build_visual_plan(task: str, card: TaskCard, art_direction: ArtDirection | None = None) -> VisualPlan:
    art = art_direction or build_art_direction(task, card)
    family = art.director_id
    visual_type = infer_visual_type(task, card.use_case, family)
    concept_candidates = concept_candidates_for(task, card, art)
    selected = selected_visual_concept(concept_candidates)
    if card.use_case == "infographic":
        concept = selected.visual_solution
        scene = selected.visual_solution
    elif "Codex" in task or "codex" in task.lower():
        concept = selected.visual_solution
        scene = selected.visual_solution
    elif family == "fashion_editorial_cover":
        concept = selected.visual_solution
        scene = "a summer coastline with ocean air, warm sand, natural movement, and clean cover-layout negative space"
    elif card.use_case == "product image":
        concept = selected.visual_solution
        scene = selected.visual_solution
    elif card.use_case == "ui mockup":
        concept = selected.visual_solution
        scene = selected.visual_solution
    else:
        concept = selected.visual_solution
        scene = selected.visual_solution
    if card.text_mode == "literal_copy" and card.literal_text:
        quoted = "; ".join(f'"{item}"' for item in card.literal_text)
        text_rule = f"Render only this literal text exactly: {quoted}. Do not add other copy."
    elif card.text_mode == "avoid_text":
        text_rule = "Avoid text unless it is explicitly necessary."
    elif card.text_mode == "headline_safe_only":
        text_rule = "Leave headline-safe negative space, but do not invent cover lines, slogans, metrics, or feature labels."
    else:
        text_rule = "If any text appears, keep it very short, large, and fully legible."
    spatial_layers = {
        "foreground": "one subtle depth cue that supports the subject",
        "midground": selected.first_read,
        "background": selected.second_read,
    }
    color_system = infer_color_system(task, visual_type, art)
    visual_breakdown = build_visual_breakdown(card, art, visual_type, scene, color_system)
    prompt_layers = build_prompt_layers(card, art, visual_breakdown, card.hard_constraints)
    style_tags = style_tags_for(visual_type, art)
    quality_target = visual_breakdown["quality_finish"]
    checklist = [
        "Main subject is clear in the first second.",
        "Light direction, contact shadows, and practical glow feel coherent for this visual type.",
        "Materials feel physical, not flat or generic.",
        "Prompt describes visible evidence and avoids hidden unverifiable detail.",
        "The image avoids cheap cues such as " + ", ".join(art.cheap_cues[:3]) + ".",
    ]
    if card.wants_text:
        checklist.append("Visible text is short, readable, and not fabricated.")
    if card.aspect_ratio in {"4:5", "9:16"}:
        checklist.append("Composition still reads at mobile thumbnail size.")
    return VisualPlan(
        direction_family=family,
        visual_type=visual_type,
        concept=concept,
        scene=scene,
        scene_concept=scene,
        visual_breakdown=visual_breakdown,
        shot_family=art.taste_anchors[0],
        spatial_layers=spatial_layers,
        composition=f"{art.layout_grammar}; keep one dominant focal subject and enough negative space for the requested {card.aspect_ratio} crop",
        lighting=art.lighting_motivation,
        materials=", ".join(art.material_specificity),
        color_system=color_system,
        style_tags=style_tags,
        quality_target=quality_target,
        generation_intent=art.visual_thesis,
        text_rule=text_rule,
        text_strategy=text_rule,
        hard_constraints=card.hard_constraints,
        constraint_pack=card.hard_constraints,
        prompt_layers=prompt_layers,
        concept_candidates=[asdict(concept) for concept in concept_candidates],
        selected_concept_id=selected.concept_id,
        reference_anchors={"identity": [], "palette": [], "lighting": [], "composition": [], "material": [], "forbidden_drift": []},
        human_checklist=checklist,
    )


def build_brief(task: str, status: str, references: list[str] | None = None) -> dict[str, Any]:
    references = classify_references(references)["valid"]
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
        "visual_type": visual_plan.visual_type,
        "visual_thesis": art_direction.visual_thesis,
        "aspect_ratio": task_card.aspect_ratio,
        "visual_breakdown": visual_plan.visual_breakdown,
        "style_tags": visual_plan.style_tags,
        "quality_target": visual_plan.quality_target,
        "prompt_layers": visual_plan.prompt_layers,
        "concept_candidates": visual_plan.concept_candidates,
        "selected_concept_id": visual_plan.selected_concept_id,
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
    no_official_mark = has_no_official_mark(task)
    exact_preservation = (
        contains_any(task, EXACT_REFERENCE_TERMS)
        or (contains_any(task, FIDELITY_TERMS) and not no_official_mark)
        or requests_reference_preservation(task)
    )
    preservation_requested = (contains_any(task, PRESERVATION_TERMS) or requests_reference_preservation(task)) and not no_official_mark
    if exact_preservation or preservation_requested:
        preserve.append("preserve identity, silhouette, proportions, and style from references or user description")
    if references:
        preserve.append("use reference files as visual source of truth")
    return preserve


def compress_prompt(text: str, max_words: int = CODEX_PROMPT_MAX_LEXICAL_UNITS) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned: list[str] = []
    seen_lines: set[str] = set()
    for line in lines:
        label, sep, body = line.partition(":")
        if sep and re.match(r"^[A-Za-z][A-Za-z ]{1,24}$", label.strip()):
            split_pattern = r";" if label.strip().lower() == "constraints" else r",|;"
            phrases = [p.strip() for p in re.split(split_pattern, body) if p.strip()]
            deduped = []
            seen_phrases = set()
            for phrase in phrases:
                key = phrase.lower()
                if key not in seen_phrases:
                    deduped.append(phrase)
                    seen_phrases.add(key)
            joiner = "; " if label.strip().lower() == "constraints" else ", "
            line = f"{label}: {joiner.join(deduped)}" if deduped else f"{label}:"
        key = line.lower()
        if key not in seen_lines:
            cleaned.append(line)
            seen_lines.add(key)
    rendered = "\n".join(cleaned)
    units = list(
        re.finditer(
            r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*|[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]",
            rendered,
        )
    )
    if len(units) <= max_words:
        return rendered
    clipped = rendered[:units[max_words - 1].end()].rstrip(",.;")
    return clipped + "."


def render_codex_prompt_v2(brief: dict[str, Any]) -> str:
    card = brief.get("task_card") or {}
    art = brief.get("art_direction") or {}
    plan = brief.get("visual_plan") or {}
    candidates = plan.get("concept_candidates") or []
    selected_id = plan.get("selected_concept_id")
    selected = next((item for item in candidates if item.get("concept_id") == selected_id), candidates[0] if candidates else {})
    first_read = selected.get("first_read") or card.get("hero_subject") or brief.get("subject") or "one clear subject"
    second_read = selected.get("second_read") or "supporting visual evidence"
    visual_solution = selected.get("visual_solution") or plan.get("scene_concept") or plan.get("scene") or brief.get("scene")
    material_specificity = art.get("material_specificity") or plan.get("materials") or brief.get("materials") or ["believable physical surfaces"]
    if isinstance(material_specificity, str):
        material_text = material_specificity
    else:
        material_text = ", ".join(material_specificity[:5])
    constraints = plan.get("hard_constraints") or brief.get("negative") or []
    text_rule = plan.get("text_rule", "")
    constraints = [
        item for item in constraints
        if not (item == "keep visible text short, large, and legible" and "legible" in text_rule.lower())
    ]
    if not constraints:
        constraints = ["do not add unrequested brand marks, fake claims, ratings, prices, or awards"]
    use_case = card.get("use_case", brief.get("use_case", "image generation"))
    generic_must_show = {
        "Codex as an AI coding agent", "credible software work context", "adult fashion model",
        "tasteful swimwear editorial", "premium finish", "specific tactile materials", "motivated light",
    }
    supplied_details = [item for item in card.get("must_show", []) if item not in generic_must_show]
    if not supplied_details:
        supplied_details = card.get("must_show") or ["only details explicitly supplied by the user"]
    hero_subject = card.get("hero_subject", brief.get("subject", "the requested subject"))
    supplied_details = [
        item for item in supplied_details
        if re.sub(r"\s+", "", item).lower() not in re.sub(r"\s+", "", str(hero_subject)).lower()
    ]
    first_read_clause = "" if re.sub(r"\s+", "", str(first_read)).lower() in re.sub(r"\s+", "", str(hero_subject)).lower() else f", with {first_read} as the first read"
    detail_clause = f" Visible details: {'; '.join(supplied_details)}." if supplied_details else ""
    purpose = {
        "infographic": "a visual explanation task",
        "ui mockup": "a product UI marketing image",
        "poster": "a commercial poster task",
        "magazine cover": "an editorial cover task",
        "portrait": "an editorial portrait task",
        "product image": "a product image task",
        "storyboard": "a storyboard task",
        "thumbnail": "a thumbnail task",
    }.get(use_case, f"a {use_case} task")
    lines = [
        f"Create a {card.get('aspect_ratio', 'well-composed')} {card.get('deliverable', brief.get('use_case', 'image'))} for {purpose}.",
        (
            f"Show {hero_subject} through {visual_solution}{first_read_clause}, "
            f"with {second_read} as the second read.{detail_clause}"
        ),
        f"Compose for {card.get('aspect_ratio', 'the requested crop')} with one dominant focal path, readable spacing, and no decorative clutter.",
        f"Use {art.get('lighting_motivation') or plan.get('lighting') or brief.get('lighting')}; make materials visible through {material_text}.",
        f"Text: {text_rule or 'avoid text unless it is necessary and fully legible'}",
        f"Constraints: {'; '.join(constraints)}.",
    ]
    preserve = brief.get("preserve") or []
    if preserve:
        lines.append(f"Preserve: {'; '.join(preserve)}.")
    prompt = "\n".join(lines)
    if count_prompt_words(prompt) <= CODEX_PROMPT_MAX_LEXICAL_UNITS:
        return prompt

    # Preserve user copy, must-show details, preservation anchors, and hard
    # constraints. Only compact the surrounding director language.
    compact_lines = [
        f"Create a {card.get('aspect_ratio', 'well-composed')} {card.get('deliverable', brief.get('use_case', 'image'))}.",
        f"Show {hero_subject}." + (f" Must show: {'; '.join(supplied_details)}." if supplied_details else ""),
        f"Compose clearly for the {card.get('aspect_ratio', 'requested')} crop.",
        "Use coherent motivated light and tactile materials.",
        f"Text: {text_rule or 'avoid text unless it is necessary and fully legible'}",
        f"Constraints: {'; '.join(constraints)}.",
    ]
    if preserve:
        compact_lines.append(f"Preserve: {'; '.join(preserve)}.")
    return "\n".join(compact_lines)


def make_codex_prompt(brief: dict[str, Any]) -> str:
    return render_codex_prompt_v2(brief)


def make_codex_prompt_legacy(brief: dict[str, Any]) -> str:
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
Use the palette {", ".join(plan.get("color_system") or ["controlled natural palette"])}. Quality target: {plan.get("quality_target") or "visible, concrete finish cues instead of generic quality words"}.
The image should feel {art.get("emotional_read") or brief.get("style")}, not {cheap_text}.
Use only visible or user-provided evidence; do not invent hidden brands, exact claims, precise locations, or unverifiable details.
{text_line}
{preserve_line}
{constraint_line}
"""
    return compress_prompt(prompt, max_words=CODEX_PROMPT_MAX_LEXICAL_UNITS)


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
    layers = plan.get("prompt_layers") or {}
    if layers.get("recreation_prompt"):
        text = f"""\
FINAL_RENDER_HANDOFF
{layers["recreation_prompt"]}
Text: {text_rule}
Style tags: {", ".join(plan.get("style_tags") or art.get("taste_anchors") or [])}.
Constraints: {"; ".join(constraints)}
"""
    else:
        text = f"""\
FINAL_RENDER_HANDOFF
Create a {card.get("aspect_ratio", "")} {card.get("deliverable", brief.get("use_case", "image"))} around {art.get("visual_thesis") or plan.get("concept") or brief.get("style")}.
Show {plan.get("scene_concept") or plan.get("scene") or brief.get("scene")} with {card.get("hero_subject", brief.get("subject"))} as the first read, {art.get("lighting_motivation") or plan.get("lighting") or brief.get("lighting")}, and tactile materials: {", ".join(art.get("material_specificity") or []) or plan.get("materials") or brief.get("materials") or "believable tactile surfaces"}.
Keep the composition {art.get("layout_grammar") or plan.get("composition") or brief.get("composition")}; quality target: {plan.get("quality_target") or "concrete visible finish cues"}.
Text: {text_rule}
Constraints: {"; ".join(constraints)}
"""
    return compress_prompt(text, max_words=10_000)


def make_identity_lock(task: str, references: list[str]) -> dict[str, Any] | None:
    references = classify_references(references)["valid"]
    no_official_mark = has_no_official_mark(task)
    exact_preservation = (
        contains_any(task, EXACT_REFERENCE_TERMS)
        or (contains_any(task, FIDELITY_TERMS) and not no_official_mark)
        or requests_reference_preservation(task)
    )
    preservation_requested = (contains_any(task, PRESERVATION_TERMS) or requests_reference_preservation(task)) and not no_official_mark
    if not (exact_preservation or preservation_requested):
        return None
    source = "provided_references" if references else "explicit_user_description"
    if contains_any(task, PERSON_TERMS) or contains_any(task, {"same person", "real person", "同一个人", "真人", "明星"}):
        scope = "person_or_character"
        anchors = ["face structure", "hair silhouette", "body proportions", "clothing anchors", "pose language"]
    elif contains_any(task, PRODUCT_TERMS) or contains_any(task, {"same product", "exact product", "同款产品", "复刻产品"}):
        scope = "product"
        anchors = ["silhouette", "proportions", "materials", "surface markings", "color placement"]
    elif contains_any(task, UI_TERMS):
        scope = "ui_system"
        anchors = ["layout grid", "component geometry", "spacing", "palette", "typography hierarchy"]
    elif contains_any(task, {"brand", "logo", "品牌", "标志"}):
        scope = "brand_style"
        anchors = ["mark geometry", "palette", "typography", "spacing", "visual language"]
    else:
        scope = "visual_style"
        anchors = ["palette", "line or surface treatment", "lighting", "composition grammar", "material behavior"]
    return {
        "scope": scope,
        "source_of_truth": source,
        "references": references,
        "anchors": anchors,
        "forbidden_drift": ["changed defining proportions", "changed anchor colors or markings", "unrequested style change"],
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
