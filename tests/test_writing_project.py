"""Initialization behavior in fresh synthetic directories; no creative fixtures."""
import json
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from writing_support.project import init_project


class ProjectInitializationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'

    def test_standalone_is_usable_without_worldbuilding(self):
        result = init_project(self.root, 'Synthetic Notebook', author='Synthetic Author')
        config = json.loads((self.root / '09_Tools/Writing_Support.json').read_text())
        self.assertEqual(config['schema_version'], 1)
        self.assertEqual(list(config['books']), ['BOOK-001'])
        self.assertEqual(config['project']['title'], 'Synthetic Notebook')
        self.assertFalse((self.root / '03_Worldbuilding').exists())
        from writing_support.core import build_index
        index = build_index(self.root, config)
        self.assertFalse(index['unavailable'])
        from writing_support.context import prepare
        request = json.loads((self.root / result['request']).read_text())
        packet = prepare(self.root, config, request)
        self.assertEqual(packet['status'], 'PREPARED')
        self.assertTrue(packet['sources'])
        self.assertTrue(all(not s['authority'].startswith('approved-') for s in config['sources']))

    def test_native_guidance_is_discoverable_and_existing_guidance_preserved(self):
        init_project(self.root, 'Synthetic')
        guidance = (self.root / 'AGENTS.md').read_text()
        self.assertIn('.ndf/docs/skills/writing-support/SKILL.md', guidance)
        self.assertIn('author', guidance.lower())
        other = self.root.parent / 'existing-project'
        other.mkdir()
        (other / 'AGENTS.md').write_text('Keep existing author rules.\n')
        init_project(other, 'Synthetic')
        self.assertEqual((other / 'AGENTS.md').read_text(), 'Keep existing author rules.\n')

    def test_custom_series_and_optional_settings(self):
        init_project(self.root, 'Synthetic Series', books={'north': 'North', 'south': 'South'},
                     options={'pov': 'alternating', 'time_systems': [{'id': 'local', 'calendar': 'custom'}],
                              'worldbuilding': True, 'authority_order': ['approved-manuscript', 'approved-canon']})
        config = json.loads((self.root / '09_Tools/Writing_Support.json').read_text())
        self.assertEqual(list(config['books']), ['north', 'south'])
        self.assertEqual(config['authority_order'][0], 'approved-manuscript')
        self.assertEqual(config['project']['pov'], 'alternating')
        self.assertTrue((self.root / '03_Worldbuilding/README.md').exists())

    def test_refuses_existing_outputs_before_writing(self):
        self.root.mkdir()
        target = self.root / '05_Books/BOOK-001/Chapters/01.md'
        target.parent.mkdir(parents=True)
        target.write_text('preserve existing source')
        before = set(self.root.rglob('*'))
        with self.assertRaises(ValueError):
            init_project(self.root, 'Synthetic')
        self.assertEqual(before, set(self.root.rglob('*')))
        self.assertEqual(target.read_text(), 'preserve existing source')

    def test_existing_intent_and_voice_are_preserved_on_attach(self):
        self.root.mkdir()
        intent = self.root / '00_Project/Author_Intent.md'
        intent.parent.mkdir()
        intent.write_text('# Existing author instructions\nKeep this.\n')
        init_project(self.root, 'Synthetic')
        self.assertEqual(intent.read_text(), '# Existing author instructions\nKeep this.\n')

    def test_traversal_and_symlinks_fail_without_outputs(self):
        with self.assertRaises(ValueError):
            init_project(self.root, 'Synthetic', books={'../escape': 'Bad'})
        self.assertFalse(self.root.exists())
        self.root.mkdir()
        outside = self.root.parent / 'outside'
        outside.mkdir()
        (self.root / '05_Books').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            init_project(self.root, 'Synthetic')
        self.assertFalse((self.root / '09_Tools').exists())
        self.assertFalse(list(outside.iterdir()))

    def test_root_symlink_is_rejected(self):
        outside = self.root.parent / 'outside'
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            init_project(self.root, 'Synthetic')
        self.assertFalse(list(outside.iterdir()))

    def test_invalid_options_and_duplicate_books_are_rejected(self):
        for kwargs in ({'options': {'context_budget': -1}}, {'books': ['same', 'same']},
                       {'title': ''}, {'options': {'unknown_option': 'ignored'}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                init_project(self.root, **({'title': 'Synthetic'} | kwargs))
        self.assertFalse(self.root.exists())

    def test_cli_initialization_and_context_commands(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/writing_toolkit.py'
        def command(*args):
            return subprocess.run([sys.executable, str(script), '--root', str(self.root), *args],
                                  capture_output=True, text=True)
        initialized = command('init', '--title', 'Synthetic CLI Novel', '--author', 'Synthetic Author')
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        indexed = command('index')
        self.assertEqual(indexed.returncode, 0, indexed.stdout + indexed.stderr)
        prepared = command('prepare', '--request', '09_Tools/context-request.json')
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        packet = json.loads((self.root / '.writing-support/context/packet.json').read_text())
        self.assertEqual(packet['status'], 'PREPARED')
        self.assertEqual(packet['book'], 'BOOK-001')

    @unittest.skipUnless(shutil.which('pandoc'), 'Pandoc not installed')
    def test_cli_initialization_and_preview_exports(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/writing_toolkit.py'
        initialized = subprocess.run([sys.executable, str(script), '--root', str(self.root),
                                      'init', '--title', 'Synthetic Preview', '--author', 'Synthetic Author'],
                                     capture_output=True, text=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        exported = subprocess.run([sys.executable, str(script), '--root', str(self.root),
                                   'export', '--manifest', '05_Books/BOOK-001/export-manifest.json', '--preview'],
                                  capture_output=True, text=True)
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        report = json.loads(exported.stdout)
        self.assertEqual(report['status'], 'BUILT_PREVIEW')
        self.assertEqual([o['format'] for o in report['outputs']], ['docx', 'epub'])
        for output in report['outputs']:
            self.assertTrue((self.root / output['path']).is_file())
            self.assertTrue(all(output['content_comparison'].values()))

    def test_failure_during_write_removes_only_created_files(self):
        from unittest.mock import patch
        self.root.mkdir()
        keep = self.root / 'unrelated.txt'
        keep.write_text('preserve')
        original = Path.open
        def fail_voice(path, *args, **kwargs):
            if path.name == 'Voice_Guide.md' and args and args[0] == 'x':
                raise OSError('synthetic write failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_voice), self.assertRaises(OSError):
            init_project(self.root, 'Synthetic')
        self.assertEqual(keep.read_text(), 'preserve')
        self.assertEqual(list(self.root.iterdir()), [keep])

    def test_export_manifest_has_current_hash_and_explicit_order(self):
        import hashlib
        result = init_project(self.root, 'Synthetic', author='Synthetic Author')
        manifest = json.loads((self.root / result['manifest']).read_text())
        source = manifest['sources'][0]
        self.assertEqual(source['sha256'], hashlib.sha256((self.root / source['path']).read_bytes()).hexdigest())
        self.assertEqual(source['approval']['status'], 'unapproved')
        self.assertEqual(manifest['formats'], ['docx', 'epub'])

if __name__ == '__main__':
    unittest.main()
