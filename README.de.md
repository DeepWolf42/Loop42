**English:** [README.md](README.md) · **Deutsch**

# Loop42

<p align="center">
  <img src="docs/assets/loop42-mark.webp" alt="Loop42 Retro-Emblem" width="300">
</p>

Loop42 hilft dabei, lange KI-gestützte Entwicklungsarbeit **verständlich, überprüfbar und fortsetzbar** zu halten.

Statt dass Chats, Werkzeuge, Branches und verschiedene Worker mit der Zeit ihre eigenen Versionen der Realität entwickeln, kehrt Loop42 immer wieder zu ein paar einfachen Fragen zurück:

**Was stimmt gerade wirklich? Was ist als Nächstes sinnvoll? Dürfen und können wir das tun? Hat es tatsächlich funktioniert? Bringt eine weitere Runde noch etwas?**

## Einfach gesagt

Loop42 ist **kein** KI-Modell, keine Projektmanagement-App und keine zweite Datenbank für dein Projekt.

Es ist eine wiederverwendbare **Arbeitsmethode mit kleinen Werkzeugen**, die dafür sorgt, dass Menschen, KI-Modelle und Automatisierung am selben aktuellen Projektstand arbeiten.

| Typisches Problem | Antwort von Loop42 |
| --- | --- |
| Alte Chats oder Annahmen werden für aktuell gehalten | Zuerst mit den Live-Quellen abgleichen |
| Mehrere Worker laufen in unterschiedliche Richtungen | Einen verbindlichen Projektstand behalten |
| Automatisierung läuft weiter, nur weil sie kann | Klare Grenzen für Rechte, Fähigkeiten und Stopps |
| „Sieht gut aus“ ersetzt einen Nachweis | Belege liefern oder Unsicherheit sichtbar lassen |
| Nach Abbrüchen wird Arbeit doppelt gemacht | Aus Zustand, Entscheidungen und Checkpoints fortsetzen |
| Mehr Prozess wird mit mehr Fortschritt verwechselt | Stoppen, wenn eine weitere Runde keinen echten Nutzen bringt |

## Der Matrixloop

Die interne Methode heißt **Matrixloop**. In normalen Worten:

1. **Abgleichen** — den Live-Zustand prüfen, statt altem Kontext blind zu vertrauen.
2. **Ein Ziel wählen** — den nächsten sinnvollen und begrenzten Arbeitsschritt festlegen.
3. **Vorher nach Fehlern suchen** — offensichtliche Sackgassen erkennen, bevor Aufwand entsteht.
4. **Umsetzen oder prüfen** — genau die Arbeit erledigen, die wirklich nötig ist.
5. **Verifizieren** — das Ergebnis mit nachvollziehbaren Belegen prüfen.
6. **Reibung prüfen** — unnötiges Setup, Bedienaufwand und Komplexität erkennen.
7. **Nutzen prüfen** — bringt eine weitere Runde eine echte Verbesserung?
8. **Stoppen oder weiterdrehen** — nur mit einem konkreten Grund weitermachen.

Technische Kurzform:

`RECONCILE → TARGET → PRE-MORTEM → IMPLEMENT/INSPECT → VERIFY → FRICTION → VALUE CHECK → STOP/ITERATE`

Das ist ein Ablauf, kein Ritual. Wenn die nötigen Belege bereits vorhanden sind, dürfen Schritte zusammenfallen.

## Die wichtigsten Regeln

**Eine Wahrheit, viele Worker.**  
Das Projekt behält einen verbindlichen aktuellen Stand. Modelle und Werkzeuge dürfen prüfen, widersprechen und verbessern, aber nicht stillschweigend konkurrierende Projektstände erzeugen.

**Belege vor Selbstvertrauen.**  
Wichtige Aussagen brauchen nachvollziehbare Belege (im technischen Teil: Evidence), eine exakte Revision oder klar sichtbare Unsicherheit.

**Begrenzte Autonomie.**  
Automatisierung darf innerhalb klarer Rechte- und Fähigkeitsgrenzen handeln. Fehlender Zugriff, fehlende Belege oder fehlende Fähigkeiten werden nicht weggeraten.

**Nützliche Änderung statt Prozessvolumen.**  
Wenn eine Runde keine neue Entscheidung, keinen neuen Beleg, keinen Fehlerfund oder keine reale Verbesserung bringt, wird sie vereinfacht oder beendet.

**Recovery by Design.**  
Abgebrochene Arbeit soll aus aktuellem Zustand, akzeptierten Entscheidungen, verifizierten Ergebnissen und offenen Blockern sauber fortsetzbar sein.

**Standardmäßig portabel.**  
Anbieter-spezifisches Verhalten gehört hinter Adapter. Die Methode soll nicht von einem bestimmten KI-Anbieter, einer IDE, Chat-Oberfläche oder einem lokalen Modell abhängen.

**Execution Fit vor Bedienarbeit.**  
Bevor ein Mensch Setup-Schritte bekommt, wird geprüft, ob der Weg überhaupt machbar, sinnvoll und die Reibung wert ist.

## Wo Loop42 hingehört

Loop42 ist nicht an ein bestimmtes Projekt gebunden. Das **angebundenen Projekt behält seinen eigenen verbindlichen Produktstand**; Loop42 liefert die wiederverwendbare Arbeitsmethode und die unterstützende Mechanik.

CORA ist das erste angebundene Projekt. CORA behält seinen eigenen Produktzustand und pinnt eine exakt verifizierte Loop42-Revision, statt automatisch jedem neuen Commit auf `main` zu folgen.

## Hier anfangen

Wenn du das System verstehen willst, ohne dich zuerst durch jedes Dokument zu graben:

- [Matrixloop](docs/MATRIXLOOP.md) — Ablauf und Stopregeln
- [Execution Fit](docs/EXECUTION_FIT.de.md) — kann und soll diese Arbeit überhaupt ausgeführt werden?
- [Recovery and Truth](docs/RECOVERY_AND_TRUTH.md) — Regeln für aktuellen Stand, veraltete Informationen und Recovery
- [Harness Contract](docs/HARNESS_CONTRACT.md) — was eine Ausführungsumgebung können muss
- [Consumer Profile](docs/CONSUMER_PROFILE.md) — wie ein Projekt an eine exakte Loop42-Revision gebunden wird

<details>
<summary>Technische Referenz und Repository-Aufbau</summary>

### Evidence, Evaluation und externe Inputs

- `docs/TRUTH_AND_GAPS.md` / [Deutsch](docs/TRUTH_AND_GAPS.de.md) — begrenzte Evidence- und Gap-Workflows
- `docs/EXTERNAL_PATTERN_SCOUT.md` / [Deutsch](docs/EXTERNAL_PATTERN_SCOUT.de.md) — begrenztes externes Pattern-Scouting
- `docs/EVALUATION.md` — Frozen-Scenario- und Methoden-Evaluation
- `tests/frozen_scenarios/` — reproduzierbare Evaluationsszenarien

### Safety, Veröffentlichung und Herkunft

- `docs/LICENSE_POLICY.md` — Lizenzregel
- `docs/PUBLICATION_GATE.md` / [Deutsch](docs/PUBLICATION_GATE.de.md) — Safety- und Operator-Entscheidungs-Gate für Veröffentlichungen
- `THIRD_PARTY.md` — externe Quellen und Provenance-Ledger
- `SECURITY.md` / [Deutsch](SECURITY.de.md) — Security-Meldung und Grenze für sensible Informationen
- `CONTRIBUTING.md` / [Deutsch](CONTRIBUTING.de.md) — Regeln für Beiträge, Verifikation, Provenance und Datenschutz

### Sprache und Implementierung

- `docs/DOCUMENTATION_LANGUAGE_POLICY.md` / [Deutsch](docs/DOCUMENTATION_LANGUAGE_POLICY.de.md) — Regel für zweisprachige Dokumentation
- `tools/` — wiederverwendbare Harness-, Context- und Verification-Werkzeuge
- `adapters/` — Beispiele für Consumer-Integration

</details>

## Dokumentationssprachen

Menschenlesbare Kern-Dokumentation folgt grundsätzlich **Englisch + Deutsch**. Code, Schemas, APIs, Tests und andere maschinennahe Artefakte bleiben Englisch, damit Zweisprachigkeit keine zweite technische Wahrheit oder unnötige Wartungsarbeit erzeugt.

Siehe [Dokumentations-Sprachregel](docs/DOCUMENTATION_LANGUAGE_POLICY.de.md).

## Status

Loop42 ist ein öffentliches Entwicklungs-Repository.

Die **v0.1 Extraction-/Consumer-Binding-Foundation ist verifiziert**. Wiederverwendbare Context-/Harness-Mechanik, Frozen-CORA-Equivalence und der Exact-Revision-Consumer-Profile-Contract sind vorhanden.

CORA pinnt derzeit die verifizierte Loop42-Revision `de5be0fa5e085d63c8f98fe683f9936828478dbf`. Dieser Pin ist absichtlich exakt; Loop42 `main` darf unabhängig davon weiterlaufen.

Loop42 steht unter der MIT-Lizenz.

<details>
<summary>Warum 42?</summary>

Weil gute Systeme begrenzte Loops, ehrliche Evidence und wiederherstellbaren Zustand brauchen —  
und gelegentlich die richtige Frage vor der richtigen Antwort.

</details>
