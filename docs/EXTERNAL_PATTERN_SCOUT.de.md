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
