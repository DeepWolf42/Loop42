**Deutsch** · [English](LOCAL_CLIENT_PROVIDER.md)

# Vorhandener lokaler Client: Anschluss für Änderungsvorschläge

`LocalClientChangeSetProvider` verbindet den bereits eingerichteten lokalen
JSON-Client mit Loop42s WorkerProvider-Vertrag. Die Ergänzung baut auf dem
aktuellen main auf und benötigt die älteren Worker-Entwürfe nicht.
Keine neuen Pakete oder Laufzeitdienste.

Ein vertrauenswürdiger, vom Verbraucher bereitgestellter Transport erhält
UTF-8-JSON-Bytes und gibt Antwortbytes zurück. Er ruft den vorhandenen Client
einmal auf und muss Server-/Prozessidentität vor Datenübertragung, Timeout,
Abbruch und Größenbegrenzung während des Einlesens sicherstellen. Der Adapter
selbst startet keine Prozesse und verwaltet keine Netzwerkverbindung.

Der Kontext bindet Auftragskennung, Versuch, Revision, Kontextfingerprint,
Rolle, Fähigkeiten und Quelldaten. Der bestehende Client meldet den SHA256 des
kompakten JSON-Inputs und Kontexttexts sowie Profil, Modus und Format zurück.
Vertauschte Antworten und falsche Profile werden abgewiesen. Die Serialisierung
muss JSON.stringify für diesen String-/Integer-Input entsprechen: kompakt,
UTF-8, unveränderte Schlüsselreihenfolge, keine ASCII-Escapes. Die Antwort muss
ein strenges ChangeSet v1 enthalten. Doppelte JSON-Schlüssel und unbekannte
ChangeSet-Felder sind ungültig; zusätzliche Client-Metadaten werden ignoriert.

Ohne propose_changes erfolgt kein Aufruf. Ohne request_verification sind
Prüfanforderungen im Vorschlag ungültig. Fehler werden ohne versteckten Retry
oder Anbieterwechsel weitergegeben. Grenzen: 8000 UTF-16-Codeeinheiten Aufgabe wie im Node-Client, 1 MiB
Aufgabe+Kontext, 1 MiB+16 KiB serialisierter Input, 8–4096 Ausgabetokens,
4 MiB Clientantwort und 2 MiB Antworttext. Adapteranweisungen zählen zum Budget.
Die Antwortgrößenprüfung erfolgt nach Rückgabe des Transports; sie begrenzt
nicht dessen Laufzeit oder Speicherverbrauch.

Das Ergebnis bleibt ein ungeprüfter Vorschlag. Hashes sind keine Signatur,
Prüfung oder Freigabe. Das Feld model bezeichnet hier das konfigurierte
Clientprofil, keine nachgewiesene Modellgewichtsidentität. Kosten sind unbekannt,
nicht automatisch null. Quellenabgleich, Schreibregeln, unabhängige Prüfung,
Prüfbeleg und Zustandsabgleich bleiben beim Verbraucher. Keine zusätzliche
Warteschlange, Hintergrundausführung, Git-Aktion oder Consumer-Pinänderung.
