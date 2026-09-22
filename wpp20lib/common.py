import os
from pathlib import Path
import subprocess

SERVICE = "yealink-wpp20.service"


def data_dir():
    return Path(os.environ.get("WPP20_DATA_DIR", str(
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "yealink-wpp20"))).absolute()


def state_dir():
    return Path(os.environ.get("WPP20_STATE_DIR", str(
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "yealink-wpp20"))).absolute()


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def wine_env(root, base=None):
    env = (os.environ if base is None else base).copy()
    # Inherited overrides from another Wine application must not affect this prefix.
    for key in list(env):
        if key.startswith("WINE") or key.startswith("PROTON_"):
            env.pop(key)
    env.update(WINEPREFIX=str(root / "prefix"), WINEARCH="win64",
               PROTON_ENABLE_HIDRAW="0x6993/0xb022",
               WINEDLLOVERRIDES="mscoree,mshtml,winemenubuilder.exe=",
               WINEDEBUG="+timestamp,+pid,warn+hid,warn+wineusb")
    return env


def stop_wine(root, env):
    server = root / "runner/bin/wineserver"
    for option in ("-k", "-w"):
        try:
            subprocess.run([str(server), option], env=env, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
