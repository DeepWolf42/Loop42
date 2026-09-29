# Contributing to Loop42

Loop42 is intentionally small and evidence-driven. Contributions should reduce risk, complexity, duplicated work or operator effort rather than add process for its own sake.

## Before changing code

1. Reconcile against the current `main` branch and existing issues/PRs.
2. Define the concrete problem and smallest useful delta.
3. Check capability, value and operator fit before adding a dependency, service or new workflow.
4. Review third-party provenance before copying or adapting code.
5. Keep consumer/product truth outside Loop42 unless the change is explicitly a generic contract or fixture.

## Pull requests

A useful PR should state:

- the problem it solves;
- the exact changed surface;
- verification performed on the submitted revision;
- relevant counterexample/failure testing;
- new dependencies, permissions or external services;
- provenance/license notes for third-party material;
- known limitations or open evidence gaps.

Run the repository test suite before submitting:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

GitHub CI and the secret scan must remain green.

## Privacy and secrets

Do not commit:

- real credentials, tokens or private keys;
- personal cloud-drive IDs or local machine paths unless they are intentionally public and necessary;
- private conversation content;
- private consumer/project state that does not belong in the generic Loop42 repository.

Use synthetic fixtures for examples.

## Authority

A PR may propose changes but does not authorize protected actions such as publication, paid-service activation, destructive history rewriting, real machine execution or consumer-product decisions.

## License

By contributing material you have the right to submit, you agree that your contribution may be distributed under Loop42's MIT License unless a file explicitly states different terms.
