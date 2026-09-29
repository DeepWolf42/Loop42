**[English](TRUTH_AND_GAPS.md)** · Deutsch

# /truth und /gaps

Status: Arbeitsvertrag für Agenten; ein ausführbarer Slash-Command-Router ist nicht implementiert.

Die Befehle machen vorhandene Matrixloop-Prüfungen gezielt aufrufbar. Sie schaffen keinen zweiten Loop, Zustandsspeicher, Wahrheitsanspruch oder zusätzliche Berechtigung. Maßstab ist das vereinbarte aktuelle Ziel. Im Gespräch gilt Groß-/Kleinschreibung nicht (`/Truth` entspricht `/truth`); native Befehlsunterstützung durch den Host darf daraus nicht abgeleitet werden.

## /truth — Belege prüfen

1. Maßgebliche Quellen und exakte aktuelle Revisionen einschließlich der vom Consumer fest gebundenen Loop42-Version ermitteln. Prüfumfang, Zeitpunkt und nicht verfügbare Quellen nennen.
2. Entscheidungsrelevante Aussagen mit Quellen, Code und Prüfergebnissen abgleichen. „Fertig“ in einer Dokumentation ist zunächst eine Behauptung.
3. Je Aussage Beleg, gültige Revision/Kontext, Einschränkung und Status angeben:
   - CONFIRMED: direkt passende Belege stützen genau diese Aussage.
   - ASSUMED: ausdrücklich gekennzeichnete Arbeitsannahme.
   - UNVERIFIED: Belege fehlen, sind nicht zugänglich oder reichen nicht aus.
   - CONTRADICTED: passende Belege widerlegen die Aussage; Gegenbeispiel nennen.
   - CONFLICT: passende Quellen widersprechen sich ohne auflösbare Rangfolge.
   - STALE: relevante Abhängigkeiten oder die zugrunde liegende Basis haben sich geändert.
4. Auswirkung auf das aktuelle Ziel und kleinsten sinnvollen Prüfschritt nennen.

Dies sind Berichtskennzeichen, kein Ersatz für bestehende Evidenztypen eines Consumers. Fehlender Beleg bedeutet nicht falsch. Hashes belegen Identität, keine physische Wahrheit. CI belegt nur die tatsächlich ausgeführten Prüfungen der genannten Revision; synthetische Tests belegen keine physische Leistung. Übereinstimmende Modellantworten sind kein unabhängiger Beweis.

Aktualität getrennt von inhaltlicher Unterstützung betrachten: Veraltete Belege bestätigen keine aktuelle Aussage. Ein neuerer Zeitstempel allein löst keinen Konflikt. Unbetroffene Belege nur mit ausdrücklich geprüften Abhängigkeiten und Gültigkeitsgrenzen wiederverwenden.

## /gaps — belegten Stand mit dem Ziel vergleichen

Die aktuelle /truth-Prüfung und ausdrückliche Abnahmekriterien verwenden. Ein unklares Ziel zuerst als Unsicherheit kennzeichnen.

Je wesentlicher Lücke nennen: unerfülltes Kriterium, Beleg oder Unsicherheit, Auswirkung, Abhängigkeit/Blocker, kleinste nächste Aktion und Abschlussnachweis. Unterscheiden:
- fehlende Implementierung oder reproduzierter Fehler;
- fehlende Prüfung oder nicht verfügbare Belege;
- externe Voraussetzung;
- Entscheidung im Verantwortungsbereich des Nutzers.

Zuerst Sicherheits-/Korrektheitsblocker, dann Voraussetzungen und den kleinsten nützlichen Fortschritt priorisieren. Verbesserungen außerhalb des vereinbarten Ziels sind optionale Vorschläge. Mit vorhandenen Issues, Branches und nachweislich abgeschlossener Arbeit abgleichen. Erledigte Arbeit nur bei geänderten Abhängigkeiten oder konkretem Gegenbeispiel wieder öffnen.

Standardausgabe: kurzes Belegurteil, höchstens drei wichtigste Lücken, eine empfohlene nächste Aktion und klare Prüfgrenzen. „Keine Lücke im geprüften Umfang gefunden“ bedeutet keine globale Vollständigkeit. Fehlt notwendige Evidenz, abhängige Arbeit mit benanntem Blocker stoppen; andere bereits erlaubte, unabhängige Arbeit kann weitergehen.

## Einbindung in den Matrixloop

- RECONCILE: /truth klärt die aktuelle Basis.
- TARGET: /gaps wählt einen nützlichen begrenzten Arbeitsschritt.
- VERIFY und FRICTION: betroffene Aussagen mit Ergebnissen und Gegenbeispielen aktualisieren.
- VALUE CHECK: /gaps vergleicht das Ergebnis mit den Abnahmekriterien.
- STOP / ITERATE: vorhandene Stoppregeln und Budgets gelten.

Kein vollständiges Repository-Audit bei jedem Schritt. Aktuelle Bewertungen wiederverwenden und nur betroffene Aussagen, Abhängigkeiten oder zuvor unzugängliche Belege neu prüfen. Ein einzeln aufgerufener Befehl prüft und berichtet; er erteilt keine Schreib- oder Ausführungsbefugnis. Ein bereits autorisierter Arbeitslauf darf innerhalb seiner bestehenden Grenzen weiterarbeiten.

Nur geprüfte, nützliche Änderungen über vorhandene Checkpoint-/Recovery-Wege sichern. Vor jedem dauerhaften Schreibvorgang Live-HEAD erneut prüfen. Produktbefunde bleiben in der vorhandenen Consumer-Projektwahrheit; generische Methoden gehören hierher. Keine fest gebundene Consumer-Version stillschweigend aktualisieren.

## Prüfszenarien

Vertragsbeispiele für die Abnahme, keine ausgeführten Softwaretests.

| Situation | Erforderliches Ergebnis |
|---|---|
| „Bereit“ in Dokumentation, kein Verhaltensnachweis | UNVERIFIED; fehlende Prüfung benennen |
| Tests bei Revision A grün, relevanter Code bei B geändert | Beleg für diese Aussage bei B STALE |
| Unabhängige Dokumentationsänderung | Belege erst nach Prüfung relevanter Abhängigkeiten wiederverwenden |
| Kein Netzwerkzugriff | Quelle nicht verfügbar; keinen Erfolg oder Fehler erfinden |
| Grüner synthetischer Druckertest | Softwareprüfung bestätigt; physischer Nutzen UNVERIFIED |
| Zwei passende Quellen widersprechen sich | CONFLICT bis Rangfolge oder direkter Beleg aufklärt |
| Inbetriebnahme der Hardware fehlt | Externe Voraussetzung; keine Messungen erfinden |
| Optionale Funktion außerhalb der Abnahmekriterien | Vorschlag, kein Abschlussblocker |
| Alle Kriterien im geprüften Umfang belegt | Keine verbleibende Lücke im Prüfumfang; stoppen |
| Consumer bindet ältere Loop42-Revision | Bindung nennen; keine automatische Übernahme behaupten |

## Übernahmegrenze

Ein Merge dieses Vertrags in Loop42 verändert weder Consumer-Bindungen noch Host-Fähigkeiten oder Automatisierungen. Neue Revisionen werden über den bestehenden Prüf-/Bindungsprozess übernommen. Bis dahin kann eine direkt angeforderte Prüfung im Gespräch diese Methode verwenden, ohne Implementierung in der gebundenen Laufzeit zu behaupten.
