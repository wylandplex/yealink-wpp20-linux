"""Supervise private Xvfb, consent-based screen capture, and private Wine."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import time

from .common import data_dir, private_dir, state_dir, stop_wine, wine_env
from .devices import check_access, find_button, launcher_command
from .patches import patch_prefix, verify_runner


def terminate(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


@contextmanager
def virtual_display(session):
    auth = session / "Xauthority"
    auth.touch(mode=0o600)
    env = os.environ.copy()
    # Xvfb -displayfd chooses and locks a free display atomically.
    cookie = secrets.token_hex(16)
    subprocess.run(["xauth", "-f", str(auth), "add", ":0", "MIT-MAGIC-COOKIE-1", cookie],
                   check=True, stdout=subprocess.DEVNULL)
    read_fd, write_fd = os.pipe()
    os.set_blocking(read_fd, False)
    server = None
    env.pop("WAYLAND_DISPLAY", None)
    try:
        with (session / "xvfb.log").open("wb") as log:
            server = subprocess.Popen(["Xvfb", "-displayfd", str(write_fd), "-screen", "0",
                "1920x1080x24", "-nolisten", "tcp", "-auth", str(auth), "-noreset"],
                pass_fds=(write_fd,), env=env, stdout=log, stderr=subprocess.STDOUT)
        os.close(write_fd)
        write_fd = None
        answer = b""
        deadline = time.monotonic() + 10
        while b"\n" not in answer:
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f"Xvfb startet nicht. Details: {session / 'xvfb.log'}")
            try:
                answer += os.read(read_fd, 64)
            except BlockingIOError:
                pass
            time.sleep(0.05)
        display = ":" + str(int(answer.strip()))
        # The X server accepts the cookie value regardless of its display number;
        # clients require the actual display in the authority lookup.
        subprocess.run(["xauth", "-f", str(auth), "add", display, "MIT-MAGIC-COOKIE-1", cookie],
                       check=True, stdout=subprocess.DEVNULL)
        env.update(DISPLAY=display, XAUTHORITY=str(auth))
        yield env, server
    finally:
        if server is not None:
            terminate(server)
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        auth.unlink(missing_ok=True)


def new_session(label):
    base = private_dir(state_dir() / "logs")
    return Path(tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-") + label + "-", dir=base))


def initialize_prefix(root):
    verify_runner(root)
    session = new_session("setup")
    print(f"Richte die private Wine-Umgebung ein. Protokoll: {session}", flush=True)
    with virtual_display(session) as (display_env, _):
        env = wine_env(root, display_env)
        try:
            with (session / "wineboot.log").open("wb") as log:
                subprocess.run([str(root / "runner/bin/wineboot"), "-u"], env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
            subprocess.run([str(root / "runner/bin/wineserver"), "-w"], env=env,
                           check=True, timeout=30)
        finally:
            stop_wine(root, env)
    patch_prefix(root)


def run(duration=0):
    root = data_dir()
    os.umask(0o077)
    private_dir(root)
    # Also guards against a second direct invocation, separate from systemd.
    with (root / "session.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Eine WPP20-Sitzung läuft bereits.") from None
        verify_runner(root)
        if not (root / "prefix/system.reg").is_file():
            raise RuntimeError("Wine-Umgebung fehlt. ./install.sh erneut ausführen.")
        device, nodes = find_button()
        check_access(nodes)
        command = launcher_command(root, device)
        patch_prefix(root)
        session = new_session("share")
        print(f"Sitzungsprotokolle: {session}", flush=True)
        ready = session / "ready"

        def stop(signum, frame):
            raise KeyboardInterrupt

        old_handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            with virtual_display(session) as (display_env, xserver):
                env = wine_env(root, display_env)
                children = []
                try:
                    bridge = subprocess.Popen(["/usr/bin/python3", "-u",
                        str(Path(__file__).with_name("bridge.py")), str(ready)], env=display_env)
                    children.append(bridge)
                    print("Bitte im Freigabedialog einen Bildschirm auswählen.", flush=True)
                    deadline = time.monotonic() + 180
                    while not ready.exists():
                        if bridge.poll() is not None:
                            raise RuntimeError("Bildschirmfreigabe abgebrochen oder nicht verfügbar.")
                        if xserver.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError("Kein Bild innerhalb von drei Minuten. wpp20 restart versuchen.")
                        time.sleep(0.1)
                    with (session / "wine.log").open("wb") as log:
                        client = subprocess.Popen(command, env=env, cwd=root,
                                                  stdout=log, stderr=subprocess.STDOUT)
                    children.append(client)
                    print("Yealink gestartet. Jetzt den physischen WPP20-Button drücken.", flush=True)
                    deadline = time.monotonic() + duration if duration else None
                    waiter = None
                    while deadline is None or time.monotonic() < deadline:
                        if bridge.poll() is not None:
                            if bridge.returncode:
                                raise RuntimeError("Bildschirmaufnahme fehlgeschlagen. wpp20 restart versuchen.")
                            print("Bildschirmfreigabe beendet.", flush=True)
                            break
                        if xserver.poll() is not None:
                            raise RuntimeError("Privates Display beendet.")
                        if not all(p.exists() for p in nodes):
                            print("WPP20 entfernt; beende die Sitzung.", flush=True)
                            break
                        result = client.poll()
                        if result is not None:
                            if result:
                                raise RuntimeError(f"Yealink-Launcher beendet ({result}); siehe {session / 'wine.log'}")
                            if waiter is None:
                                waiter = subprocess.Popen([str(root / "runner/bin/wineserver"), "-w"], env=env)
                                children.append(waiter)
                            if waiter.poll() is not None:
                                break
                        time.sleep(0.25)
                finally:
                    # This env points ONLY to our own prefix; never kill other Wine apps.
                    stop_wine(root, env)
                    for child in reversed(children):
                        terminate(child)
        except KeyboardInterrupt:
            print("WPP20-Sitzung wird beendet.", flush=True)
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
            ready.unlink(missing_ok=True)
    print("Aufnahme und private Wine-Sitzung beendet.", flush=True)
