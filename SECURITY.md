# Security Policy

Loop42 aims to keep automation bounded, reproducible and safe to inspect.

## Reporting a vulnerability

Do **not** post secrets, credentials, exploit details or other sensitive material in a public issue.

For a public Loop42 repository, prefer GitHub's private vulnerability reporting / Security Advisory flow when it is available. If no private reporting channel is visible, open a minimal public issue titled **"Private security contact requested"** without technical exploit details, credentials or personal information.

## What to include privately

When a private channel is available, include:

- affected revision or exact commit;
- affected file/component;
- reproduction steps or evidence;
- expected impact;
- whether credentials, private data or physical execution could be involved.

## Scope

Security-relevant areas include:

- authority and approval bypasses;
- stale-state or single-writer failures;
- secret/credential exposure;
- unsafe tool or provider boundaries;
- untrusted external input becoming execution authority;
- recovery paths that can silently replay stale work;
- consumer-boundary failures that could change product truth without review.

Do not include real credentials in test cases. Use clearly synthetic values such as `example.invalid`.

## Response principle

A report is evidence to investigate, not automatic proof. The smallest reproducible case should be verified against the current source of truth before a fix is accepted.

Loop42 does not promise a specific response time or security-service level.
