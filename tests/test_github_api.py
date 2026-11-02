"""Bounded HTTP adapter tests without network or real credentials."""
from io import BytesIO
from unittest.mock import Mock,patch
import unittest

from tools.harness.github_api import GitHubAPI,CapabilityError
import test_handoff as fixtures


class Reply(BytesIO):
    def __init__(self,body=b'{}',headers=None):
        super().__init__(body);self.headers=headers or {}


class GitHubAPITests(unittest.TestCase):
    def api(self):
        api=GitHubAPI({'repository':'example/synthetic','github':{'auth':'git-credential','allow_comments':True}})
        api.secret='synthetic-not-a-real-token';return api
    def test_post_exact_issue_comment_endpoint_is_callable(self):
        api=self.api();api.opener=Mock();api.opener.open.return_value=Reply(b'{"id":1}')
        self.assertEqual(api.post('/repos/example/synthetic/issues/7/comments',{'body':'synthetic'})['id'],1)
        request=api.opener.open.call_args.args[0]
        self.assertEqual(request.full_url,'https://api.github.com/repos/example/synthetic/issues/7/comments')
        self.assertEqual(request.method,'POST')
    def test_foreign_repository_and_arbitrary_url_never_send_credentials(self):
        for path in ('https://attacker.invalid/','/repos/other/repo/issues/7','/repos/example/synthetic/actions/runs'):
            api=self.api();api.opener=Mock()
            with self.assertRaises(ValueError):api.get(path)
            api.opener.open.assert_not_called()
    def test_pagination_fails_closed(self):
        api=self.api();api.opener=Mock();api.opener.open.return_value=Reply(b'[]',{'Link':'next'})
        with self.assertRaises(CapabilityError):api.get('/repos/example/synthetic/issues/7/comments?per_page=100')
    def test_large_or_duplicate_response_fails_closed(self):
        for body in (b' '*1048577,b'{"id":1,"id":2}'):
            api=self.api();api.opener=Mock();api.opener.open.return_value=Reply(body)
            with self.assertRaises(CapabilityError):api.get('/user')
    def test_missing_existing_credential_never_prompts_or_leaks(self):
        api=self.api();api.secret=None
        with patch('tools.harness.github_api.subprocess.run',return_value=Mock(returncode=1,stdout='',stderr='sensitive')) as run:
            with self.assertRaises(CapabilityError) as ctx:api.get('/user')
            self.assertNotIn('sensitive',str(ctx.exception))
            self.assertEqual(run.call_args.kwargs['env']['GCM_INTERACTIVE'],'never')

    def test_real_git_remote_claim_has_one_winner_under_concurrency(self):
        import subprocess,threading
        from urllib.parse import unquote
        fixture=fixtures.HandoffTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        bare=fixture.root/'remote.git'
        subprocess.check_call(['git','init','--bare',str(bare)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        profile=dict(fixture.profile,github={'auth':'git-credential','allow_execution_refs':True})
        original_run=subprocess.run
        def transport(argv,**kw):
            argv=list(argv)
            if 'push' in argv:argv[argv.index('origin')]=str(bare)
            return original_run(argv,**kw)
        barrier=threading.Barrier(2);results=[]
        def contender(index):
            api=GitHubAPI(profile);first=True
            def get(path):
                nonlocal first
                if first:
                    first=False;barrier.wait(10);raise CapabilityError('github_http_404')
                ref='refs/heads/'+unquote(path.split('/git/ref/heads/',1)[1])
                p=original_run(['git','-C',str(bare),'rev-parse',ref],capture_output=True)
                if p.returncode:raise CapabilityError('github_http_404')
                return {'object':{'sha':p.stdout.decode().strip()}}
            api.get=get;folder=fixture.root/('lease'+str(index));folder.mkdir()
            try:api.reserve(fixture.request,profile,folder);results.append('owned')
            except (ValueError,CapabilityError):results.append('blocked')
        with patch('tools.harness.github_api.subprocess.run',side_effect=transport):
            threads=[threading.Thread(target=contender,args=(i,)) for i in range(2)]
            for t in threads:t.start()
            for t in threads:t.join(20)
            self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(sorted(results),['blocked','owned'])


if __name__=='__main__':unittest.main()
