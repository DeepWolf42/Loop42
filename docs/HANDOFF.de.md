**Deutsch** · [English](HANDOFF.md)

# Ausführbare lokale Übergabe (Kandidat für Issue #77)

Die Kandidatenhistorie muss nach RED, vor Apply und vor dem Commit auf der
gebundenen Quellrevision bleiben. GREEN muss den Git-Index unverändert lassen;
gestagte fremde Dateien oder von Prüfkommandos erzeugte Commits blockieren den
Abschluss mit UNKNOWN. Bestehende Recoverydaten bleiben erhalten. Diese Kontrolle
erkennt Prüfernebenwirkungen; registrierte Kommandos bleiben vertrauenswürdige
Programme ohne Sicherheitssandbox. Ein geänderter Prüferfingerprint erfordert
eine neue Qualifikation; historische Receipts werden nicht stillschweigend aufgewertet.

## GitHub-Eingang und automatischer Rückkanal — 01.11.2026

Die zusätzliche CLI liest genau einen vom konfigurierten Operator verfassten
GitHub-Kommentar mit einem `loop42-handoff`-JSON-Codeblock. Er verwendet das
vorhandene v1-Auftragsschema; lokale Pfad-/Prüf-/Freigabeprofile bleiben lokal.
Task-ID aus Repository-ID und Kommentar-ID, Kommentartext, Autor, Bearbeitungszeit
und aktueller Quellbranch-SHA werden gebunden. Der lokale Checkout muss ebenfalls
exakt passen. Fremde Autoren, fremde Issues, geänderte Eingaben und zusätzliche
Profil-/Kommandofelder werden abgewiesen.

Im privaten Profil ergänzt `github` die Felder `issue_number`, `source_branch`,
`operator_login`, `auth: "git-credential"`, `allow_comments: true` und
`allow_execution_refs: true`. Vollständige Beispiele stehen im englischen
Vertragsdokument. Nur bestehende, nichtinteraktive Git-Anmeldung für github.com
wird verwendet; keine neuen Tokens, Rechte oder Installationen. Fehlende
Fähigkeiten bleiben BLOCKED_CAPABILITY. Diese Variante unterstützt ausschließlich
ausdrücklich ausgewählte öffentliche, offene Issues mit passender Operator-ID.

```text
python -B -m tools.harness.github_handoff run --profile project.local.json --comment-id FREIGEGEBENE_KOMMENTAR_ID
python -B -m tools.harness.github_handoff status --profile project.local.json --comment-id FREIGEGEBENE_KOMMENTAR_ID
```

Vor dem Workerstart reserviert ein Nonce-Commit mit unverändertem Quellbaum den
Branch `loop42-claims/TASK_ID` per normalem Git-Push. Konkurrierende Geschwister-
Claims können einander nicht vorspulen; nur ein Versuch erhält den Claim. Dessen
Remote-SHA wird vor Ausführung erneut gelesen. Erforderlich sind explizite
Profilfreigabe und vorhandene HTTPS-Schreibrechte. Keine Force-Updates, Löschungen
oder Produktbranch-Änderungen. Fehlendes lokales Recovery und ein bereits belegter
Claim blockieren auch auf einem zweiten Host. Claim-Branches bleiben bis zur
bewussten Reconciliation erhalten; Löschen erteilt keine Retryfreigabe. Der
eigentliche Ergebniskandidat bleibt lokal; kein automatischer Kandidatenpush/PR.
Der öffentliche Claim enthält auch Git-Autorname und -E-Mail aus dem Profil.
Dafür eine bewusst öffentliche Noreply- oder synthetische Identität verwenden;
dies gehört zur ausdrücklichen Freigabe `allow_execution_refs`.

Der Rückkanal veröffentlicht nur Aufgaben-/Quell-/Receiptidentität, Status und
begrenzte Prüf-Exitdaten. Keine lokalen Pfade, Rohlogs, Prompts, Zugangsdaten oder
Modelltexte. Atomarer Publikationsclaim und persistierter SideEffectIntent gehen
einem einzigen POST voraus; anschließend erfolgt ein unabhängiges GET. Verlorene
Antworten werden nur durch den exakten eigenen Ergebnismarker bestätigt. Fehlende
oder widersprüchliche Belege bleiben UNKNOWN; kein automatischer erneuter POST.
Geänderte GitHub-Aufträge/Quellen verhindern Apply beziehungsweise Veröffentlichung.
Redirects, Pagination, übergroße Antworten und automatische HTTP-Retries werden
abgewiesen. Remote-Status trägt ausdrücklich
`github_report_not_local_reverification`: authentifizierter Berichtabruf, keine
eigene erneute lokale Ausführung. Unbeaufsichtigter Hosttrigger und Privat-Repo-
Unterstützung werden dadurch nicht behauptet.

Quellen: [GitHub-Kommentar-API](https://docs.github.com/en/rest/issues/comments),
[bestehende Git-Credential-Helper](https://git-scm.com/docs/gitcredentials).

Ein freigegebener Host-Aufruf prüft Auftrag, Repository, exakte Quellrevision und
sauberen Checkout. Ein vorhandener Provider liefert genau einen Vorschlag. Der
bestehende ChangeSet-/Policy-/Dispatch-/Verification-Kern wendet ihn in einem
isolierten Git-Arbeitsordner an, prüft ihn, committet den Kandidaten und erzeugt
einen VerificationReceipt. Der Quellcheckout bleibt unverändert. Ein zweiter
CLI-Prozess kann den Status unabhängig vom ausführenden Prozess prüfen.

## Entscheidung und Abnahme

Keine neue Datenbank, kein Daemon und kein Scheduler. Ein atomarer Claim und ein
Ergebnis liegen im ausdrücklich konfigurierten Recovery-Verzeichnis des Consumers.
`git_workspace.py` wird unverändert aus Loop42-Draft #45 bei
`25ff944816af17ca6a151a6acd6f59158adb8d09` wiederverwendet (Blob `40a47eb`), ohne
dessen alten Ollama-Stack zu übernehmen oder den Draft zu mergen. #31 liefert
optionale Open-Work-Suche, keinen Host-Trigger, und bleibt eigenständig.

Arbeitsplan/Abnahme: Git-/Prozesstests und Gegenfälle; minimaler Runner; echter
Codex-CLI-Aufruf mit synthetischem Auftrag; RED/GREEN und Kandidatencommit;
separater Statusaufruf; Gesamttests und revisionsgebundene CI.

## Einrichtung und nächster Auftrag

### Start mit freigegebenem öffentlichem Text

`github_submit` erzeugt das bestehende Auftragsschema aus UTF-8-Auftragstext und
vertrauenswürdigem Projektprofil, veröffentlicht den Eingang im ausgewählten
Issue und nutzt danach `github_handoff`. Das Profil liefert sämtliche erlaubten
Pfade und registrierten Prüfkennungen; RED ist Pflicht. Das Profil entsprechend
eng begrenzen. `github.allow_task_comments: true` muss zusätzlich ausdrücklich
die Veröffentlichung des Auftragstextes erlauben. Die bisherigen Freigaben für
Ergebnisbelege und Claim-Refs reichen dafür nicht aus. Keine privaten Aufträge,
Chats, Pfade, Zugangsdaten oder Patientendaten übermitteln.

```text
python -B -m tools.harness.github_submit start --profile project.local.json --submission-id freigegebener-auftrag-1 --expected-revision EXAKTER_40_HEX_SHA --task-file oeffentlicher-auftrag.txt
```

`--task-file -` liest vom durch den Aufrufer kontrollierten stdin. Maximal 2048
UTF-8-Bytes, keine Markdown-Codezäune. JSON-Erstellung, manuelle Kommentar-ID-
Übertragung und Zwischenübergaben entfallen. `submit` statt `start` veröffentlicht
nur den Eingang und liefert SUBMITTED, keinen Workererfolg. Die zurückgegebene
`input_comment_id` eignet sich für den vorhandenen Remote-Statusaufruf. Der Host
muss offene Arbeit und Auftragsabsicht vorher abgleichen; beliebiger Issue-Text
erteilt keine Ausführungsfreigabe.

Der stabile Einreichungsschlüssel bindet numerische Repository-/Operator-IDs und
das ausgewählte Issue. Wiederverwendung mit anderem Text, Quellstand oder Umfang
blockiert. Ein exakter eigener Eingangsmarker ist auf einem zweiten Host wieder
auffindbar. Der vorhandene Git-Claim reserviert auch die Einreichung vor ihrem
einzigen POST; der normale Ausführungsclaim schützt weiterhin den Worker. Beide
bleiben erhalten. Verlorene Antworten werden über exakte eigene Kommentare und
den vorhandenen SideEffectIntent-Vertrag abgeglichen. Fehlende oder widersprüchliche
Belege erlauben keinen Retry. Unvollständige lokale oder belegte entfernte Claims
blockieren, statt einen zweiten Eingang zu erzeugen. Keine neue Datenbank,
Zeitsteuerung, Dienste, Zugangsdaten oder Rechte; Recovery bleibt beim Consumer.

Abnahme: echte Git-Tests für Einreichung, Start, Duplikate und Fehlerfälle;
Gesamtsuite und Gates; anschließend ein tatsächlicher öffentlicher synthetischer
Ein-Befehl-Lauf mit unabhängigem Abruf des Receipts. Testdoubles sind kein
Live-GitHub-/Modellnachweis.

Die vollständigen JSON-Beispiele stehen im [englischen Vertragsdokument](HANDOFF.md).
Einmal pro Projekt eine private, vertrauenswürdige `project.local.json` außerhalb
der Versionsverwaltung einrichten: Repository-ID, absoluter Checkoutpfad,
Recovery-Verzeichnis außerhalb des Repositorys, exakt erlaubte vorhandene
UTF-8-Dateien, Commitfreigabe, Autor und registrierte Prüfkennungen mit festen
argv-Kommandos und Timeouts. Profil und Kommandos niemals aus einem Issue oder
Modellresultat als vertrauenswürdig übernehmen. Origin muss zum Projekt passen;
der Checkout muss einschließlich unversionierter Dateien sauber sein.

Ein berechtigter Host kann den freigegebenen GitHub-Auftrag selbst lesen, offene
Arbeit abgleichen und eine `loop42.handoff.v1`-Anfrage erzeugen: stabile Task-ID,
Repository, vollständiger Quell-SHA, Aufgabe, erlaubte Pfade, Prüfkennungen und
`require_red`. Dadurch muss der Nutzer keine Zwischenberichte kopieren.

```text
python -B -m tools.harness.handoff_cli run --input request.json --profile project.local.json
python -B -m tools.harness.handoff_cli status --input request.json --profile project.local.json
```

Python 3.12 verwenden und `PYTHONDONTWRITEBYTECODE=1` auch für Test-Unterprozesse
setzen. Aufruf aus dem Loop42-Checkout. Der CLI-Adapter verwendet den offiziell
dokumentierten `codex exec` mit bestehender Anmeldung, leerem Arbeitsverzeichnis,
ignorierter Nutzerkonfiguration und lesendem Sandboxmodus. Benannte Toolfeatures
werden deaktiviert, ausgegebene Toolereignisse abgelehnt. Das beweist weder ein
leeres Toolangebot noch eine vollständige Dateilese-/Privatsphärenisolation.
Nur freigegebene Daten verwenden. `allow_codex` erlaubt ausdrücklich den
ausgewählten Text und einen CLI-Kontingentaufruf. Kein neuer Schlüssel, Dienst
oder Installation. Fehlt die Fähigkeit, wird sie blockiert. Das Promptlimit ist
3500 Zeichen; Prozessargumente können lokal sichtbar sein. Keine vertraulichen
oder Patientendaten über diesen Adapter senden. Modellidentität und Geldkosten
bleiben UNKNOWN, soweit nicht tatsächlich erfasst.

Prüfkommandos sind vertrauenswürdige Programme mit Nutzerrechten, keine Sandbox.
Modelloutput bleibt Vorschlag. Nur ModifyChange für exakt erlaubte Pfade ist
zulässig; keine Modellkommandos, Dateierstellung oder Löschung.

## Status, Doppelstartschutz und Wiederaufnahme

`claim.json` bindet Auftrag und lokales Profil. `result.json` hält das Ergebnis.
Beide gehören zur bestehenden Recovery-Verantwortung des Consumers, nicht zu
einer neuen Projektwahrheit. Der Claim wird nicht automatisch gelöscht. Dieselbe
Task-ID führt den Provider höchstens einmal aus. Andere Eingaben unter derselben
ID werden abgelehnt. Claim ohne Ergebnis bedeutet UNKNOWN und keinen Retry.
Vor einem neuen freigegebenen Versuch müssen Arbeitsordner, Prozessruhe und
Nebenwirkungen ausdrücklich abgeglichen werden; neue Task-ID verwenden.

DONE_VERIFIED bedeutet: registrierte Prüfungen bestanden am exakten committeten
Kandidatenbaum. Status prüft Identität, Quelle/Kandidat, Receiptfingerprint,
Prüfercode-/Pythonfingerprint, Prüferkennung/Zeit und Evidenzhashes erneut.
Diese lokalen Daten sind keine Signaturen gegen einen Angreifer mit Hostzugriff.
Andere Quellen oder Prüfer benötigen neue Qualifikation. Rote Tests bleiben
FAILED, fehlende/beschädigte Belege UNKNOWN. Arbeitsordner bleiben für Recovery
erhalten. Kein automatischer Ergebniskandidatenpush, PR, Merge oder Hintergrundlauf.
Der GitHub-Adapter darf nur ausdrücklich freigegebene Claim-Refs reservieren.

Ein berechtigter Host kann einen geprüften, nichtprivaten Kurzbeleg im vorhandenen
GitHub-Issue/PR hinterlegen: Task-ID, Quell-/Kandidaten-SHAs, Receiptfingerprint und
Prüfergebnisse. Andere berechtigte Sitzungen können ihn dort abrufen. Rohdaten
und lokale Pfade bleiben privat. Das ist ein übernommener Bericht, keine eigene
lokale Nachprüfung; dafür benötigt der Statusaufruf den erhaltenen Recoverypfad.
Die ursprüngliche `handoff_cli` überlässt das dem Host; `github_handoff`
automatisiert ausschließlich den begrenzten Ergebnisbeleg.

## Produktgrenzen und Aufwand

Geprüfte offizielle Quellen vom 29.10.2026:
[Codex Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
und [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory).
Unterstützte Host-Aufgaben bedeuten keinen Zugriff auf beliebige fremde Sitzungen.
Hier wird keine direkte Chat–Work–Codex-Verbindung und kein Eventtrigger installiert.
Der Pfad funktioniert bei einem Host mit GitHub und lokaler Ausführung. Fehlt
lokale Ausführung, ist dieser Schritt BLOCKED_CAPABILITY; GitHub-Statuslesen bleibt
möglich. Unbeaufsichtigte Auslösung braucht einen separat geprüften Hostmechanismus.

KI-Multisteckers vorhandene Textschnittstelle ist kein allgemeiner Codingworker
und bleibt unverändert. Keine alten Worker werden wiederbelebt. Andere Consumer
benötigen nur eigene Repo-/Pfad-/Prüferkonfiguration; CORA, Arthur und dentalCOM
behalten eigene Wahrheit, Pins und Sicherheits-/Patientendatengrenzen.

Der reale synthetische Lauf und Messwerte werden am Kandidaten-PR belegt.
Deterministische Testprovider sind als Testdoubles gekennzeichnet. Frühere manuelle
Kopiervorgänge wurden nicht instrumentiert: UNKNOWN. Der geprüfte Hostpfad braucht
einen Start und keine manuellen Zwischenübergaben. Das beweist keine Verfügbarkeit
in jeder Oberfläche. Gesamtzeit, Tokens, Hostaktionen und Kosten bleiben UNKNOWN,
soweit nicht gesondert gemessen.
