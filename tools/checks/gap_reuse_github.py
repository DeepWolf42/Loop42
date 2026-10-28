"""Bounded GitHub title probe. Returned metadata is untrusted discovery data."""
from __future__ import annotations

from datetime import datetime, timezone
from http.client import HTTPException
import json
import re
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE_BYTES = 512 * 1024
MAX_ITEMS = 8
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")


class NoRedirect(HTTPRedirectHandler):
    """Do not follow repository moves or forward credentials to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-standard JSON constant")


def collect_open_work(repository: str, *, target: str, revision: str,
                      token: str | None = None) -> dict[str, Any]:
    """One GET, no retry/pagination. Scope: open PR/issue titles, not code fit."""
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise ValueError("github repository must be owner/name on github.com")
    if not isinstance(target, str) or not target.strip() or len(target) > 240:
        raise ValueError("target must be 1-240 characters")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a full 40-hex commit")
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_.-]{3,}", target)
             if term.lower() not in {"with", "from", "this", "that", "eine", "einen", "und", "the", "for"}}
    if not terms:
        raise ValueError("target needs a searchable term of at least three characters")
    if token is not None and (not isinstance(token, str) or not token or not token.isascii()
                              or any(ord(char) < 33 or ord(char) > 126 for char in token)):
        raise ValueError("invalid GitHub token format")

    url = (f"https://api.github.com/repos/{repository}/issues"
           "?state=open&sort=updated&direction=desc&per_page=100&page=1")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Loop42-gap-reuse-preflight",
               "X-GitHub-Api-Version": "2026-03-10"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    blocked = {"status": "BLOCKED_UNKNOWN", "reason": "GitHub open-work probe unavailable"}
    try:
        with build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                return {**blocked, "reason": "GitHub response exceeds 512 KiB limit"}
            if response.headers.get("Link", ""):
                # No pagination is followed, even when a supplied link points elsewhere.
                return {**blocked, "reason": "GitHub page coverage incomplete; pagination not followed"}
        values = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                            parse_constant=_reject_constant)
        if not isinstance(values, list) or len(values) > 100:
            raise ValueError("invalid issue list")
        candidates = []
        seen = set()
        for value in values:
            if not isinstance(value, dict):
                raise ValueError("invalid issue")
            number, title = value.get("number"), value.get("title")
            if (type(number) is not int or number <= 0 or number in seen
                    or not isinstance(title, str) or not 0 < len(title.strip()) <= 256
                    or value.get("state") != "open"):
                raise ValueError("invalid open issue metadata")
            seen.add(number)
            kind = "pull" if "pull_request" in value else "issues"
            reference = f"https://github.com/{repository}/{kind}/{number}"
            if not isinstance(value.get("html_url"), str) or value["html_url"].lower() != reference.lower():
                raise ValueError("issue reference differs from selected repository")
            if any(term in title.lower() for term in terms):
                label = "PR" if kind == "pull" else "Issue"
                candidates.append({"name": f"{label} #{number} {title}"[:300],
                                   "reference": reference,
                                   "reason": "title keyword match only; inspect live state, revision and reuse fit"})
        return {"status": "USEFUL_CANDIDATE" if candidates else "CHECKED_NO_DELTA",
                "source": f"GitHub {repository}: open PR/issue title probe, one page <=100, <=8 leads",
                "checked_at": datetime.now(timezone.utc).isoformat(), "revision": revision,
                "items": candidates[:MAX_ITEMS]}
    except HTTPError as error:
        return {**blocked, "reason": f"GitHub HTTP {error.code}; access/rate/redirect failure, no retry"}
    except (OSError, ValueError, HTTPException, RecursionError):
        # Exception text and response bodies can contain credentials or private data.
        return {**blocked, "reason": "GitHub transport or response invalid; no retry"}
