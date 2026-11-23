"""Generic framework regression coverage; all sources are synthetic."""
import copy
import tempfile
import unittest
from pathlib import Path
from scripts.writing_support import core, context

class GenericTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('a.md','b.md','approval.md'):
            (self.root/name).write_text(name + '\nOnly synthetic material.\n')
        self.config = {'schema_version':1, 'books':{'one':{'repository_id':'one'}}, 'sources':[
            {'path':'a.md','source_class':'direction','authority':'draft'},
            {'path':'b.md','source_class':'canon','authority':'unknown'}]}
        self.request = {'task':'context','book':'one','scene':'entry','viewpoint':'unknown'}

    def test_project_authority_order_controls_selection(self):
        self.config['authority_order'] = ['unknown','draft']
        packet = context.prepare(self.root,self.config,self.request)
        self.assertEqual(packet['sources'][0]['path'],'b.md')

    def test_custom_approved_authority_requires_evidence(self):
        self.config.update(authority_order=['author-locked','draft'], approved_authorities=['author-locked'])
        self.config['sources'][1]['authority']='author-locked'
        index=core.build_index(self.root,self.config)
        self.assertTrue(index['unavailable'])
        self.config['sources'][1]['authority_evidence']={'path':'approval.md','source_class':'governance'}
        index=core.build_index(self.root,self.config)
        self.assertEqual(len(index['sources']),2)
        self.assertEqual(index['sources'][1]['approval_status'],'approval-evidence-linked')

    def test_omitted_relevant_source_change_invalidates_packet(self):
        self.config['sources'][0]['critical']=True
        packet=context.prepare(self.root,self.config,{**self.request,'budget':1})
        self.assertEqual(len(packet['sources']),1)
        (self.root/'b.md').write_text('changed synthetic source\n')
        with self.assertRaisesRegex(ValueError,'changed|mismatch'):
            core.validate_packet(self.root,packet)

    def test_outputs_are_never_overwritten(self):
        core.write_json(self.root,'.writing-support/proposal.json',{'first':True})
        with self.assertRaises(FileExistsError):
            core.write_json(self.root,'.writing-support/proposal.json',{'first':False})
        self.assertTrue(core.read_json(self.root/'.writing-support/proposal.json')['first'])

    def test_invalid_configuration_rejected_before_source_reads(self):
        for updates in ({'schema_version':True},{'sources':[None]}, {'authority_order':['draft','draft']}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                core.build_index(self.root,{**self.config,**updates})

    def test_context_cannot_relabel_source_authority(self):
        ref=core.snapshot(self.root,self.config['sources'][0])
        ref['authority']='approved-canon'
        request={**self.request,'scene_context':{'location':{'text':'invented','evidence':[ref]}}}
        with self.assertRaises(ValueError):
            context.prepare(self.root,self.config,request)

    def test_full_packet_budget_accounts_for_metadata_and_never_silently_overflows(self):
        self.config['sources'][0]['critical']=True
        packet=context.prepare(self.root,self.config,{**self.request,'budget':50})
        self.assertIn('packet_estimated_tokens',packet['budget'])
        self.assertGreater(packet['budget']['packet_estimated_tokens'],50)
        self.assertTrue(any('budget' in gap.lower() for gap in packet['critical_gaps']))

    def test_inapplicable_source_is_not_read_or_a_freshness_dependency(self):
        self.config['sources'][1]['applicability']={'books':['other']}
        packet=context.prepare(self.root,self.config,self.request)
        (self.root/'b.md').write_bytes(b'\xff')
        core.validate_packet(self.root,packet)

    def test_reader_packet_drops_all_author_side_metadata(self):
        self.config['sources']=[{**self.config['sources'][0], 'source_class':'manuscript',
            'account':'SECRET identity', 'review_scope':'SECRET ending',
            'applicability':{'reader_visible':{'book':'one','position':1}}}]
        packet=context.prepare(self.root,self.config,{**self.request, 'task':'reader',
            'objective':'SECRET twist', 'chapter':'SECRET finale',
            'reading_order':['one'], 'reader_point':{'one':1}})
        import json
        self.assertNotIn('SECRET',json.dumps(packet))

    def test_installed_demo_uses_managed_synthetic_fixtures(self):
        import shutil
        from scripts.writing_support.demo import make_demo
        fixtures=Path(__file__).parent/'fixtures/writing_support'
        managed=self.root/'.ndf/tests/fixtures/writing_support'
        shutil.copytree(fixtures,managed)
        result=make_demo(self.root)
        packet=core.read_json(self.root/result['continuity.packet'])
        self.assertTrue(all(ref['path'].startswith('.ndf/tests/') for ref in packet['sources']))
        self.assertFalse((self.root/'tests').exists())
        core.validate_packet(self.root,packet)

    def test_request_file_change_makes_prepared_cli_task_stale(self):
        import json, subprocess, sys
        script=Path(__file__).resolve().parents[1]/'scripts/writing_toolkit.py'
        (self.root/'config.json').write_text(json.dumps(self.config))
        (self.root/'request.json').write_text(json.dumps(self.request))
        args=[sys.executable,str(script),'--root',str(self.root),'--config','config.json']
        first=subprocess.run(args+['prepare','--request','request.json'],capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stderr)
        (self.root/'request.json').write_text(json.dumps({**self.request,'objective':'changed task'}))
        checked=subprocess.run(args+['check','--packet','.writing-support/context/packet.json'],capture_output=True,text=True)
        self.assertNotEqual(checked.returncode,0)

    def test_reports_ignored_in_existing_repo_without_changing_author_ignore(self):
        import subprocess
        subprocess.run(['git','init',str(self.root)],capture_output=True,check=True)
        ignore=self.root/'.gitignore'
        ignore.write_text('# existing author rules\n')
        core.write_json(self.root,'.writing-support/private-report.json',{'synthetic':'secret'})
        self.assertEqual(ignore.read_text(),'# existing author rules\n')
        checked=subprocess.run(['git','-C',str(self.root),'check-ignore','.writing-support/private-report.json'],capture_output=True)
        self.assertEqual(checked.returncode,0)

    def test_chapter_character_and_time_applicability_narrow_context(self):
        self.config['sources'][1]['applicability']={'chapters':['later'],'characters':['other'],'times':['era-two']}
        packet=context.prepare(self.root,self.config,{**self.request,'chapter':'opening','characters':['protagonist'],'time':'era-one'})
        self.assertEqual([s['path'] for s in packet['sources']],['a.md'])

    def test_boolean_schema_versions_are_rejected(self):
        packet=context.prepare(self.root,self.config,self.request)
        packet['schema_version']=True
        packet['packet_id']=core.packet_identity(packet)
        with self.assertRaises(ValueError):
            core.validate_packet(self.root,packet)
