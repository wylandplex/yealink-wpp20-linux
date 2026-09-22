# Testumfang und bestätigter Stand

Stand: **22. September 2026**. Praktischer Übertragungstest am 21. September;
Installation und Paketprüfungen am 21./22. September. Referenz für die geprüfte
Paketversion: [`904889e`](https://github.com/wylandplex/yealink-wpp20-linux/commit/904889e8e536fd0107f94bf9aa3b9880765570ac)
(`0.1.0`). Diese Notiz dokumentiert einen einzelnen lokalen Testaufbau.

**Bestätigt ist die Bildübertragung mit dem ursprünglichen Aufbau und genau
einem Mauszeiger.** Die anschließend daraus erstellte Paketversion wurde auf
demselben Laptop installiert und technisch geprüft. Eine erneute Übertragung
mit dieser Paketversion zum Raumbildschirm war mangels angeschlossenem Button
bei den Abschlussprüfungen nicht möglich. Dieser letzte Praxistest ist offen.

## Testsystem

Die Hostdaten wurden am 22. September lokal ausgelesen. Die aufgeführten
GNOME-/GStreamer-/PipeWire-Versionen waren laut Paketdatenbank bereits vor dem
Übertragungstest am 21. September installiert. Der Kernelstand wurde erst bei
dieser Bestandsaufnahme erfasst, nicht separat während der Übertragung.

| Bestandteil | Erfasster Stand / Grenze der Aussage |
| --- | --- |
| Laptop | Lenovo ThinkPad E15 Gen 4 (AMD), x86_64 |
| CPU / integrierte Grafik | AMD Ryzen 7 5825U with Radeon Graphics |
| Betriebssystem | Fedora Linux 44 Workstation Edition |
| Kernel bei Bestandsaufnahme | `7.2.5-200.fc44.x86_64` |
| Desktop / Compositor | GNOME Shell `50.5-1.fc44`, Mutter `50.5-1.fc44` |
| Sitzung | Lokale GNOME-Sitzung auf **Wayland** |
| ScreenCast-Portal | `xdg-desktop-portal 1.22.1-1.fc44`, GNOME-Backend `50.0-1.fc44` |
| PipeWire / GStreamer-Anbindung | `1.6.9-1.fc44` |
| GStreamer / Plugins Base und Good | `1.28.7-1.fc44` |
| Python / PyGObject | Python `3.14.7-1.fc44`, PyGObject `3.56.3-1.fc44` |
| Xvfb | `21.1.24-1.fc44`; im ursprünglichen Aufbau lokal aus dem RPM entpackt, bei der Paketinstallation systemweit installiert |
| Wine | Bottles **Soda 9.0-1**, private Kopie mit HID- und Cursor-Korrektur; genaue Prüfsummen siehe [Implementierung](implementation.md) |
| Virtueller Bildschirm | `1920 × 1080`, 24 Bit; ein ausgewählter Monitor mit eingebettetem Mauszeiger |

Diese Daten beschreiben den Testrechner. Daraus folgt keine geprüfte
Kompatibilität mit sämtlichen Fedora-44-Rechnern, anderen Grafiktreibern oder
anderen Versionen dieser Komponenten.

## Button und Raumsystem

| Bestandteil | Bestätigt / erfasst |
| --- | --- |
| Button | Yealink **WPP20**, USB-ID `6993:b022` |
| Button-Firmware | `81.354.0.25`, im Gerätehandshake erfasst |
| Windows-Launcher vom Button | `PresentationLauncher.exe`, Version `1.0.0.119` |
| Präsentationssoftware | Wurde in Empfängerreichweite vom Raumsystem geladen; die genaue Version des nachgeladenen vollständigen Clients ist nicht dokumentiert |
| Raumsystem | Vom Benutzer als Yealink **MCore**, Beschriftung **T2C-MCORE**, angegeben |
| Empfangendes Präsentationsmodul | Exaktes Modul/Modell und Firmware nicht separat verifiziert; die MCore-Angabe allein identifiziert nicht alle beteiligten Komponenten |
| Verbindung | Bereits gekoppelter Button, Empfänger eingeschaltet und in Funkreichweite |
| Raumbildschirm | Sichtbare Bildausgabe vom Benutzer bestätigt; Modell, native Auflösung und Bildfrequenz nicht erfasst |

Es wurde nur **ein Laptop, ein WPP20 und ein Raumsystem** praktisch erprobt.
Der zunächst untersuchte Barco-ClickShare-Button gehört nicht zu diesem
erfolgreichen Testaufbau.

## Praktisch bestätigte Funktionen des ursprünglichen Aufbaus

| Beobachtung | Nachweis und Einschränkung |
| --- | --- |
| WPP20 wird angesprochen | USB-/HID-Erkennung und Gerätehandshake nach der privaten Wine-HID-Korrektur erfolgreich |
| Verbindung zum Raumsystem | In Funkreichweite Verbindung hergestellt und Präsentationssoftware nachgeladen |
| Echter Laptopbildschirm erscheint | Nach Auswahl im GNOME-Portal und Drücken des Buttons vom Benutzer am Raumbildschirm bestätigt |
| Genau ein Mauszeiger | Nach der privaten `GetCursorInfo`-Korrektur ausdrücklich vom Benutzer bestätigt |
| Erneuter Start nach Abziehen/Einstecken | Im ursprünglichen Aufbau erfolgreich protokolliert; kein Nachweis für den neuen udev-/Dienststartweg |
| Frühere Abbruchursache nach etwa einer Minute entfernt | Die fehlschlagende periodische sudo-Prüfung wurde entfernt; die anschließende Sitzung blieb über diese Grenze hinaus aktiv |

Der erfolgreiche Pfad war:
GNOME-ScreenCast-Portal → PipeWire/GStreamer → privater Xvfb →
privater Wine-/Yealink-Client → WPP20 → Raumsystem.
Im ursprünglichen Aufbau wurden die Geräteberechtigungen vorübergehend über
ACLs vergeben. Das Paket verwendet dafür eine neu eingerichtete udev-Regel.

Es gab einen zeitlich begrenzten Fünfminutentest, dessen Ende dem gesetzten
Zeitlimit entsprach. Daraus lässt sich **keine Langzeitstabilität der abschließend
korrigierten oder der später paketierten Version** ableiten. Eine belastbare
Messung von Latenz, Bildfrequenz oder Bildqualität am Raumbildschirm liegt nicht vor.

## Geprüft an der Paketversion

| Prüfung | Ergebnis / tatsächlicher Umfang |
| --- | --- |
| `./install.sh --system --archive …` | Erfolgreich auf dem vorhandenen Fedora-Testrechner; offizielles Soda-Archiv separat heruntergeladen, Prüfsumme geprüft, neue private Wine-Kopie und neues Prefix eingerichtet |
| Abhängigkeiten | Fehlendes System-Xvfb installiert; die meisten übrigen Pakete waren auf diesem Rechner bereits vorhanden |
| Erneutes `./install.sh` | Erfolgreich mit bereits eingerichtetem Runner/Prefix; Benutzerdateien erneut installiert |
| `wpp20 doctor --no-device` | Erfolgreich; Abhängigkeiten, Runner-Korrekturen und Vorhandensein des Prefix geprüft, kein Hardwaretest |
| Benutzerdienst | Unit durch `systemd-analyze --user verify` geprüft und eingerichtet; kein vollständiger Live-Start mit Button nach der Paketierung |
| Menüeintrag | Installiert und mit `desktop-file-validate` geprüft; tatsächlicher Start per Mausklick nicht separat erprobt |
| udev-Regel | Installiert und mit `udevadm verify` geprüft; Rechtevergabe nach erneutem Einstecken noch nicht praktisch verifiziert |
| `wpp20 start` ohne Button | Verständliche Fehlermeldung statt Start einer Sitzung |
| `wpp20 stop` bei inaktivem Dienst | Erfolgreich; kein Test des Beendens einer laufenden paketierten Übertragung |
| Lokale automatisierte Tests | **13 Tests bestanden**, einschließlich der drei optionalen Tests mit echten Soda-Dateien |
| GitHub-CI | Erfolgreich: **10 Tests bestanden, 3 mangels Wine-Testdateien übersprungen**; zusätzlich Syntaxprüfungen und Prüfung auf eingecheckte Laufzeitdateien |

Die automatisierten Tests decken Versionsschutz und Idempotenz der Patches,
Prüfung aller Eingabedateien vor einer Änderung, Schutz des Quellrunners bei
Symlinks, ungültige Archive und Pfad-Traversal, isolierte Wine-Umgebungsvariablen,
Pfad-Escaping sowie die Geräte-/Laufwerkszuordnung mit künstlichen sysfs-Daten ab.
Sie enthalten keine simulierte oder echte vollständige Bildschirmübertragung.

Der [CI-Lauf für die Referenzversion](https://github.com/wylandplex/yealink-wpp20-linux/actions/runs/35733848383)
verwendet einen **Ubuntu-24.04-GitHub-Runner** (im Referenzlauf Ubuntu `24.04.5`).
Das bestätigt die dort ausgeführten Codeprüfungen, **keine WPP20-Funktion unter
Ubuntu**.

## Nicht getestet oder weiterhin offen

| Bereich | Fehlender Nachweis / Grund |
| --- | --- |
| Vollständiger Paketablauf | `wpp20 start` → Bildschirmauswahl → Bild am Empfänger → `stop`/`restart` wurde mit der installierten Paketversion noch nicht durchgespielt; Button fehlte bei den Abschlussprüfungen |
| Neuinstallation auf frischem Betriebssystem | Nur auf dem bereits vorbereiteten Testrechner installiert; kein zweiter Rechner und keine saubere Fedora-Neuinstallation |
| Weitere Installerpfade | Integrierter Download ohne `--archive`, Installation über `--runner`, Deinstallation und vollständige Neuinstallation nach Entfernung nicht separat praktisch getestet |
| Standby / Zuklappen | Verbindungsverlust wurde im ursprünglichen Aufbau beobachtet und ein Neustart ausgeführt; keine dokumentierte erfolgreiche Wiederübertragung mit der paketierten `wpp20 restart`-Funktion nach Standby |
| Automatische Wiederverbindung | Nicht implementiert; nach Standby ist ein manueller Neustart mit erneuter Bildschirmauswahl vorgesehen |
| Fehlerbehandlung während der Übertragung | Portalabbruch, gesperrter Desktop, USB-Abziehen, Empfängerneustart und Reichweitenverlust sind in der Paketversion nicht systematisch als Live-Szenarien geprüft |
| Dauerbetrieb | Kein protokollierter mehrstündiger Test, keine Serie wiederholter Standby-/Reconnect-Zyklen oder CPU-/Speichermessung |
| Audio und Konferenzfunktionen | Tonübertragung, Kamera, Mikrofon, Touch/Rückkanal und Videokonferenzbetrieb nicht verifiziert; die Bridge transportiert Bildschirmbilder |
| Anzeigevarianten | HiDPI, verschiedene Skalierungsfaktoren, HDR, 4K-Ausgabe, Monitorwechsel im Betrieb, Fensterfreigabe und mehrere gleichzeitige Streams nicht geprüft; implementiert ist die Auswahl eines Monitors |
| Andere Plattformen | Kein Hardwaretest unter Ubuntu/Debian, anderen Fedora-Versionen, KDE, anderen Wayland-Compositors, einer nativen X11-Sitzung oder ARM |
| Andere Geräte / Softwarestände | Keine weiteren WPP20-Firmwarestände, anderen Yealink-Buttons/Empfänger, Barco-ClickShare-Geräte oder anderen Wine-Versionen geprüft |
| Einrichtung des Raumsystems | Pairing eines ungepaarten Buttons, Firmwareupdates und Änderungen der Empfängerkonfiguration nicht getestet und vom Installer nicht vorgenommen |
| Weitere Einsatzbedingungen | Mehrere Buttons gleichzeitig, Benutzerwechsel, USB-Hubs/Docks und unterschiedliche WLAN-/Raumkonfigurationen nicht systematisch geprüft |

„Nicht getestet“ bedeutet hier, dass kein belastbarer Funktionsnachweis vorliegt.
Es ist weder eine Funktionszusage noch automatisch ein Nachweis eines Defekts.

## Nächster noch ausstehender Praxistest

Mit demselben WPP20 und Raumsystem die neue Geräteregel nach erneutem Einstecken
prüfen, über `wpp20 start` freigeben und das Bild einschließlich bewegtem Mauszeiger
am Empfänger bestätigen. Danach `stop`, erneuten Start sowie Zuklappen/Aufklappen
mit `restart` testen und eine längere Sitzung mit tatsächlich beobachteter Dauer
dokumentieren. Erst danach diese Punkte von „offen“ auf „bestätigt“ setzen.

Neue Testberichte sollten Datum, Projektcommit, OS-/Desktop-/Wine-Version,
Button-/Empfängermodell und Firmware, getestete Schritte, Dauer und beobachtetes
Ergebnis nennen. Keine Geräte-Seriennummern, WLAN-Zugangsdaten oder unbearbeiteten
Yealink-Protokolle veröffentlichen.
