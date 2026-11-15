import unittest

import helpers
from common.loader import load_script


class ScriptTests(unittest.TestCase):
    def test_html_converter(self):
        c = load_script("html-converter")
        html = c.markdown_to_html("# 제목\n\n본문 **굵게** [링크](https://a.com)\n\n- 하나\n- 둘\n\n| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<h1>제목</h1>", html)
        self.assertIn("<strong>굵게</strong>", html)
        self.assertIn('href="https://a.com"', html)
        self.assertIn("<ul><li>하나</li><li>둘</li></ul>", html)
        self.assertIn("<td>2</td>", html)

    def test_html_converter_is_safe(self):
        c = load_script("html-converter")
        html = c.markdown_to_html("<script>alert(1)</script> [x](javascript:alert(1))")
        self.assertNotIn("<script>", html)
        self.assertNotIn("javascript:", html)

    def test_naver_flattens_headings(self):
        c = load_script("html-converter")
        out = c.markdown_to_naver("# 대제목\n\n## 소제목\n\n본문")
        self.assertNotIn("<h", out)
        self.assertIn("■ 소제목", out)

    def test_seo_checker(self):
        s = load_script("seo-checker")
        body = "# 이유식 시작 시기\n\n" + "이유식 시작 시기를 알아봅니다. " * 5 + "\n\n## 이유식 준비물\n\n" + "내용입니다. " * 150 + "\n\n## 마무리\n\n" + "정리합니다. " * 20
        ok = s.check(body, "이유식 시작 시기와 준비물 완벽 정리 가이드", "이유식 시작 시기", ["준비물"], config={"min_chars": 500})
        names = {c["name"]: c["passed"] for c in ok["checks"]}
        self.assertTrue(names["keyword_in_title"])
        self.assertTrue(names["keyword_in_intro"])
        self.assertTrue(names["min_length"])
        bad = s.check("## a\n\n짧음 ![](x.png)", "짧", "없는키워드", [])
        self.assertFalse(bad["passed"])
        failed = {c["name"] for c in bad["checks"] if not c["passed"]}
        self.assertTrue({"title_length", "keyword_in_title", "min_length", "image_alt_text"} <= failed)

    def test_image_processor_plan(self):
        p = load_script("image-processor")
        self.assertEqual(p.plan_resize(2400, 1200, 1200), (1200, 600))
        self.assertEqual(p.plan_resize(800, 600, 1200), (800, 600))
        with self.assertRaises(ValueError):
            p.plan_resize(0, 10)


if __name__ == "__main__":
    unittest.main()
