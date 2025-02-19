import re
from lib import constants

term_regex = re.compile("^(?P<year>[0-9]{2})(?P<term>[WSXFwsxf])$")


def numeric_value_of_term(term):
    term_data = term_regex.match(term)
    if term_data and term_data.group("year") and term_data.group("term"):
        year = int(term_data.group("year"))
        term = term_data.group("term")
        return year * 10 + {"s": 2, "x": 3, "f": 4}[term.lower()]
    return 0


def is_valid_term(term):
    if not isinstance(term, str) or len(term) != 3:
        return False
    if not term[:2].isdigit():
        return False
    last_char = term[2].upper()
    if last_char not in ['X', 'S', 'F']:
        return False
    current_term = constants.CURRENT_TERM
    current_value = numeric_value_of_term(current_term)
    term_value = numeric_value_of_term(term)
    if not term_value or not current_value:
        if term[2].upper() > current_term[2].upper():
            return False
        if term[2].upper() < current_term[2].upper():
            return True
        return True
    return current_value >= term_value


def split_term(term):
    term_data = term_regex.match(term)
    if term_data and term_data.group("year") and term_data.group("term"):
        year = int(term_data.group("year"))
        term = term_data.group("term").upper()
        return year, term
    else:
        raise ValueError


def get_next_term(term):
    year, season = split_term(term)
    if season == "F":
        year += 1
    season = {
        "W": "S",
        "S": "X",
        "X": "F",
        "F": "W",
    }[season]
    return "{}{}".format(year, season)
