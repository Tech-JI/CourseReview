import re

from lib import constants

term_regex = re.compile(r"^(?P<year>[0-9]{2})(?P<term>SP|SU|FA)$", re.IGNORECASE)

TERM_ALIASES = {
    "SP": "SP",
    "SU": "SU",
    "FA": "FA",
}


def normalize_term(term):
    """Return the canonical YYSP/YYSU/YYFA form."""
    if not isinstance(term, str):
        return None
    term = term.strip().upper()
    if len(term) not in (3, 4) or not term[:2].isdigit():
        return None
    season = TERM_ALIASES.get(term[2:])
    return f"{term[:2]}{season}" if season else None


def numeric_value_of_term(term):
    term = normalize_term(term)
    if not term:
        return 0
    return int(term[:2]) * 10 + {"SP": 1, "SU": 2, "FA": 3}[term[2:]]


def is_valid_term(term):
    if not isinstance(term, str) or not term_regex.fullmatch(term):
        return False
    term_value = numeric_value_of_term(term)
    current_value = numeric_value_of_term(constants.CURRENT_TERM)
    return 0 < term_value <= current_value


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
    if season == "FA":
        year += 1
    season = {
        "SP": "SU",
        "SU": "FA",
        "FA": "SP",
    }[season]
    return "{}{}".format(year, season)
