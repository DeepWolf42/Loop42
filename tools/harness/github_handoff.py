"""Operator-authored GitHub input and one reconciled nonprivate result comment."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import json
from pathlib import Path
import re
from urllib.parse import quote

from tools.harness.github_api import GitHubAPI,CapabilityError
from tools.harness.handoff import execute,status as local_status,digest,encoded,_save
from tools.harness.handoff_cli import CodexProvider
from tools.harness.ollama_worker import strict_json
from tools.harness.worker_dispatch_cli import _read_input
from tools.harness.side_effect_reconcile import SideEffectIntent,SideEffectObservation,SideEffectState,reconcile_side_effect
from tools.harness.action_policy import ActionRequest,ActionEffect,PolicyRule,PolicyDecision,evaluate_action_policy
from tools.harness.worker_provider import WorkerResult,WorkerStatus


def _scope(profile):
    cfg=profile['github'];issue=cfg['issue_number'];login=cfg['operator_login']
    if type(issue) is not int or issue<1 or not isinstance(login,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,39}',login):
        raise ValueError('invalid configured issue/operator')
    repository=profile['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('invalid repository')
    return '/repos/'+repository,issue,login


def _branch_path(profile):
    branch=profile['github']['source_branch']
    if not isinstance(branch,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}',branch) or any(p in ('','.','..') for p in branch.split('/')):
        raise ValueError('invalid configured source branch')
    return '/repos/'+profile['repository']+'/git/ref/heads/'+quote(branch,safe='')


def _capture(comment_id,profile,api):
    base,issue,login=_scope(profile)
    if type(comment_id) is not int or comment_id<1:raise ValueError('invalid comment ID')
    user=api.get('/user');repo=api.get(base);issue_data=api.get(base+'/issues/'+str(issue))
    if user['login'].casefold()!=login.casefold() or repo['full_name'].casefold()!=profile['repository'].casefold():
        raise ValueError('authenticated identity/repository mismatch')
    if repo.get('private') is not False or issue_data['number']!=issue or issue_data['state']!='open':
        raise ValueError('only explicitly selected public open issue supported')
    comment=api.get(base+'/issues/comments/'+str(comment_id))
    if (comment['id']!=comment_id or comment['user']['id']!=user['id']
            or comment['issue_url']!='https://api.github.com'+base+'/issues/'+str(issue)):
        raise ValueError('input author/issue mismatch')
    if not isinstance(comment['body'],str) or len(comment['body'].encode())>65536:
        raise ValueError('input body exceeds bound')
    blocks=re.findall(r'^```loop42-handoff\r?\n(.*?)\r?\n```\s*$',comment['body'],re.MULTILINE|re.DOTALL)
    if len(blocks)!=1 or comment['body'].count('```loop42-handoff')!=1:
        raise ValueError('exactly one request block required')
    request=strict_json(blocks[0].encode())
    expected={'schema','task_id','repository','source_revision','task','paths','verification_ids','require_red'}
    if not isinstance(request,dict) or set(request)!=expected or request['repository']!=profile['repository']:
        raise ValueError('remote request cannot supply authority/profile fields')
    if request['schema']!='loop42.handoff.v1' or not isinstance(request['source_revision'],str) or not re.fullmatch(r'[0-9a-f]{40}',request['source_revision']):
        raise ValueError('invalid remote schema/revision')
    if api.get(_branch_path(profile))['object']['sha']!=request['source_revision']:
        raise ValueError('live remote source revision changed')
    request['task_id']='gh-'+str(repo['id'])+'-'+str(comment_id)
    capture={'id':comment_id,'body':comment['body'],'updated_at':comment['updated_at'],
             'author_id':comment['user']['id'],'issue_url':comment['issue_url'],'source_revision':request['source_revision']}
    return request,capture,user


def _unchanged(capture,profile,api):
    base,issue,login=_scope(profile)
    value=api.get(base+'/issues/comments/'+str(capture['id']))
    observed={'id':value['id'],'body':value['body'],'updated_at':value['updated_at'],
              'author_id':value['user']['id'],'issue_url':value['issue_url'],
              'source_revision':api.get(_branch_path(profile))['object']['sha']}
    return observed==capture


def _marker(task_id):return '<!-- loop42-handoff-result:'+task_id+' -->'


def _summary(request,capture,report):
    allowed={'DONE_VERIFIED','UNKNOWN','BLOCKED_CAPABILITY','FAILED_WORKER','FAILED_VERIFICATION','RED_NOT_REPRODUCED','BLOCKED_SCOPE'}
    result={'schema':'loop42.github-handoff-result.v1','task_id':request['task_id'],
        'repository':request['repository'],'source_revision':request['source_revision'],
        'input_comment_id':capture['id'],'input_fingerprint':digest(capture),
        'status':report.get('status') if report.get('status') in allowed else 'UNKNOWN'}
    if result['status']=='DONE_VERIFIED':
        for name,pattern in (('commit',r'[0-9a-f]{40}'),('receipt_fingerprint',r'[0-9a-f]{64}')):
            value=report.get(name)
            if not isinstance(value,str) or not re.fullmatch(pattern,value):raise ValueError('invalid result identity')
            result[name]=value
        result['verification']=[{'identifier':v['identifier'],'exit_code':v['exit_code'],
            'timed_out':v['timed_out'],'output_truncated':v['output_truncated']} for v in report['green']]
    return result


def _body(summary):
    return _marker(summary['task_id'])+'\n```json\n'+encoded(summary).decode()+'\n```'


def _validate_summary(value,request,capture):
    basic={'schema','task_id','repository','source_revision','input_comment_id','input_fingerprint','status'}
    statuses={'DONE_VERIFIED','UNKNOWN','BLOCKED_CAPABILITY','FAILED_WORKER','FAILED_VERIFICATION','RED_NOT_REPRODUCED','BLOCKED_SCOPE'}
    if not isinstance(value,dict) or value.get('status') not in statuses:raise ValueError('invalid summary')
    fields=basic|({'commit','receipt_fingerprint','verification'} if value['status']=='DONE_VERIFIED' else set())
    if (set(value)!=fields or value['schema']!='loop42.github-handoff-result.v1'
            or value['task_id']!=request['task_id'] or value['repository']!=request['repository']
            or value['source_revision']!=request['source_revision'] or value['input_comment_id']!=capture['id']
            or value['input_fingerprint']!=digest(capture)):
        raise ValueError('summary identity/shape mismatch')
    if value['status']=='DONE_VERIFIED':
        if not re.fullmatch(r'[0-9a-f]{40}',value['commit']) or not re.fullmatch(r'[0-9a-f]{64}',value['receipt_fingerprint']):
            raise ValueError('invalid summary fingerprints')
        checks=value['verification']
        if not isinstance(checks,list) or [v['identifier'] for v in checks]!=request['verification_ids']:
            raise ValueError('verification coverage mismatch')
        for v in checks:
            if (set(v)!={'identifier','exit_code','timed_out','output_truncated'} or type(v['exit_code']) is not int
                    or v['exit_code']!=0 or v['timed_out'] is not False or v['output_truncated'] is not False):
                raise ValueError('remote verification not passed')


def _observed(summary,profile,api,user):
    base,issue,login=_scope(profile)
    values=api.get(base+'/issues/'+str(issue)+'/comments?per_page=100')
    if not isinstance(values,list) or len(values)>100:raise ValueError('incomplete comment observation')
    matches=[v for v in values if _marker(summary['task_id']) in v.get('body','')]
    if len(matches)!=1:return None,'absent' if not matches else 'conflict'
    value=matches[0]
    if value['user']['id']!=user['id'] or value['body']!=_body(summary):return None,'conflict'
    return value,'exact'


def run_comment(comment_id,profile,*,api=None,provider=None):
    base,issue,login=_scope(profile)
    if profile['github'].get('allow_comments') is not True:
        raise PermissionError('explicit result-comment authority required')
    if profile['github'].get('allow_execution_refs') is not True:
        raise PermissionError('explicit execution-claim branch authority required')
    api=api or GitHubAPI(profile)
    request,capture,user=_capture(comment_id,profile,api)
    bound=dict(profile,github_source={'comment_id':comment_id,'fingerprint':digest(capture),'author_id':user['id']})
    if not _unchanged(capture,profile,api):raise ValueError('input changed before execution')
    folder=Path(profile['state_dir']).resolve()/request['task_id']
    prior=api.get(base+'/issues/'+str(issue)+'/comments?per_page=100')
    if any(_marker(request['task_id']) in v.get('body','') for v in prior) and not (folder/'claim.json').is_file():
        return {'status':'UNKNOWN','reason':'remote_result_requires_original_recovery_no_execution'}
    def guarded_provider(worker_request):
        if not _unchanged(capture,profile,api):
            return WorkerResult(status=WorkerStatus.BLOCKED,provider='github-source-guard',model='not-dispatched',
                task_id=worker_request.task_id,attempt_id=worker_request.attempt_id,
                source_revision=worker_request.source_revision,context_fingerprint=worker_request.context_fingerprint,
                rationale_summary='GitHub task/source changed before provider dispatch')
        result=provider(worker_request)
        if _unchanged(capture,profile,api):return result
        return WorkerResult(status=WorkerStatus.BLOCKED,provider=result.provider,model=result.model,
            task_id=worker_request.task_id,attempt_id=worker_request.attempt_id,
            source_revision=worker_request.source_revision,context_fingerprint=worker_request.context_fingerprint,
            rationale_summary='GitHub task/source changed; no apply')
    report=execute(request,bound,provider=guarded_provider if provider is not None else None,
                   before_provider=lambda folder,task:api.reserve(request,profile,folder))
    if report.get('status')=='DONE_VERIFIED':report=local_status(request,bound)
    if report.get('status')=='UNKNOWN':return {'status':'UNKNOWN','reason':'local_evidence_incomplete_no_publication'}
    if not _unchanged(capture,profile,api):return {'status':'UNKNOWN','reason':'input_changed_no_publication'}
    summary=_summary(request,capture,report)
    folder=Path(profile['state_dir']).resolve()/request['task_id']
    body=_body(summary)
    intent_path=folder/'publication-intent.json'
    existing= intent_path.exists()
    target='github:'+profile['repository']+':issue:'+str(issue)
    intent=SideEffectIntent(request['task_id'],'github.comment',target,'exact-owned-result-marker',
        digest({'marker':'absent'}),digest({'body':body,'author':user['id']}))
    if existing:
        if strict_json(_read_input(str(intent_path)))!=asdict(intent):
            return {'status':'UNKNOWN','reason':'publication_intent_conflict'}
    value,kind=_observed(summary,profile,api,user)
    if kind=='conflict':return {'status':'UNKNOWN','reason':'remote_marker_conflict'}
    now=datetime.now(timezone.utc)
    state_fp=intent.desired_fingerprint if kind=='exact' else intent.before_fingerprint
    observed=SideEffectObservation(now,target,intent.state_scope,state_fp)
    outcome=reconcile_side_effect(intent,now=now,observation=observed)
    if outcome.state is SideEffectState.APPLIED:
        return dict(summary,publication='CONFIRMED',comment_id=value['id'])
    if existing:
        return {'status':'UNKNOWN','reason':'ambiguous_publication_no_replay'}
    # A separate atomic publication claim prevents concurrent runner duplicates
    # from posting two results after both obtained the same local receipt.
    try:(folder/'publication-claim').mkdir()
    except FileExistsError:return {'status':'UNKNOWN','reason':'publication_in_flight_no_replay'}
    action=ActionRequest('github.comment',target,ActionEffect.REVERSIBLE_WRITE)
    rule=PolicyRule('explicit-issue-summary',PolicyDecision.ALLOW,action=action.action,target_prefix=target,effect=action.effect)
    if evaluate_action_policy(action,interactive=False,rules=(rule,)).decision is not PolicyDecision.ALLOW:
        raise PermissionError('publication policy denied')
    if not _unchanged(capture,profile,api):return {'status':'UNKNOWN','reason':'input_changed_before_post'}
    _save(intent_path,asdict(intent))
    try:
        response=api.post(base+'/issues/'+str(issue)+'/comments',{'body':body})
        check=api.get(base+'/issues/comments/'+str(response['id']))
        if check['body']!=body or check['user']['id']!=user['id'] or check['issue_url']!=capture['issue_url']:
            return {'status':'UNKNOWN','reason':'publication_readback_mismatch'}
    except (CapabilityError,TimeoutError,OSError,ValueError,KeyError):
        # POST may have succeeded even if its response was lost. Only re-read;
        # absence never proves quiescence and never authorizes another POST.
        value,kind=_observed(summary,profile,api,user)
        if kind!='exact':return {'status':'UNKNOWN','reason':'ambiguous_publication_no_replay'}
        check=value
    return dict(summary,publication='CONFIRMED',comment_id=check['id'])


def remote_status(comment_id,profile,*,api=None):
    api=api or GitHubAPI(profile)
    request,capture,user=_capture(comment_id,profile,api)
    base,issue,login=_scope(profile)
    values=api.get(base+'/issues/'+str(issue)+'/comments?per_page=100')
    marker=_marker(request['task_id'])
    matches=[v for v in values if marker in v.get('body','')]
    if len(matches)!=1 or matches[0]['user']['id']!=user['id']:
        return {'status':'UNKNOWN','reason':'remote_result_missing_or_conflicting'}
    body=matches[0]['body']
    try:
        raw=body.split('\n```json\n',1)[1].removesuffix('\n```')
        value=strict_json(raw.encode())
        _validate_summary(value,request,capture)
        if _body(value)!=body:
            raise ValueError('remote binding mismatch')
        return dict(value,evidence_origin='github_report_not_local_reverification',comment_id=matches[0]['id'])
    except (ValueError,KeyError,IndexError,TypeError):return {'status':'UNKNOWN','reason':'remote_result_invalid'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('run','status'))
    parser.add_argument('--comment-id',type=int,required=True)
    parser.add_argument('--profile',required=True)
    args=parser.parse_args(argv)
    try:
        profile=strict_json(_read_input(args.profile))
        result=remote_status(args.comment_id,profile) if args.operation=='status' else run_comment(args.comment_id,profile,provider=CodexProvider(profile))
        print(json.dumps(result,ensure_ascii=True,allow_nan=False))
        return 0 if result['status']=='DONE_VERIFIED' else 3
    except (CapabilityError,PermissionError) as error:
        print(json.dumps({'status':'BLOCKED_CAPABILITY','reason':type(error).__name__}));return 3
    except (ValueError,KeyError,TypeError,OSError,RuntimeError):
        print(json.dumps({'status':'UNKNOWN','reason':'request_or_evidence_invalid'}));return 2


if __name__=='__main__':raise SystemExit(main())
