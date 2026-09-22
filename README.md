# Yealink WPP20 unter Linux

Bildschirmübertragung mit einem **Yealink WPP20 (`6993:b022`) unter GNOME/Wayland**.
Ein eigener Benutzerdienst verbindet den Windows-Client des Buttons über eine
private, angepasste Wine-Umgebung mit der Bildschirmfreigabe des Linux-Desktops.

**Experimentell, unabhängig von Yealink.** Auf Fedora 44, GNOME/Wayland und
x86_64 mit einem WPP20 an einem Yealink-MCore-Raumsystem praktisch erprobt:
Bildübertragung und ein einzelner Mauszeiger funktionieren. Andere Buttons,
Empfänger und Firmwarestände sind nicht automatisch kompatibel. Dies ist kein
ClickShare-Treiber und keine allgemeine Unterstützung für alle Yealink-Produkte.

## Tägliche Nutzung

Nach der einmaligen Installation:

```bash
wpp20 start
```

1. Den bereits mit dem Raumsystem gekoppelten WPP20 einstecken und in Reichweite
   des Empfängers gehen.
2. Bei der ersten Nutzung das **WPP20-Laufwerk im Dateimanager öffnen**, damit
   Linux es einhängt. Anschließend `wpp20 start` ausführen.
3. Im Freigabedialog den gewünschten Bildschirm auswählen und freigeben.
4. Den **physischen Knopf am WPP20** drücken. Bei der ersten Verbindung kann der
   Client zunächst Software vom Empfänger laden.

Alternativ im Anwendungsmenü **Yealink WPP20** öffnen. Dieser Eintrag startet die
Verbindung neu und zeigt danach die Bildschirmauswahl. Das Terminal darf nach der
Startmeldung geschlossen werden; die Übertragung läuft als Benutzerdienst weiter.

| Befehl | Funktion |
| --- | --- |
| `wpp20 start` | Starten; eine laufende Sitzung bleibt bestehen |
| `wpp20 stop` | Aufnahme und privaten Wine-Client beenden |
| `wpp20 restart` | Verbindung neu aufbauen, z. B. nach Zuklappen/Standby |
| `wpp20 status` | Dienststatus anzeigen |
| `wpp20 doctor` | Installation, Button und Zugriffsrechte prüfen |
| `wpp20 doctor --no-device` | Installation ohne eingesteckten Button prüfen |
| `wpp20 logs` | Letzte Dienstmeldungen und Pfad zu Detailprotokollen anzeigen |

**Nach dem Zuklappen des Laptops:** `wpp20 restart`, Bildschirm erneut freigeben,
Button drücken. Ein physischer Tastendruck allein erneuert eine abgebrochene
Wayland-Aufnahmesitzung nicht. Mit der Stoppfunktion der GNOME-Bildschirmfreigabe
lässt sich die Aufnahme ebenfalls beenden.

## Installation auf Fedora

Voraussetzungen: Fedora x86_64, eine lokale GNOME/Wayland-Sitzung mit PipeWire und
systemd-Benutzerdiensten, Python 3.12 oder neuer, etwa 1,2 GB freier Speicherplatz.
Der Button muss bereits mit dem Empfänger gekoppelt sein. Die Linux-Einrichtung
übernimmt kein Pairing und ändert keine Firmware.

Repository herunterladen/klonen, dann **als normaler Desktop-Benutzer**:

```bash
cd yealink-wpp20-linux
./install.sh --system
wpp20 doctor --no-device
```

Der Installer fordert bei Bedarf einmal das sudo-Passwort an und:

- installiert Fedora-Pakete einschließlich Xvfb und benötigter 32-Bit-Bibliotheken;
- installiert eine udev-Regel ausschließlich für den WPP20, die dem aktiven
  lokalen Desktop-Benutzer USB-/HID-Zugriff gibt;
- lädt **Soda 9.0-1** direkt von Bottles, prüft die festgelegte SHA-256-Prüfsumme
  und erstellt eine eigene Wine-Kopie mit den zwei benötigten Korrekturen;
- richtet die private Wine-Umgebung, den Befehl, den Benutzerdienst und den
  Menüeintrag ein.

Danach den Button **einmal abziehen und wieder einstecken**, sein Laufwerk öffnen
und `wpp20 start` ausführen. Im Alltag ist **kein sudo** nötig. Die Installation
startet keine Übertragung und aktiviert keinen automatischen Start beim Anmelden.

Falls die Shell `wpp20` nicht findet:

```bash
~/.local/bin/wpp20 start
# Optional für diese Shell:
export PATH="$HOME/.local/bin:$PATH"
```

Ein vorhandener Bottles-Runner kann statt des Downloads kopiert werden:

```bash
./install.sh --system --runner \
  "$HOME/.var/app/com.usebottles.bottles/data/bottles/runners/soda-9.0-1"
```

Die Quellkopie bleibt unverändert. Alternativ ist
`./install.sh --archive /pfad/soda-9.0-1-x86_64.tar.xz` möglich. Das Archiv wird
genauso geprüft. Ohne `--system` werden nur Benutzerdateien eingerichtet;
Systempakete und udev-Regel müssen dann bereits vorhanden sein.

Andere Distributionen sind nicht getestet. Das Fedora-Paketskript lehnt sie ab.
Für eine Portierung benötigt man dieselben GStreamer-/Portal-/X11-Komponenten,
32-Bit-Wine-Abhängigkeiten und die Regel aus
[`system/70-yealink-wpp20.rules`](system/70-yealink-wpp20.rules). Danach kann der
Benutzerteil mit `./install.sh` installiert werden. Ein aktuelles System-Wine ist
kein austauschbarer Ersatz: Die Korrekturen sind an exakt Soda 9.0-1 gebunden.

## Fehlersuche

| Symptom | Vorgehen |
| --- | --- |
| Kein Button gefunden | WPP20 neu einstecken; `lsusb -d 6993:b022`; `wpp20 doctor` |
| Zugriff verweigert | `./install.sh --system`; Button neu einstecken; aus der lokalen Desktop-Sitzung starten |
| WPP20-Laufwerk fehlt | Im Dateimanager das Laufwerk öffnen; bei der ersten Nutzung ist der Launcher darauf erforderlich |
| Dienst läuft, aber kein Bild | Im Portal Bildschirm auswählen, Empfängerreichweite prüfen, Button drücken; `wpp20 logs` |
| Nach Standby eingefroren | `wpp20 restart`, Bildschirm erneut freigeben, Button drücken |
| Bildschirmauswahl abgebrochen | `wpp20 restart`; nach drei Minuten ohne Auswahl endet der Startversuch |
| Schwarzes Bild | `wpp20 restart`; in `wpp20 logs` nach Fehlern der Bildschirmaufnahme suchen |
| Zweiter Mauszeiger | `wpp20 doctor` prüft die installierte Runner-Korrektur; Dienst stoppen und Installer erneut ausführen |

Für Diagnose im Vordergrund:

```bash
wpp20 stop
wpp20 run             # Strg+C beendet die gesamte Sitzung
# Optionaler begrenzter Test; Zeit zählt ab Clientstart:
wpp20 run --duration 120
```

Direkte systemd-Befehle sind ebenfalls möglich:

```bash
systemctl --user stop yealink-wpp20.service
systemctl --user status yealink-wpp20.service
journalctl --user -u yealink-wpp20.service -n 60 --no-pager
```

Zum Starten `wpp20 start` bevorzugen: Der Befehl prüft Voraussetzungen und
übernimmt die aktuelle Desktop-Umgebung in den Benutzerdienst.

## Umfang und Grenzen

- Bildschirm mit eingebettetem Mauszeiger; privates virtuelles Display in
  1920 × 1080. Kein zugesichertes Leistungs-/Latenzniveau.
- Ton, Kamera, Mikrofon, Touch und Konferenzfunktionen sind **nicht verifiziert**.
- Ein Button und eine Aufnahme pro Benutzer; keine automatische Wiederaufnahme
  nach Standby. Nach jedem Neustart wird die Bildschirmauswahl erneut verlangt.
- Die Wine-/HID-Änderung ist eine gerätespezifische Umgehung; sie darf nicht
  pauschal auf andere Wine-Versionen oder das System-Wine übertragen werden.

## Dateien, Updates und Entfernen

| Pfad (Standard) | Inhalt |
| --- | --- |
| `~/.local/bin/wpp20` | Startbefehl |
| `~/.local/share/yealink-wpp20/app/` | Installierter Projektcode |
| `~/.local/share/yealink-wpp20/runner/` | Private Wine-Kopie |
| `~/.local/share/yealink-wpp20/prefix/` | Private Windows-Umgebung und lokal geladene Yealink-Software |
| `~/.local/state/yealink-wpp20/logs/` | Private Diagnoseprotokolle |
| `~/.config/systemd/user/yealink-wpp20.service` | Benutzerdienst |
| `~/.local/share/applications/yealink-wpp20.desktop` | Menüeintrag |
| `/etc/udev/rules.d/70-yealink-wpp20.rules` | Einmalig installierte Geräteregel |

XDG-Daten-/Status-/Konfigurationspfade werden berücksichtigt. Der Befehl bleibt
in `~/.local/bin`. Installation und Laufzeit speichern nichts im Git-Checkout.
Der Checkout kann nach der Installation verschoben oder gelöscht werden.

**Protokolle und Wine-Prefix nicht veröffentlichen:** Die Yealink-Software kann
Gerätekonfiguration und WLAN-Zugangsdaten darin protokollieren. Diese Verzeichnisse
werden privat angelegt (0700/0600) und gehören nicht in Issues oder Releases.
Alte Sitzungsprotokolle können nach `wpp20 stop` bei Bedarf gelöscht werden.

Update aus einer neuen Version dieses Repositorys:

```bash
wpp20 stop
./install.sh
```

Entfernen des installierten Programms, Dienstes und Menüeintrags:

```bash
./uninstall.sh
```

Die private Wine-Umgebung und Protokolle bleiben erhalten. Der Uninstaller zeigt
ihre Pfade an. Bei Bedarf diese Verzeichnisse anschließend selbst löschen.
Die systemweite Geräteregel lässt sich separat entfernen:

```bash
sudo rm /etc/udev/rules.d/70-yealink-wpp20.rules
sudo udevadm control --reload-rules
```

Den Button danach neu einstecken. Gemeinsame Systempakete bleiben installiert.

## Entwicklung und Veröffentlichung

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q wpp20lib
bash -n install.sh uninstall.sh system/install-fedora.sh
```

Die CI prüft Code und hardwareunabhängige Tests. Für die optionalen Tests der
echten Wine-Dateien kann `WPP20_TEST_RUNNER` auf einen originalen oder bereits
gepatchten Soda-9.0-1-Runner zeigen. Hardware-/Portaltests brauchen eine lokale
GNOME-Sitzung, den Button und den Empfänger; ein CI-Erfolg bestätigt keine
Übertragung auf andere Geräte.

Nur die Quelldateien dieses Verzeichnisses veröffentlichen. Ein Release-Archiv
kann nach einem Commit mit `git archive --format=zip HEAD -o ../wpp20-source.zip`
erstellt werden. Keine Wine-/Yealink-Binärdateien, Protokolle oder Geräteabbilder
hinzufügen. Technische Details: [Implementierung](docs/implementation.md).
Lizenzen: [MIT](LICENSE), [Drittsoftware](THIRD_PARTY.md).
