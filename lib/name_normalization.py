"""Instructor / professor name canonicalization shared by crawlers and review I/O.

GC (gc.sjtu.edu.cn) is the college's own course site, and its pages are the
single source of truth for instructor names. The pages themselves are
inconsistent across terms (case, hyphens, middle names, term/CJK annotations,
given-vs-family order, nickname variants, occasional typos), so any place that
accepts an instructor name from outside — crawler imports or user-submitted
reviews — must normalize it against the canonical Instructor rows before
storing, and only fall back to creating/keeping a new name when nothing
matches.

All helpers here are pure string functions (no Django imports) so both the
spider apps and the web review API can share them without import cycles.
"""

import re

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")
PAREN_RE = re.compile(r"[\(（][^)）]*[\)）]")
TITLE_RE = re.compile(r"^(dr|prof|ms|mr|mrs|miss)\.?\s+", re.IGNORECASE)
QUOTE_RE = re.compile(r"[\"'“”‘’]")
TRAILING_PUNCT_RE = re.compile(r"[\s.,;:]+$")

# Cells that are not instructor names at all and must never be stored.
JUNK_INSTRUCTOR_NAMES = {
    ",",
    "，",
    ";",
    "；",
    "-",
    "–",
    "—",
    ".",
    "教师",
    "教授",
    "老师",
    "staff",
    "tbd",
    "tba",
}

# Source cells that cram several instructors into one string without
# separators (curated; grows as the site produces new cases).
INSTRUCTOR_SPLITS = {
    "Zhaoguang Wang Ting Sun": ["Zhaoguang Wang", "Ting Sun"],
}

# Token-level nicknames that plain subsequence matching cannot catch
# (Nick/Nicholas is not a prefix relationship).
TOKEN_ALIASES = {"nick": "nicholas"}


def clean_instructor_name(name):
    """Strip page annotations so names are clean and matchable.

    Removes leading titles (Dr./Prof./...), parenthetical annotations
    ("(Fall)", "(Summer).", "(余琼)", "(UM)"), trailing CJK annotations
    ("YAN Xu 闫旭"), quotes ("Jaehyung “Joshua” Ju"), and stray trailing
    punctuation. Returns "" when nothing meaningful remains.
    """
    n = (name or "").replace("\u00a0", " ")
    n = TITLE_RE.sub("", n)
    n = PAREN_RE.sub(" ", n)
    n = CJK_RE.sub(" ", n)
    n = QUOTE_RE.sub("", n)
    n = TRAILING_PUNCT_RE.sub("", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def name_tokens(name):
    """Lowercased letter tokens; hyphens/punctuation inside a token are merged
    (e.g. 'Welch-Bolen' -> 'welchbolen') so hyphen variants compare equal."""
    tokens = []
    for raw in name.split():
        token = re.sub(r"[^a-z]", "", raw.lower())
        if token:
            tokens.append(token)
    return tokens


def _levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def tokens_equivalent(a, b):
    """Token equality allowing curated nicknames (nick ~ nicholas)."""
    return a == b or TOKEN_ALIASES.get(a, a) == b or a == TOKEN_ALIASES.get(b, b)


def _fuzzy_pair(a, b):
    """True when a token pair is a plausible typo: same-ish length, small
    edit distance. Short tokens are never fuzzy-matched (surname confusions
    like Bo/Po must not collapse)."""
    if len(a) < 5 or len(b) < 5:
        return False
    if abs(len(a) - len(b)) > 2:
        return False
    distance = _levenshtein(a, b)
    return distance <= 2 and distance <= len(a) // 3 + 1


def is_token_subsequence(short_tokens, long_tokens):
    """Ordered subsequence with alias/fuzzy awareness.

    Used to catch middle-name/extra-token variants ('Horst Harold Hohberger'
    vs 'Horst Hohberger'); fuzzy pairs are only tolerated for the shared run
    of tokens, never to skip extra tokens.
    """
    it = iter(long_tokens)
    for token in short_tokens:
        for candidate in it:
            if tokens_equivalent(token, candidate) or _fuzzy_pair(token, candidate):
                break
        else:
            return False
    return True


def best_name_match(clean_name, candidate_names):
    """Return the candidate a cleaned name refers to, or None.

    Matching ladder, first hit wins:
      1. exact name
      2. identical letter sequence (case/punctuation/hyphen variants)
      3. same word set (given-vs-family order variants)
      4. ordered token subsequence with >=2 tokens (middle names dropped,
         nickname aliases)
      5. single-token typo (same token count, one fuzzy edit-distance pair)
    Callers should pass candidates ordered by preference (most-used spelling
    first) so ties resolve deterministically.
    """
    tokens = name_tokens(clean_name)
    letters = "".join(tokens)
    if not letters:
        return None

    for candidate in candidate_names:
        candidate_tokens = name_tokens(candidate)
        if not candidate_tokens:
            continue
        candidate_letters = "".join(candidate_tokens)
        if candidate == clean_name:
            return candidate
        if candidate_letters == letters:
            return candidate
        if (
            len(candidate_tokens) >= 2
            and len(tokens) >= 2
            and set(candidate_tokens) == set(tokens)
        ):
            return candidate
    for candidate in candidate_names:
        candidate_tokens = name_tokens(candidate)
        if len(candidate_tokens) >= 2 and is_token_subsequence(
            candidate_tokens, tokens
        ):
            return candidate
        if len(tokens) >= 2 and is_token_subsequence(tokens, candidate_tokens):
            return candidate
    for candidate in candidate_names:
        candidate_tokens = name_tokens(candidate)
        if len(tokens) == len(candidate_tokens) and len(tokens) >= 2:
            fuzzy = sum(
                1
                for a, b in zip(tokens, candidate_tokens)
                if not tokens_equivalent(a, b) and not _fuzzy_pair(a, b)
            )
            if fuzzy == 0 and tokens != candidate_tokens:
                return candidate
    return None


def canonicalize_professor(raw_name, candidate_names):
    """Canonicalize a user-supplied professor name against candidate names
    (typically the course's instructors). Returns the canonical candidate when
    a match is found; otherwise the submitted name is kept as its own
    professor (to be resolved later, not guessed). Unmatched names are stored
    cleaned of annotations when they still carry a real first+last name;
    inputs like "Dr. Testing" (title + single name) are kept verbatim.
    """
    cleaned = clean_instructor_name(raw_name)
    if not cleaned:
        return ""
    match = best_name_match(cleaned, list(candidate_names))
    if match is not None:
        return match

    def pretty(name):
        return " ".join(
            token if token.isupper() else token.title() for token in name.split()
        )

    if len(cleaned.split()) >= 2:
        return pretty(cleaned)
    return pretty(raw_name.strip())
