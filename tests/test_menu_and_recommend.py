import unittest

from restaurant.menu import ALLERGENS, CATEGORIES, MENU, get_item, items_in
from restaurant.recommend import GENDERS, recommend


class MenuTest(unittest.TestCase):
    def test_at_least_20_items(self):
        self.assertGreaterEqual(len(MENU), 20)

    def test_ids_unique_and_prices_positive(self):
        self.assertEqual(len({item.id for item in MENU}), len(MENU))
        for item in MENU:
            self.assertGreater(item.price, 0)
            self.assertIn(item.category, CATEGORIES)
            self.assertTrue(item.allergens <= set(ALLERGENS))

    def test_filter_by_category(self):
        for category in CATEGORIES:
            items = items_in(category)
            self.assertTrue(items)
            self.assertTrue(all(item.category == category for item in items))
        self.assertEqual(len(items_in(None)), len(MENU))


class AllergyTest(unittest.TestCase):
    def test_allergen_label(self):
        self.assertEqual(get_item("N01").allergen_label, "なし")
        self.assertEqual(get_item("I02").allergen_label, "卵・小麦・えび・大豆")  # ALLERGENS の順

    def test_every_allergen_is_used(self):
        used = set().union(*(item.allergens for item in MENU))
        self.assertEqual(used, set(ALLERGENS))

    def test_filter_excludes_items(self):
        for allergen in ALLERGENS:
            with self.subTest(allergen=allergen):
                shown = items_in(None, [allergen])
                self.assertTrue(all(allergen not in item.allergens for item in shown))
                self.assertLess(len(shown), len(MENU))

    def test_filter_multiple_allergens(self):
        shown = items_in(None, ["卵", "乳", "小麦"])
        self.assertTrue(all(item.allergens.isdisjoint({"卵", "乳", "小麦"}) for item in shown))
        self.assertIn("N01", [item.id for item in shown])
        self.assertNotIn("N10", [item.id for item in shown])  # 玉子

    def test_filter_with_category(self):
        shown = items_in("握り", ["えび"])
        self.assertTrue(all(item.category == "握り" and "えび" not in item.allergens for item in shown))


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
        self.assertIn("N14", [r.item.id for r in recommend(8, "回答しない")])
        self.assertNotIn("N14", [r.item.id for r in recommend(30, "回答しない")])

    def test_results_differ_by_profile(self):
        child = [r.item.id for r in recommend(8, "回答しない")]
        senior = [r.item.id for r in recommend(70, "回答しない")]
        self.assertNotEqual(child, senior)

    def test_allergens_excluded_from_recommendations(self):
        for age in (8, 16, 30, 50, 75):
            for allergen in ALLERGENS:
                with self.subTest(age=age, allergen=allergen):
                    recs = recommend(age, "回答しない", [allergen])
                    self.assertTrue(recs)
                    self.assertTrue(all(allergen not in r.item.allergens for r in recs))

    def test_child_with_egg_allergy_gets_alternative(self):
        recs = {r.item.category: r.item.id for r in recommend(8, "回答しない", ["卵"])}
        self.assertNotEqual(recs["握り"], "N14")  # お子さま寿司セットは卵を含む
        self.assertNotIn("卵", get_item(recs["握り"]).allergens)

    def test_category_skipped_when_nothing_left(self):
        recs = recommend(30, "回答しない", list(ALLERGENS))
        self.assertTrue(all(not r.item.allergens for r in recs))


if __name__ == "__main__":
    unittest.main()
