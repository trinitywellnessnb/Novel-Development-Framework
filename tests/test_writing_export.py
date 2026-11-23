"""Neutral export risk fixtures: order, formatting, boundaries, and approval."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from writing_support import exporter

FIXTURE = Path(__file__).parent / "fixtures" / "writing_export"


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(FIXTURE, self.root / "test-material")
        self.output = self.root / ".writing-support" / "export"
        self.manifest = {"schema_version": 1, "book": "TEST-ONLY",
                         "metadata": {"title": "Synthetic Review", "author": "Test Writer", "language": "en-US"},
                         "sources": [self.record("02-first.md", "chapter"), self.record("01-second.md", "chapter")],
                         "assets": [self.record("marker.png")], "formats": ["docx", "epub"]}

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, name, role=None):
        path = self.root / "test-material" / name
        result = {"path": str(path.relative_to(self.root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "approval": {"status": "unapproved"}}
        if role:
            result["role"] = role
        return result

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_real_formats_preserve_order_metadata_and_structure(self):
        originals = {p: p.read_bytes() for p in (self.root / "test-material").iterdir()}
        report = exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertEqual(report["status"], "BUILT_PREVIEW")
        self.assertEqual([s["path"] for s in report["sources"]], [s["path"] for s in self.manifest["sources"]])
        for item in report["outputs"]:
            self.assertTrue(all(item["content_comparison"].values()))
        with zipfile.ZipFile(self.output / "draft-preview.docx") as archive:
            core = archive.read("docProps/core.xml").decode()
            self.assertIn("Synthetic Review", core)
            self.assertIn("Test Writer", core)
            doc = archive.read("word/document.xml").decode()
            self.assertLess(doc.index("First Synthetic Chapter"), doc.index("Second Synthetic Chapter"))
            self.assertIn("w:i", doc)
            self.assertIn("o:hr=", doc)
            self.assertIn("“", doc)
            self.assertTrue(any(n.startswith("word/media/") for n in archive.namelist()))
        with zipfile.ZipFile(self.output / "draft-preview.epub") as archive:
            self.assertEqual(archive.read("mimetype"), b"application/epub+zip")
            opf = next(n for n in archive.namelist() if n.endswith(".opf"))
            metadata = archive.read(opf).decode()
            self.assertIn("Synthetic Review", metadata)
            self.assertIn("Test Writer", metadata)
            self.assertIn("en-US", metadata)
            xhtml = "\n".join(archive.read(n).decode() for n in archive.namelist() if n.endswith(".xhtml") and "nav" not in n)
            self.assertIn("<em>", xhtml)
            self.assertIn("<hr", xhtml)
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        stored = json.loads((self.output / "build.json").read_text())
        self.assertEqual(stored["sources"], report["sources"])
        self.assertIn(report["outputs"][1]["conformance"]["status"], {"SKIPPED", "PASSED", "FAILED"})

    def test_publication_rejects_unapproved_source(self):
        with self.assertRaisesRegex(exporter.ExportError, "approved"):
            exporter.export_book(self.root, self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_stale_input_rejected_before_writing(self):
        (self.root / self.manifest["sources"][0]["path"]).write_text("Changed.")
        with self.assertRaisesRegex(exporter.ExportError, "Stale"):
            exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertFalse(self.output.exists())

    def test_output_boundary_and_symlink(self):
        with self.assertRaisesRegex(exporter.ExportError, "inside .writing-support"):
            exporter.export_book(self.root, self.manifest, self.root / "test-material" / "out", preview=True)
        (self.root / ".writing-support").symlink_to(self.root / "test-material", target_is_directory=True)
        with self.assertRaisesRegex(exporter.ExportError, "Symlink"):
            exporter.export_book(self.root, self.manifest, self.output, preview=True)

    def test_fabricated_approval_quote_rejected(self):
        source = self.manifest["sources"][0]
        source["approval"] = {"status": "approved", "evidence": {**self.record("01-second.md"),
                                  "line_start": 1, "line_end": 2, "excerpt": "Approved by the author", "authority": "unknown"}}
        with self.assertRaisesRegex(exporter.ExportError, "quotation"):
            exporter.export_book(self.root, {**self.manifest, "assets": []}, self.output)

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_remote_and_undeclared_images_rejected(self):
        path = self.root / "test-material" / "02-first.md"
        path.write_text("# Test\n\n![Bad](https://example.com/secret.png)")
        self.manifest["sources"][0] = self.record("02-first.md", "chapter")
        with self.assertRaisesRegex(exporter.ExportError, "explicitly hashed local"):
            exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_cover_is_explicit_and_preserved(self):
        self.manifest["cover"] = "test-material/marker.png"
        self.manifest["formats"] = ["epub"]
        result = exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertTrue(all(result["outputs"][0]["content_comparison"].values()))
        with zipfile.ZipFile(self.output / "draft-preview.epub") as archive:
            opf = next(n for n in archive.namelist() if n.endswith(".opf"))
            self.assertIn("cover-image", archive.read(opf).decode())

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_approval_evidence_allows_build_without_promoting_sources(self):
        approval_path = self.root / "test-material" / "approval.md"
        approval_path.write_text("TEST MATERIAL ONLY. The test author approves this synthetic export.\n")
        evidence = {**self.record("approval.md"), "line_start": 1, "line_end": 1,
                    "excerpt": "The test author approves this synthetic export.", "authority": "test-material"}
        evidence.pop("approval")
        for source in self.manifest["sources"] + self.manifest["assets"]:
            source["approval"] = {"status": "approved", "evidence": evidence}
        self.manifest["formats"] = ["docx"]
        result = exporter.export_book(self.root, self.manifest, self.output)
        self.assertEqual(result["status"], "BUILT")
        self.assertNotIn("PREVIEW", result["metadata"]["title"])
        self.assertEqual(approval_path.read_text(), "TEST MATERIAL ONLY. The test author approves this synthetic export.\n")

    def test_missing_epubcheck_is_skipped_not_validated(self):
        fake = self.root / "test.epub"
        fake.write_bytes(b"not validated")
        with patch.object(exporter, "_epubcheck_command", return_value=None):
            self.assertEqual(exporter.validate_epub(fake)["status"], "SKIPPED")

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_rebuild_is_content_stable_and_does_not_replace_prior_output(self):
        one = exporter.export_book(self.root, self.manifest, self.output, preview=True)
        two = exporter.export_book(self.root, self.manifest, self.output.parent / "second", preview=True)
        self.assertEqual(one["manifest_sha256"], two["manifest_sha256"])
        self.assertEqual(one["outputs"][0]["content_comparison"], two["outputs"][0]["content_comparison"])
        self.assertEqual([o["sha256"] for o in one["outputs"]], [o["sha256"] for o in two["outputs"]])
        with self.assertRaisesRegex(exporter.ExportError, "already exists"):
            exporter.export_book(self.root, self.manifest, self.output, preview=True)

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_series_metadata_and_embedded_image_bytes(self):
        self.manifest["series"] = {"name": "Synthetic Companion Collection", "position": 2}
        report = exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertEqual(report["series"], self.manifest["series"])
        with zipfile.ZipFile(self.output / "draft-preview.epub") as archive:
            opf = next(n for n in archive.namelist() if n.endswith(".opf"))
            xml = archive.read(opf).decode()
            self.assertIn("Synthetic Companion Collection", xml)
            self.assertIn("belongs-to-collection", xml)
            self.assertIn("group-position", xml)
        image_hash = self.manifest["assets"][0]["sha256"]
        for format_ in ("epub", "docx"):
            with zipfile.ZipFile(self.output / ("draft-preview." + format_)) as archive:
                actual = {hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                          if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))}
                self.assertIn(image_hash, actual)
        self.assertTrue(all(item["asset_bytes_preserved"] for item in report["outputs"]))

    def test_invalid_series_metadata_rejected_before_writing(self):
        self.manifest["series"] = {"name": "Synthetic", "position": "second"}
        with self.assertRaisesRegex(exporter.ExportError, "Series"):
            exporter.export_book(self.root, self.manifest, self.output, preview=True)
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc integration unavailable")
    def test_archive_check_detects_replaced_embedded_image(self):
        self.manifest["formats"] = ["docx"]
        exporter.export_book(self.root, self.manifest, self.output, preview=True)
        path = self.output / "draft-preview.docx"
        with zipfile.ZipFile(path) as archive:
            entries = [(name, archive.read(name)) for name in archive.namelist()]
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in entries:
                archive.writestr(name, b"replacement bytes" if name.startswith("word/media/") else data)
        with self.assertRaisesRegex(exporter.ExportError, "image bytes changed"):
            exporter._archive_check(path, "docx", {"scene_breaks": 1}, [self.manifest["assets"][0]["sha256"]])


if __name__ == "__main__":
    unittest.main()
