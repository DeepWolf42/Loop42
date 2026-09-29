# Sicherheitsrichtlinie

Loop42 soll Automatisierung begrenzt, reproduzierbar und sicher prüfbar halten.

## Sicherheitsproblem melden

**Keine** Secrets, Zugangsdaten, Exploit-Details oder andere sensible Informationen in einem öffentlichen Issue veröffentlichen.

Bei einem öffentlichen Loop42-Repository soll nach Möglichkeit GitHubs Private Vulnerability Reporting bzw. der Security-Advisory-Weg verwendet werden. Ist kein privater Meldeweg sichtbar, nur ein minimales öffentliches Issue mit dem Titel **„Private security contact requested“** erstellen — ohne technische Exploit-Details, Zugangsdaten oder persönliche Informationen.

## Privat hilfreiche Angaben

Wenn ein privater Kanal verfügbar ist:

- betroffene Revision bzw. exakter Commit;
- betroffene Datei/Komponente;
- Reproduktionsschritte oder Evidence;
- erwartete Auswirkung;
- ob Zugangsdaten, private Daten oder physische Ausführung betroffen sein könnten.

## Umfang

Sicherheitsrelevant sind unter anderem:

- Umgehung von Authority-/Approval-Grenzen;
- Stale-State- oder Single-Writer-Fehler;
- Offenlegung von Secrets/Zugangsdaten;
- unsichere Tool-/Provider-Grenzen;
- nicht vertrauenswürdiger externer Input, der Ausführungsautorität erhält;
- Recovery-Wege, die veraltete Arbeit stillschweigend erneut ausführen;
- Consumer-Boundary-Fehler, die Produktwahrheit ohne Review verändern könnten.

Keine echten Zugangsdaten in Testfällen verwenden. Beispiele müssen klar synthetisch sein, etwa mit `example.invalid`.

## Reaktionsprinzip

Eine Meldung ist Evidence für eine Untersuchung, kein automatischer Beweis. Vor Annahme eines Fixes soll der kleinste reproduzierbare Fall gegen die aktuelle Source of Truth geprüft werden.

Loop42 verspricht derzeit keine bestimmte Reaktionszeit oder Security-Service-Level.
