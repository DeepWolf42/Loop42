# Publication Gate

Status: aktive Pre-Publication-Checkliste  
Gilt für: Loop42 öffentlich schalten oder einen Release veröffentlichen

Veröffentlichung ist eine geschützte Operator-Entscheidung. Automatisierung darf das Repository vorbereiten und verifizieren, aber ohne ausdrückliche Freigabe weder die Repository-Sichtbarkeit ändern noch einen Release veröffentlichen.

## Vor öffentlicher Sichtbarkeit erforderlich

- Die exakte Kandidaten-Revision hat grüne Repository-CI.
- Der Full-History-Secret-Scan ist auf der exakten Kandidaten-Revision grün.
- Lokale Zugangsdaten, Tokens, private Schlüssel, maschinenspezifische Pfade und persönliche Konfiguration sind nicht Teil der versionierten Repository-Inhalte.
- Third-Party-Quellen sowie CI-/Runtime-Abhängigkeiten haben einen releasespezifischen Provenance- und Lizenz-Check.
- Eine Root-Projektlizenz wurde bewusst gewählt und für den öffentlichen Release hinzugefügt.
- README-/Status-Text behauptet nicht mehr, dass das Repository privat ist.
- Repository-Historie und Author-Metadaten wurden auf Informationen geprüft, die der Operator nicht öffentlich machen möchte.
- Für den gewählten Veröffentlichungszustand nötige öffentliche Security-/Kontakt-Hinweise sind vorhanden.
- Offene Draft-Arbeit ist entweder bewusst nicht Teil des Releases oder ausdrücklich integriert und verifiziert.

## Geschützte Entscheidungen

Die letzte Entscheidung bleibt beim Operator für:

- Repository-Sichtbarkeit;
- Public Release/Publish;
- Wahl der Root-Projektlizenz;
- destruktives Umschreiben der Historie oder Entfernen bestehender Historie;
- kostenpflichtige Dienste oder Tarifänderungen.

## Security-Baseline

Das Repository verwendet:

- auf Commit-SHAs gepinnte GitHub Actions;
- einen Full-History-Gitleaks-Workflow;
- gruppierte Dependabot-Updates für GitHub Actions;
- lokale Ignore-Regeln für Secrets/Zugangsdaten;
- Repository-Tests, die diese Baseline absichern.

Diese Prüfungen reduzieren Risiko; sie beweisen nicht, dass das Repository frei von jedem Secret, jeder Schwachstelle oder jedem Lizenzproblem ist.

## Stopregel

Wenn ein erforderlicher Punkt unbekannt oder fehlgeschlagen ist, bleibt das Repository privat und es wird nur die kleinste noch offene Entscheidung oder Evidence-Lücke vorgelegt. Ein geplanter Termin allein ist kein Veröffentlichungsgrund.
