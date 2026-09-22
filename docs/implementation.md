# Implementierung

```text
GNOME-Bildschirmfreigabe (vom Benutzer ausgewählt; Mauszeiger eingebettet)
  → PipeWire → GStreamer → Vollbildfenster in privatem Xvfb
  → Yealink-Windows-Client in privatem Soda/Wine
  → WPP20 per USB/HID → gekoppelter Empfänger → Raumbildschirm
```

Rootless XWayland bietet dem Windows-GDI-Client nicht den gesamten
Wayland-Bildschirm. Das zuvor beobachtete Ergebnis war ein schwarzes Bild mit
Mauszeiger. Die Bridge verwendet deshalb das
[ScreenCast-Portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html)
mit `types=1` (Monitor), `multiple=false` und `cursor_mode=2` (eingebettet).
Eine Queue mit zwei Buffern und `leaky=downstream` verwirft alte Videoframes.

Xvfb wählt seine Displaynummer mit `-displayfd` selbst. Eine zufällige private
Xauthority schützt das Display, TCP ist abgeschaltet. Der Supervisor startet den
Client erst nach dem ersten Videoframe. Stoppen, Entfernen des USB-Geräts oder
Beenden der Portalsitzung beendet auch die privaten Kindprozesse. Wine wird
ausschließlich mit dem projektspezifischen `WINEPREFIX` angesprochen.
systemd übernimmt die Prozessgruppe; nach 45 Sekunden greift dessen Stopplimit.

## Festgelegte Wine-Version

[Bottles Soda 9.0-1](https://github.com/bottlesdevs/wine/releases/tag/soda-9.0-1),
Datei `soda-9.0-1-x86_64.tar.xz` (61.960.416 Byte).

```text
SHA-256 c38fe0ad3c12a49b61ec1fcaea5c5d8da4a3d1afc5991befe2af6b125f014c28
```

Die Prüfsumme wurde am offiziellen Release-Archiv ermittelt; dessen MD5 stimmt
mit dem [Bottles-Komponentenkatalog](https://github.com/bottlesdevs/components/blob/main/runners/wine/soda-9.0-1.yml)
überein. Der Installer akzeptiert nur dieses Archiv und prüft zusätzlich die
betroffenen PE-Dateien vor und nach dem Patchen. Eine abweichende Datei führt
zum Abbruch. Der Quellrunner einer vorhandenen Bottles-Installation wird kopiert
und nicht verändert. Es wird kein gepatchter Runner im Repository verteilt.

### HID-Schreiblänge

Der WPP20 nutzt nummerierte HID-Reports mit 1024 Byte. Bei dieser Wine-Version
zog `hidclass.sys` ein Padding-Byte von der bereits vollständig gemeldeten
Schreiblänge ab. Der Yealink-Client versuchte daraufhin, ein ungültiges einzelnes
Restbyte zu senden, was zu Abbrüchen führte.

In der privaten 64-Bit-Datei `hidclass.sys` werden bei Dateioffset `0x1280` die
vier Bytes `49 29 45 38` durch NOPs ersetzt. Das unterbindet diese Subtraktion.
Diese Umgehung wurde nur für den WPP20 geprüft; sie ist kein allgemeiner
Wine-HID-Fix. Kopien im Runner und im Prefix werden berücksichtigt.

### Doppelter Mauszeiger

Das Portalvideo enthält bereits den echten Mauszeiger. Der Windows-Client
erfasste zusätzlich den Cursor des virtuellen Displays. In der privaten
32-Bit-Datei `user32.dll` wird der Export `GetCursorInfo` auf einen 29-Byte-Wrapper
im verifizierten `.text`-Padding umgeleitet. Dieser ruft zuerst das Original auf
und setzt bei Erfolg `CURSORINFO.flags` auf null. Der echte, im Portalvideo
eingebettete Mauszeiger bleibt erhalten.

Exportziel, freies Padding, Eingangs- und Ausgangsprüfsummen werden geprüft.
Weder ein Yealink-Programm noch Desktop-Cursoreinstellungen werden verändert.

## Gerätezugriff und Sitzungsdauer

Die udev-Regel verwendet `TAG+="uaccess"` für exakt `6993:b022` und dessen
HID-Geräte. Sie liegt vor systemds `73-seat-late.rules`, damit logind Zugriff
für den aktiven lokalen Sitzungsbenutzer vergeben kann. Es gibt weder globale
Schreibrechte noch Laufzeit-sudo oder Änderungen an sudoers.

Der erste Prototyp prüfte während der Übertragung regelmäßig ein sudo-Ticket.
Das verursachte einen reproduzierbaren Abbruch nach ungefähr einer Minute.
Diese Prüfung ist hier nicht vorhanden. Die normale Sitzung hat kein Zeitlimit;
lediglich die anfängliche Bildschirmauswahl ist auf drei Minuten begrenzt.

## Erprobte Kombination

- Fedora 44, x86_64, GNOME auf Wayland;
- WPP20 USB-ID `6993:b022`, Firmware `81.354.0.25`;
- Launcher `1.0.0.119`, Yealink-MCore-Raumsystem;
- tatsächlich beobachtete Bildübertragung, anschließend genau ein Mauszeiger.

Automatisierte Tests prüfen zusätzlich Versionsschutz, Patch-Idempotenz,
Archivschutz und Gerätezuordnung. Sie ersetzen keinen praktischen Test mit
einem bestimmten Empfänger/Firmwarestand.
