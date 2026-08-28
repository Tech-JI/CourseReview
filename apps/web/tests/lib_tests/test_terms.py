import random

from django.test import TestCase

from lib import constants, terms


class TermsTestCase(TestCase):
    def test_term_regex_works_in_common_case(self):
        term_data = terms.term_regex.match("16SP")
        self.assertTrue(
            term_data
            and term_data.group("year") == "16"
            and term_data.group("term") == "SP"
        )

    def test_term_regex_only_allows_two_digit_years(self):
        term_data = terms.term_regex.match("2016SP")
        self.assertFalse(term_data)

    def test_term_regex_disallows_bad_terms(self):
        self.assertFalse(terms.term_regex.match("16a"))

    def test_term_regex_allows_for_lower_and_upper_terms(self):
        term_data = terms.term_regex.match("16SP")
        self.assertTrue(
            term_data
            and term_data.group("year") == "16"
            and term_data.group("term") == "SP"
        )
        term_data = terms.term_regex.match("16sp")
        self.assertTrue(
            term_data
            and term_data.group("year") == "16"
            and term_data.group("term") == "sp"
        )
        term_data = terms.term_regex.match("16FA")
        self.assertTrue(
            term_data
            and term_data.group("year") == "16"
            and term_data.group("term") == "FA"
        )

    def test_term_regex_allows_for_current_term(self):
        term_data = terms.term_regex.match(constants.CURRENT_TERM)
        self.assertTrue(
            term_data
            and term_data.group("year") == constants.CURRENT_TERM[:2]
            and term_data.group("term") == constants.CURRENT_TERM[2:]
        )

    def test_numeric_value_of_term_returns_0_if_bad_term(self):
        self.assertEqual(terms.numeric_value_of_term(""), 0)
        self.assertEqual(terms.numeric_value_of_term("asd"), 0)
        self.assertEqual(terms.numeric_value_of_term("2001"), 0)
        self.assertEqual(terms.numeric_value_of_term("1s"), 0)
        self.assertEqual(terms.numeric_value_of_term("2016sp"), 0)
        self.assertEqual(terms.numeric_value_of_term("fall"), 0)

    def test_numeric_value_of_term_ranks_terms_in_correct_order(self):
        correct_order = [
            "",
            "09SP",
            "09SU",
            "09FA",
            "12SP",
            "14SU",
            "20FA",
        ]
        shuffled_data = list(correct_order)
        while correct_order == shuffled_data:
            random.shuffle(shuffled_data)
        sorted_data = sorted(
            shuffled_data, key=lambda term: terms.numeric_value_of_term(term)
        )
        self.assertNotEqual(correct_order, shuffled_data)
        self.assertEqual(correct_order, sorted_data)

    def test_numeric_value_of_term_gives_expected_numeric_value(self):
        self.assertEqual(terms.numeric_value_of_term("16SP"), 161)

    def test_numeric_value_of_term_rejects_legacy_codes(self):
        self.assertEqual(terms.numeric_value_of_term("26S"), 0)
        self.assertEqual(terms.numeric_value_of_term("26X"), 0)
        self.assertEqual(terms.numeric_value_of_term("26F"), 0)

    def test_is_valid_term_returns_false_if_in_future(self):
        term_data = terms.term_regex.match(constants.CURRENT_TERM)
        if term_data is None:
            raise AssertionError("CURRENT_TERM did not match term_regex")
        next_year = int(term_data.group("year")) + 1
        self.assertFalse(terms.is_valid_term(f"{next_year}SP"))

    def test_is_valid_term_returns_false_for_next_term(self):
        next_term = terms.get_next_term(constants.CURRENT_TERM)
        self.assertFalse(terms.is_valid_term(next_term))

    def test_is_valid_term_returns_false_if_no_term(self):
        self.assertFalse(terms.is_valid_term(""))

    def test_is_valid_term_returns_false_if_no_year(self):
        self.assertFalse(terms.is_valid_term("sp"))

    def test_is_valid_term_returns_true_for_current_term(self):
        self.assertTrue(terms.is_valid_term(constants.CURRENT_TERM))

    def test_normalize_term_accepts_canonical_codes_case_insensitively(self):
        self.assertEqual(terms.normalize_term("26Sp"), "26SP")
        self.assertEqual(terms.normalize_term("26sp"), "26SP")
        self.assertEqual(terms.normalize_term("26su"), "26SU")
        self.assertEqual(terms.normalize_term("26Fa"), "26FA")
        self.assertIsNone(terms.normalize_term("26S"))
        self.assertIsNone(terms.normalize_term("26X"))
        self.assertIsNone(terms.normalize_term("26F"))
