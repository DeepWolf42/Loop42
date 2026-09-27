#!/usr/bin/env python3
"""Validate a Loop42 consumer profile and its exact revision pin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


SCHEMA = "loop42.consumer-profile.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_AUTHORITY = {
    "product_truth": "consumer",
    "recovery": "consumer",
    "execution": "consumer-policy",
}


def _nonempty_string(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def validate_profile(value, expected_revision=None):
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError("invalid consumer profile schema")

    loop42 = value.get("loop42")
    consumer = value.get("consumer")
    capabilities = value.get("capabilities")
    authority = value.get("authority")
    evidence = value.get("evidence")

    if not isinstance(loop42, dict):
        raise ValueError("loop42 section is required")
    _nonempty_string(loop42.get("repository"), "loop42.repository")
    revision = _nonempty_string(loop42.get("revision"), "loop42.revision")
    if not HEX40.fullmatch(revision):
        raise ValueError("loop42.revision must be an exact 40-hex commit")

    if expected_revision is not None:
        if not HEX40.fullmatch(expected_revision):
            raise ValueError("expected revision must be an exact 40-hex commit")
        if revision != expected_revision:
            raise ValueError("stale Loop42 revision pin")

    if not isinstance(consumer, dict):
        raise ValueError("consumer section is required")
    _nonempty_string(consumer.get("name"), "consumer.name")
    _nonempty_string(consumer.get("repository"), "consumer.repository")
    _nonempty_string(consumer.get("context_manifest"), "consumer.context_manifest")
    canonical = consumer.get("canonical_sources")
    if not isinstance(canonical, dict):
        raise ValueError("consumer.canonical_sources is required")
    _nonempty_string(canonical.get("project_state"), "canonical project_state")
    _nonempty_string(canonical.get("recovery"), "canonical recovery")

    if (
        not isinstance(capabilities, list)
        or not capabilities
        or any(not isinstance(item, str) or not item.strip() for item in capabilities)
        or len(set(capabilities)) != len(capabilities)
    ):
        raise ValueError("capabilities must be a non-empty unique string list")

    if authority != REQUIRED_AUTHORITY:
        raise ValueError("consumer authority boundary is invalid")

    if not isinstance(evidence, dict):
        raise ValueError("evidence section is required")
    _nonempty_string(evidence.get("equivalence_suite"), "evidence.equivalence_suite")
    if evidence.get("status") != "verified":
        raise ValueError("equivalence evidence must be verified")
    verified = _nonempty_string(
        evidence.get("verified_loop42_revision"),
        "evidence.verified_loop42_revision",
    )
    if not HEX40.fullmatch(verified) or verified != revision:
        raise ValueError("verified Loop42 revision must equal the pinned revision")

    return {
        "schema": SCHEMA,
        "consumer": consumer["name"],
        "loop42_repository": loop42["repository"],
        "loop42_revision": revision,
        "capabilities": capabilities,
        "status": "valid",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--expected-revision")
    args = parser.parse_args()

    try:
        value = json.loads(args.profile.read_text(encoding="utf-8"))
        result = validate_profile(value, args.expected_revision)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"loop42 consumer profile: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
