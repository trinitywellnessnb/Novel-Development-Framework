"""Neutral fixtures for the optional read-only review-packet checker."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_review_packet.py"
spec = importlib.util.spec_from_file_location("validate_review_packet", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        self.file = self.root / "docs" / "fixture.md"
        self.file.write_text("One fact.\nAnother fact.\n", encoding="utf-8")
        self.packet = {
            "schema_version": 1,
            "repository_revision": "a" * 40,
            "purpose": "Fictional validation fixture",
            "authorized_sources": ["docs/fixture.md"],
            "sources": [{
                "path": "docs/fixture.md",
                "sha256": hashlib.sha256(self.file.read_bytes()).hexdigest(),
                "line_start": 1,
                "line_end": 1,
                "excerpt": "One fact.",
                "authority": "synthetic fixture",
            }],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_authorized_source(self):
        self.assertEqual(module.validate(self.root, self.packet), 1)

    def test_modified_bytes_are_rejected(self):
        self.file.write_text("Revised.\n", encoding="utf-8")
        with self.assertRaisesRegex(module.PacketError, "mismatch"):
            module.validate(self.root, self.packet)

    def test_unlisted_source_is_rejected(self):
        self.packet["authorized_sources"] = ["docs/other.md"]
        with self.assertRaisesRegex(module.PacketError, "authorized"):
            module.validate(self.root, self.packet)

    def test_traversal_is_rejected(self):
        self.packet["authorized_sources"] = ["docs/../fixture.md"]
        with self.assertRaisesRegex(module.PacketError, "Unsafe"):
            module.validate(self.root, self.packet)

    def test_mismatched_excerpt_is_rejected(self):
        self.packet["sources"][0]["excerpt"] = "Something else"
        with self.assertRaisesRegex(module.PacketError, "Excerpt"):
            module.validate(self.root, self.packet)

    def test_missing_anchor_is_rejected(self):
        self.packet["sources"][0]["line_end"] = 99
        with self.assertRaisesRegex(module.PacketError, "anchor"):
            module.validate(self.root, self.packet)

    def test_symlink_is_rejected(self):
        (self.root / "docs" / "alias.md").symlink_to(self.file)
        self.packet["authorized_sources"] = ["docs/alias.md"]
        self.packet["sources"][0]["path"] = "docs/alias.md"
        with self.assertRaisesRegex(module.PacketError, "Symlink"):
            module.validate(self.root, self.packet)

    def test_protected_requires_extra_opt_in(self):
        (self.root / "archive").mkdir()
        protected = self.root / "archive" / "note.md"
        protected.write_text("Source.\n", encoding="utf-8")
        self.packet["authorized_sources"] = ["archive/note.md"]
        self.packet["sources"][0].update(path="archive/note.md", sha256=hashlib.sha256(protected.read_bytes()).hexdigest(), excerpt="Source.")
        with self.assertRaisesRegex(module.PacketError, "--allow-protected"):
            module.validate(self.root, self.packet)
        self.assertEqual(module.validate(self.root, self.packet, allow_protected=True), 1)

    def test_packet_file_cli(self):
        packet_file = self.root / "packet.json"
        packet_file.write_text(json.dumps(self.packet), encoding="utf-8")
        self.assertEqual(module.main(["--root", str(self.root), "--packet", str(packet_file)]), 0)


if __name__ == "__main__":
    unittest.main()
