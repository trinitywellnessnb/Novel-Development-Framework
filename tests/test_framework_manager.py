"""Synthetic installation/update exercises; no project sources are distributed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("framework_manager", ROOT / "scripts/framework_manager.py")


class FrameworkManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SPEC.origin or not Path(SPEC.origin).exists():
            raise AssertionError("framework manager implementation is missing")
        cls.m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.m)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "framework"
        self.source.mkdir()
        self.project = self.base / "novel"
        self.project.mkdir()
        self.creative = self.project / "manuscript.md"
        self.creative.write_bytes(b"Original synthetic novel.\r\n")
        self.config = self.project / "writing-project.json"
        self.config.write_text('{"project":"independent"}\n')
        self.source_file = self.source / "scripts/writing_toolkit.py"
        self.source_file.parent.mkdir()
        self.source_file.write_text('print("toolkit v1")\n')
        self.runtime = ["scripts/writing_toolkit.py", "scripts/validate_review_packet.py", "scripts/framework_manager.py"]
        self.runtime += ["scripts/writing_support/" + name + ".py" for name in
                         ("__init__", "context", "core", "demo", "exporter", "reviews", "structure", "project")]
        for name in self.runtime[1:]:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('"""Synthetic runtime component."""\n')
        self.set_version("1.0.0")
        self.v1 = self.base / "v1"
        self.m.bundle(self.source, self.v1)

    def set_version(self, version, schema=1):
        (self.source / "framework.json").write_text(json.dumps({
            "framework_version": version, "toolkit_version": version,
            "configuration_schema": schema, "python_requires": ">=3.10",
            "managed_files": self.runtime}))

    def install(self):
        self.m.install(self.v1, self.project)

    def newer(self, version="1.1.0", schema=1):
        self.set_version(version, schema)
        self.source_file.write_text('print("toolkit v2")\n')
        target = self.base / ("v" + version)
        self.m.bundle(self.source, target)
        return target

    def protected(self):
        self.assertEqual(self.creative.read_bytes(), b"Original synthetic novel.\r\n")
        self.assertEqual(self.config.read_text(), '{"project":"independent"}\n')

    def test_install_separate_project_and_cli_version(self):
        self.install()
        self.assertEqual((self.project / ".ndf/scripts/writing_toolkit.py").read_bytes(), self.source_file.read_bytes())
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.0.0")
        self.protected()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/framework_manager.py"),
            "version", "--project", str(self.project)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1.0.0", result.stdout)

    def test_reinstall_refuses_overwrite(self):
        self.install()
        with self.assertRaises(ValueError):
            self.install()

    def test_actual_repository_bundle_runs_installed_project_workflow(self):
        distribution = self.base / "actual-distribution"
        self.m.bundle(ROOT, distribution)
        self.m.install(distribution, self.project)
        cli = self.project / ".ndf/scripts/writing_toolkit.py"
        for arguments in [("version",), ("init", "--title", "Synthetic Independent Novel"),
                          ("index",), ("prepare", "--request", "09_Tools/context-request.json")]:
            result = subprocess.run([sys.executable, str(cli), "--root", str(self.project), *arguments],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.project / ".writing-support/context/packet.json").exists())
        self.protected()

    def test_invalid_installation_receipt_blocks_adoption(self):
        self.install()
        (self.project / ".ndf/install.json").write_text('{"unexpected":"state"}')
        self.assertEqual(self.m.plan(self.newer(), self.project)["status"], "BLOCKED")

    def test_upgrade_detection_apply_and_rollback_preserve_creative_files(self):
        self.install()
        candidate = self.newer()
        plan = self.m.plan(candidate, self.project)
        self.assertEqual(plan["status"], "READY")
        self.assertEqual(plan["current_version"], "1.0.0")
        self.assertEqual(plan["target_version"], "1.1.0")
        self.assertTrue(plan["files_affected"])
        self.m.apply(plan, self.project)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.1.0")
        self.m.rollback(self.project)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.0.0")
        self.protected()

    def test_locally_modified_component_blocks_without_changes(self):
        self.install()
        local = self.project / ".ndf/scripts/writing_toolkit.py"
        local.write_text("# project extension\n")
        plan = self.m.plan(self.newer(), self.project)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("scripts/writing_toolkit.py", str(plan["conflicts"]))
        with self.assertRaises(ValueError):
            self.m.apply(plan, self.project)
        self.assertEqual(local.read_text(), "# project extension\n")
        self.protected()

    def test_unknown_installation_file_blocks_upgrade(self):
        self.install()
        extra = self.project / ".ndf/custom.txt"
        extra.write_text("keep extension")
        self.assertEqual(self.m.plan(self.newer(), self.project)["status"], "BLOCKED")
        self.assertEqual(extra.read_text(), "keep extension")

    def test_edit_after_plan_is_rejected(self):
        self.install()
        plan = self.m.plan(self.newer(), self.project)
        (self.project / ".ndf/scripts/writing_toolkit.py").write_text("# changed after plan\n")
        with self.assertRaises(ValueError):
            self.m.apply(plan, self.project)
        self.protected()

    def test_candidate_tampering_after_plan_is_rejected(self):
        self.install()
        candidate = self.newer()
        plan = self.m.plan(candidate, self.project)
        (candidate / "scripts/writing_toolkit.py").write_text("# changed candidate\n")
        with self.assertRaises(ValueError):
            self.m.apply(plan, self.project)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.0.0")

    def test_major_schema_downgrade_and_same_version_changes_block(self):
        self.install()
        for version, schema in [("2.0.0", 1), ("1.2.0", 2), ("0.9.0", 1), ("1.0.0", 1)]:
            with self.subTest(version=version, schema=schema):
                plan = self.m.plan(self.newer(version, schema), self.project)
                self.assertEqual(plan["status"], "BLOCKED")

    def test_numeric_semver_comparison(self):
        self.set_version("1.9.0")
        dist = self.base / "v19"
        self.m.bundle(self.source, dist)
        self.m.install(dist, self.project)
        self.assertEqual(self.m.plan(self.newer("1.10.0"), self.project)["status"], "READY")

    def test_bundle_never_includes_creative_sources(self):
        (self.source / "manuscript.md").write_text("private creative bytes")
        with self.assertRaises(ValueError):
            config = json.loads((self.source / "framework.json").read_text())
            config["managed_files"].append("manuscript.md")
            (self.source / "framework.json").write_text(json.dumps(config))
            self.m.bundle(self.source, self.base / "unsafe")

    def test_distribution_extra_file_rejected(self):
        (self.v1 / "unexpected.md").write_text("not manifest-owned")
        with self.assertRaises(ValueError):
            self.install()

    def test_missing_runtime_module_blocks_candidate(self):
        self.install()
        candidate = self.newer()
        manifest = candidate / "manifest.json"
        value = json.loads(manifest.read_text())
        del value["files"]["scripts/writing_support/project.py"]
        (candidate / "scripts/writing_support/project.py").unlink()
        manifest.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.m.plan(candidate, self.project)

    def test_plan_output_is_ignored_without_changing_existing_project_ignore(self):
        self.install()
        candidate = self.newer()
        ignored = self.project / ".gitignore"
        ignored.write_text("# Author-owned ignore rules\n*.bak\n")
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/framework_manager.py"),
            "plan", "--distribution", str(candidate), "--project", str(self.project)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        checked = subprocess.run(["git", "-C", str(self.project), "check-ignore", ".writing-support/framework-upgrade.json"],
                                 capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(ignored.read_text(), "# Author-owned ignore rules\n*.bak\n")

    def test_empty_extension_directory_is_not_discarded(self):
        self.install()
        (self.project / ".ndf/custom-extension").mkdir()
        self.assertEqual(self.m.plan(self.newer(), self.project)["status"], "BLOCKED")

    def test_duplicate_json_fields_rejected(self):
        manifest = self.v1 / "manifest.json"
        text = manifest.read_text()
        manifest.write_text(text.replace('"distribution_schema": 1', '"distribution_schema": 2, "distribution_schema": 1'))
        with self.assertRaises(ValueError):
            self.install()

    def test_traversal_manifest_rejected(self):
        manifest = self.v1 / "manifest.json"
        value = json.loads(manifest.read_text())
        value["files"]["../manuscript.md"] = hashlib.sha256(b"x").hexdigest()
        manifest.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.install()
        self.protected()

    def test_python_cache_can_be_regenerated_without_blocking_update(self):
        self.install()
        cache = self.project / ".ndf/scripts/__pycache__"
        cache.mkdir()
        (cache / "writing_toolkit.cpython-310.pyc").write_bytes(b"regenerable")
        self.assertEqual(self.m.plan(self.newer(), self.project)["status"], "READY")

    def test_symlink_source_distribution_and_project_rejected(self):
        other = self.base / "other.py"
        other.write_text("print('other')\n")
        self.source_file.unlink()
        self.source_file.symlink_to(other)
        with self.assertRaises(ValueError):
            self.m.bundle(self.source, self.base / "symlink-source")
        managed = self.v1 / "scripts/writing_toolkit.py"
        managed.unlink()
        managed.symlink_to(other)
        with self.assertRaises(ValueError):
            self.install()
        alias = self.base / "alias"
        alias.symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.m.install(self.v1, alias)

    def test_malformed_python_rejected_before_install(self):
        self.source_file.write_text("def invalid(\n")
        with self.assertRaises(ValueError):
            self.m.bundle(self.source, self.base / "invalid-python")

    def test_rollback_refuses_modified_current_or_backup(self):
        self.install()
        self.m.apply(self.m.plan(self.newer(), self.project), self.project)
        receipt = json.loads((self.project / ".ndf/install.json").read_text())
        previous = self.project / receipt["previous_backup"]
        (previous / "scripts/writing_toolkit.py").write_text("# tamper backup\n")
        with self.assertRaises(ValueError):
            self.m.rollback(self.project)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.1.0")

    def test_transaction_recovery_restores_old_tree_after_first_rename(self):
        self.install()
        candidate = self.newer()
        plan = self.m.plan(candidate, self.project)
        original = self.m._rename
        calls = []
        def interrupted(source, destination):
            calls.append((source, destination))
            if len(calls) == 2:
                raise KeyboardInterrupt("synthetic crash")
            original(source, destination)
        self.m._rename = interrupted
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.m.apply(plan, self.project)
        finally:
            self.m._rename = original
        self.assertFalse((self.project / ".ndf").exists())
        self.m.recover(self.project)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.0.0")
        self.protected()

    def test_operational_failure_between_renames_recovers_automatically(self):
        self.install()
        plan = self.m.plan(self.newer(), self.project)
        original = self.m._rename
        count = 0
        def fail_once(source, destination):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("synthetic write failure")
            original(source, destination)
        self.m._rename = fail_once
        try:
            with self.assertRaises(OSError):
                self.m.apply(plan, self.project)
        finally:
            self.m._rename = original
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.0.0")
        self.assertFalse((self.project / ".ndf-transaction.json").exists())
        self.protected()

    def test_recovery_recognizes_completed_second_rename(self):
        self.install()
        plan = self.m.plan(self.newer(), self.project)
        original = self.m._rename
        count = 0
        def interrupt_after(source, destination):
            nonlocal count
            count += 1
            original(source, destination)
            if count == 2:
                raise KeyboardInterrupt("synthetic process interruption after commit")
        self.m._rename = interrupt_after
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.m.apply(plan, self.project)
        finally:
            self.m._rename = original
        result = self.m.recover(self.project)
        self.assertEqual(result["status"], "COMPLETED_PENDING_TRANSACTION")
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.1.0")

    def test_concurrent_transaction_blocks_without_removing_existing_journal(self):
        self.install()
        plan = self.m.plan(self.newer(), self.project)
        journal = self.project / ".ndf-transaction.json"
        journal.write_text('{"existing":"operation"}')
        with self.assertRaises(ValueError):
            self.m.apply(plan, self.project)
        self.assertEqual(journal.read_text(), '{"existing":"operation"}')

    def test_recover_cannot_remove_an_active_apply_transaction(self):
        self.install()
        proposal = self.m.plan(self.newer(), self.project)
        original = self.m._rename
        attempted = False
        def concurrent_recovery(source, destination):
            nonlocal attempted
            if not attempted:
                attempted = True
                with self.assertRaises(ValueError):
                    self.m.recover(self.project)
            original(source, destination)
        self.m._rename = concurrent_recovery
        try:
            self.m.apply(proposal, self.project)
        finally:
            self.m._rename = original
        self.assertTrue(attempted)
        self.assertEqual(self.m.version(self.project)["framework_version"], "1.1.0")
        self.assertFalse((self.project / ".ndf-transaction.json").exists())


if __name__ == "__main__":
    unittest.main()
