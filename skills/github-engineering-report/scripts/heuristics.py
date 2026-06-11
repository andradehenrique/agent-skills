"""
Helpers for GitHub Engineering Report skill.
Used by the agent to classify and detect patterns in PR/review data.
"""

import re
from datetime import datetime, timezone

# Known bot usernames (case-insensitive)
KNOWN_BOTS = {
    "dependabot", "github-actions", "sonarqube", "renovate", "codecov", "semantic-release"
}


def is_bot(username: str) -> bool:
    """Return True if username is a known bot."""
    if not username:
        return False
    username = username.lower().replace("[bot]", "").strip()
    return username in KNOWN_BOTS or username.endswith("bot")


def classify_pr(title: str, branch: str) -> str:
    """Classify PR as feature, bugfix, or other."""
    text = f"{title or ''} {branch or ''}".lower()
    if any(k in text for k in ("feat", "feature", "add ", "implement")):
        return "feature"
    if any(k in text for k in ("fix", "bug", "hotfix")):
        return "bugfix"
    return "other"


def detect_blocked(pr: dict, reviews: list, comments: list) -> bool:
    """Detect if PR is potentially blocked."""
    # Open > 3 days
    created = pr.get("created_at")
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - dt).days > 3:
                return True
        except:
            pass
    # > 5 comments and no merge
    if len(comments) > 5 and not pr.get("merged_at"):
        return True
    # Changes requested in latest review
    for review in reversed(reviews):
        if review.get("state") == "CHANGES_REQUESTED":
            return True
    return False


def detect_long_running(pr: dict) -> bool:
    """Detect if PR is long-running (> 5 days)."""
    created = pr.get("created_at")
    if not created or pr.get("merged_at"):
        return False
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days > 5
    except:
        return False


def extract_jira_keys(text: str) -> list:
    """Extract Jira ticket keys (e.g., ABC-123) from text."""
    if not text:
        return []
    return list(set(re.findall(r'\b[A-Z][A-Z0-9]+-\d+\b', text)))


def classify_verdict(pr: dict, reviews: list) -> str:
    """Classify PR verdict."""
    if detect_long_running(pr):
        return "Long-running"
    if detect_blocked(pr, reviews, []):
        return "Blocked"
    if pr.get("merged_at"):
        return "Healthy"
    return "Healthy"
