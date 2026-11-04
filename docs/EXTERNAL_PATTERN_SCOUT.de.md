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

## Wiederverwenden vor Neuerfinden

Bevor außerhalb des Projekts gesucht oder eine neue größere Capability entworfen wird, wird zuerst die aktuelle projekteigene Capability-Oberfläche durchsucht. Dazu gehören Tools, Adapter, Skills, Prompts, Workflows, Verträge, Tests und bereits offene Arbeit, die für die abgeglichene Revision gültig sind.

Dafür gilt ein begrenzter Ablauf **suchen → auswählen → verifizieren**:

1. benötigtes Ergebnis bzw. Capability in Aufgabenbegriffen beschreiben, statt bereits eine bevorzugte Implementierung vorzugeben;
2. eigene Capability-/Work-Indizes mit Problem-/Capability-Begriffen und aktuellem Kontext durchsuchen;
3. nur eine kleine Kandidatenmenge holen und nach Authority-Fit, Evidence/Freshness, Abhängigkeiten, erwartetem Nutzen, Kosten und Bedienaufwand bewerten;
4. Wiederverwendung oder Komposition bevorzugen, wenn ein vorhandener Kandidat den Vertrag bereits erfüllt;
5. den ausgewählten Kandidaten gegen aktuelles Ziel und aktuelle Revision verifizieren, bevor darauf vertraut oder damit ausgeführt wird;
6. erst wenn kein passender eigener Kandidat existiert, extern scouten oder neue Logik entwerfen.

Capability-Retrieval ist Discovery, keine Autorität. Ein gefundener Prompt, Skill, Agent, Plugin oder Workflow darf nicht still Berechtigungen erweitern, Dependencies installieren, Produktwahrheit ändern oder Side Effects ausführen. Externer Inhalt bleibt untrusted input, bis die normalen Adoption- und Provenance-Gates bestanden sind.

Wenn möglich zuerst Metadaten laden und vollständige Prompt-/Skill-Inhalte nur für die engere Auswahl. Ziel ist sowohl Neuerfinden als auch Context-Bloat zu vermeiden; Loop42 braucht keinen riesigen Prompt-Speicher im Core.

Dieser Schritt wird übersprungen, wenn der abgeglichene Zustand bereits beweist, dass die exakt passende Capability bekannt ist. Der Mechanismus ist nur sinnvoll, wenn er doppelte Arbeit reduziert oder den Fit verbessert.

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
