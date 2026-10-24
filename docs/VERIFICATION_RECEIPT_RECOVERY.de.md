**Deutsch** · [English](VERIFICATION_RECEIPT_RECOVERY.md)

# Gespeicherte Prüfbelege wieder aufnehmen

`parse_receipt(bytes)` liest den bestehenden VerificationReceipt-Vertrag aus
strengem UTF-8-JSON: exakte Felder und Schema, keine doppelten Schlüssel oder
Sonderkonstanten, Zeit mit Zeitzone, maximal 1 MiB, 128 Kriterien und je 64
Belegverweise. Einlesen allein bestätigt die gespeicherten Behauptungen nicht.

`python -m tools.harness.verification_receipt_cli --input request.json` prüft
den gespeicherten Beleg in einem getrennten Prozess. Alle Felder sind Pflicht:

- schema: `loop42.verification-receipt-cli.v1`;
- receipt: gespeichertes `loop42.verification-receipt.v1`-Objekt;
- task: aktueller DispatchTask mit Auftrags-/Versuchkennung, Quellenrevision,
  Kontextfingerprint und geordneten acceptance_criteria;
- subject_fingerprint: unabhängig neu gelesene aktuelle SHA256 des Ergebnisses;
- verifier_id / verifier_revision: aktuelle vertrauenswürdige Prüferbasis;
- observed_at: aktuelle Beobachtungszeit mit Zeitzone;
- evidence_fingerprints: exakte Zuordnung aller Belegquellen zu unabhängig neu
  gelesenen SHA256-Werten.

Nur wenn Identität, Kriterienreihenfolge, alle PASS-Belege, Ergebnisdatei,
Prüfer und Belegprüfsummen übereinstimmen, gibt das Werkzeug ein terminales
AttemptArtifact für den bestehenden Zustandsabgleich zurück. Ein Beleg aus der
Zukunft wird abgewiesen. Fehler: Exit2 ohne Erfolgsobjekt auf stdout. Stdin
ist ebenfalls möglich, die gesamte Anfrage ist auf 1 MiB begrenzt.

Das Werkzeug beschafft oder authentifiziert keine Belege. Neu einlesen und
Prüfervertrauen bleiben beim Verbraucher; passende selbst gelieferte Hashes
sind kein Ausführungs-, Aktualitäts- oder physischer Nachweis. Es gibt keine
allgemeine Altersgrenze: Gültigkeit hängt von sämtlichen Verbraucherabhängigkeiten
und aktuellen Beobachtungen ab. Keine neue Warteschlange, Modellwiederholung,
GitHub-Aktion, Rechteerweiterung oder eigene Projektwahrheit.

Nach unterbrochener Rückmeldung muss der Verbraucher das Ziel neu lesen. Ein
exakter eigener Belegmarker kann bereits erfolgte Zustellung bestätigen; ein
widersprüchlicher Marker stoppt den Ablauf. Ein fehlender Marker nach einem
unklaren Schreibausgang rechtfertigt weder einen neuen Modellauftrag noch eine
blinde Wiederholung der Veröffentlichung. Bestehende Regeln für Seiteneffekte,
Freigaben und Wiederaufnahme bleiben maßgeblich.
