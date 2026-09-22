# Drittsoftware

Dieses Repository enthält eigene Python-/Shell-Skripte und Dokumentation unter
der MIT-Lizenz. Drittsoftware wird zur Laufzeit lokal verwendet, aber nicht im
Repository mitgeliefert. Die MIT-Lizenz gilt nicht für diese Drittsoftware.

- **Wine / Soda 9.0-1:** Wine steht unter LGPL-2.1-or-later; Komponenten des
  Runners können weitere Lizenzen haben. Der Installer bezieht den unveränderten
  Runner von [Bottles](https://github.com/bottlesdevs/wine/releases/tag/soda-9.0-1)
  und wendet zwei versionsgebundene Änderungen auf die private lokale Kopie an.
  [Wine-Quellcode](https://gitlab.winehq.org/wine/wine),
  [Bottles-Buildprojekt](https://github.com/bottlesdevs/wine),
  [Wine-Lizenz](https://gitlab.winehq.org/wine/wine/-/blob/master/COPYING.LIB).
- **Yealink PresentationLauncher und Presentation Pod:** proprietäre Software.
  Wird vom eigenen WPP20-Button bzw. dem damit verbundenen Empfänger geladen.
  Kein Yealink-Programm ist Bestandteil dieses Repositorys; dessen eigene
  Lizenzbedingungen gelten weiterhin.
- **X.Org Xvfb, GStreamer, PipeWire, PyGObject, systemd und xdg-desktop-portal:**
  werden über die Linux-Distribution installiert; ihre jeweiligen Lizenzen gelten.

Yealink und WPP20 sind Bezeichnungen ihrer jeweiligen Rechteinhaber. Dieses
Projekt ist unabhängig und kein offizielles Yealink-Produkt.

Veröffentliche keine Kopie des installierten Laufzeitverzeichnisses als Release.
Ein öffentliches Release dieses Projekts besteht ausschließlich aus den im Git
erfassten Quelldateien.
