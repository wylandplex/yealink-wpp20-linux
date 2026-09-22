from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wpp20lib.devices import find_button, mounted_launcher


class Devices(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("bus/usb/devices", "class/hidraw", "class/block", "devices"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)

    def usb(self, name, vendor, product):
        path = self.root / "devices" / name
        path.mkdir()
        for key, value in {"idVendor": vendor, "idProduct": product, "busnum": "3", "devnum": "42"}.items():
            (path / key).write_text(value)
        (self.root / "bus/usb/devices" / name).symlink_to(path)
        hid = self.root / "class/hidraw" / ("hidraw0" if name == "wpp20" else "hidraw1")
        hid.mkdir()
        (path / "interface/hid").mkdir(parents=True)
        (hid / "device").symlink_to(path / "interface/hid")
        return path

    def test_only_button_hid_is_selected(self):
        button = self.usb("wpp20", "6993", "b022")
        self.usb("keyboard", "1234", "abcd")
        actual, nodes = find_button(self.root, Path("/example-dev"))
        self.assertEqual(actual, button)
        self.assertEqual(nodes, [Path("/example-dev/bus/usb/003/042"), Path("/example-dev/hidraw0")])

    def test_multiple_buttons_require_disambiguation(self):
        self.usb("wpp20", "6993", "b022")
        self.usb("second", "6993", "b022")
        with self.assertRaisesRegex(RuntimeError, "gefunden: 2"):
            find_button(self.root)

    def test_similar_usb_ids_not_accepted(self):
        self.usb("other", "6993", "b023")
        with self.assertRaisesRegex(RuntimeError, "gefunden: 0"):
            find_button(self.root)

    def test_volume_must_belong_to_the_button(self):
        button = self.usb("wpp20", "6993", "b022")
        (button / "storage/block/sr7").mkdir(parents=True)
        (self.root / "class/block/sr7").symlink_to(button / "storage/block/sr7")
        wrong, right = self.root / "WPP20-fake", self.root / "real volume"
        for volume in (wrong, right):
            volume.mkdir()
            (volume / "PresentationLauncher.exe").touch()
        import json
        listing = {"blockdevices": [
            {"name": "/dev/sr6", "mountpoints": [str(wrong)]},
            {"name": "/dev/sr7", "mountpoints": [None, str(right)]}]}
        with patch("subprocess.check_output", return_value=json.dumps(listing)):
            self.assertEqual(mounted_launcher(button, self.root), right)
