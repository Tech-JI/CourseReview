import DOMPurify from "dompurify";

export const sanitize = (html) =>
  DOMPurify.sanitize(html, {
    FORBID_TAGS: ["img", "svg", "math", "script", "iframe"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onmouseout"],
    USE_PROFILES: { html: true },
    SAFE_FOR_TEMPLATES: true,
    SANITIZE_DOM: true,
    KEEP_CONTENT: false,
  });

export default { sanitize };
