# Dokumentations-Sprachregel

Status: aktive generische Repository-Regel  
Gilt für: Loop42 sowie Präsentations-/Dokumentationskonventionen von Consumer-Projekten

## Zweck

Menschenlesbare Repositories sollen auf Englisch und Deutsch verständlich sein, ohne dadurch zwei konkurrierende technische Wahrheiten zu erzeugen.

## Regeln

1. **Englisch ist die kanonische technische Sprache.**
   - Code, APIs, Schemas, Bezeichner, Testnamen, maschinenlesbare Contracts und technische Dateinamen bleiben Englisch, außer ein nutzerseitiges Format verlangt etwas anderes.
   - Commit- und CI-Konventionen bleiben Englisch-first.

2. **Zentrale menschenlesbare Dokumentation ist zweisprachig.**
   - Repository-Startseiten verwenden `README.md` (Englisch) und `README.de.md` (Deutsch).
   - Wichtige Overview-, Architektur-, Roadmap-/Status-, Contributor- und Getting-Started-Dokumente sollen eine deutsche Schwesterfassung besitzen, wenn sie aktiv für Menschen gepflegt werden.
   - Bevorzugtes Paar: `FOO.md` ↔ `FOO.de.md`.

3. **Übersetzungen sind keine zweite Projektwahrheit.**
   - Bei exakten Formulierungsunterschieden ist das englische technische Dokument kanonisch.
   - Die deutsche Fassung muss dieselbe technische Bedeutung, dieselben Grenzen, denselben Status und dasselbe Evidence-Niveau behalten.
   - Eine Übersetzung darf keine Fähigkeiten, Entscheidungen oder Anforderungen hinzufügen, die in der kanonischen Quelle nicht existieren.

4. **Maschinenmaterial wird nicht nur wegen Zweisprachigkeit dupliziert.**
   - Quellcode, Tests, JSON/YAML/TOML, generierte Artefakte, Hashes, Fixtures und Protokoll-Payloads werden nicht übersetzt.
   - Historische Evidence und archivierte Recherche dürfen in ihrer ursprünglichen Sprache bleiben, wenn eine Übersetzung nur Wartungsaufwand ohne praktischen Nutzen erzeugen würde.

5. **Die Sprachumschaltung bleibt sichtbar.**
   - Ein zweisprachiges Einstiegsdokument zeigt oben einen Umschalter Englisch/Deutsch.

6. **Dokumentpaare bleiben synchron.**
   - Inhaltliche Änderungen an aktiv gepflegten zweisprachigen Dokumenten sollen beide Sprachversionen im selben Arbeitsblock aktualisieren, sofern praktisch möglich.
   - Ist eine Übersetzung vorübergehend hinterher, wird das oben ausdrücklich markiert, statt veralteten Text still als aktuell darzustellen.

## Schreibstil

Repository-Texte bleiben beschreibend und evidenzbasiert. Keine Werbesprüche, kein Startup-Schaum und keine Fähigkeitsbehauptungen, die der aktuelle Projektstand nicht belegt. Die visuelle Identität darf Charakter haben; technische Aussagen bleiben wörtlich belastbar.

## Consumer-Projekte

Consumer-Repositories behalten ihre eigene Produktwahrheit und können diese Konvention übernehmen, ohne Loop42 zur Autorität für ihre Domäneninhalte zu machen. Die Sprachregel betrifft die Präsentationsstruktur, nicht Produktentscheidungen.
