# Gap & Reuse Preflight

Status: **optionales, rein lesendes CLI-Werkzeug**, kein autonomer Scout, Slash-Befehl, Hintergrunddienst, zusätzliche Matrixloop-Stufe oder Freigabesystem.

Aufruf im vorhandenen Git-Checkout während **RECONCILE / TARGET**:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger architecture --expected-head "$(git rev-parse HEAD)"
```

Weitere Auslöser: `new_infrastructure`, `repeated_failure`, `dependency_decision`, `scheduled`. `routine` überspringt den Check bewusst. Ein Host muss Auslöser und Zeitpunkt selbst bestimmen; **kein** automatischer Chat-Dispatcher ist vorhanden.

Die CLI nutzt Loop42s vorhandene Repository-Map und liefert höchstens drei mögliche Wiederverwendungskandidaten. Dateinamen- und Symboltreffer beweisen **keine** funktionierende Lösung. Eigener Code wird vor offenen Arbeiten, installierten Tools und externen Mustern betrachtet.

Autorisierte Adapter können mit `--evidence datei.json` Belege zu `open_work`, `installed_capabilities` und `external_patterns` liefern. Die Felder und ein JSON-Beispiel stehen in der [englischen Referenz](GAP_REUSE_PREFLIGHT.md). Ohne Adapterbeleg ist der Status **NOT_SEARCHED**, nicht „keine Verbesserung gefunden“. Weitere Werte: `CHECKED_NO_DELTA`, `USEFUL_CANDIDATE`, `BLOCKED_UNKNOWN`. Geprüfte Angaben brauchen Quelle, Zeitpunkt und bei projektgebundenen Daten eine passende HEAD-Revision. Veraltete Angaben werden blockiert.

Das Ergebnis ist revisionsgebundenes JSON; `adoption_authorized` bleibt immer `false`. Keine Codeänderung, Installation, Freigabe oder Consumer-Pin-Aktualisierung. Vorschläge müssen gegen die aktuelle Quelle und die bestehenden Sicherheits- und Prüfgates getestet werden.

**Für einen vollständig autonom arbeitenden Scout fehlen noch:** Host-Trigger, authentifizierte PR-/Issue-Abfrage, Tool-Inventar, externe Research-Adapter und echte Consumer-Akzeptanztests. Die vorhandene CLI darf daher nicht als vollständige Forschungsautomatik ausgegeben werden.
