import unittest
from datetime import datetime, timedelta, timezone

from collection import compute_collection_cutoff, limit_articles


UTC = timezone.utc


class CollectionCutoffTests(unittest.TestCase):
    def test_uses_last_success_with_overlap(self):
        now = datetime(2026, 8, 8, 5, tzinfo=UTC)
        previous = datetime(2026, 8, 7, 17, tzinfo=UTC)

        cutoff = compute_collection_cutoff(
            now,
            previous,
            initial_lookback_hours=14,
            overlap_minutes=60,
        )

        self.assertEqual(cutoff, datetime(2026, 8, 7, 16, tzinfo=UTC))

    def test_falls_back_to_initial_window_without_state(self):
        now = datetime(2026, 8, 8, 5, tzinfo=UTC)

        cutoff = compute_collection_cutoff(
            now,
            None,
            initial_lookback_hours=14,
            overlap_minutes=60,
        )

        self.assertEqual(cutoff, now - timedelta(hours=14))

    def test_ignores_future_state(self):
        now = datetime(2026, 8, 8, 5, tzinfo=UTC)

        cutoff = compute_collection_cutoff(
            now,
            now + timedelta(hours=1),
            initial_lookback_hours=14,
            overlap_minutes=60,
        )

        self.assertEqual(cutoff, now - timedelta(hours=14))


class ArticleLimitTests(unittest.TestCase):
    @staticmethod
    def article(source, hour, name):
        return {
            "source": source,
            "title": name,
            "published_at": f"2026-08-07T{hour:02d}:00:00+00:00",
        }

    def test_applies_source_limit_before_global_limit(self):
        articles = [
            self.article("arXiv", 18, "a3"),
            self.article("arXiv", 17, "a2"),
            self.article("arXiv", 16, "a1"),
            self.article("CERT", 15, "c1"),
            self.article("ANSSI", 14, "n1"),
        ]

        selected, dropped = limit_articles(
            articles,
            max_per_source=2,
            max_total=3,
        )

        self.assertEqual([a["title"] for a in selected], ["a3", "a2", "c1"])
        self.assertEqual(dropped, {"per_source": 1, "global": 1, "total": 2})

    def test_prioritizes_dated_articles_and_keeps_inputs_untouched(self):
        undated = {"source": "Blog", "title": "sans date", "published_at": ""}
        recent = self.article("CERT", 20, "récent")
        articles = [undated, recent]

        selected, _ = limit_articles(
            articles,
            max_per_source=50,
            max_total=1,
        )

        self.assertEqual(selected, [recent])
        self.assertNotIn("seen", undated)


if __name__ == "__main__":
    unittest.main()
