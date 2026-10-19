import unittest

from restaurant.validation import ValidationError, parse_age, parse_quantity


class ParseAgeTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_age("25"), 25)
        self.assertEqual(parse_age(" 0 "), 0)
        self.assertEqual(parse_age("１２０"), 120)  # 全角数字

    def test_invalid_does_not_crash(self):
        for text in ("", "   ", None, "abc", "二十", "-5", "-0", "3.5", "1e3", "20歳", "121", "99999999999999999999"):
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    parse_age(text)

    def test_negative_message(self):
        with self.assertRaisesRegex(ValidationError, "負の値"):
            parse_age("-1")


class ParseQuantityTest(unittest.TestCase):
    def test_range(self):
        self.assertEqual(parse_quantity("1"), 1)
        self.assertEqual(parse_quantity("99"), 99)
        for text in ("0", "100", "-2", "x"):
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    parse_quantity(text)


if __name__ == "__main__":
    unittest.main()
