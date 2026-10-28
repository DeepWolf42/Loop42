# Gap & Reuse Preflight

Status: **optionales, rein lesendes CLI-Werkzeug**, kein autonomer Scout, Slash-Befehl, Hintergrunddienst, zusätzliche Matrixloop-Stufe oder Freigabesystem.

Aufruf im vorhandenen Git-Checkout während **RECONCILE / TARGET**:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger architecture --expected-head "$(git rev-parse HEAD)"
```

Weitere Auslöser: `new_infrastructure`, `repeated_failure`, `dependency_decision`, `scheduled`. `routine` überspringt den Check bewusst. Ein Host muss Auslöser und Zeitpunkt selbst bestimmen; **kein** automatischer Chat-Dispatcher ist vorhanden.

Die CLI nutzt Loop42s vorhandene Repository-Map und liefert höchstens drei mögliche Wiederverwendungskandidaten. Dateinamen- und Symboltreffer beweisen **keine** funktionierende Lösung. Eigener Code wird vor offenen Arbeiten, installierten Tools und externen Mustern betrachtet.

## Optionaler Live-Adapter für offene Arbeit

Bei einer größeren Abhängigkeits- oder Capability-Entscheidung kann derselbe RECONCILE-/TARGET-Aufruf offene PRs und Issues direkt lesen:

```bash
python -m tools.checks.gap_reuse_preflight --repo . --target "checkpoint recovery" --trigger dependency_decision --expected-head "$(git rev-parse HEAD)" --github-repository example/project
```

`--github-repository owner/name` wählt die Quelle auf github.com ausdrücklich aus. Sie wird nicht aus Remotes abgeleitet; der Host muss die passende Quelle wählen. Nach der anfänglichen HEAD-/Root-Prüfung sammelt der Adapter nur bei Nicht-`routine`-Auslösern Belege. Anschließend wird HEAD erneut geprüft. Es wird kein Chat-/Host-Hook registriert und keine Hintergrundausführung aktiviert.

Genau **ein GET** auf GitHubs [Repository-Issue-Endpunkt](https://docs.github.com/en/rest/issues/issues#list-repository-issues) liest auch PRs: höchstens 100 offene Einträge und 512 KiB, mit 10 Sekunden Socket-Timeout. Keine Wiederholung, Pagination oder Weiterleitung. Pagination-Header, fehlender Zugriff, Rate Limit, Transportfehler oder ungültige Antworten ergeben `BLOCKED_UNKNOWN`; die eigene Codeprüfung bleibt nutzbar. `routine` erzeugt auch mit gesetzter Option keinen Abruf.

Abgeglichen werden ausschließlich **Titel und Zielbegriffe**. Höchstens acht Metadatenhinweise gehen in die bestehende Auswahl mit maximal drei Kandidaten ein. Die URLs müssen zum gewählten Repository passen. Inhalte, Kommentare, Patches oder Anweisungen werden nicht interpretiert oder ausgeführt. `CHECKED_NO_DELTA` bedeutet nur: kein Begriffstreffer in der vollständig gelieferten Titelliste. Titel bleiben untrusted Daten; PR-Revision, Implementierung und Eignung müssen separat geprüft werden. Der Zeitstempel dokumentiert die Beobachtung; die lokale Revision bindet sie an den Aufruf und friert den entfernten Arbeitsstand nicht ein.

Öffentliche Quellen funktionieren anonym. Ein vom Host bereits bereitgestelltes `GITHUB_TOKEN` wird nur für den ausdrücklich gewählten Abruf verwendet; Zugangsdaten werden weder beschafft noch Berechtigungen geändert. Tokenwerte, rohe API-Antworten und Exception-Texte erscheinen nicht im Ergebnis. Keine Geheimnisse im Zieltext und keine privaten Berichte committen. Vorhandene Repository-Connectoren können weiterhin `--evidence` liefern. Gleichzeitige Live-Abfrage und `open_work`-Belege werden zurückgewiesen, damit kein Beleg still überschrieben wird.

Autorisierte Adapter können mit `--evidence datei.json` Belege zu `open_work`, `installed_capabilities` und `external_patterns` liefern. Die Felder und ein JSON-Beispiel stehen in der [englischen Referenz](GAP_REUSE_PREFLIGHT.md). Ohne Adapterbeleg ist der Status **NOT_SEARCHED**, nicht „keine Verbesserung gefunden“. Weitere Werte: `CHECKED_NO_DELTA`, `USEFUL_CANDIDATE`, `BLOCKED_UNKNOWN`. Geprüfte Angaben brauchen Quelle, Zeitpunkt und bei projektgebundenen Daten eine passende HEAD-Revision. Veraltete Angaben werden blockiert.

Das Ergebnis ist revisionsgebundenes JSON; `adoption_authorized` bleibt immer `false`. Keine Codeänderung, Installation, Freigabe oder Consumer-Pin-Aktualisierung. Vorschläge müssen gegen die aktuelle Quelle und die bestehenden Sicherheits- und Prüfgates getestet werden.

**Für einen vollständig autonom arbeitenden Scout fehlen noch:** Host-Trigger, Tool-Inventar, externe Muster-Recherche und echte Consumer-Akzeptanztests. Der optionale GitHub-Adapter ist eine bedarfsgesteuerte Titelprüfung, keine Forschungsautomatik oder Übernahme-/Mergefreigabe.
