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
- ob ein einfacherer Weg das Ziel bereits ausreichend erfüllt.

Ein kostenpflichtiges Upgrade, eine neue Abhängigkeit oder eine komplexere Architektur braucht einen proportionalen Mehrwert. Ein Weg wird nicht nur deshalb weiterverfolgt, weil bereits Arbeit hineingeflossen ist.

### 3. Operator Fit

Wähle unter den brauchbaren Wegen die Variante mit dem geringsten Reibungsverlust, die Ziel sowie Safety-/Quality-Grenzen noch erfüllt.

Bevorzuge:

- einen ausführbaren Block statt vieler zerstückelter Einzelbefehle;
- bereits installierte Werkzeuge statt neuer Abhängigkeiten;
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
