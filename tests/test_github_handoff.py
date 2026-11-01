"""Transport doubles + real Git runner: not live GitHub/AI evidence."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

import test_handoff as fixtures
from tools.harness.github_handoff import run_comment, remote_status


class FakeGitHub:
    def __init__(self,request):
        self.task={'id':123,'issue_url':'https://api.github.com/repos/example/synthetic/issues/7',
                   'user':{'login':'operator','id':9},'updated_at':'2026-11-01T10:00:00Z',
                   'body':'```loop42-handoff\n'+json.dumps(request)+'\n```'}
        self.comments=[];self.posts=0;self.lose_response=False;self.change_on_read=None;self.reads=0
        self.head=request['source_revision']
        self.leases={}
    def reserve(self,request,profile,folder):
        if request['task_id'] in self.leases:raise ValueError('already claimed')
        self.leases[request['task_id']]=str(folder)
    def get(self,path):
        if path=='/user': return {'id':9,'login':'operator'}
        if path=='/repos/example/synthetic': return {'id':42,'full_name':'example/synthetic','private':False}
        if path=='/repos/example/synthetic/issues/7': return {'number':7,'state':'open'}
        if path=='/repos/example/synthetic/git/ref/heads/main':return {'object':{'sha':self.head}}
        if path=='/repos/example/synthetic/issues/comments/123':
            self.reads+=1
            if self.change_on_read==self.reads:self.task['body']+='\nEDITED'
            return copy.deepcopy(self.task)
        if path=='/repos/example/synthetic/issues/7/comments?per_page=100':return copy.deepcopy(self.comments)
        if path.startswith('/repos/example/synthetic/issues/comments/'):
            return copy.deepcopy(next(c for c in self.comments if str(c['id'])==path.rsplit('/',1)[1]))
        raise AssertionError(path)
    def post(self,path,body):
        assert path=='/repos/example/synthetic/issues/7/comments'
        self.posts+=1
        result={'id':123+self.posts,'body':body['body'],'user':{'id':9,'login':'operator'},
                'updated_at':'2026-11-01T10:01:00Z',
                'issue_url':'https://api.github.com/repos/example/synthetic/issues/7',
                'html_url':'https://github.com/example/synthetic/issues/7#issuecomment-124'}
        self.comments.append(result)
        if self.lose_response:raise TimeoutError('synthetic lost response after commit')
        return copy.deepcopy(result)


class GitHubHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.HandoffTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        for name in ('root','repo','head','profile','request','provider'):
            setattr(self,name,getattr(self.fixture,name))
        self.profile['github']={'issue_number':7,'source_branch':'main','operator_login':'operator','allow_comments':True,'allow_execution_refs':True,'auth':'git-credential'}
        self.api=FakeGitHub(self.request)
    @property
    def calls(self):return self.fixture.calls
    def run_remote(self):
        return run_comment(123,self.profile,api=self.api,provider=self.provider)
    def test_remote_roundtrip_and_second_entry(self):
        result=self.run_remote()
        self.assertEqual(result['status'],'DONE_VERIFIED')
        self.assertEqual(self.api.posts,1)
        self.assertEqual(remote_status(123,self.profile,api=self.api)['status'],'DONE_VERIFIED')
        self.assertEqual(self.run_remote()['status'],'DONE_VERIFIED')
        self.assertEqual(self.api.posts,1);self.assertEqual(self.calls,1)
        body=self.api.comments[0]['body']
        self.assertNotIn(str(self.root),body);self.assertNotIn('argv',body);self.assertNotIn('rationale',body)
    def test_other_author_never_executes(self):
        self.api.task['user']={'id':999,'login':'stranger'}
        with self.assertRaises(ValueError):self.run_remote()
        self.assertEqual(self.calls,0);self.assertEqual(self.api.posts,0)
    def test_cross_issue_never_executes(self):
        self.api.task['issue_url']='https://api.github.com/repos/example/synthetic/issues/8'
        with self.assertRaises(ValueError):self.run_remote()
        self.assertEqual(self.calls,0)
    def test_remote_profile_cannot_grant_permission(self):
        self.request['profile']={'allow_commit':True}
        self.api=FakeGitHub(self.request)
        with self.assertRaises(ValueError):self.run_remote()
        self.assertEqual(self.calls,0)
    def test_edit_before_execution_stops(self):
        self.api.change_on_read=2
        with self.assertRaises(ValueError):self.run_remote()
        self.assertEqual(self.calls,0)
    def test_edit_during_worker_never_publishes(self):
        original=self.provider
        def editing(request):
            self.api.task['body']+='\nchanged during worker'
            return original(request)
        result=run_comment(123,self.profile,api=self.api,provider=editing)
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,0)
    def test_missing_write_authority_stops_before_worker(self):
        self.profile['github']['allow_comments']=False
        with self.assertRaises(PermissionError):self.run_remote()
        self.assertEqual(self.calls,0)
    def test_lost_response_with_exact_remote_result_does_not_repost(self):
        self.api.lose_response=True
        result=self.run_remote()
        self.assertEqual(result['status'],'DONE_VERIFIED')
        self.assertEqual(self.run_remote()['status'],'DONE_VERIFIED')
        self.assertEqual(self.api.posts,1);self.assertEqual(self.calls,1)
    def test_unknown_post_outcome_never_replays(self):
        def lost(path,body):
            self.api.posts+=1;raise TimeoutError('uncertain')
        self.api.post=lost
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,1);self.assertEqual(self.calls,1)
    def test_conflicting_result_marker_stops(self):
        self.run_remote();self.api.comments[0]['body']+='\nTAMPERED'
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,1);self.assertEqual(self.calls,1)
    def test_missing_receipt_never_posts_success(self):
        self.run_remote()
        result=next((self.root/'state').glob('*/result.json'));result.unlink()
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,1);self.assertEqual(self.calls,1)

    def test_live_branch_must_match_declared_source(self):
        self.api.head='0'*40
        with self.assertRaises(ValueError):self.run_remote()
        self.assertEqual(self.calls,0);self.assertEqual(self.api.posts,0)

    def test_input_changed_during_claim_never_consumes_provider(self):
        reserve=self.api.reserve
        def changed(request,profile,folder):
            reserve(request,profile,folder);self.api.head='0'*40
        self.api.reserve=changed
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.calls,0);self.assertEqual(self.api.posts,0)

    def test_source_moves_during_worker_without_apply_or_publication(self):
        original=self.provider
        def moving(request):
            self.api.head='0'*40;return original(request)
        result=run_comment(123,self.profile,api=self.api,provider=moving)
        self.assertEqual(result['status'],'UNKNOWN');self.assertEqual(self.api.posts,0)
        workspace=next((self.root/'state').glob('*/.loop42-worktree-*'))
        self.assertEqual((workspace/'answer.txt').read_bytes(),b'wrong\n')

    def test_other_state_directory_cannot_rerun_completed_remote_task(self):
        self.run_remote()
        self.profile['state_dir']=str(self.root/'other-state')
        result=self.run_remote()
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(self.calls,1);self.assertEqual(self.api.posts,1)

    def test_existing_remote_lease_blocks_worker_even_without_result(self):
        self.api.leases['gh-42-123']='some-other-host'
        self.assertEqual(self.run_remote()['status'],'UNKNOWN')
        self.assertEqual(self.calls,0);self.assertEqual(self.api.posts,0)

    def test_remote_done_summary_requires_complete_passing_verification(self):
        self.run_remote()
        original=self.api.comments[0]['body']
        for change in ('missing','red','wrong-task','extra-private'):
            body=original.split('\n```json\n',1)[1].removesuffix('\n```')
            value=json.loads(body)
            if change=='missing':value['verification']=[]
            elif change=='red':value['verification'][0]['exit_code']=1
            elif change=='wrong-task':value['task_id']='foreign'
            else:value['private_log']='must not be reflected'
            self.api.comments[0]['body']=original.split('\n```json\n',1)[0]+'\n```json\n'+json.dumps(value,sort_keys=True,separators=(',',':'))+'\n```'
            self.assertEqual(remote_status(123,self.profile,api=self.api)['status'],'UNKNOWN',change)


if __name__=='__main__':unittest.main()
