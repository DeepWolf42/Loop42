"""Bounded github.com REST transport using an existing Git credential only.

No credential acquisition, prompting, redirects, pagination or automatic retries.
Tokens stay in process memory and are never part of reports or exceptions.
"""
import os
from pathlib import Path
import re
import subprocess
import uuid
import urllib.error
import urllib.request

from tools.harness.handoff import encoded,_save,git
from tools.harness.ollama_worker import strict_json


class CapabilityError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class GitHubAPI:
    def __init__(self,profile):
        repository=profile.get('repository','')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
            raise ValueError('invalid repository')
        if profile.get('github',{}).get('auth')!='git-credential':
            raise CapabilityError('existing_git_auth_not_selected')
        self.repository=repository
        self.allow_comments=profile.get('github',{}).get('allow_comments') is True
        self.cwd=Path(profile.get('repo','.'))
        self.secret=None
        self.opener=urllib.request.build_opener(_NoRedirect())

    def _credential(self):
        if self.secret is not None:return self.secret
        try:
            p=subprocess.run(['git','credential','fill'],cwd=self.cwd,
                input='protocol=https\nhost=github.com\npath='+self.repository+'.git\n\n',
                text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,
                env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never','GCM_GUI_PROMPT':'0'},shell=False)
            value=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
            secret=value.get('password')
            if p.returncode or not secret or '\n' in secret or '\r' in secret:
                raise CapabilityError('existing_git_auth_unavailable')
            self.secret=secret
            return secret
        except (OSError,subprocess.SubprocessError):
            raise CapabilityError('existing_git_auth_unavailable') from None

    def _request(self,method,path,data=None):
        base='/repos/'+self.repository
        # Only exact endpoints this adapter requires; no caller-controlled URL.
        allowed=(path=='/user' or path==base or
            re.fullmatch(re.escape(base)+r'/issues/[1-9][0-9]*(?:/comments\?per_page=100)?',path) or
            re.fullmatch(re.escape(base)+r'/issues/comments/[1-9][0-9]*',path) or
            (method=='POST' and re.fullmatch(re.escape(base)+r'/issues/[1-9][0-9]*/comments',path)) or
            (method=='GET' and re.fullmatch(re.escape(base)+r'/git/ref/heads/[A-Za-z0-9._%/-]+',path)))
        if not allowed or (method=='POST' and not re.fullmatch(re.escape(base)+r'/issues/[1-9][0-9]*/comments',path)):
            raise ValueError('endpoint outside authorized transport scope')
        headers={'Authorization':'Bearer '+self._credential(),'Accept':'application/vnd.github+json',
                 'User-Agent':'Loop42-handoff','X-GitHub-Api-Version':'2022-11-28'}
        raw=None if data is None else encoded(data)
        if raw is not None and len(raw)>16384:raise ValueError('publication exceeds bound')
        request=urllib.request.Request('https://api.github.com'+path,data=raw,headers=headers,method=method)
        try:
            with self.opener.open(request,timeout=15) as response:
                if response.headers.get('Link'):
                    raise CapabilityError('paginated_observation_incomplete')
                raw=response.read(1024*1024+1)
                if len(raw)>1024*1024:raise CapabilityError('response_exceeds_bound')
            return strict_json(raw)
        except urllib.error.HTTPError as error:
            raise CapabilityError('github_http_'+str(error.code)) from None
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,RecursionError):
            raise CapabilityError('github_response_unavailable_or_invalid') from None

    def get(self,path):return self._request('GET',path)
    def post(self,path,data):
        if not self.allow_comments:raise PermissionError('comment writes not authorized')
        return self._request('POST',path,data)

    def reserve(self,request,profile,folder):
        """Create one non-fast-forwardable Git claim using ordinary push CAS.

        Different hosts create sibling claim commits; only one can create the
        fixed ref. No force update, deletion, retry or product-branch write.
        """
        if profile.get('github',{}).get('allow_execution_refs') is not True:
            raise PermissionError('execution ref creation not authorized')
        root=Path(profile['repo']).resolve()
        expected='https://github.com/'+self.repository
        if git(root,'remote','get-url','--push','origin') not in (expected,expected+'.git'):
            raise ValueError('HTTPS push repository mismatch')
        path=folder/'execution-lease.json'
        ref='refs/heads/loop42-claims/'+request['task_id']
        tree=git(root,'rev-parse',request['source_revision']+'^{tree}')
        # Random nonce is public claim identity, not a secret or authorization.
        message='Loop42 execution claim '+request['task_id']+' '+uuid.uuid4().hex
        commit=git(root,'-c','user.name='+profile['author_name'],'-c','user.email='+profile['author_email'],
                   'commit-tree',tree,'-p',request['source_revision'],'-m',message)
        _save(path,{'ref':ref,'commit':commit,'source_revision':request['source_revision']})
        remote='/repos/'+self.repository+'/git/ref/heads/loop42-claims%2F'+request['task_id']
        try:
            previous=self.get(remote)
        except CapabilityError as error:
            if str(error)!='github_http_404':raise
            previous=None
        if previous is not None:raise ValueError('execution already claimed; original recovery required')
        try:
            # Normal push rejects sibling updates and uses the advertised old
            # ref as compare-and-swap. Never --force or --force-with-lease.
            subprocess.run(['git','-C',str(root),'push','--porcelain','origin',commit+':'+ref],
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=45,check=False,shell=False,
                env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never','GCM_GUI_PROMPT':'0'})
        except (subprocess.TimeoutExpired,OSError):
            pass  # Read the provider postcondition; do not repeat the push.
        observed=self.get(remote)
        if observed['object']['sha']!=commit:
            raise ValueError('remote execution claim not owned')
