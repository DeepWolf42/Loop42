"""One consumer-owned handoff journal, existing execution/receipt contracts.

Trusted local profile supplies authority and commands. Requests are data, never
shell commands. No scheduler, network publication, retry or consumer pin update.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from tools.harness.action_policy import ActionEffect, PolicyDecision, PolicyRule
from tools.harness.change_set import ModifyChange, normalize_changeset
from tools.harness.changeset_executor import apply_changeset, issue_changeset_permit
from tools.harness.git_workspace import create_detached_worktree
from tools.harness.verification_registry import VerificationRegistry, VerificationSpec, run_verifications
from tools.harness.verification_receipt import (
    CriterionStatus, CriterionVerification, EvidenceRef, VerificationReceipt,
    parse_receipt, receipt_payload, result_artifact_from_receipt, validate_receipt,
)
from tools.harness.worker_dispatch import DispatchTask, HostObservation, issue_dispatch_permit, validate_dispatch_permit
from tools.harness.worker_provider import WorkerRequest, WorkerStatus


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def verifier_revision():
    names=('handoff.py','git_workspace.py','change_set.py','changeset_executor.py',
           'verification_registry.py','verification_process.py','verification_receipt.py',
           'worker_dispatch.py','action_policy.py','worker_provider.py')
    return digest({'python':sys.version,'sources':{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names}})


def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), *args], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, shell=False)
    if p.returncode:
        raise ValueError('Git operation failed: ' + args[0])
    return p.stdout.decode('utf-8').strip()


def _validate(request, profile):
    fields = {'schema','task_id','repository','source_revision','task','paths','verification_ids','require_red'}
    if not isinstance(request,dict) or set(request) != fields or request['schema'] != 'loop42.handoff.v1':
        raise ValueError('invalid handoff fields/schema')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', request['task_id']):
        raise ValueError('invalid task ID')
    if not re.fullmatch(r'[0-9a-f]{40}', request['source_revision']):
        raise ValueError('exact full source commit required')
    if request['repository'] != profile['repository'] or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',request['repository']):
        raise ValueError('repository identity mismatch')
    if type(request['require_red']) is not bool or not isinstance(request['task'],str) or not request['task'].strip():
        raise ValueError('invalid task or red requirement')
    paths = request['paths']
    if not isinstance(paths,list) or not paths or len(paths)>64 or len(set(paths))!=len(paths):
        raise ValueError('invalid bounded paths')
    for path in paths:
        # Existing ChangeSet validation owns portable path validation.
        ModifyChange(path,'0'*64,'a','b')
        if path not in profile['allowed_paths']:
            raise ValueError('path not authorized by trusted profile')
    registry = VerificationRegistry(tuple(VerificationSpec(v['identifier'],tuple(v['argv']),v['timeout_seconds'])
                                           for v in profile['verifications']))
    ids = request['verification_ids']
    if not isinstance(ids,list) or not ids:
        raise ValueError('verification is mandatory')
    registry.resolve(ids)
    repo = Path(profile['repo']).resolve()
    if Path(git(repo,'rev-parse','--show-toplevel')).resolve()!=repo:
        raise ValueError('exact Git top-level required')
    origin=git(repo,'remote','get-url','origin')
    if (origin not in ('https://github.com/'+request['repository']+'.git',
                       'https://github.com/'+request['repository'])
            and origin.split('@',1)!=['git','github.com:'+request['repository']+'.git']):
        raise ValueError('origin repository mismatch')
    state = Path(profile['state_dir']).resolve()
    if state==repo or repo in state.parents or state.is_symlink() or state.is_junction():
        raise ValueError('consumer recovery directory must be outside repository')
    return repo, state / request['task_id'], registry


def _save(path, value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('xb') as f:
        f.write(encoded(value)); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)


def _subject(workspace, commit, repository):
    return digest({'repository':repository,'commit':commit,'tree':git(workspace,'rev-parse',commit+'^{tree}')})


def status(request, profile):
    repo, folder, registry = _validate(request,profile)
    if not folder.exists():
        return {'status':'UNKNOWN','reason':'no_claim_or_receipt'}
    identity = {'request':request,'profile':profile}
    try:
        claim=json.loads((folder/'claim.json').read_bytes())
        if claim['identity']!=digest(identity):
            raise ValueError('task ID already bound to another request/profile')
    except FileNotFoundError:
        return {'status':'UNKNOWN','reason':'incomplete_claim_no_replay'}
    try:
        report=json.loads((folder/'result.json').read_bytes())
    except FileNotFoundError:
        return {'status':'UNKNOWN','reason':'interrupted_attempt_no_replay'}
    if report.get('status')!='DONE_VERIFIED':
        return report
    try:
        if git(repo,'rev-parse','HEAD')!=request['source_revision'] or git(repo,'status','--porcelain'):
            raise ValueError('source moved')
        workspace=Path(report['workspace'])
        commit=report['commit']
        if git(workspace,'rev-parse','HEAD')!=commit or git(workspace,'status','--porcelain'):
            raise ValueError('candidate changed')
        receipt=parse_receipt(encoded(report['receipt']))
        task=DispatchTask(request['task_id'],'attempt-1',request['source_revision'],digest(identity),tuple(request['verification_ids']))
        if receipt.verifier_revision != report['verifier_revision']:
            raise ValueError('verifier revision mismatch')
        current_revision=verifier_revision()
        if current_revision!=receipt.verifier_revision:
            raise ValueError('harness changed; requalification required')
        validation=validate_receipt(receipt,task,subject_fingerprint=_subject(workspace,commit,request['repository']))
        if (not validation.valid or report['receipt_fingerprint']!=validation.fingerprint
                or receipt.verifier_id!='local-registered-verifier'
                or receipt.verified_at>datetime.now(timezone.utc)):
            raise ValueError('receipt mismatch')
        evidence={v['identifier']:digest(v) for v in report['green']}
        if set(evidence)!=set(request['verification_ids']):
            raise ValueError('incomplete verification')
        for c in receipt.criteria:
            if c.evidence!=(EvidenceRef(c.criterion,evidence[c.criterion]),):
                raise ValueError('evidence changed')
        return report
    except (ValueError,KeyError,OSError,TypeError):
        return {'status':'UNKNOWN','reason':'saved_receipt_not_current_or_complete'}


def execute(request, profile, *, provider=None):
    repo, folder, registry=_validate(request,profile)
    if folder.exists():
        return status(request,profile)  # never rerun an ambiguous attempt
    if profile.get('allow_commit') is not True:
        raise PermissionError('explicit local commit authority required')
    if git(repo,'rev-parse','HEAD')!=request['source_revision']:
        raise ValueError('stale source revision')
    if git(repo,'status','--porcelain'):
        raise ValueError('unclean/untracked source checkout')
    identity={'request':request,'profile':profile}
    task=DispatchTask(request['task_id'],'attempt-1',request['source_revision'],digest(identity),tuple(request['verification_ids']))
    now=datetime.now(timezone.utc)
    observation=HostObservation(now,'local-handoff',True)
    permit=issue_dispatch_permit(task=task,now=now,observation=observation,artifacts=())
    if permit is None or not validate_dispatch_permit(permit,task=task,now=now,observation=observation,artifacts=()):
        raise ValueError('dispatch not permitted')
    folder.parent.mkdir(parents=True,exist_ok=True)
    try:
        folder.mkdir()  # atomic claim across concurrent processes; never removed for retry
    except FileExistsError:
        return status(request,profile)
    _save(folder/'claim.json',{'identity':digest(identity),'created_at':now.isoformat()})
    report={'task_id':task.task_id,'source_revision':task.source_revision,
            'record_path':str(folder/'result.json'),'status':'UNKNOWN',
            'started_at':now.isoformat(),'cost_microunits':None}
    def finish(value):
        report.update(value);report['finished_at']=datetime.now(timezone.utc).isoformat()
        _save(folder/'result.json',report)
        return report
    if provider is None:
        return finish({'status':'BLOCKED_CAPABILITY','reason':'no_callable_authorized_provider'})
    lease=create_detached_worktree(repo,request['source_revision'],parent=folder)
    workspace=lease.root
    report['workspace']=str(workspace)
    report['harness_revision']=git(Path(__file__).resolve().parents[2],'rev-parse','HEAD')
    report['verifier_revision']=verifier_revision()
    red=tuple(asdict(v) for v in run_verifications(workspace,request['verification_ids'],registry,stop_on_failure=False))
    report['red']=red
    if request['require_red'] and not any(v['exit_code'] not in (0,None) and not v['timed_out'] and not v['output_truncated'] for v in red):
        return finish({'status':'RED_NOT_REPRODUCED'})
    if git(workspace,'status','--porcelain'):
        return finish({'status':'UNKNOWN','reason':'verifier_changed_source'})
    files={}
    for p in request['paths']:
        target=workspace/p
        if any(q.is_symlink() or q.is_junction() for q in (target,*target.parents)):
            return finish({'status':'BLOCKED_SCOPE','reason':'linked_source_path'})
        raw=target.read_bytes()
        if len(raw)>2*1024*1024:
            return finish({'status':'BLOCKED_SCOPE','reason':'source_too_large'})
        files[p]=raw.decode('utf-8')
    context=encoded({'repository':request['repository'],'files':files,
        'file_sha256':{p:hashlib.sha256(t.encode()).hexdigest() for p,t in files.items()},
        'verification_ids':request['verification_ids']}).decode()
    worker_request=WorkerRequest(task.task_id,task.attempt_id,task.source_revision,task.context_fingerprint,
        request['task'],context,('propose_changes','request_verification'),'coding')
    result=provider(worker_request)
    if (result.task_id,result.attempt_id,result.source_revision,result.context_fingerprint)!=(task.task_id,task.attempt_id,task.source_revision,task.context_fingerprint):
        return finish({'status':'UNKNOWN','reason':'worker_identity_mismatch'})
    report['worker']={'provider':result.provider,'model':result.model,'usage':asdict(result.usage),
                      'rationale_summary':result.rationale_summary}
    if result.status is not WorkerStatus.PROPOSAL:
        return finish({'status':'BLOCKED_CAPABILITY' if result.status is WorkerStatus.BLOCKED else 'FAILED_WORKER'})
    changeset=result.changeset
    if any(not isinstance(c,ModifyChange) or c.path not in request['paths'] for c in changeset.changes):
        return finish({'status':'BLOCKED_SCOPE'})
    if set(changeset.requested_verification)-set(request['verification_ids']):
        return finish({'status':'BLOCKED_SCOPE'})
    normalized=normalize_changeset(changeset,files)
    # Re-read source, candidate and policy immediately before side effects.
    if git(repo,'rev-parse','HEAD')!=task.source_revision or git(repo,'status','--porcelain') or git(workspace,'status','--porcelain'):
        return finish({'status':'UNKNOWN','reason':'source_changed_before_apply'})
    rules=tuple(PolicyRule('authorized-path-'+str(i),PolicyDecision.ALLOW,action='changeset.modify',
        target_prefix='repo:'+p,effect=ActionEffect.REVERSIBLE_WRITE) for i,p in enumerate(request['paths']))
    change_permit=issue_changeset_permit(workspace,normalized,interactive=False,rules=rules)
    apply_changeset(workspace,normalized,change_permit,interactive=False,rules=rules)
    green=tuple(asdict(v) for v in run_verifications(workspace,request['verification_ids'],registry,stop_on_failure=False))
    report['green']=green
    if any(v['exit_code']!=0 or v['timed_out'] or v['output_truncated'] for v in green):
        return finish({'status':'FAILED_VERIFICATION'})
    # A verifier cannot silently edit the candidate or include foreign files.
    for c in normalized.files:
        if hashlib.sha256((workspace/c.path).read_bytes()).hexdigest()!=c.after_sha256:
            return finish({'status':'UNKNOWN','reason':'verified_candidate_changed'})
    dirty=git(workspace,'diff','--name-only').splitlines()
    if git(repo,'rev-parse','HEAD')!=task.source_revision or git(repo,'status','--porcelain'):
        return finish({'status':'UNKNOWN','reason':'source_changed_before_commit'})
    if set(dirty)!=set(c.path for c in normalized.files) or git(workspace,'ls-files','--others','--exclude-standard'):
        return finish({'status':'UNKNOWN','reason':'unexpected_candidate_delta'})
    git(workspace,'add','--',*(c.path for c in normalized.files))
    tree=git(workspace,'write-tree')
    git(workspace,'-c','user.name='+profile['author_name'],'-c','user.email='+profile['author_email'],
        'commit','-m','Loop42 handoff '+task.task_id)
    commit=git(workspace,'rev-parse','HEAD')
    if git(workspace,'rev-parse','HEAD^{tree}')!=tree or git(workspace,'status','--porcelain'):
        return finish({'status':'UNKNOWN','reason':'commit_tree_changed'})
    subject=_subject(workspace,commit,request['repository'])
    receipt=VerificationReceipt(task.task_id,task.attempt_id,task.source_revision,task.context_fingerprint,
        subject,'local-registered-verifier',report['verifier_revision'],datetime.now(timezone.utc),
        tuple(CriterionVerification(v['identifier'],CriterionStatus.PASS,(EvidenceRef(v['identifier'],digest(v)),)) for v in green))
    artifact=result_artifact_from_receipt(receipt,task,observed_at=datetime.now(timezone.utc),subject_fingerprint=subject)
    return finish({'status':'DONE_VERIFIED','commit':commit,'tree':tree,'receipt':receipt_payload(receipt),
                   'receipt_fingerprint':artifact.receipt_fingerprint})
