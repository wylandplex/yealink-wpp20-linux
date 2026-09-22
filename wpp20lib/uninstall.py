import os
from pathlib import Path
import shutil
import subprocess

from .common import SERVICE, data_dir, state_dir


def main():
    if os.geteuid() == 0:
        raise SystemExit("Ohne sudo als Desktop-Benutzer ausführen.")
    result = subprocess.run(["systemctl", "--user", "stop", SERVICE], capture_output=True, text=True)
    if result.returncode and "not loaded" not in result.stderr and "not found" not in result.stderr:
        raise SystemExit("Dienst konnte nicht gestoppt werden: " + result.stderr)
    root = data_dir()
    command = Path.home() / ".local/bin/wpp20"
    if command.is_symlink() and command.resolve() == root / "app/wpp20":
        command.unlink()
    units = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"
    desktop = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
    (units / SERVICE).unlink(missing_ok=True)
    (desktop / "yealink-wpp20.desktop").unlink(missing_ok=True)
    if (root / "app").exists():
        shutil.rmtree(root / "app")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print(f"Programm, Dienst und Menüeintrag entfernt.\nErhalten: {root}\nErhalten: {state_dir()}\n"
          "Die systemweite udev-Regel und gemeinsam verwendete Systempakete bleiben erhalten.")


if __name__ == "__main__":
    main()
