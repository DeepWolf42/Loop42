# External Pattern Scout

Status: vorgeschlagener generischer Loop42-Workflow  
Kanonische Sprache: Englisch

## Zweck

Loop42 soll regelmäßig nach außen schauen, bevor Infrastruktur, Workflow-Mechanik, Safety-Gates, Recovery-Logik, Observability oder Agent-Orchestrierung neu erfunden werden.

Das Ziel ist kein Trend-Hopping. Gesucht werden kleine, wiederverwendbare Muster, die Risiko, Komplexität, Bedienaufwand oder doppelte Arbeit reduzieren können.

External Scouting ist ein Input für Matrixloop, keine neue Projektwahrheit und keine neue Loop-Stufe.

## Wann gescoutet wird

Ein begrenzter Scout ist sinnvoll, wenn mindestens eines davon gilt:

- eine neue Architektur- oder Orchestrierungsmechanik wird entworfen;
- das Projekt würde Infrastruktur bauen, die wahrscheinlich anderswo bereits existiert;
- ein wiederholter Fehler deutet darauf hin, dass andere Projekte dafür bereits ein belastbares Muster haben;
- eine Dependency- oder Provider-Entscheidung wird neu bewertet;
- ein geplanter Wartungs-Pulse ist fällig.

Normale Produktarbeit darf nicht blockieren, nur weil kein aktueller Scout existiert.

## Suchbreite

Gesucht wird nach dem **Problem**, nicht nur nach Projekten, die wie Loop42 aussehen.

Mit den wörtlichen Begriffen aus Nutzerziel oder Projekt starten und dann bewusst
auf Synonyme, Mechaniken und benachbarte Fachgebiete erweitern. Ein brauchbarer
Kandidat muss sich nicht selbst als KI-Agent, Loop oder Orchestrator bezeichnen,
wenn er denselben Fehlermodus löst.

Sinnvolle Suchfamilien sind unter anderem:

- KI / Agenten / Prompts / Context Engineering / Memory / Evals / Grader;
- Durable Workflows / State Machines / Checkpoints / Replay / Reconciliation;
- Distributed Systems / Idempotency / Optimistic Concurrency / Leases / Fencing /
  Event Sourcing / Saga / Outbox;
- Queues / Worker / Supervision / Retry / Circuit Breaker / Dead-Letter Handling /
  Backpressure / begrenzte Parallelität;
- inkrementelle Buildsysteme / Dependency Graphs / Invalidierung /
  content-addressed State / Reproduzierbarkeit / Caching;
- Policy / Provenance / Attestations / Audit / Autorisierung;
- Fault Injection / Chaos Engineering / Model Checking / Property-based Testing;
- relevante technische Regelsysteme, wenn ihr Problem zum Consumer-Fall passt.

Ein Scout soll relevante Familien stichprobenartig mischen, statt nur kleine
Varianten derselben Produktkategorie zu suchen. Keyword-Erweiterung ist eine
Discovery-Heuristik und keine Erlaubnis, einen größeren Backlog zu erzeugen.

Ein ähnliches Produkt ist weder Voraussetzung noch automatisch ein guter Fund.
Bevorzugt wird die kleinste übertragbare Mechanik, die das aktuelle Problem löst.

## Perspektiv-Probe

Wenn Unsicherheit, wiederholtes Scheitern oder eine wesentliche Designentscheidung
es rechtfertigt, DARF der Scout das Problem in einem begrenzten Durchlauf neu
betrachten, bevor Kandidaten ausgewählt werden. Nur Linsen verwenden, die Suche
oder Pre-Mortem tatsächlich verändern können:

- **Danach-Linse** — wenn der aktuelle Plan funktioniert, was wird zum nächsten
  Engpass, zur ungültigen Annahme oder zum Bedienaufwand?
- **Umkehr-Linse** — welche zentrale Annahme würde den aktuellen Problemrahmen
  falsch machen, und zeigt Entfernen oder Umkehren einer Abhängigkeit einen
  einfacheren Weg?
- **Außen-Linse** — wie würde ein Operator, Maintainer, Safety-Reviewer oder ein
  benachbartes Fachgebiet dasselbe Problem beschreiben?

Die Probe liefert höchstens ein oder zwei konkrete alternative Hypothesen oder
Suchrichtungen. Sie ist keine Brainstorming-Pflicht und MUSS entfallen, wenn sie
keine eigene Entscheidung, kein neues Evidence-Ziel und keine neue
Fehlerhypothese erzeugt.


## Lückenerkennung und Wiederverwendungsprüfung

Vor größerer neuer Infrastruktur, einer wichtigen Workflow-Änderung oder
wiederholtem Scheitern **eine begrenzte Lücken- und Reuse-Probe in RECONCILE /
TARGET** durchführen. Sie ist Teil des vorhandenen Matrixloop und der
/truth-/gaps-Prüfungen, **keine zusätzliche Loop-Stufe**, kein Agent, Scheduler,
Zustandsspeicher, Recht oder neuer Wahrheitsanspruch.

1. **Zuerst abgleichen.** Vereinbartes Ziel, Abnahmekriterien, aktuelle Quelle
   und Revision, vorhandene Implementierung, offene Issues/PRs/Branches,
   frühere Recherche und Fähigkeiten bereits vorhandener Werkzeuge festhalten.
   Designziele, Drafts und Tests auf alten Revisionen sind keine integrierten
   aktuellen Funktionen.
2. **Kleinen Umfang abstecken.** Den betroffenen durchgängigen Arbeitsweg und
   Fehlermodi stichprobenartig prüfen statt nur die erstgenannte Bibliothek/API.
   Bei Bedarf Bedienweg, Sicherheit, Recovery sowie Dependency-/License-Folgen
   einbeziehen; nicht bei jedem Aufruf das gesamte Produkt auditieren.
3. **Suchabdeckung ehrlich kennzeichnen.** Je relevantem Ausschnitt zwischen
   `CHECKED_NO_DELTA` (auf benannter Grundlage geprüft, kein nützlicher Gewinn),
   `USEFUL_CANDIDATE` (belegte prüfbare Alternative), `NOT_SEARCHED`
   (Recherche-Lücke) und `BLOCKED_UNKNOWN` (Quelle, Fähigkeit oder Beleg
   fehlt) unterscheiden. **NOT_SEARCHED ist nicht NO_USEFUL_DELTA.** Fehlende
   Quellen sind kein Negativbefund; Grenze nennen und abhängige Behauptung stoppen.
4. **Wiederverwenden vor Neuerfinden.** Vorhandene eigene Implementierung,
   offene Arbeit, unterstützte Funktionen installierter Werkzeuge und neue
   Plugin-/SDK-Möglichkeiten mit kleinen externen Mustern vergleichen. Auch
   benachbarte Fachgebiete und reale Bedienerprobleme prüfen, wenn sie eine
   Entscheidung verändern können. `REUSE_EXISTING` oder `SMALL_ADAPTER`
   einem neuen Framework vorziehen.
5. **Priorisieren und stoppen.** Wenige wesentliche blinde Flecken nach
   Auswirkung, Safety/Korrektheit, gespartem Aufwand, Kosten und Unsicherheit
   ordnen. Kleinsten reproduzierbaren Gegenfall oder Kompatibilitätstest
   auswählen oder einen begrenzten `NEEDS_RESEARCH`-Folgeschritt nennen.
   Kandidaten- und Zeit-/Run-Budget beachten; keine Aufgaben nur für eine
   vollständige Matrix erzeugen.

Ergebnis ist ein kleines **Abdeckungs-Delta**, kein Vollständigkeitsversprechen:
geprüfter Umfang und Revision, wichtigste bislang übersehene Suchrichtung,
Quellen/Aktualität, bereits vorhandene eigene Stärke, kleinste sinnvolle
Fremdlösung, Einführungs-/Prüfaufwand, offene Unsicherheiten und nächster Test
oder `NO_USEFUL_DELTA`. Gültige frühere Prüfergebnisse wiederverwenden, solange
ihre Abhängigkeiten unverändert sind. Design, offene PR, Benchmark-Behauptung
oder ungetestete Idee nie stillschweigend zu integrierter Funktion erklären.
Produktbezogene Ergebnisse bleiben in der autoritativen Consumer-Quelle;
der Scout schlägt nur Muster vor. Umsetzung und geschützte Entscheidungen
behalten ihre bisherigen Freigabegrenzen.

## Scout-Contract

Ein Scout braucht:

- eine klare Problemfrage;
- ein zum Thema passendes Freshness-Fenster;
- ein kleines Kandidatenlimit;
- ein Zeit-/Run-Budget;
- explizite Stopbedingungen.

Für jeden Kandidaten werden festgehalten:

1. Quelle/Projekt und nach Möglichkeit exakte Revision oder datierte Referenz;
2. das konkrete Loop42- oder Consumer-Problem, das dadurch besser werden könnte;
3. das Muster, das sich zu übernehmen lohnt;
4. was ausdrücklich **nicht** kopiert oder angenommen werden darf;
5. License-/Provenance-Status für jede Code-Wiederverwendung;
6. Evidence-Level: VERIFIED_SOURCE, PLAUSIBLE_PATTERN oder NEEDS_VERIFICATION;
7. erwarteter Nutzen gegenüber Einführungs- und Wartungskosten.

## Adoption Gate

Fund ist nicht Übernahme.

Ein Kandidat darf die Implementierung erst beeinflussen, wenn er diese Prüfungen besteht:

1. **Relevanz** — löst ein aktuelles Problem statt nur Neuheit zu erzeugen;
2. **Fit** — respektiert Source of Truth, Autoritätsgrenzen und Provider-Portabilität;
3. **Value** — Nutzen steht im Verhältnis zu neuer Komplexität und Wartung;
4. **Provenance** — kopierter oder adaptierter Code hat exakte Quellen- und Lizenzprüfung;
5. **Verification** — das übernommene Muster wird gegen das aktuelle Projekt reproduziert, bevor es als brauchbare Evidence gilt.

Architekturideen dürfen unabhängig neu implementiert werden, wenn kein Code kopiert wird. Direkte Code-Wiederverwendung durchläuft weiterhin das normale Third-Party-Provenance- und License-Gate.

## Ergebnis

Ein brauchbarer Scout endet mit genau einem dieser Ergebnisse:

- **ADOPT_CANDIDATE** — ein begrenztes Muster lohnt einen Matrixloop-Test;
- **PARK** — interessant, aber aktuell nicht gerechtfertigt;
- **NO_USEFUL_DELTA** — nichts Gefundenes schlägt den aktuellen Ansatz.

Ein Scout darf keine Arbeit erzeugen, nur weil Kandidaten existieren.

## Anti-Patterns

Nicht:

- Frameworks importieren, nur weil sie populär sind;
- Code vor License-/Provenance-Prüfung kopieren;
- Stars, Benchmarks, Blog-Claims oder Modellvertrauen als Beweis für Projekt-Fit behandeln;
- externe Projekte die Consumer-Produktwahrheit definieren lassen;
- Scouting in einen unbegrenzten Research-Backlog verwandeln;
- dasselbe verworfene Muster ohne neue Evidence ständig neu entdecken.

## Verhältnis zu Consumer-Projekten

Loop42 besitzt die generische Scouting-Methode. Consumer-Projekte entscheiden selbst, ob ein gefundenes Muster für ihre Domäne relevant ist.

CORA kann zum Beispiel ein generisches Checkpoint- oder Authority-Muster übernehmen, ohne Produktsemantik, Druckerannahmen oder Safety-Claims eines Fremdprojekts zu importieren.

## Ausführbarer, optionaler Preflight

Der lesende Check `python -m tools.checks.gap_reuse_preflight` ist in [Gap & Reuse Preflight](GAP_REUSE_PREFLIGHT.de.md) beschrieben. Ein Host muss ihn innerhalb von RECONCILE / TARGET ausdrücklich aufrufen; er führt keine eigene Websuche aus und läuft nicht bei jeder Codeänderung. Fehlende PR-, Tool- und externe Recherchedaten bleiben `NOT_SEARCHED`, bis ein autorisierter Adapter sie liefert. Die CLI ist noch kein autonomer vollständiger Scout und keine Freigabe.
