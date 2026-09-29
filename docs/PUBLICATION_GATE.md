# Publication Gate

Status: active pre-publication checklist  
Applies to: making the Loop42 repository public or publishing a release

Publication is a protected operator decision. Automation may prepare and verify the repository, but it must not change repository visibility or publish a release without explicit approval.

## Required before public visibility

- The exact candidate commit has green repository CI.
- Full-history secret scanning is green on the exact candidate commit.
- Local credentials, tokens, private keys, machine-specific paths and personal configuration are not part of tracked repository content.
- Third-party sources and CI/runtime dependencies have a release-specific provenance and license review.
- A root project license has been selected intentionally and added for the public release.
- README/status text no longer claims that the repository is private.
- Repository history and author metadata have been reviewed for information the operator does not want to make public.
- Any public-facing security/contact instructions required for the chosen release state are present.
- Open draft work is either intentionally excluded from the release or explicitly integrated and verified.

## Protected decisions

The operator keeps the final decision for:

- repository visibility;
- public release/publish;
- root project license choice;
- destructive history rewriting or removal of existing public-facing history;
- any paid service or plan change.

## Security baseline

The repository uses:

- commit-pinned GitHub Actions;
- a full-history Gitleaks workflow;
- grouped Dependabot updates for GitHub Actions;
- local secret/credential ignore rules;
- repository tests that guard these baseline properties.

These checks reduce risk; they do not prove that a repository is free of every secret, vulnerability or licensing issue.

## Stop rule

If a required item is unknown or failed, keep the repository private and surface the smallest unresolved decision or evidence gap. Do not publish merely because a planned date has arrived.
