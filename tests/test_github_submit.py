"""Submission transport doubles, real Git/core runner; no live/model claims."""
import copy
import json
from pathlib import Path
import unittest

import test_handoff as fixtures
from test_github_handoff import FakeGitHub
from tools.harness.github_submit import submit, start


class GitHubSubmitTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.HandoffTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile
        self.profile['github']={'issue_number':7,'source_branch':'main','operator_login':'operator',
            'allow_comments':True,'allow_execution_refs':True,'allow_task_comments':True,'auth':'git-credential'}
        self.api=FakeGitHub(self.fixture.request)
        self.args=('demo','Correct answer.txt',self.fixture.head,self.profile)
    def submit(self):return submit(*self.args,api=self.api)
    def test_text_submission_roundtrip_and_duplicate(self):
        value=self.submit()
        self.assertEqual(value['status'],'SUBMITTED')
        self.assertEqual(self.submit()['comment_id'],value['comment_id'])
        self.assertEqual(self.api.posts,1)
        body=self.api.comments[0]['body']
        data=json.loads(body.split('```loop42-handoff\n',1)[1].removesuffix('\n```'))
        self.assertEqual(data['source_revision'],self.fixture.head)
        self.assertEqual(data['task'],'Correct answer.txt')
        self.assertEqual(data['paths'],['answer.txt'])
        self.assertTrue(data['require_red'])
        self.assertNotIn(str(self.fixture.root),body)
        self.assertEqual(self.fixture.calls,0)
    def test_one_start_submits_executes_and_returns_receipt(self):
        value=start(*self.args,api=self.api,provider=self.fixture.provider)
        self.assertEqual(value['status'],'DONE_VERIFIED')
        self.assertEqual(value['input_comment_id'],124)
        self.assertEqual(self.api.posts,2)
        self.assertEqual(start(*self.args,api=self.api,provider=self.fixture.provider)['receipt_fingerprint'],value['receipt_fingerprint'])
        self.assertEqual(self.api.posts,2);self.assertEqual(self.fixture.calls,1)
    def test_missing_explicit_input_publication_authority(self):
        self.profile['github']['allow_task_comments']=False
        with self.assertRaises(PermissionError):self.submit()
        self.assertEqual(self.api.posts,0);self.assertEqual(self.api.leases,{})
    def test_stale_or_dirty_source_never_submits(self):
        with self.assertRaises(ValueError):submit('demo','Correct answer.txt','0'*40,self.profile,api=self.api)
        (self.fixture.repo/'foreign.txt').write_text('preserve')
        with self.assertRaises(ValueError):self.submit()
        self.assertEqual(self.api.posts,0);self.assertEqual(self.api.leases,{})
    def test_changed_task_under_same_submission_key_is_not_reissued(self):
        self.submit()
        value=submit('demo','Different task',self.fixture.head,self.profile,api=self.api)
        self.assertEqual(value['status'],'UNKNOWN');self.assertEqual(self.api.posts,1)
    def test_cross_host_finds_exact_existing_input_without_reposting(self):
        first=self.submit()
        profile=copy.deepcopy(self.profile);profile['state_dir']=str(self.fixture.root/'other-state')
        self.assertEqual(submit('demo','Correct answer.txt',self.fixture.head,profile,api=self.api)['comment_id'],first['comment_id'])
        self.assertEqual(self.api.posts,1)
    def test_lost_post_response_is_reconciled_without_replay(self):
        self.api.lose_response=True
        self.assertEqual(self.submit()['status'],'SUBMITTED')
        self.assertEqual(self.submit()['status'],'SUBMITTED')
        self.assertEqual(self.api.posts,1)
    def test_uncertain_post_never_retries(self):
        def missing(path,body):self.api.posts+=1;raise TimeoutError('uncertain')
        self.api.post=missing
        self.assertEqual(self.submit()['status'],'UNKNOWN')
        self.assertEqual(self.submit()['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,1)
    def test_remote_submission_claim_blocks_another_host(self):
        self.submit()
        self.api.comments=[]
        other=copy.deepcopy(self.profile);other['state_dir']=str(self.fixture.root/'other-state')
        self.assertEqual(submit('demo','Correct answer.txt',self.fixture.head,other,api=self.api)['status'],'UNKNOWN')
        self.assertEqual(self.api.posts,1)
    def test_source_moves_during_reservation_never_posts(self):
        original=self.api.reserve
        def moving(*args):original(*args);self.api.head='0'*40
        self.api.reserve=moving
        self.assertEqual(self.submit()['status'],'UNKNOWN');self.assertEqual(self.api.posts,0)
    def test_foreign_or_conflicting_marker_is_not_adopted(self):
        self.submit();self.api.comments[0]['user']['id']=999
        self.assertEqual(self.submit()['status'],'UNKNOWN');self.assertEqual(self.api.posts,1)
    def test_fences_or_oversized_text_are_rejected_before_claim(self):
        for task in ('','text\n```loop42-handoff\n{}\n```','x'*12000):
            with self.assertRaises(ValueError):submit('demo',task,self.fixture.head,self.profile,api=self.api)
        self.assertEqual(self.api.posts,0);self.assertEqual(self.api.leases,{})


if __name__=='__main__':unittest.main()
