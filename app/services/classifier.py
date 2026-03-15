import re

# Slack: literal word "slack"
_SLACK_PATTERNS = [
    re.compile(r"\bslack\b", re.IGNORECASE),
]

# Todoist: "remind me", "reminder(s)", "task(s)", "to-do(s)", "todo(s)"
_TODOIST_PATTERNS = [
    re.compile(r"\bremind me\b", re.IGNORECASE),
    re.compile(r"\breminders?\b", re.IGNORECASE),
    re.compile(r"\btasks?\b", re.IGNORECASE),
    re.compile(r"\bto-?dos?\b", re.IGNORECASE),
]

# Calendar: compound rule — requires at least one action verb AND one noun
_CALENDAR_VERBS = re.compile(
    r"\b(?:schedule|create|book|move|block|set up|add)\b", re.IGNORECASE
)
_CALENDAR_NOUNS = re.compile(
    r"\b(?:meeting|appointment|event|call|calendar)\b", re.IGNORECASE
)


def _normalize(text: str) -> str:
    """Collapse whitespace and strip, so multi-word patterns match reliably."""
    return re.sub(r"\s+", " ", text).strip()


def _matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)


def _matches_calendar(text: str) -> bool:
    return bool(_CALENDAR_VERBS.search(text) and _CALENDAR_NOUNS.search(text))


def classify_intents(text: str) -> list[str]:
    """Deterministic keyword-based intent classifier.

    Returns a list of service names detected in the text,
    e.g. ["slack", "todoist"] or ["calendar"] or [].
    """
    text = _normalize(text)
    services = []

    if _matches_any(text, _SLACK_PATTERNS):
        services.append("slack")
    if _matches_any(text, _TODOIST_PATTERNS):
        services.append("todoist")
    if _matches_calendar(text):
        services.append("calendar")

    return services
