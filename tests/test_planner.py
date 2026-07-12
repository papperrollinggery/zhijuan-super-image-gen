from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from imageops_core import (  # noqa: E402
    CODEX_PROMPT_MAX_WORDS,
    EXPLICIT_CONSTRAINT_WORD_LIMIT,
    analyze_feasibility,
    build_brief,
    build_hard_constraints,
    classify_references,
    compress_prompt,
    count_prompt_words,
    choose_direction_family,
    infer_use_case,
    make_codex_prompt,
    make_chatgpt_prompt,
    make_identity_lock,
)


FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "image_tasks.json").read_text(encoding="utf-8"))


class PlannerFixtureTest(unittest.TestCase):
    def test_fixture_classification_and_prompt_shape(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture["id"]):
                task = fixture["task"]
                references = fixture.get("references", [])
                feasibility = analyze_feasibility(task, references)
                brief = build_brief(task, feasibility["status"], references)
                card = brief["task_card"]
                art = brief["art_direction"]
                plan = brief["visual_plan"]
                prompt = make_codex_prompt(brief)
                identity_lock = make_identity_lock(task, references)

                self.assertEqual(feasibility["status"], fixture["expected_status"])
                self.assertEqual(feasibility["references_required"], fixture["references_required"])
                self.assertEqual(infer_use_case(task), fixture["expected_use_case"])
                self.assertEqual(card["use_case"], fixture["expected_use_case"])
                self.assertEqual(choose_direction_family(task, type("Card", (), card)), fixture["expected_director"])
                self.assertEqual(art["director_id"], fixture["expected_director"])
                self.assertEqual(bool(identity_lock), fixture["identity_lock"])
                self.assertLessEqual(count_prompt_words(prompt), min(fixture["max_prompt_lexical_units"], CODEX_PROMPT_MAX_WORDS))
                self.assertIn("Text:", prompt)
                self.assertIn("Constraints:", prompt)
                self.assertNotIn("Build the image around", prompt)
                self.assertNotIn("highly detailed", prompt.lower())

                if feasibility["status"] in {"PROCEED", "PROCEED_WITH_ASSUMPTIONS", "NEEDS_REFERENCES"}:
                    candidates = plan.get("concept_candidates", [])
                    self.assertGreaterEqual(len(candidates), 1)
                    selected = [item for item in candidates if item.get("selected")]
                    self.assertEqual(len(selected), 1)
                    self.assertEqual(plan.get("selected_concept_id"), selected[0]["concept_id"])

    def test_known_regressions_are_fixed(self) -> None:
        by_id = {item["id"]: item for item in FIXTURES}

        infographic = by_id["chinese_infographic"]
        feasibility = analyze_feasibility(infographic["task"], [])
        self.assertFalse(feasibility["references_required"])
        self.assertEqual(feasibility["status"], "PROCEED")
        self.assertEqual(infer_use_case(infographic["task"]), "infographic")

        portrait = by_id["chinese_portrait"]
        self.assertNotEqual(analyze_feasibility(portrait["task"], [])["status"], "NOT_USEFUL")

        no_logo = by_id["no_logo_brand_explainer"]
        self.assertIsNone(make_identity_lock(no_logo["task"], []))

        simple_poster = "生成一张极简科技海报：一个 AI 助手正在整理图片生成提示词，画面干净，高级，16:9，不要 logo，不要小字。"
        brief = build_brief(simple_poster, analyze_feasibility(simple_poster, [])["status"], [])
        hero_subject = brief["task_card"]["hero_subject"]
        prompt = make_codex_prompt(brief)
        self.assertIn("AI 助手正在整理图片生成提示词", hero_subject)
        self.assertNotIn("不要 logo", hero_subject)
        self.assertNotIn("不要小字", hero_subject)
        self.assertNotIn("不要 logo", prompt)
        self.assertNotIn("不要小字", prompt)

    def test_literal_copy_and_inline_directives_survive_compilation(self) -> None:
        task = (
            "Create a 4:5 recorder poster. Headline: LISTEN CLOSER.\n"
            "Constraints: no price; no awards. Avoid: floating UI cards."
        )
        brief = build_brief(task, analyze_feasibility(task, [])["status"], [])
        prompt = make_codex_prompt(brief)

        self.assertEqual(brief["task_card"]["literal_text"], ["LISTEN CLOSER."])
        self.assertIn("LISTEN CLOSER.", prompt)
        self.assertIn("user constraint: no price", prompt)
        self.assertIn("user constraint: no awards", prompt)
        self.assertIn("avoid: floating UI cards", prompt)

    def test_multi_sentence_headline_and_all_explicit_constraints_survive(self) -> None:
        task = (
            "Create a 16:9 developer poster. Headline: BUILD. SHIP. WIN.\n"
            "Constraints: no price; no awards; no badges; no fake metrics; no tiny text; "
            "Avoid: floating UI cards; official logos."
        )
        brief = build_brief(task, analyze_feasibility(task, [])["status"], [])
        constraints = build_hard_constraints(task, max_items=1)
        prompt = make_codex_prompt(brief)

        self.assertEqual(brief["task_card"]["literal_text"], ["BUILD. SHIP. WIN."])
        self.assertIn("BUILD. SHIP. WIN.", prompt)
        for expected in (
            "user constraint: no price",
            "user constraint: no awards",
            "user constraint: no badges",
            "user constraint: no fake metrics",
            "user constraint: no tiny text",
            "avoid: floating UI cards",
            "avoid: official logos",
        ):
            self.assertIn(expected, constraints)
            self.assertIn(expected, prompt)

    def test_literal_copy_uses_known_label_or_newline_boundaries(self) -> None:
        cases = {
            "生成海报。标题：你好。世界。": "你好。世界。",
            "Create a poster. Headline: build quietly. ship confidently.": "build quietly. ship confidently.",
            "Create a poster. Headline: one. two.\nConstraints: no price.": "one. two.",
        }
        for task, literal in cases.items():
            with self.subTest(task=task):
                brief = build_brief(task, analyze_feasibility(task, [])["status"], [])
                self.assertEqual(brief["task_card"]["literal_text"], [literal])
                self.assertIn(literal, make_codex_prompt(brief))

    def test_natural_language_preservation_requires_valid_references(self) -> None:
        tasks = [
            "Create a portrait and keep her face, hairstyle, and proportions unchanged from the attachment.",
            "生成品牌海报，严格保持附件里的品牌视觉、字体、配色和版式一致。",
        ]
        for task in tasks:
            with self.subTest(task=task):
                feasibility = analyze_feasibility(task, [])
                lock = make_identity_lock(task, [])
                self.assertEqual(feasibility["status"], "NEEDS_REFERENCES")
                self.assertTrue(feasibility["references_required"])
                self.assertIsNotNone(lock)
                self.assertEqual(lock["source_of_truth"], "explicit_user_description")
                self.assertEqual(lock["references"], [])

    def test_excessive_explicit_constraints_become_non_proceed_and_never_validate_by_size(self) -> None:
        constraints = "; ".join(f"constraint {index} must remain exactly as specified" for index in range(30))
        task = f"Create a 16:9 poster.\nConstraints: {constraints}."
        feasibility = analyze_feasibility(task, [])
        brief = build_brief(task, feasibility["status"], [])
        prompt = make_codex_prompt(brief)
        chatgpt_prompt = make_chatgpt_prompt(brief)

        self.assertEqual(feasibility["status"], "NEEDS_USER_INPUT")
        self.assertTrue(feasibility["constraint_budget_exceeded"])
        self.assertGreater(feasibility["constraint_word_count"], EXPLICIT_CONSTRAINT_WORD_LIMIT)
        self.assertGreater(count_prompt_words(prompt), CODEX_PROMPT_MAX_WORDS)
        for index in range(30):
            self.assertIn(f"constraint {index} must remain exactly as specified", prompt)
            self.assertIn(f"constraint {index} must remain exactly as specified", chatgpt_prompt)

    def test_reference_classification_requires_readable_local_files(self) -> None:
        task = "Recreate the exact product from the reference image as a 4:5 product poster."
        missing = str(ROOT / "tests" / "fixtures" / "missing-reference.png")
        feasibility = analyze_feasibility(task, [missing])
        brief = build_brief(task, feasibility["status"], [missing])
        lock = make_identity_lock(task, [missing])

        self.assertEqual(feasibility["status"], "NEEDS_REFERENCES")
        self.assertTrue(feasibility["references_required"])
        self.assertEqual(feasibility["invalid_references"], [missing])
        self.assertEqual(brief["references"], [])
        self.assertEqual(lock["source_of_truth"], "explicit_user_description")
        self.assertEqual(lock["references"], [])

        url = "https://example.com/product.png"
        self.assertEqual(classify_references([url])["urls"], [url])
        self.assertEqual(classify_references([url])["valid"], [])
        url_feasibility = analyze_feasibility(task, [url])
        self.assertEqual(url_feasibility["status"], "NEEDS_REFERENCES")
        self.assertTrue(url_feasibility["references_required"])
        self.assertFalse(url_feasibility["use_codex_image_gen_directly"])
        self.assertTrue(any("do not satisfy identity or style" in item for item in url_feasibility["assumptions"]))

        for remote in ("https://example.com/not-an-image", "https://example.com/404.png"):
            with self.subTest(remote=remote):
                remote_feasibility = analyze_feasibility(task, [remote])
                self.assertEqual(remote_feasibility["status"], "NEEDS_REFERENCES")
                self.assertTrue(remote_feasibility["references_required"])

    def test_non_image_and_empty_local_references_do_not_unlock_identity_gate(self) -> None:
        task = "Recreate the exact product from the reference image as a 4:5 product poster."
        with tempfile.TemporaryDirectory() as tmp:
            text_file = Path(tmp) / "not-image.txt"
            empty_file = Path(tmp) / "empty.png"
            text_file.write_text("not an image", encoding="utf-8")
            empty_file.write_bytes(b"")

            references = [str(text_file), str(empty_file)]
            classified = classify_references(references)
            feasibility = analyze_feasibility(task, references)

            self.assertEqual(classified["valid"], [])
            self.assertEqual(classified["invalid"], references)
            self.assertEqual(feasibility["status"], "NEEDS_REFERENCES")
            self.assertTrue(feasibility["references_required"])

    def test_supported_local_image_signatures_unlock_identity_gate(self) -> None:
        task = "Recreate the exact product from the reference image as a 4:5 product poster."
        signatures = {
            "sample.png": b"\x89PNG\r\n\x1a\nextra",
            "sample.jpg": b"\xff\xd8\xff\xe0extra",
            "sample.gif": b"GIF89aextra",
            "sample.webp": b"RIFF\x04\x00\x00\x00WEBPextra",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, payload in signatures.items():
                with self.subTest(name=name):
                    path = Path(tmp) / name
                    path.write_bytes(payload)
                    self.assertEqual(classify_references([str(path)])["valid"], [str(path.resolve())])
                    self.assertFalse(analyze_feasibility(task, [str(path)])["references_required"])

    def test_explicit_constraints_preserve_dotted_tokens_and_following_items(self) -> None:
        task = (
            "Create a 4:5 product poster. "
            "Constraints: keep the label v2.1 exactly; preserve the red seal. "
            "Avoid: example.com badges; serial A.B-2."
        )

        constraints = build_hard_constraints(task, max_items=0)

        self.assertIn("user constraint: keep the label v2.1 exactly", constraints)
        self.assertIn("user constraint: preserve the red seal", constraints)
        self.assertIn("avoid: example.com badges", constraints)
        self.assertIn("avoid: serial A.B-2", constraints)

    def test_blocked_status_requires_explicit_entry(self) -> None:
        task = "Create a poster whose headline says BLOCKED but uses a clear geometric composition."

        self.assertNotEqual(analyze_feasibility(task, [])["status"], "BLOCKED")
        self.assertEqual(analyze_feasibility(task, [], blocked=True)["status"], "BLOCKED")
        self.assertFalse(analyze_feasibility(task, [], blocked=True)["use_codex_image_gen_directly"])

    def test_identity_lock_uses_scope_specific_anchors(self) -> None:
        product = make_identity_lock(
            "Recreate the exact product from the reference image and preserve its proportions.",
            ["https://example.com/product.png"],
        )
        style = make_identity_lock(
            "根据参考图保持插画风格，生成一个新的城市夜景概念图。",
            ["https://example.com/style.png"],
        )

        self.assertEqual(product["scope"], "product")
        self.assertIn("silhouette", product["anchors"])
        self.assertNotIn("face structure", product["anchors"])
        self.assertEqual(style["scope"], "visual_style")

    def test_primary_task_fit_wins_concept_selection(self) -> None:
        task = "生成一个高端 SaaS 数据看板 UI mockup，白底，信息层级清晰，适合官网 hero 图。"
        brief = build_brief(task, analyze_feasibility(task, [])["status"], [])

        self.assertEqual(brief["visual_plan"]["selected_concept_id"], "primary_screen_hero")

    def test_blocked_word_inside_copy_does_not_fake_a_policy_block(self) -> None:
        task = "Create a poster with the literal headline: UNBLOCKED IDEAS and a clear geometric composition."

        self.assertNotEqual(analyze_feasibility(task, [])["status"], "BLOCKED")

    def test_deliverable_terms_beat_subject_terms(self) -> None:
        self.assertEqual(infer_use_case("Create a launch poster for a mobile app."), "poster")
        self.assertEqual(infer_use_case("Create a YouTube thumbnail about a dashboard app."), "thumbnail")

    def test_specialized_formats_get_specialized_concepts(self) -> None:
        cases = {
            "生成一张成人夏季度假风泳装杂志封面，阳光海岸，时尚高级。": "coastal_editorial_cover",
            "生成一个三镜头分镜，表现机器人进门、发现礼物、开心离开。": "sequential_story_beats",
            "Create a YouTube thumbnail about an AI image workflow.": "thumbnail_single_hook",
        }
        for task, expected in cases.items():
            with self.subTest(task=task):
                brief = build_brief(task, analyze_feasibility(task, [])["status"], [])
                self.assertEqual(brief["visual_plan"]["selected_concept_id"], expected)

    def test_generic_reference_does_not_force_identity_lock(self) -> None:
        self.assertIsNone(make_identity_lock("Create a landscape scene with soft morning light.", ["mood.jpg"]))

    def test_multisentence_visible_details_survive_artifacts_and_prompt(self) -> None:
        task = (
            "Create a 4:5 product poster. A matte copper kettle sits on the left shelf. "
            "Three cobalt-blue cups form a triangle below it. Steam curls upward toward the amber window. "
            "The handle is dark walnut and the base is brushed steel."
        )
        brief = build_brief(task, analyze_feasibility(task, [])["status"], [])
        prompt = make_codex_prompt(brief)
        visible = " ".join(brief["task_card"]["must_show"])
        for detail in (
            "matte copper kettle",
            "left shelf",
            "Three cobalt-blue cups",
            "triangle below it",
            "Steam curls upward",
            "amber window",
            "dark walnut",
            "brushed steel",
        ):
            self.assertIn(detail, visible)
            self.assertIn(detail, prompt)

    def test_cjk_lexical_units_and_constraint_budget(self) -> None:
        self.assertEqual(count_prompt_words("中文海报"), 4)
        self.assertEqual(count_prompt_words("日本語ポスター"), 7)
        constraints = "；".join(f"必须保留红色物体位置动作材质数量{i}" for i in range(12))
        task = f"生成一张海报。\n约束：{constraints}"
        feasibility = analyze_feasibility(task, [])
        self.assertEqual(feasibility["status"], "NEEDS_USER_INPUT")
        self.assertTrue(feasibility["constraint_budget_exceeded"])
        self.assertEqual(count_prompt_words(compress_prompt("中文海报测试", max_words=4)), 4)

    def test_common_photo_sources_and_fidelity_require_references(self) -> None:
        tasks = [
            "Create a portrait preserving facial identity from the attached photo.",
            "Create a product poster matching the supplied image exactly.",
            "Create a campaign image with brand fidelity from the uploaded photo.",
            "Create a product image and preserve product identity.",
        ]
        for task in tasks:
            with self.subTest(task=task):
                result = analyze_feasibility(task, [])
                self.assertEqual(result["status"], "NEEDS_REFERENCES")
                self.assertTrue(result["references_required"])

    def test_spanish_japanese_and_unknown_visual_requests_do_not_become_not_useful(self) -> None:
        tasks = [
            "Crea un póster 4:5 con una tetera roja sobre una mesa azul.",
            "赤い急須が青い机の上にある4:5のポスターを生成して。",
        ]
        for task in tasks:
            with self.subTest(task=task):
                self.assertNotEqual(analyze_feasibility(task, [])["status"], "NOT_USEFUL")
        unknown = "შექმენი ვიზუალური კომპოზიცია წითელი საგნით."
        self.assertEqual(analyze_feasibility(unknown, [])["status"], "NEEDS_USER_INPUT")


if __name__ == "__main__":
    unittest.main()
