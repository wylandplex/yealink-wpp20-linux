import argparse
import ctypes
import os
import platform
import shutil
import subprocess
import sys
import time

from . import __version__
from .common import SERVICE, data_dir, state_dir
from .devices import check_access, find_button
from .patches import verify_runner


def dependencies():
    errors = []
    if platform.machine() != "x86_64":
        errors.append("Unterstützt wird Linux x86_64.")
    if sys.version_info < (3, 12):
        errors.append("Python 3.12 oder neuer erforderlich.")
    for command in ("Xvfb", "xauth", "lsblk", "systemctl"):
        if not shutil.which(command):
            errors.append(f"Programm fehlt: {command}")
    try:
        import gi
        gi.require_version("Gst", "1.0")
        gi.require_version("GstVideo", "1.0")
        from gi.repository import Gst, GstVideo, Gio  # noqa: F401
        Gst.init(None)
        for element in ("pipewiresrc", "queue", "videoconvert", "videoscale", "ximagesink"):
            if not Gst.ElementFactory.find(element):
                errors.append(f"GStreamer-Plugin fehlt: {element}")
        ctypes.CDLL("libX11.so.6")
    except (ImportError, ValueError, OSError) as error:
        errors.append(f"Desktop-Abhängigkeit fehlt: {error}")
    return errors


def doctor(require_device=True):
    errors = dependencies()
    try:
        verify_runner(data_dir())
        if not (data_dir() / "prefix/system.reg").is_file():
            errors.append("Private Wine-Umgebung fehlt.")
    except (ValueError, OSError) as error:
        errors.append(str(error))
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        errors.append("Kein Desktop-Sitzungsbus; aus einem Terminal in der Desktop-Sitzung starten.")
    if require_device:
        try:
            _, nodes = find_button()
            check_access(nodes)
            print("WPP20 erkannt; USB- und HID-Zugriff vorhanden.")
        except (RuntimeError, OSError) as error:
            errors.append(str(error))
    if errors:
        for error in errors:
            print("FEHLER:", error, file=sys.stderr)
        return 1
    print("Installation OK." + (" (USB-Prüfung übersprungen.)" if not require_device else ""))
    return 0


def control(*args, check=True, capture=False):
    return subprocess.run(["systemctl", "--user", *args, SERVICE], check=check,
                          text=True, stdout=subprocess.PIPE if capture else None)


def start():
    if control("is-active", "--quiet", check=False).returncode == 0:
        print("WPP20 läuft bereits. Neu verbinden: wpp20 restart")
        return 0
    if doctor():
        return 1
    keys = [key for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "XDG_SESSION_TYPE",
                           "XDG_CURRENT_DESKTOP", "DBUS_SESSION_BUS_ADDRESS") if key in os.environ]
    subprocess.run(["systemctl", "--user", "import-environment", *keys], check=True)
    control("reset-failed", check=False, capture=True)
    control("start")
    time.sleep(0.7)
    if control("is-active", "--quiet", check=False).returncode != 0:
        print("Start fehlgeschlagen. Diagnose: wpp20 logs", file=sys.stderr)
        return 1
    print("Dienst gestartet. Bildschirm auswählen, dann den WPP20-Button drücken.\n"
          "Stoppen: wpp20 stop | Nach Standby: wpp20 restart")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Yealink WPP20 unter GNOME/Wayland")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, description in (("start", "Bildschirmfreigabe starten"), ("stop", "Freigabe beenden"),
                              ("restart", "Nach Standby/Verbindungsabbruch neu starten"),
                              ("status", "Dienststatus anzeigen"), ("logs", "Dienstprotokoll anzeigen")):
        commands.add_parser(name, help=description)
    diag = commands.add_parser("doctor", help="Installation und Gerätezugriff prüfen")
    diag.add_argument("--no-device", action="store_true", help="Prüfung ohne eingesteckten Button")
    foreground = commands.add_parser("run", help="Im Vordergrund starten (Strg+C stoppt)")
    foreground.add_argument("--duration", type=int, default=0, help="Testdauer in Sekunden; 0 = unbegrenzt")
    args = parser.parse_args(argv)
    try:
        if os.geteuid() == 0:
            raise RuntimeError("Als angemeldeter Desktop-Benutzer starten, nicht mit sudo.")
        if args.command == "doctor":
            return doctor(not args.no_device)
        if args.command == "start":
            return start()
        if args.command == "restart":
            control("stop")
            return start()
        if args.command == "stop":
            control("stop")
            print("WPP20-Dienst gestoppt.")
        elif args.command == "status":
            return control("status", "--no-pager", check=False).returncode
        elif args.command == "logs":
            print(f"Private Detailprotokolle: {state_dir() / 'logs'}", flush=True)
            return subprocess.run(["journalctl", "--user", "-u", SERVICE,
                                   "-n", "60", "--no-pager"]).returncode
        elif args.command == "run":
            if args.duration < 0:
                parser.error("--duration darf nicht negativ sein")
            from .runtime import run
            run(args.duration)
        return 0
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"WPP20: {error}", file=sys.stderr)
        return 1
