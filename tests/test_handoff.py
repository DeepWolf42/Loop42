"""Real Git/process tests; deterministic providers are test doubles, not AI evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.harness.handoff import execute, status
from tools.harness.change_set import ChangeSet, ModifyChange
from tools.harness.worker_provider import WorkerResult, WorkerStatus


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.git('remote', 'add', 'origin', 'https://github.com/example/synthetic.git')
        (self.repo / 'answer.txt').write_bytes(b'wrong\n')
        self.git('add', 'answer.txt')
        self.git('commit', '-m', 'synthetic failing basis')
        self.head = self.git('rev-parse', 'HEAD')
        self.profile = {
            'repository': 'example/synthetic', 'repo': str(self.repo),
            'state_dir': str(self.root / 'state'), 'allowed_paths': ['answer.txt'],
            'allow_commit': True, 'author_name': 'Synthetic Test',
            'author_email': 'test@example.invalid',
            'verifications': [{'identifier': 'test:answer', 'argv': [sys.executable, '-B', '-c',
                "from pathlib import Path;assert Path('answer.txt').read_bytes()==b'right\\n'"],
                'timeout_seconds': 10}],
        }
        self.request = {'schema': 'loop42.handoff.v1', 'task_id': 'synthetic-1',
            'repository': 'example/synthetic', 'source_revision': self.head,
            'task': 'Correct answer.txt', 'paths': ['answer.txt'],
            'verification_ids': ['test:answer'], 'require_red': True}
        self.calls = 0

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.STDOUT).decode().strip()

    def provider(self, request):
        self.calls += 1
        context = json.loads(request.context)
        text = context['files']['answer.txt']
        return WorkerResult(status=WorkerStatus.PROPOSAL, provider='test-double', model='deterministic',
            task_id=request.task_id, attempt_id=request.attempt_id,
            source_revision=request.source_revision, context_fingerprint=request.context_fingerprint,
            rationale_summary='Synthetic test proposal',
            changeset=ChangeSet((ModifyChange('answer.txt', hashlib.sha256(text.encode()).hexdigest(),
                                             'wrong', 'right'),), ('test:answer',)))

    def test_real_git_red_green_commit_and_separate_status(self):
        result = execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(result['status'], 'DONE_VERIFIED')
        self.assertEqual(result['red'][0]['exit_code'], 1)
        self.assertTrue(result['green'][0]['exit_code'] == 0)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.head)
        self.assertEqual((self.repo/'answer.txt').read_bytes(), b'wrong\n')
        self.assertEqual(status(self.request, self.profile)['status'], 'DONE_VERIFIED')
        self.assertEqual(execute(self.request, self.profile, provider=self.provider)['commit'], result['commit'])
        self.assertEqual(self.calls, 1)

    def test_stale_revision_blocks_before_provider(self):
        self.request['source_revision'] = '0'*40
        with self.assertRaises(ValueError): execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(self.calls, 0)

    def test_dirty_checkout_blocks(self):
        (self.repo/'foreign.txt').write_text('preserve')
        with self.assertRaises(ValueError): execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(self.calls, 0)

    def test_missing_capability_is_not_success_or_retried(self):
        result = execute(self.request, self.profile, provider=None)
        self.assertEqual(result['status'], 'BLOCKED_CAPABILITY')
        self.assertEqual(status(self.request, self.profile)['status'], 'BLOCKED_CAPABILITY')

    def test_failed_green_keeps_candidate_and_never_success(self):
        self.profile['verifications'][0]['argv'] = [sys.executable, '-B', '-c', 'raise SystemExit(1)']
        result = execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(result['status'], 'FAILED_VERIFICATION')
        self.assertNotIn('commit', result)
        self.assertEqual(status(self.request, self.profile)['status'], 'FAILED_VERIFICATION')

    def test_missing_receipt_is_unknown_without_replay(self):
        result = execute(self.request, self.profile, provider=self.provider)
        record = Path(result['record_path'])
        record.unlink()
        self.assertEqual(execute(self.request, self.profile, provider=self.provider)['status'], 'UNKNOWN')
        self.assertEqual(self.calls, 1)

    def test_changed_identity_under_same_task_id_blocks(self):
        execute(self.request, self.profile, provider=self.provider)
        self.request['task'] = 'different'
        with self.assertRaises(ValueError): execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(self.calls, 1)

    def test_tampered_evidence_invalidates_saved_receipt(self):
        result = execute(self.request, self.profile, provider=self.provider)
        record = Path(result['record_path'])
        data = json.loads(record.read_text())
        data['green'][0]['output'] = 'tampered'
        record.write_text(json.dumps(data))
        self.assertEqual(status(self.request, self.profile)['status'], 'UNKNOWN')

    def test_extra_path_not_authorized(self):
        self.request['paths'].append('outside.txt')
        with self.assertRaises(ValueError): execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(self.calls, 0)

    def test_missing_commit_permission_blocks_before_provider(self):
        self.profile['allow_commit'] = False
        with self.assertRaises(PermissionError): execute(self.request, self.profile, provider=self.provider)
        self.assertEqual(self.calls, 0)

    def test_no_red_reproduction_blocks_provider(self):
        self.profile['verifications'][0]['argv'] = [sys.executable, '-B', '-c', 'pass']
        self.assertEqual(execute(self.request,self.profile,provider=self.provider)['status'], 'RED_NOT_REPRODUCED')
        self.assertEqual(self.calls, 0)

    def test_status_missing_task_is_unknown(self):
        self.assertEqual(status(self.request,self.profile)['status'], 'UNKNOWN')

    def test_future_or_wrong_verifier_or_missing_fingerprint_is_unknown(self):
        result=execute(self.request,self.profile,provider=self.provider)
        record=Path(result['record_path'])
        original=record.read_bytes()
        for change in ('future','verifier','fingerprint'):
            data=json.loads(original)
            if change=='future': data['receipt']['verified_at']='2999-01-01T00:00:00+00:00'
            elif change=='verifier': data['receipt']['verifier_id']='foreign-verifier'
            else: del data['receipt_fingerprint']
            record.write_text(json.dumps(data))
            self.assertEqual(status(self.request,self.profile)['status'],'UNKNOWN',change)

    def test_source_movement_or_dirty_source_invalidates_status(self):
        execute(self.request,self.profile,provider=self.provider)
        (self.repo/'foreign.txt').write_text('foreign')
        self.assertEqual(status(self.request,self.profile)['status'],'UNKNOWN')

    def test_source_advances_during_green_and_prevents_commit(self):
        command=("from pathlib import Path;import subprocess;"
                 "assert Path('answer.txt').read_bytes()==b'right\\n';"
                 "subprocess.check_call(['git','-C',"+repr(str(self.repo))+",'commit','--allow-empty','-m','other writer'])")
        self.profile['verifications'][0]['argv']=[sys.executable,'-B','-c',command]
        result=execute(self.request,self.profile,provider=self.provider)
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['reason'],'source_changed_before_commit')
        self.assertNotIn('commit',result)

    def test_concurrent_claim_has_only_one_provider_call(self):
        import threading
        entered=threading.Event(); release=threading.Event(); results=[]
        def waiting(request):
            entered.set();release.wait(10);return self.provider(request)
        worker=threading.Thread(target=lambda:results.append(execute(self.request,self.profile,provider=waiting)))
        worker.start()
        try:
            self.assertTrue(entered.wait(10))
            second=execute(self.request,self.profile,provider=self.provider)
            self.assertEqual(second['status'],'UNKNOWN')
            self.assertEqual(self.calls,0)
        finally:
            release.set();worker.join(20)
        self.assertEqual(self.calls,1)
        self.assertEqual(results[0]['status'],'DONE_VERIFIED')


if __name__ == '__main__':
    unittest.main()
