"""Provider regressions: a file is not evidence of a completed CLI turn."""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.harness.handoff_cli import CodexProvider, main
from tools.harness.verification_registry import VerificationResult
from tools.harness.worker_provider import WorkerRequest, WorkerStatus


class CodexCompletionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.proposal={'schema':'loop42.changeset.v1','changes':[{'operation':'modify','path':'answer.py',
            'base_sha256':'0'*64,'search':'wrong','replace':'right','expected_matches':1}],
            'requested_verification':['test:answer']}
        self.events=[{'type':'thread.started','thread_id':'synthetic-thread'},
            {'type':'turn.started'},
            {'type':'item.completed','item':{'id':'final','type':'agent_message','text':json.dumps(self.proposal)}},
            {'type':'turn.completed','usage':{'input_tokens':12,'output_tokens':3}}]
        self.request=WorkerRequest('example','attempt-1','a'*40,'b'*64,'Fix answer',
            '{"files":{"answer.py":"wrong"},"file_sha256":{"answer.py":"'+ '0'*64 +'"},"verification_ids":["test:answer"]}',
            ('propose_changes','request_verification'),'coding')

    def call(self,events=None,raw=None,file_data=None,exit_code=0):
        data=json.dumps(self.proposal).encode() if file_data is None else file_data
        stream='\n'.join(json.dumps(e) for e in (self.events if events is None else events)) if raw is None else raw
        def process(workspace,identifiers,registry,**kwargs):
            argv=registry.specs[0].argv
            Path(argv[argv.index('--output-last-message')+1]).write_bytes(data)
            return (VerificationResult('provider:codex',argv,exit_code,False,stream,False),)
        with patch('tools.harness.handoff_cli.shutil.which',return_value='codex'),patch('tools.harness.handoff_cli.run_verifications',side_effect=process):
            return CodexProvider({'allow_codex':True})(self.request)

    def rejected(self,**kwargs):
        result=self.call(**kwargs)
        self.assertEqual(result.status,WorkerStatus.FAILED)
        self.assertIsNone(result.changeset)
        return result

    def test_complete_bound_turn_preserves_usage(self):
        result=self.call()
        self.assertEqual(result.status,WorkerStatus.PROPOSAL)
        self.assertEqual((result.usage.input_tokens,result.usage.output_tokens),(12,3))

    def test_missing_completion_failed_turn_and_explicit_error_reject_existing_file(self):
        cases=[self.events[:-1],self.events[:-1]+[{'type':'turn.failed','error':{'message':'synthetic failure'}}],
               self.events[:-1]+[{'type':'error','message':'synthetic failure'},self.events[-1]]]
        for events in cases:
            with self.subTest(events=events):self.rejected(events=events)

    def test_ambiguous_order_duplicate_completion_and_post_completion_events_rejected(self):
        cases=[self.events+[self.events[-1]],self.events[:2]+[self.events[-1],self.events[2]],
               self.events+[{'type':'item.completed','item':{'id':'late','type':'reasoning','text':'late'}}],
               self.events[:2]+[self.events[2],self.events[2],self.events[-1]]]
        for events in cases:
            with self.subTest(events=events):self.rejected(events=events)

    def test_unknown_or_non_object_events_and_duplicate_json_keys_rejected(self):
        for event in ({'type':'future.unknown'},[],{'type':'item.completed','item':None}):
            with self.subTest(event=event):self.rejected(events=self.events[:2]+[event]+self.events[2:])
        raw='\n'.join(json.dumps(e) for e in self.events[:-1])+'\n{"type":"turn.failed","type":"turn.completed","usage":{}}'
        self.rejected(raw=raw)

    def test_non_json_stdout_is_not_ignored_even_with_a_valid_completion(self):
        self.rejected(raw='unstructured stdout\n'+'\n'.join(json.dumps(e) for e in self.events))

    def test_message_and_file_must_bind_to_the_same_proposal(self):
        alternate=copy.deepcopy(self.proposal);alternate['changes'][0]['replace']='different'
        self.rejected(file_data=json.dumps(alternate).encode())

    def test_invalid_or_oversized_output_becomes_failure_not_exception(self):
        for data in (b'{invalid',b'[]',b'x'*(2*1024*1024+1)):
            with self.subTest(length=len(data)):self.rejected(file_data=data)

    def test_invalid_usage_does_not_escape_as_exception_or_authority(self):
        for value in (True,-1,'12'):
            events=copy.deepcopy(self.events);events[-1]['usage']['input_tokens']=value
            with self.subTest(value=value):self.rejected(events=events)

    def test_missing_usage_is_unknown_not_invented_zero(self):
        events=copy.deepcopy(self.events);events[-1]['usage']={}
        result=self.call(events=events)
        self.assertEqual(result.status,WorkerStatus.PROPOSAL)
        self.assertIsNone(result.usage.input_tokens)

    def test_unfinished_item_or_tools_never_authorize_a_proposal(self):
        events=self.events[:2]+[{'type':'item.started','item':{'id':'pending','type':'reasoning'}}]+self.events[2:]
        self.rejected(events=events)
        events=self.events[:2]+[{'type':'item.completed','item':{'id':'tool','type':'command_execution'}}]+self.events[2:]
        self.rejected(events=events)

    def test_raw_provider_diagnostics_are_not_returned_to_callers(self):
        result=self.rejected(raw='SYNTHETIC_PRIVATE_DIAGNOSTIC',exit_code=1)
        self.assertNotIn('SYNTHETIC_PRIVATE_DIAGNOSTIC',result.rationale_summary)

    def test_final_json_binding_is_semantic_but_preserves_json_types(self):
        result=self.call(file_data=json.dumps(self.proposal,indent=2,sort_keys=True).encode())
        self.assertEqual(result.status,WorkerStatus.PROPOSAL)
        events=copy.deepcopy(self.events)
        different=copy.deepcopy(self.proposal);different['changes'][0]['expected_matches']=True
        events[2]['item']['text']=json.dumps(different)
        self.rejected(events=events)

    def test_valid_reasoning_lifecycle_does_not_grant_extra_authority(self):
        events=self.events[:2]+[
            {'type':'item.started','item':{'id':'reason','type':'reasoning'}},
            {'type':'item.updated','item':{'id':'reason','type':'reasoning','text':'Untrusted reasoning text'}},
            {'type':'item.completed','item':{'id':'reason','type':'reasoning','text':'Not evidence'}}]+self.events[2:]
        self.assertEqual(self.call(events=events).status,WorkerStatus.PROPOSAL)

    def test_provider_failure_is_persisted_and_duplicate_does_not_relaunch(self):
        import hashlib
        import test_handoff as fixtures
        from tools.harness.handoff import execute,status,encoded
        fixture=fixtures.HandoffTests('test_real_git_red_green_commit_and_separate_status')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        calls=[]
        def process(workspace,identifiers,registry,**kwargs):
            calls.append(1);argv=registry.specs[0].argv
            proposal=copy.deepcopy(self.proposal)
            proposal['changes'][0].update(path='answer.txt',base_sha256=hashlib.sha256(b'wrong\n').hexdigest())
            Path(argv[argv.index('--output-last-message')+1]).write_text(json.dumps(proposal))
            return (VerificationResult('provider:codex',argv,0,False,'{"type":"turn.failed"}',False),)
        with patch('tools.harness.handoff_cli.shutil.which',return_value='codex'),patch('tools.harness.handoff_cli.run_verifications',side_effect=process):
            provider=CodexProvider({'allow_codex':True})
            result=execute(fixture.request,fixture.profile,provider=provider)
            self.assertEqual(result['status'],'FAILED_WORKER')
            saved=json.loads(encoded(result))
            self.assertEqual(status(fixture.request,fixture.profile),saved)
            self.assertEqual(execute(fixture.request,fixture.profile,provider=provider),saved)
        self.assertEqual(len(calls),1)
        self.assertNotIn('commit',result)
        self.assertNotIn('green',result)
        self.assertEqual((fixture.repo/'answer.txt').read_bytes(),b'wrong\n')
        self.assertEqual((Path(result['workspace'])/'answer.txt').read_bytes(),b'wrong\n')


class HandoffHumanDiagnosticsTests(unittest.TestCase):
    def invoke(self,request,profile,extra=(),result=None,error=None):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for name,value in (('input.json',request),('profile.json',profile)):
                (folder/name).write_text(json.dumps(value),encoding='utf-8')
            output=io.StringIO()
            with patch('tools.harness.handoff_cli.execute',return_value=result,side_effect=error),redirect_stdout(output):
                code=main(['run','--input',str(folder/'input.json'),'--profile',str(folder/'profile.json'),*extra])
            return code,output.getvalue()

    def test_invalid_input_shape_is_json_failure_without_traceback(self):
        for request,profile in (({},[]),([],{})):
            with self.subTest(request=request,profile=profile):
                code,output=self.invoke(request,profile)
                value=json.loads(output)
                self.assertEqual(code,2)
                self.assertEqual(value['status'],'UNKNOWN')
                self.assertEqual(value['diagnostic_code'],'INVALID_INPUT_SHAPE')

    def test_stale_source_has_actionable_code_without_private_error_text(self):
        code,output=self.invoke({}, {},error=ValueError('stale source revision'))
        value=json.loads(output)
        self.assertEqual(code,2)
        self.assertEqual(value['reason'],'ValueError')
        self.assertEqual(value['diagnostic_code'],'STALE_SOURCE_REVISION')

    def test_human_output_is_german_and_does_not_render_worker_text(self):
        code,output=self.invoke({}, {},extra=['--human'],result={'status':'FAILED_WORKER',
            'worker':{'rationale_summary':'\u001b[31mSYNTHETIC_PRIVATE_DIAGNOSTIC'}})
        self.assertEqual(code,3)
        self.assertIn('Worker',output)
        self.assertNotIn('SYNTHETIC_PRIVATE_DIAGNOSTIC',output)
        self.assertNotIn('\u001b',output)

    def test_default_json_result_and_exit_code_remain_compatible(self):
        expected={'status':'DONE_VERIFIED','commit':'a'*40}
        code,output=self.invoke({}, {},result=expected)
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output),expected)

    def test_new_human_mode_preserves_failed_attempt_exit_code(self):
        code,output=self.invoke({}, {},extra=['--human'],result={'status':'UNKNOWN','reason':'interrupted_attempt_no_replay'})
        self.assertEqual(code,3)
        self.assertIn('Unbekannt',output)

    def test_real_cli_process_invalid_profile_has_no_traceback(self):
        import subprocess,sys,os
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/'input.json').write_text('{}')
            (folder/'profile.json').write_text('[]')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
            process=subprocess.run([sys.executable,'-B','-m','tools.harness.handoff_cli','status',
                '--input',str(folder/'input.json'),'--profile',str(folder/'profile.json')],
                cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,timeout=10)
        self.assertEqual(process.returncode,2)
        self.assertEqual(json.loads(process.stdout)['diagnostic_code'],'INVALID_INPUT_SHAPE')
        self.assertNotIn(b'Traceback',process.stderr)

if __name__=='__main__':unittest.main()
