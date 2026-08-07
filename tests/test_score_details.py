import unittest

from score_details import render_score_details


class ScoreDetailsTests(unittest.TestCase):
    def test_renders_only_scores_three_to_five_with_reasons(self):
        articles = [
            self.article("Score 3", 3, "utile"),
            self.article("Score 1", 1, "bruit"),
            self.article("Score 5", 5, "critique"),
            self.article("Score 4", 4, "important"),
            self.article("Score 2", 2, "marginal"),
        ]

        rendered = render_score_details(articles)

        self.assertIn("**5/5**", rendered)
        self.assertIn("**4/5**", rendered)
        self.assertIn("**3/5**", rendered)
        self.assertIn("Raison : critique", rendered)
        self.assertIn("Raison : important", rendered)
        self.assertIn("Raison : utile", rendered)
        self.assertNotIn("Score 1", rendered)
        self.assertNotIn("Score 2", rendered)
        self.assertLess(rendered.index("Score 5"), rendered.index("Score 4"))
        self.assertLess(rendered.index("Score 4"), rendered.index("Score 3"))

    def test_uses_original_phase_one_score(self):
        article = self.article("Article dédupliqué", 2, "raison finale")
        article["score_phase1"] = 5

        rendered = render_score_details([article])

        self.assertIn("**5/5**", rendered)
        self.assertNotIn("**2/5**", rendered)

    def test_escapes_untrusted_text_and_ignores_non_http_links(self):
        article = self.article("Titre [test]", 4, "raison *forte*")
        article["link"] = "javascript:alert(1)"

        rendered = render_score_details([article])

        self.assertIn(r"Titre \[test\]", rendered)
        self.assertIn(r"raison \*forte\*", rendered)
        self.assertNotIn("javascript:", rendered)

    @staticmethod
    def article(title, score, reason):
        return {
            "title": title,
            "source": "Source",
            "link": "https://example.com/article",
            "score": score,
            "score_phase1": score,
            "raison": reason,
        }


if __name__ == "__main__":
    unittest.main()
