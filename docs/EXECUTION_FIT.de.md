# Execution Fit

Status: aktive generische Matrixloop-Regel  
Kanonische technische Fassung: [EXECUTION_FIT.md](EXECUTION_FIT.md)

Execution Fit verhindert, dass ein technisch korrekter Plan zu unnötiger Arbeit für den Operator wird. Die Prüfung findet in **TARGET** und **PRE-MORTEM** statt, bevor detaillierte Setup- oder UI-Anweisungen gegeben werden.

## Entscheidungsreihenfolge

### 1. Capability Fit

Prüfe zuerst, ob der vorgeschlagene Weg in der aktuellen Umgebung tatsächlich verfügbar ist.

Materielle Voraussetzungen umfassen zum Beispiel:

- Fähigkeiten vorhandener Tools oder Connectoren;
- Sichtbarkeit eines Repositories sowie Account-/Tarifberechtigungen;
- Rechte und Richtlinien;
- Betriebssystem- und Softwareversion;
- Hardware- und Netzwerkverfügbarkeit;
- notwendige Zugangsdaten oder externe Dienste;
- kostenpflichtige oder irreversible Voraussetzungen.

Aus einem sichtbaren UI-Schalter darf nicht automatisch geschlossen werden, dass eine Funktion tatsächlich wirksam genutzt werden kann. Ist eine Funktion im aktuellen Tarif nur sichtbar, aber nicht durchsetzbar, oder durch Rechte blockiert, gilt die Voraussetzung als nicht erfüllt.

### 2. Value Fit

Prüfe danach, ob sich der Weg für das eigentliche Ziel lohnt.

Berücksichtige:

- erwarteten praktischen Nutzen;
- finanzielle Kosten;
- Setup- und Wartungsaufwand;
- Auswirkungen auf Sicherheit und Zuverlässigkeit;
- spätere Bindung oder Migrationskosten;
- ob ein einfacherer Weg das Ziel bereits ausreichend erfüllt;
- ob ein anderes oder neues Tool genug Netto-Vorteil bringt, um Wechsel-, Lern-, Wartungs-, Lock-in- und Operator-Kosten zu rechtfertigen.

Ein kostenpflichtiges Upgrade, eine neue Abhängigkeit oder eine komplexere Architektur braucht einen proportionalen Mehrwert. Ein Weg wird nicht nur deshalb weiterverfolgt, weil bereits Arbeit hineingeflossen ist.

### 3. Operator Fit

Wähle unter den brauchbaren Wegen die Variante mit dem geringsten Reibungsverlust, die Ziel sowie Safety-/Quality-Grenzen noch erfüllt.

Bevorzuge:

- einen ausführbaren Block statt vieler zerstückelter Einzelbefehle;
- vorhandene Werkzeuge, solange sie insgesamt der beste Fit bleiben;
- ein neues Tool, wenn sein belegbarer Netto-Vorteil die Wechsel-, Lern-, Wartungs-, Lock-in- und Operator-Kosten klar überwiegt;
- reversible Änderungen statt invasivem Setup;
- automatische Verifikation statt manueller Werteprüfung;
- direkte Evidenz statt Screenshot-Ketten;
- Vorgaben, die zur echten Umgebung passen, statt generischer Standardanweisungen.

Vermeide:

- unnötiges Copy/Paste;
- wiederholte Fragen zu bereits bekanntem Kontext;
- UI-Navigation bevor Voraussetzungen geprüft sind;
- Setup-Schritte, die später gar nicht wirksam werden können;
- Prüfungen durch den Operator, die vorhandene Tools selbst durchführen können.

## Entscheidungshoheit des Operators

Weniger Operator-Aufwand darf niemals stillschweigend weniger Entscheidungshoheit bedeuten.

Automatisierung darf ohne Unterbrechung nur innerhalb bereits freigegebener, begrenzter und reversibler Arbeit weiterlaufen. Die letzte Entscheidung bleibt beim Operator für geschützte Aktionen wie:

- Geld ausgeben oder kostenpflichtige Dienste aktivieren;
- Veröffentlichen, Releasen, Mergen in einen geschützten Produktzustand oder Ändern der Repository-Sichtbarkeit;
- reale Maschinenbewegung, Heizung, Aktorik oder andere physische Aktionen;
- Änderungen an Safety-, Quality- oder Authority-Grenzen;
- destruktive oder wesentlich irreversible Änderungen;
- grundlegende Produkt-Richtungsentscheidungen außerhalb des aktuell freigegebenen Ziels.

Decision Compression soll die Zahl der Unterbrechungen reduzieren, nicht diese Entscheidungen wegautomatisieren. Wenn eine geschützte Entscheidung nötig ist, wird die kleinstmögliche Entscheidung vorgelegt, die echte Wahlfreiheit erhält.

## Aufgaben- und Automationskompression

Task-Kapazität und Operator-Aufmerksamkeit sind begrenzte Ressourcen.

Bevor ein weiterer Agent, geplanter Task, Spezialisten-Job oder Monitoring-Loop erzeugt wird:

1. prüfen, ob die Arbeit im aktuellen Lauf erledigt werden kann;
2. prüfen, ob sie ohne Verantwortungsunklarheit in einen bestehenden Task integriert werden kann;
3. prüfen, ob ein lokaler Worker die begrenzte Vorarbeit übernehmen kann, statt einen knappen Orchestrierungs-Slot zu belegen;
4. einen neuen dauerhaften Task nur erzeugen, wenn die Trennung einen klaren Mehrwert hat.

Ein kohärenter Task mit mehreren verwandten Quellen ist mehreren überlappenden Watchern vorzuziehen. Freie Kapazität für unerwartete oder besonders wertvolle Arbeit soll bewusst erhalten bleiben.

## Ressourcen- und Client-Fit

Ausführungskapazität und Client-Verfügbarkeit sind ausdrückliche Voraussetzungen.

Vergleiche vor einer Eskalation oder Aufteilung die gesamten Ausführungskosten der brauchbaren Wege: knappe Modell-/Agenten-Kapazität, Tool-Aufrufe, wiederholtes Laden des Kontexts, Operator-Aufwand, Latenz, Fehler-/Recovery-Risiko und Qualität der Verifikation. Direkte Überlegung oder ein enger Tool-Aufruf genügt oft; eine feste Chat-zuerst-Reihenfolge ist aber nicht vorgeschrieben. Ein Spezialist oder ein länger laufender Agent kann die begrenzte Aufgabe mit geringeren Gesamtkosten und gleich guter oder besserer Verifikation abschließen. Bündele kompatible Arbeit, wenn dadurch Kontext nicht mehrfach geladen werden muss; Verifikation und Verantwortlichkeit müssen klar bleiben.

Behandle tarifabhängige Kontingente, Rate Limits, Modell-/Agenten-Nutzung, Task-Slots und Kontext als endliche Ressourcen. Verbrauche knappe Kapazität nicht durch wiederholte vollständige Abgleiche, doppelte Prüfungen, vermeidbares Polling oder erneutes Lesen von Evidenz, die für die Entscheidung noch aktuell genug ist. Halte Reserven für Fehler, hochwertige Umsetzung und Recovery frei.

Prüfe auch den aktiven Client oder Host. Browser, Desktop, Mobilgerät und automatisierte Laufzeit können selbst im selben Konto unterschiedliche Fähigkeiten anbieten. Fehlt die gewählte Aktion im aktuellen Client, wiederhole gescheiterte Versuche nicht endlos und gib keine langen unbrauchbaren Klickpfade vor. Bereite die begrenzte Arbeit vor, wechsle oder verschiebe sie auf einen geeigneten Client, wenn praktikabel, oder wähle einen einfacheren Ausweichweg, der das Ziel erhält.

## Tool-Routing und Client-Übergabe

Wähle Tools nach Aufgabenform und gesamten Ausführungskosten statt nach einer festen Eskalationsleiter. Stufen dürfen übersprungen werden, wenn ein Spezialistenweg klar günstiger oder zuverlässiger ist.

- Nutze direkte Überlegung, wenn weder frischer externer Zustand noch Dateiänderung oder spezielle Ausführung nötig ist.
- Nutze einen engen Connector-/Tool-Aufruf, wenn eine maßgebliche Quelle oder begrenzte Aktion genügt.
- Nutze ein Spezialwerkzeug, wenn seine fachliche Fähigkeit Korrektheit, Qualität oder Operator-Aufwand wesentlich verbessert, etwa Design-Tools für bearbeitbare UI-Arbeit.
- Nutze einen Coding-/Repository-Agenten, wenn Umsetzung, Repository-Prüfung, Tests oder Patch-Iteration die Aufgabe bestimmen.
- Nutze länger laufende oder appübergreifende Ausführung, wenn das Ziel mehrere Systeme oder Schritte umfasst und sonst wiederholten Kontextaufbau oder manuelle Orchestrierung erfordert.
- Rufe nicht mehrere überlappende Tools nur zur gefühlten Absicherung auf; ein zusätzliches Tool braucht eigenständigen Evidenz- oder Ausführungswert.

Ist der gewählte Weg im aktuellen Client nicht verfügbar, erstelle eine begrenzte Übergabe statt die Aufgabe von vorn zu beginnen. Verwende den vorhandenen Arbeitsnachweis oder Chat und keinen zweiten Zustandsspeicher. Die Übergabe enthält nur das Nötige: Ziel, maßgebliche Live-Basis/Revisionen, abgeschlossene Vorbereitung, gewähltes Tool/Vorgehen, verbleibende Aktion, Akzeptanz-/Stop-Bedingung und noch erforderliche geschützte Freigaben.

Prüfe bei Wiederaufnahme nur veränderliche Abhängigkeiten und Live-HEADs, die die Übergabe ungültig machen könnten. Stabile Vorbereitung und unbeeinflusste Evidenz werden wiederverwendet.

## Verhalten bei fehlendem Fit

Wenn Capability Fit fehlschlägt:

1. den blockierten Weg vor weiterem Setup stoppen;
2. die fehlende Voraussetzung oder Einschränkung nennen;
3. nach einer einfacheren brauchbaren Alternative suchen;
4. bewerten, ob Bezahlen, Upgraden oder zusätzliche Komplexität den Mehrwert rechtfertigen;
5. Operator-Anweisungen erst für den ausgewählten tatsächlich ausführbaren Weg geben.

Wenn Value Fit fehlschlägt, wird der Weg verworfen oder geparkt.

Wenn Operator Fit fehlschlägt, wird der Ausführungsweg vereinfacht, bevor Arbeit an den Operator abgegeben wird.

## Evidenz

Execution-Fit-Aussagen sollen sich auf aktuelle, für die Entscheidung passende Evidenz stützen: Live-Account-/Repository-Zustand, Tool-Fähigkeitsantworten, exakte Hardware-/Softwaredaten, aktuelle Dokumentation oder eine direkt reproduzierte Einschränkung.

Eine plausible Annahme reicht nicht, wenn sie Operator-Arbeit, Kosten oder eine Architekturentscheidung auslösen würde.

## Eingefrorenes Regressionsszenario

`tests/frozen_scenarios/execution_fit_private_repo_paid_feature_v1.json` hält den Fehlerfall fest, der diese Regel ausgelöst hat:

- ein privates Repository zeigt eine UI für Branch-Rulesets;
- deren Durchsetzung erfordert einen kostenpflichtigen Tarif;
- der schlechte Weg gibt zuerst detaillierte Setup-Schritte und prüft den Tarif erst danach;
- der erwartete Weg prüft zuerst die Voraussetzung, bewertet den Mehrwert eines Upgrades, verwirft unnötige Komplexität, bietet die einfachste brauchbare Alternative an und gibt erst dann ausführbare Schritte.

Das Szenario ist generisch. GitHub dient nur als konkrete Fixture, damit der Operator-Friction-Fehler reproduzierbar bleibt.
