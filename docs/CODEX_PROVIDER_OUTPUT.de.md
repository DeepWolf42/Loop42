[English](CODEX_PROVIDER_OUTPUT.md) · **Deutsch**

# Codex-Vorschläge: vollständiger Abschluss und verständliche Fehler

Eine vorhandene Vorschlagsdatei reicht nicht zur Übernahme eines ChangeSets.
Der lokale Codex-Adapter verlangt einen vollständigen, widerspruchsfreien
CLI-Ereignisstrom. Die bestehenden Prüfungen für Tests, Rechte, Auftragsumfang,
Dispatch und Verifikationsbelege bleiben zusätzlich erforderlich.

## Wann ein Vorschlag angenommen wird

- Genau ein Thread und ein gestarteter Turn, danach eine abgeschlossene finale
  Agentennachricht und genau ein erfolgreiches `turn.completed`.
- Nur Reasoning- und Agentennachrichten. Werkzeuge, Fehlermeldungen, fehlgeschlagene
  Turns, unbekannte Ereignisse, doppelte/unfertige Elemente und nachträgliche
  Aktivität werden zurückgewiesen.
- Finale Nachricht und Ausgabedatei müssen denselben geparsten JSON-Vorschlag
  enthalten. Formatierung und Schlüsselreihenfolge dürfen abweichen, Typen und
  Werte nicht. Die vorhandene ChangeSet-Prüfung kontrolliert weiterhin Schema,
  Pfade, Hashes und angeforderte Tests.
- Fehlende Verbrauchsdaten bleiben unbekannt. Vorhandene Tokenzahlen müssen
  nichtnegative ganze Zahlen sein; Wahrheitswerte sind keine gültigen Tokenzahlen.
  Fehlender Verbrauch oder Geldkosten werden nicht als null ausgegeben.

Der vorhandene Prozessrunner behält seine Frist, Ausgabegrenze und Begrenzung
der Prozessnachkommen. Die Vorschlagsdatei wird mit höchstens2MiB+1 Bytes gelesen;
der angenommene Ereignisstrom ist auf1MiB und4096 nichtleere Zeilen begrenzt.
Keine neue Prozessverwaltung, Abhängigkeit, Zugangsdaten oder Hintergrunddienste.

## Fehler bleiben nachvollziehbar

Ungültige oder zu große Vorschläge und widersprüchliche Ereignisse ergeben einen
fehlgeschlagenen WorkerResult mit festem `codex:CLI_*`-Code. Der vorhandene Handoff
speichert ihn vor einer Änderung als `FAILED_WORKER`. Dieselbe Auftragskennung
ruft anschließend das gespeicherte Ergebnis ab, statt die KI erneut zu starten.
Unterbrechungen bleiben wie bisher UNKNOWN ohne automatische Wiederholung.
Rohe CLI-Diagnosen werden nicht in Workerbegründung oder Textanzeige übernommen.

Beispiele: `codex:CLI_INCOMPLETE_TURN`, `codex:CLI_REPORTED_FAILURE`,
`codex:CLI_PROPOSAL_MISMATCH`, `codex:CLI_INVALID_PROPOSAL`. Ursache und gespeicherten
Zustand prüfen, bevor ein gesondert freigegebener neuer Versuch erwogen wird.
Die Diagnose erteilt keine neue Wiederholungs-, Commit-, Push- oder Mergefreigabe.

## Bedienung

Standard bleibt JSON. Statuswerte und Exit-Codes bleiben kompatibel:0 bei
`DONE_VERIFIED`,3 bei erfolglosem gespeicherten Ergebnis,2 bei Eingabe-/Laufzeitfehler.
Vorprüfungsfehler behalten ihre Ausnahme-Klasse in `reason`; hinzu kommt ein fester
`diagnostic_code`, etwa `STALE_SOURCE_REVISION`, `SOURCE_NOT_CLEAN`,
`COMMIT_NOT_AUTHORIZED`, `TASK_ID_CONFLICT` oder `INVALID_INPUT_SHAPE`.

Für eine verständliche deutsche Ausgabe gibt es bei beiden Operationen `--human`:

```text
python -B -m tools.harness.handoff_cli status --input request.json --profile project.local.json --human
```

Angezeigt werden feste Erklärungen und gegebenenfalls ein syntaktisch gültiger
Kandidatenhash, keine beliebige Modellbegründung. Programme verwenden weiter JSON.

## Nachweise und Grenzen

Gegenfälle prüfen unvollständige/fehlgeschlagene/mehrdeutige Streams, abweichende
Vorschläge, ungültige JSON-/Verbrauchsdaten, unerlaubte Werkzeuge, gespeicherte
Fehlversuche und CLI-Kompatibilität. Deterministische Prozessfixtures bleiben
Test-Doubles. Ein echter CLI-Kompatibilitätslauf ist ein gesonderter Nachweis.

Der vorhandene Runner bietet jetzt optional `separate_stderr=True`, hier nur für
diesen Adapter. Standardverhalten mit gemischter Ausgabe und Ergebnisschema
bleiben unverändert. Beide Kanäle teilen eine Ausgabegrenze und Prozessbegrenzung;
stderr wird begrenzt gelesen, aber nicht als Vorschlagsereignis oder Begründung
zurückgegeben. Ungültige UTF-8-Zeichen werden weiterhin ersetzt: kein Nachweis des
bytegenauen stdout-Kanals. Nicht-JSON-Daten in stdout führen zur Ablehnung;
unbekannte CLI-/Ereignisformate brauchen eine ausdrückliche neue Prüfung.
Ein gültiger Stream ist keine Quellattestation,
Datenschutz-Sandbox, signierter Beleg oder allgemeiner Modellqualitätsnachweis.

Offizielle Schnittstellenreferenz, geprüft01.11.2026:
[Codex non-interaktive JSON-Ausgabe](https://learn.chatgpt.com/docs/non-interactive-mode).
