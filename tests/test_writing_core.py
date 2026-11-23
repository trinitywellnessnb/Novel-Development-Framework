"""Risk tests use neutral temporary material, never project creative sources."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.writing_support import core, context


class WritingCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "rules.md").write_text("TEST MATERIAL\nApproved only for this test.\nKeep the scarf green.\n", encoding="utf-8")
        (self.root / "scene.md").write_text("TEST MATERIAL\nNeri wore the green scarf.\n", encoding="utf-8")
        self.rule = {"path": "rules.md", "source_class": "test", "authority": "test-material", "critical": True}
        self.scene = {"path": "scene.md", "source_class": "test", "authority": "draft",
                      "applicability": {"reader_visible": {"book": "Test", "position": 1}}}
        self.config = {"schema_version": 1, "books": {"Test": {"repository_id": "TEST"}},
                       "sources": [self.rule, self.scene]}
        self.request = {"book": "Test", "scene": "Test scene", "viewpoint": "Neri", "task": "context"}

    def test_evidence_uses_uncommitted_bytes_and_rejects_fabrication(self):
        ref = core.snapshot(self.root, self.rule)
        self.assertEqual(ref["sha256"], hashlib.sha256((self.root / "rules.md").read_bytes()).hexdigest())
        wrong = {**ref, "excerpt": "The scarf is blue."}
        with self.assertRaises(ValueError):
            core.verify_evidence(self.root, wrong)
        wrong = {**ref, "line_start": 0}
        with self.assertRaises(ValueError):
            core.verify_evidence(self.root, wrong)

    def test_stale_packet_and_mutation_rejected(self):
        packet = context.prepare(self.root, self.config, self.request)
        core.validate_packet(self.root, packet)
        edited = copy.deepcopy(packet)
        edited["viewpoint"] = "Someone else"
        with self.assertRaises(ValueError):
            core.validate_packet(self.root, edited)
        (self.root / "scene.md").write_text("Changed test scene\n")
        with self.assertRaises(ValueError):
            core.validate_packet(self.root, packet)

    def test_stable_rebuild_budget_and_critical_overflow(self):
        request = {**self.request, "budget": 1}
        a = context.prepare(self.root, self.config, request)
        b = context.prepare(self.root, self.config, request)
        self.assertEqual(a, b)
        self.assertEqual([ref["path"] for ref in a["sources"]], ["rules.md"])
        self.assertTrue(a["critical_gaps"])
        self.assertIn("budget", a["omissions"][0]["reason"])

    def test_unknown_and_draft_authority_not_promoted(self):
        packet = context.prepare(self.root, self.config, self.request)
        self.assertEqual(packet["sources"][1]["authority"], "draft")
        self.assertEqual(packet["unknowns"], list(context.CONTEXT_FIELDS))
        with self.assertRaises(ValueError):
            core.snapshot(self.root, {**self.rule, "authority": "approved-canon"})

    def test_missing_critical_source_explicit(self):
        self.config["sources"].append({**self.rule, "path": "missing.md"})
        packet = context.prepare(self.root, self.config, self.request)
        self.assertTrue(any("missing.md" in gap for gap in packet["critical_gaps"]))

    def test_source_and_output_boundaries(self):
        for name in ["../outside.md", ".writing-support/report.md", "_inbox/source.md", "tests/fixture.md"]:
            with self.assertRaises(ValueError):
                core.snapshot(self.root, {**self.rule, "path": name})
        for name in ["rules.md", "../outside.md", ".writing-support/../rules.md"]:
            with self.assertRaises(ValueError):
                core.write_json(self.root, name, {})
        (self.root / ".writing-support").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            core.write_json(self.root, ".writing-support/rules.md", {})

    def test_reader_visibility_excludes_author_secrets_and_future_books(self):
        packet = context.prepare(self.root, self.config,
            {**self.request, "task": "reader", "reading_order": ["Test"], "reader_point": {"Test": 1}})
        self.assertEqual([ref["path"] for ref in packet["sources"]], ["scene.md"])
        self.assertNotIn("rules.md", json.dumps(packet))
        self.assertNotIn("Keep the scarf", json.dumps(packet))
        self.scene["applicability"]["reader_visible"]["position"] = 2
        with self.assertRaises(ValueError):
            context.prepare(self.root, self.config,
                {**self.request, "task": "reader", "reading_order": ["Test"], "reader_point": {"Test": 1}})

    def test_reader_budget_and_missing_visible_material_remain_incomplete(self):
        second = {**self.scene, "path": "visible-missing.md", "critical": True}
        self.config["sources"].append(second)
        request = {**self.request, "task": "reader", "reading_order": ["Test"], "reader_point": {"Test": 1}}
        packet = context.prepare(self.root, self.config, request)
        self.assertTrue(packet["critical_gaps"])
        self.assertNotIn("visible-missing.md", json.dumps(packet))
        self.config["sources"] = [self.rule, {**self.scene, "critical": True}]
        packet = context.prepare(self.root, self.config, {**request, "budget": 1})
        self.assertTrue(packet["critical_gaps"])

    def test_changed_configuration_invalidates_file_bound_packet(self):
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(self.config))
        packet = context.prepare(self.root, self.config, self.request)
        core.bind_configuration(self.root, packet, config_path)
        core.validate_packet(self.root, packet)
        config_path.write_text(json.dumps({**self.config, "context_budget": 1}))
        with self.assertRaisesRegex(ValueError, "Configuration changed"):
            core.validate_packet(self.root, packet)

    def test_supersession_preserved_and_sources_unchanged(self):
        self.rule["supersedes"] = [{"path": "old-rule.md", "scope": "scarf only"}]
        before = {p.name: p.read_bytes() for p in self.root.glob("*.md")}
        packet = context.prepare(self.root, self.config, self.request)
        self.assertEqual(packet["sources"][0]["supersedes"], self.rule["supersedes"])
        core.write_json(self.root, ".writing-support/context.json", packet)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob("*.md")})

    def test_context_factual_fields_require_selected_evidence(self):
        wrong = {**self.request, "scene_context": {"location": "a plausible town"}}
        with self.assertRaises(ValueError):
            context.prepare(self.root, self.config, wrong)
        ref = core.snapshot(self.root, self.rule)
        packet = context.prepare(self.root, self.config,
            {**self.request, "scene_context": {"possessions": {"text": "green scarf", "evidence": [ref]}}})
        self.assertNotIn("possessions", packet["unknowns"])

    def test_rendered_source_links_and_fences_remain_literal_data(self):
        from scripts.validate_framework import outside_fenced_code
        text = "TEST MATERIAL\n[Relative source link](missing-in-derived-directory.md)\n```\nQuoted code\n```"
        rendered = core.literal(text)
        self.assertIn(text, rendered)
        self.assertNotIn("missing-in-derived-directory", "".join(outside_fenced_code(rendered)))

    def test_cli_help_and_context_preparation(self):
        script = Path(__file__).resolve().parents[1] / "scripts/writing_toolkit.py"
        (self.root / "config.json").write_text(json.dumps(self.config))
        (self.root / "request.json").write_text(json.dumps(self.request))
        proc = subprocess.run([sys.executable, str(script), "--root", str(self.root), "--config", "config.json",
            "prepare", "--request", "request.json"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PREPARED", proc.stdout)
        core.validate_packet(self.root, core.read_json(self.root / ".writing-support/context/packet.json"))


if __name__ == "__main__":
    unittest.main()
