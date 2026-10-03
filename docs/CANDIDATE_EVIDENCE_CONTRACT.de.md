**Deutsch** · [English](CANDIDATE_EVIDENCE_CONTRACT.md)

# Vertrag für evidenzgebundene Kandidatenbewertung

Status: generischer Methodenvertrag; keine Laufzeitfunktion und keine Consumer-Übernahme werden dadurch behauptet

## Zweck

Manche Consumer müssen zwischen mehreren technisch brauchbaren Wegen wählen und dabei Evidenz, harte Randbedingungen und Unsicherheit erhalten. Loop42 darf dieses Muster generisch unterstützen, ohne Domänenlogik zu übernehmen.

Die generische Frage lautet:

> Welche einer endlichen Menge consumer-definierter Kandidaten scheiden an harten Randbedingungen aus, welche bleiben UNKNOWN und welche nicht-dominierten Kandidaten bleiben für eine consumer-eigene Entscheidung übrig?

Dieser Vertrag bleibt absichtlich domänenneutral.

## Bestehende Verträge bleiben maßgeblich

Der Vertrag ergänzt Matrixloop, `/truth`, `/gaps`, Action Policy und Consumer Profile. Er erzeugt keinen zweiten Loop, keinen neuen State Store, keine zusätzliche Autorität und keine neue Produktwahrheit.

Consumer-Repositories behalten Anforderungen, Policies, Domänenmodelle, Ziele/Gewichte, Sicherheitsbedeutung und die Semantik der abschließenden Empfehlung.

## Generische Begriffe

### Evidenzgebundene Aussage

Eine entscheidungsrelevante Aussage sollte genug Kontext behalten, um ihre aktuelle Anwendbarkeit prüfen zu können:

- Quellen-/Referenzidentität;
- Revision, Artefakt-Hash oder andere stabile Identität, soweit vorhanden;
- Geltungsbereich, Kontext und Bedingungen;
- Freshness-/Abhängigkeitszustand;
- explizite Annahmen und Grenzen;
- mit dem Consumer kompatibler Evidenz-/Gültigkeitsstatus.

Loop42 darf keinen universellen numerischen Confidence-Wert verlangen. Freshness, Provenienz, Anwendbarkeit, Unsicherheit und Gültigkeit sind verschiedene Dimensionen und dürfen nicht still in eine Zahl gepresst werden.

### Capability-Aussage

Eine Capability-Aussage beschreibt, dass ein Subjekt unter expliziten Bedingungen und mit expliziter Evidenz eine consumer-definierte Fähigkeit bereitstellen kann.

Konzeptionell:

```text
Subjekt
+ Capability-Identifier
+ Bedingungen
+ Evidenzreferenzen
+ Anwendbarkeit/Freshness
+ Status
```

Identifier und fachliche Bedeutung der Capability gehören dem Consumer.

Ein Produktname, Modell, Anbieter oder Label ist für sich allein kein Beweis, dass die Fähigkeit verfügbar ist.

### Kandidat

Ein Kandidat ist eine undurchsichtige consumer-definierte Option mit deterministischer Identität. Loop42 schreibt ihre internen Domänenfelder nicht vor.

Der Consumer darf Kandidaten selbst oder durch einen autorisierten deterministischen Producer erzeugen. Kandidatenerzeugung und Kandidatenbewertung bleiben getrennt.

### Constraint-Ergebnis

Die Bewertung einer consumer-definierten Randbedingung sollte auf einen kleinen expliziten Zustand hinauslaufen, etwa:

- PASS — anwendbare Evidenz stützt die Erfüllung;
- FAIL — anwendbare Evidenz belegt die Verletzung;
- UNKNOWN — Evidenz fehlt, ist stale, widersprüchlich, nicht anwendbar oder unzureichend.

Ein UNKNOWN bei einer harten Randbedingung darf durch keinen Ranking-Score zu PASS werden.

Der Consumer definiert, welche Randbedingungen hart und welche verhandelbar sind.

## Generische Auswertungsreihenfolge

Eine wiederverwendbare Loop42-kompatible Bewertung sollte folgende Reihenfolge erhalten:

1. maßgebliche Inputs und exakte Revisionen abgleichen;
2. deterministische Kandidatenidentitäten herstellen;
3. harte Randbedingungen mit PASS / FAIL / UNKNOWN und Evidenzreferenzen bewerten;
4. nur tatsächlich ausgeschlossene Kandidaten entfernen;
5. stoppen oder Auflösung anfordern, wenn ein entscheidungskritisches UNKNOWN einen sinnvollen/sicheren Vergleich blockiert;
6. consumer-definierte Zielwerte nur für ausreichend belegte brauchbare Kandidaten berechnen;
7. bei gewünschter Pareto-Reduktion Kandidaten entfernen, die über die deklarierten Ziele dominiert werden;
8. verbleibende Entscheidungsmenge samt Gründen, Evidenz und offenen Grenzen zurückgeben;
9. fachliche Empfehlung und jede Nebenwirkung der Consumer-Policy/-Autorität überlassen.

Ein Consumer kann bewusst eine andere Entscheidungsregel verwenden. Loop42 erzwingt keinen universellen Optimierer.

## Reproduzierbarkeit

Eine Kandidatenbewertung sollte aus ihrer deklarierten Basis reproduzierbar sein.

Wo sinnvoll, können Consumer Folgendes fingerprinten:

- Kandidatenidentität;
- Anforderungs-/Constraint-Menge;
- Capability-/Evidenz-Inputs;
- Zieldefinitionen;
- Evaluator-Version/-Konfiguration.

Eine Wiederholung auf derselben deklarierten Basis darf sich nicht still ändern, weil irgendwo eine unabhängige Quelle geändert wurde.

Ändern sich relevante Abhängigkeiten, werden frühere Ergebnisse nach der bestehenden Evidenzsemantik des Consumers STALE oder neu zu bewerten.

## Robustheit und Betriebsfenster

Loop42 darf generisch zwischen Folgendem unterscheiden:

- behauptetem/beobachtetem Maximum; und
- consumer-definiertem zuverlässigem Betriebsfenster unter angegebenen Bedingungen.

Loop42 bestimmt nicht die technische Reserve. Wie Robustheit, Störgrößen und Margin berechnet werden und welche Evidenz genügt, gehört dem Consumer.

## Provenienz ist keine Vertrauensrangliste

Quellenklassen dürfen gespeichert werden, aber generisches Loop42 darf nicht annehmen, dass eine Klasse immer vertrauenswürdiger ist als eine andere.

Ein lokaler Test kann sehr gut passen, aber schlecht ausgeführt sein; ein Herstellerwert kann sauber gemessen, aber schlecht übertragbar sein. Der Consumer bewertet die Eignung der Evidenz zur konkreten Aussage.

Widersprüchliche anwendbare Evidenz bleibt sichtbar, bis Consumer-Regeln oder direkte Verifikation sie auflösen.

## Autoritätsgrenze

Dieser Vertrag erlaubt Loop42 nicht:

- Domänenanforderungen zu erfinden;
- Consumer-Sicherheitsgrenzen festzulegen;
- versteckte Präferenzgewichte zu vergeben;
- Modellübereinstimmung in Evidenz umzudeuten;
- UNKNOWN zu PASS zu machen;
- reale Aktionen auszuwählen oder auszuführen;
- einen exakten Loop42-Pin eines Consumers vorzurücken.

Modellausgaben dürfen Kandidaten oder Interpretationen nur dort vorschlagen, wo der Consumer diese Rolle bereits zulässt. Bis zur unabhängigen Prüfung nach Consumer-Vertrag bleiben sie Vorschläge.

## Beispielabbildung eines Consumers

Ein FDM-Consumer könnte Folgendes abbilden:

```text
Kandidat = Material + Maschine + Bauorientierung + Prozessfenster
harte Randbedingungen = Einsatztemperatur, Geometrie, Maschinenfenster, nötige Evidenz
Ziele = Robustheit, Zeit, Kosten, Masse, Oberfläche oder andere deklarierte Ziele
```

Loop42 kennt keine FDM-Bedeutung. Es erhält nur die generische Bewertungs-/Evidenzmechanik.

## Übernahmeregel

Ein Consumer übernimmt diesen Vertrag nur über seine bestehende Bindung an eine exakte Revision samt Äquivalenz-/Verifikationsprozess.

Das Mergen dieses Dokuments in Loop42 beweist keine Laufzeitimplementierung, ändert kein Consumer Profile und erzeugt keine automatische Decision Engine.
