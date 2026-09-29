**[English](CONTRIBUTING.md)** · Deutsch

# Zu Loop42 beitragen

Loop42 bleibt bewusst klein und evidenzbasiert. Beiträge sollen Risiko, Komplexität, doppelte Arbeit oder Operator-Aufwand reduzieren, statt Prozess um des Prozesses willen zu erzeugen.

## Vor einer Änderung

1. Mit dem aktuellen `main` sowie vorhandenen Issues/PRs abgleichen.
2. Das konkrete Problem und das kleinste nützliche Delta definieren.
3. Capability, Value und Operator Fit prüfen, bevor eine neue Abhängigkeit, ein Dienst oder Workflow hinzukommt.
4. Vor kopiertem oder adaptiertem Code die Third-Party-Provenance prüfen.
5. Consumer-/Produktwahrheit außerhalb von Loop42 halten, außer es handelt sich ausdrücklich um einen generischen Contract oder eine Fixture.

## Pull Requests

Ein nützlicher PR soll nennen:

- das gelöste Problem;
- die exakt geänderte Oberfläche;
- die auf der eingereichten Revision ausgeführte Verifikation;
- relevante Gegenbeispiele/Fehlertests;
- neue Abhängigkeiten, Rechte oder externe Dienste;
- Provenance-/Lizenzhinweise für Third-Party-Material;
- bekannte Grenzen oder offene Evidence-Lücken.

Repository-Tests vor dem Einreichen ausführen:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

GitHub-CI und Secret Scan müssen grün bleiben.

## Datenschutz und Secrets

Nicht committen:

- echte Zugangsdaten, Tokens oder private Schlüssel;
- persönliche Cloud-Drive-IDs oder lokale Maschinenpfade, außer sie sind bewusst öffentlich und notwendig;
- private Gesprächsinhalte;
- private Consumer-/Projektzustände, die nicht in das generische Loop42-Repository gehören.

Für Beispiele synthetische Fixtures verwenden.

## Authority

Ein PR darf Änderungen vorschlagen, autorisiert aber keine geschützten Aktionen wie Veröffentlichung, Aktivierung kostenpflichtiger Dienste, destruktives Umschreiben der Historie, reale Maschinenausführung oder Consumer-Produktentscheidungen.

## Lizenz

Wer Material beiträgt, für das die nötigen Rechte bestehen, stimmt zu, dass der Beitrag unter Loop42s MIT-Lizenz verteilt werden darf, sofern eine Datei nicht ausdrücklich andere Bedingungen nennt.
