"""Sanitizer for model-authored markdown before it is stored and rendered.

``Syllabus.summary_md`` is produced by an LLM from an uploader-supplied
document and is rendered as HTML by the frontend, so it is an untrusted
markup path. This keeps markdown syntax intact while removing raw HTML tags
and script-bearing URL schemes. It is deliberately conservative: markdown
autolinks such as ``<https://example.com>`` survive, HTML does not.
"""

import re

# Whole elements that can execute or embed content.
_STRIP_ELEMENTS_RE = re.compile(
    r"<(script|style|iframe|object|embed|svg|form|template)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Any tag-like token. The negative lookahead keeps markdown autolinks, which
# look like `<scheme://host>`, untouched.
_TAG_RE = re.compile(
    r"</?[A-Za-z][A-Za-z0-9-]*(?!\s*://)(?:\s[^<>]*)?/?>",
)
_UNSAFE_SCHEME_RE = re.compile(
    r"(\]\(|\()\s*(?:javascript|data|vbscript)\s*:", re.IGNORECASE
)
_REF_DEFINITION_RE = re.compile(
    r"(?im)^([ \t]{0,3}\[[^\]]+\]:[ \t]*<?[ \t]*)"
    r"(?:javascript|data|vbscript)[ \t]*:"
)


def sanitize_markdown(text):
    """Return ``text`` with raw HTML and unsafe link schemes removed."""
    if text is None:
        return ""
    cleaned = _STRIP_ELEMENTS_RE.sub("", text)
    cleaned = _COMMENT_RE.sub("", cleaned)
    cleaned = _TAG_RE.sub("", cleaned)
    cleaned = _UNSAFE_SCHEME_RE.sub(r"\1#", cleaned)
    cleaned = _REF_DEFINITION_RE.sub(r"\1#", cleaned)
    return cleaned
