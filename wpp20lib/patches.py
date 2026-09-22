"""Version-locked patches for our private Soda 9.0-1 copy only.

No Wine or Yealink binaries are distributed in this repository. See
docs/implementation.md for the two workarounds and their limitations.
"""
import hashlib
from pathlib import Path
import struct

HID_ORIGINAL = "29e78f841a70c79b6f68998ef55d857a2fd90f5126c10d02c76708ca9b684b68"
HID_PATCHED = "7a03a5620ee383c646e4bd8764a27ea36bccbc3096f99b5c0b8c32978b1d5fed"
CURSOR_ORIGINAL = "01dd47d31083115fefe5681f32f1dde54831c57a81b2d71c12ae276de17aa1a2"
CURSOR_PATCHED = "89056cd6b08419e67fb4c5e7a0a697368ed555011c80aa2bec6357dff212dc7c"
TARGETS = (
    ("lib/wine/x86_64-windows/hidclass.sys", "system32/drivers/hidclass.sys", "hid"),
    ("lib32/wine/i386-windows/user32.dll", "syswow64/user32.dll", "cursor"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def patch_bytes(data, kind):
    original, patched = {"hid": (HID_ORIGINAL, HID_PATCHED),
                         "cursor": (CURSOR_ORIGINAL, CURSOR_PATCHED)}[kind]
    digest = sha(data)
    if digest == patched:
        return data
    require(digest == original, f"Unbekannte {kind}-Version; Änderung verweigert (SHA-256 {digest}).")
    b = bytearray(data)
    if kind == "hid":
        require(b[0x1280:0x1284] == bytes.fromhex("49 29 45 38"), "Unerwartete HID-Instruktion.")
        b[0x1280:0x1284] = b"\x90" * 4
    else:
        pe = struct.unpack_from("<I", b, 0x3c)[0]
        optional = pe + 24
        require(struct.unpack_from("<H", b, pe + 4)[0] == 0x14c, "Kein i386-PE.")
        require(struct.unpack_from("<H", b, optional)[0] == 0x10b, "Kein PE32.")
        table = optional + struct.unpack_from("<H", b, pe + 20)[0]
        sections = []
        for i in range(struct.unpack_from("<H", b, pe + 6)[0]):
            offset = table + 40 * i
            name = b[offset:offset + 8].split(b"\0")[0]
            size, rva, raw_size, raw = struct.unpack_from("<IIII", b, offset + 8)
            sections.append((name, size, rva, raw_size, raw, offset))

        def file_offset(rva):
            for _, size, base, raw_size, raw, _ in sections:
                if base <= rva < base + max(size, raw_size):
                    return raw + rva - base
            raise ValueError("Unbekannte PE-Adresse.")

        export = file_offset(struct.unpack_from("<I", b, optional + 96)[0])
        count, functions, names, ordinals = struct.unpack_from("<IIII", b, export + 24)
        entry = None
        for i in range(count):
            name_rva = struct.unpack_from("<I", b, file_offset(names) + 4 * i)[0]
            start = file_offset(name_rva)
            if b[start:b.index(0, start)] == b"GetCursorInfo":
                ordinal = struct.unpack_from("<H", b, file_offset(ordinals) + 2 * i)[0]
                entry = file_offset(functions) + 4 * ordinal
                break
        require(entry is not None, "GetCursorInfo fehlt.")
        target = struct.unpack_from("<I", b, entry)[0]
        require(target == 0x901a8, "Unerwartete GetCursorInfo-Adresse.")
        _, size, rva, raw_size, raw, header = next(s for s in sections if s[0] == b".text")
        wrapper_rva = rva + size
        code = bytes.fromhex("55 89 e5 ff 75 08 e8")
        code += struct.pack("<i", target - (wrapper_rva + 11))
        code += bytes.fromhex("85 c0 74 0a 8b 55 08 c7 42 04 00 00 00 00 c9 c2 04 00")
        require(size + len(code) <= raw_size, "Kein Platz für Cursor-Wrapper.")
        require(b[raw + size:raw + size + len(code)] == bytes(len(code)), "Padding nicht leer.")
        b[raw + size:raw + size + len(code)] = code
        struct.pack_into("<I", b, header + 8, size + len(code))
        struct.pack_into("<I", b, entry, wrapper_rva)
    require(sha(b) == patched, "Ergebnis-Prüfsumme stimmt nicht überein.")
    return bytes(b)


def patch_paths(paths):
    # Validate every input before changing any file. Atomic replace also breaks
    # prefix hardlinks/symlinks rather than modifying a source runner through them.
    changes = [(Path(path), patch_bytes(Path(path).read_bytes(), kind)) for path, kind in paths]
    for path, result in changes:
        if path.read_bytes() == result:
            continue
        mode = path.stat().st_mode & 0o777
        temporary = path.with_name(path.name + ".wpp20-new")
        temporary.write_bytes(result)
        temporary.chmod(mode)
        temporary.replace(path)


def patch_runner(root):
    patch_paths([(root / "runner" / relative, kind) for relative, _, kind in TARGETS])


def patch_prefix(root):
    patch_paths([(root / "prefix/drive_c/windows" / relative, kind)
                 for _, relative, kind in TARGETS])


def verify_runner(root):
    for relative, _, kind in TARGETS:
        path = root / "runner" / relative
        expected = HID_PATCHED if kind == "hid" else CURSOR_PATCHED
        require(sha(path.read_bytes()) == expected, f"Wine-Korrektur fehlt: {path}")
