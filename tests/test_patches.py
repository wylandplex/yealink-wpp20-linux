import os
from pathlib import Path
import tempfile
import unittest

from wpp20lib.patches import (CURSOR_PATCHED, HID_PATCHED, TARGETS, patch_bytes,
                              patch_paths, sha)


class VersionGuards(unittest.TestCase):
    def test_unknown_inputs_are_rejected_without_mutation(self):
        for kind in ("hid", "cursor"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "unrecognized.bin"
                path.write_bytes(b"not the supported Wine version")
                with self.assertRaises(ValueError):
                    patch_paths([(path, kind)])
                self.assertEqual(path.read_bytes(), b"not the supported Wine version")

    def test_checks_survive_python_optimization(self):
        # require() deliberately uses exceptions, not removable assert statements.
        import subprocess
        import sys
        code = "from wpp20lib.patches import patch_bytes; patch_bytes(b'wrong', 'hid')"
        result = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"ValueError", result.stderr)


@unittest.skipUnless(os.environ.get("WPP20_TEST_RUNNER"), "optional: set WPP20_TEST_RUNNER")
class ActualWineFiles(unittest.TestCase):
    def test_exact_output_and_idempotence(self):
        for relative, _, kind in TARGETS:
            with self.subTest(kind=kind):
                data = (Path(os.environ["WPP20_TEST_RUNNER"]) / relative).read_bytes()
                patched = patch_bytes(data, kind)
                self.assertEqual(sha(patched), HID_PATCHED if kind == "hid" else CURSOR_PATCHED)
                self.assertEqual(patch_bytes(patched, kind), patched)

    def test_all_inputs_validated_before_first_write(self):
        with tempfile.TemporaryDirectory() as temp:
            good, bad = Path(temp) / "good", Path(temp) / "bad"
            original = (Path(os.environ["WPP20_TEST_RUNNER"]) / TARGETS[0][0]).read_bytes()
            good.write_bytes(original)
            bad.write_bytes(b"unsupported DLL")
            with self.assertRaises(ValueError):
                patch_paths([(good, "hid"), (bad, "cursor")])
            self.assertEqual(good.read_bytes(), original)

    def test_prefix_symlink_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as temp:
            target, link = Path(temp) / "source", Path(temp) / "prefix-link"
            data = (Path(os.environ["WPP20_TEST_RUNNER"]) / TARGETS[0][0]).read_bytes()
            target.write_bytes(data)
            link.symlink_to(target)
            patch_paths([(link, "hid")])
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(sha(link.read_bytes()), HID_PATCHED)
