import unittest

from restaurant.menu import CATEGORIES, MENU, items_in
from restaurant.recommend import GENDERS, recommend


class MenuTest(unittest.TestCase):
    def test_at_least_20_items(self):
        self.assertGreaterEqual(len(MENU), 20)

    def test_ids_unique_and_prices_positive(self):
        self.assertEqual(len({item.id for item in MENU}), len(MENU))
        for item in MENU:
            self.assertGreater(item.price, 0)
            self.assertIn(item.category, CATEGORIES)

    def test_filter_by_category(self):
        for category in CATEGORIES:
            items = items_in(category)
            self.assertTrue(items)
            self.assertTrue(all(item.category == category for item in items))
        self.assertEqual(len(items_in(None)), len(MENU))


class RecommendTest(unittest.TestCase):
    def test_one_per_category_for_all_profiles(self):
        for age in (0, 8, 12, 13, 19, 20, 35, 45, 70, 120):
            for gender in GENDERS:
                recs = recommend(age, gender)
                self.assertEqual([r.item.category for r in recs], list(CATEGORIES))
                self.assertTrue(all(r.reason for r in recs))

    def test_no_alcohol_for_minors(self):
        for age in range(0, 20):
            self.assertFalse(any("alcohol" in r.item.tags for r in recommend(age, "男性")))

    def test_kids_menu_only_for_children(self):
        self.assertIn("M06", [r.item.id for r in recommend(8, "回答しない")])
        self.assertNotIn("M06", [r.item.id for r in recommend(30, "回答しない")])

    def test_results_differ_by_profile(self):
        child = [r.item.id for r in recommend(8, "回答しない")]
        senior = [r.item.id for r in recommend(70, "回答しない")]
        self.assertNotEqual(child, senior)


if __name__ == "__main__":
    unittest.main()
