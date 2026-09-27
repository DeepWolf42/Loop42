# Documentation Language Policy

Status: active generic repository policy  
Applies to: Loop42 and consumer-project repository presentation/documentation conventions

## Purpose

Human-facing repositories should be understandable in both English and German without creating two competing technical truths.

## Rules

1. **English is the canonical technical language.**
   - Code, APIs, schemas, identifiers, test names, machine-readable contracts and technical file names stay in English unless a user-facing format requires otherwise.
   - Commit and CI conventions remain English-first.

2. **Core human-facing documentation is bilingual.**
   - Repository landing pages use `README.md` (English) and `README.de.md` (German).
   - Important overview, architecture, roadmap/status, contributor and getting-started documents should have a German companion when they are actively maintained for people to read.
   - Preferred pairing: `FOO.md` ↔ `FOO.de.md`.

3. **Translations are not a second source of truth.**
   - The English technical document is canonical when exact wording differs.
   - The German version must preserve the same technical meaning, limits, status and evidence level.
   - A translation must not add capabilities, decisions or requirements that do not exist in the canonical source.

4. **Do not duplicate machine-facing material just to satisfy bilingual presentation.**
   - Source code, tests, JSON/YAML/TOML, generated artifacts, hashes, fixtures and protocol payloads are not translated.
   - Historical evidence and archived research may remain in their original language when translating it would add maintenance cost without practical value.

5. **Language navigation stays visible.**
   - A bilingual landing document should place an English/Deutsch switch at the top.

6. **Keep paired documents synchronized.**
   - Substantive changes to an actively maintained bilingual document should update both language versions in the same work block whenever practical.
   - If a translation is temporarily behind, say so explicitly at the top rather than silently presenting stale text as current.

## Writing style

Repository copy is descriptive and evidence-based. Avoid promotional filler, startup slogans and capability claims that are not supported by the current project state. Visual identity may have character; technical claims stay literal.

## Consumer projects

Consumer repositories keep their own product truth and may adopt this convention without making Loop42 authoritative for their domain content. The language policy governs presentation structure, not product decisions.
