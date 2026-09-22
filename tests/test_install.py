import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from wpp20lib.common import wine_env
from wpp20lib.install import desktop_quote, systemd_quote, unpack_archive, verify_archive


class Installation(unittest.TestCase):
    def test_corrupt_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "broken.tar.xz"
            archive.write_bytes(b"bad download")
            with self.assertRaises(ValueError):
                verify_archive(archive)

    def test_tar_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "archive.tar.xz"
            with tarfile.open(archive, "w:xz") as tar:
                info = tarfile.TarInfo("../escaped")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
            with patch("wpp20lib.install.verify_archive"):
                with self.assertRaises(tarfile.FilterError):
                    unpack_archive(archive, Path(temp) / "unpack")
            self.assertFalse((Path(temp) / "escaped").exists())

    def test_other_wine_environment_is_not_inherited(self):
        root = Path("/private/wpp20")
        env = wine_env(root, {"WINEPREFIX": "/other", "WINELOADER": "/wrong/wine",
                              "PROTON_ENABLE_HIDRAW": "anything", "DISPLAY": ":123"})
        self.assertEqual(env["WINEPREFIX"], "/private/wpp20/prefix")
        self.assertEqual(env["DISPLAY"], ":123")
        self.assertNotIn("WINELOADER", env)
        self.assertEqual(env["PROTON_ENABLE_HIDRAW"], "0x6993/0xb022")

    def test_unit_paths_escape_specifiers_and_spaces(self):
        self.assertEqual(systemd_quote("/a b/100%/app"), '"/a b/100%%/app"')
        with self.assertRaises(ValueError):
            systemd_quote("/bad\n[Service]")
        self.assertEqual(desktop_quote("/a b/100%/app"), '"/a b/100%%/app"')
