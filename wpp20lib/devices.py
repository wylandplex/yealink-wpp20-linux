"""Find only the exact WPP20 USB device and its own HID/storage children."""
import json
import os
from pathlib import Path
import subprocess


def find_button(sysfs=Path("/sys"), devroot=Path("/dev")):
    devices = []
    for path in (sysfs / "bus/usb/devices").iterdir():
        try:
            ids = tuple((path / key).read_text().strip() for key in ("idVendor", "idProduct"))
            if ids == ("6993", "b022"):
                devices.append(path.resolve())
        except FileNotFoundError:
            continue
    if len(devices) != 1:
        raise RuntimeError(f"Genau ein WPP20 (6993:b022) muss eingesteckt sein; gefunden: {len(devices)}.")
    device = devices[0]
    bus, address = (int((device / key).read_text()) for key in ("busnum", "devnum"))
    nodes = [devroot / f"bus/usb/{bus:03}/{address:03}"]
    for hid in sorted((sysfs / "class/hidraw").glob("hidraw*")):
        if device in (hid / "device").resolve().parents:
            nodes.append(devroot / hid.name)
    if len(nodes) < 2:
        raise RuntimeError("Der WPP20 hat noch keine HID-Geräte. Kurz warten oder neu einstecken.")
    return device, nodes


def check_access(nodes):
    denied = [str(p) for p in nodes if not os.access(p, os.R_OK | os.W_OK)]
    if denied:
        raise RuntimeError("Kein Zugriff auf " + ", ".join(denied) +
                           ". Einmal ./install.sh --system ausführen und Button neu einstecken.")


def mounted_launcher(device, sysfs=Path("/sys")):
    # Do not trust a volume name alone; its block device must belong to this USB button.
    blocks = {str(Path("/dev") / p.name) for p in (sysfs / "class/block").iterdir()
              if device in p.resolve().parents}
    listing = json.loads(subprocess.check_output(
        ["lsblk", "--json", "--paths", "--output", "NAME,MOUNTPOINTS"], text=True))

    def walk(entries):
        for entry in entries:
            yield entry
            yield from walk(entry.get("children", []))

    for entry in walk(listing["blockdevices"]):
        if entry["name"] in blocks:
            for mount in entry.get("mountpoints") or []:
                if mount and (Path(mount) / "PresentationLauncher.exe").is_file():
                    return Path(mount)
    return None


def launcher_command(root, device):
    mount = mounted_launcher(device)
    if mount:
        drive = root / "prefix/dosdevices/d:"
        if drive.is_symlink():
            drive.unlink()
        elif drive.exists():
            raise RuntimeError(f"Unerwartetes Verzeichnis anstelle des privaten Laufwerks: {drive}")
        drive.symlink_to(mount)
        return [str(root / "runner/bin/wine"), "D:\\PresentationLauncher.exe"]
    cached = list((root / "prefix/drive_c/users").glob(
        "*/AppData/Roaming/Yealink/Yealink Wireless Presentation Pod/app/PresentationLauncher.exe"))
    if len(cached) == 1:
        print("WPP20-Laufwerk nicht eingehängt; verwende den lokalen Yealink-Launcher.", flush=True)
        return [str(root / "runner/bin/wine"), str(cached[0]), "upgradeapp"]
    raise RuntimeError("Im Dateimanager das WPP20-Laufwerk öffnen/einhängen, dann wpp20 restart.")
