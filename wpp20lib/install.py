"""Install source-only app and a checksum-pinned, private Wine runtime."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

from .cli import dependencies
from .common import SERVICE, data_dir, private_dir, state_dir
from .patches import patch_runner, verify_runner
from .runtime import initialize_prefix

SOURCE = Path(__file__).resolve().parent.parent
RUNNER_URL = "https://github.com/bottlesdevs/wine/releases/download/soda-9.0-1/soda-9.0-1-x86_64.tar.xz"
RUNNER_SHA256 = "c38fe0ad3c12a49b61ec1fcaea5c5d8da4a3d1afc5991befe2af6b125f014c28"


def verify_archive(path):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != RUNNER_SHA256:
        raise ValueError(f"Soda-Archiv hat eine unbekannte SHA-256-Prüfsumme: {actual}")


def unpack_archive(archive, destination):
    verify_archive(archive)
    with tarfile.open(archive, "r:xz") as bundle:
        # Python 3.12's data filter rejects traversal, outside links and device files.
        bundle.extractall(destination, filter="data")
    runner = destination / "soda-9.0-1-x86_64"
    if not (runner / "bin/wine").is_file():
        raise ValueError("Wine fehlt im Soda-Archiv.")
    return runner


def prepare_runner(root, source=None, archive=None):
    if (root / "runner").exists():
        verify_runner(root)
        print("Vorhandene private Wine-Kopie ist geprüft.")
        return
    with tempfile.TemporaryDirectory(prefix="install-", dir=root) as temporary:
        stage = Path(temporary)
        if source:
            # GNU cp can use reflinks; never hardlink a runner that will be patched.
            subprocess.run(["cp", "-a", "--reflink=auto", str(source.resolve()),
                            str(stage / "runner")], check=True)
        else:
            if archive is None:
                archive = stage / "soda.tar.xz"
                print("Lade Soda 9.0-1 von der offiziellen Bottles-Veröffentlichung (~62 MB).", flush=True)
                subprocess.run(["curl", "--fail", "--location", "--proto", "=https",
                                "--proto-redir", "=https", "--connect-timeout", "20",
                                "--max-time", "300", "--output", str(archive), RUNNER_URL], check=True)
            unpack_archive(archive, stage).rename(stage / "runner")
        patch_runner(stage)
        verify_runner(stage)
        (stage / "runner").rename(root / "runner")


def systemd_quote(value):
    if any(ord(c) < 32 for c in value):
        raise ValueError("Steuerzeichen in Installationspfaden werden nicht unterstützt.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def desktop_quote(value):
    if any(ord(c) < 32 for c in value):
        raise ValueError("Steuerzeichen in Installationspfaden werden nicht unterstützt.")
    result = value.replace("%", "%%")
    for char in ("\\", '"', "`", "$"):
        result = result.replace(char, "\\" + char)
    # Desktop Entry value escaping precedes the Exec quoting pass.
    return '"' + result.replace("\\", "\\\\") + '"'


def install_user_files(root):
    app = private_dir(root / "app")
    shutil.copytree(SOURCE / "wpp20lib", app / "wpp20lib", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("wpp20", "README.md", "LICENSE", "THIRD_PARTY.md"):
        shutil.copy2(SOURCE / name, app / name)
    (app / "wpp20").chmod(0o755)
    bin_dir = Path.home() / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    command = bin_dir / "wpp20"
    if command.is_symlink() and command.resolve() == app / "wpp20":
        pass
    elif command.exists() or command.is_symlink():
        raise RuntimeError(f"Vorhandener fremder Befehl wird nicht überschrieben: {command}")
    else:
        command.symlink_to(app / "wpp20")
    units = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"
    units.mkdir(parents=True, exist_ok=True)
    unit = "\n".join([
        "[Unit]", "Description=Yealink WPP20 screen sharing (unofficial)",
        "After=graphical-session.target", "PartOf=graphical-session.target", "",
        "[Service]", "Type=simple", "UMask=0077",
        "Environment=" + systemd_quote("WPP20_DATA_DIR=" + str(root)),
        "Environment=" + systemd_quote("WPP20_STATE_DIR=" + str(state_dir())),
        "ExecStart=/usr/bin/python3 -u " + systemd_quote(str(app / "wpp20")).replace("$", "$$") + " run",
        "KillMode=mixed", "TimeoutStopSec=45", "Restart=no", "",
    ])
    (units / SERVICE).write_text(unit)
    desktop_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    (desktop_dir / "yealink-wpp20.desktop").write_text("\n".join([
        "[Desktop Entry]", "Type=Application", "Name=Yealink WPP20",
        "Comment=Bildschirm teilen oder Verbindung neu starten",
        "Exec=/usr/bin/python3 " + desktop_quote(str(app / "wpp20")) + " restart",
        "Icon=video-display", "Terminal=true", "Categories=AudioVideo;",
        "Keywords=Yealink;WPP20;Präsentation;Bildschirm;", "",
    ]))
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print(f"\nInstalliert: {command}\nAnwendungsmenü: Yealink WPP20\n"
          "Start: wpp20 start | Stop: wpp20 stop | Nach Standby: wpp20 restart\n"
          "Die Installation startet noch keine Bildschirmfreigabe.")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print('Für den Kurzbefehl ~/.local/bin zum PATH hinzufügen oder ~/.local/bin/wpp20 verwenden.')


def main(argv=None):
    parser = argparse.ArgumentParser(description="WPP20 für den angemeldeten Desktop-Benutzer installieren")
    parser.add_argument("--system", action="store_true", help="Fedora-Pakete und udev-Regel einmalig mit sudo installieren")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--runner", type=Path, help="Vorhandene Soda-9.0-1-Kopie verwenden (wird nicht verändert)")
    source.add_argument("--archive", type=Path, help="Bereits heruntergeladenes offizielles Soda-Archiv")
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        parser.error("Als Desktop-Benutzer ausführen, ohne sudo vor ./install.sh.")
    os.umask(0o077)
    try:
        if sys.version_info < (3, 12):
            raise RuntimeError("Python 3.12 oder neuer erforderlich.")
        root = private_dir(data_dir())
        private_dir(state_dir())
        with (root / "session.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("WPP20 läuft noch. Erst wpp20 stop ausführen.") from None
            if args.system:
                subprocess.run(["sudo", "bash", str(SOURCE / "system/install-fedora.sh")], check=True)
            missing = dependencies()
            if missing:
                raise RuntimeError("\n".join(missing) + "\nAuf Fedora: ./install.sh --system")
            prepare_runner(root, args.runner, args.archive.absolute() if args.archive else None)
            initialize_prefix(root)
            install_user_files(root)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(f"Installation abgebrochen: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
