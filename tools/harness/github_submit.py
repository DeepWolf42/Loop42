"""One explicitly approved text task into the existing GitHub handoff."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from tools.harness.github_api import GitHubAPI,CapabilityError
from tools.harness.github_handoff import _scope,_branch_path,run_comment
from tools.harness.handoff import _validate,_save,digest,encoded,git
from tools.harness.handoff_cli import CodexProvider
from tools.harness.ollama_worker import strict_json
from tools.harness.worker_dispatch_cli import _read_input
from tools.harness.side_effect_reconcile import SideEffectIntent,SideEffectObservation,SideEffectState,reconcile_side_effect
from tools.harness.action_policy import ActionRequest,ActionEffect,PolicyRule,PolicyDecision,evaluate_action_policy


def _preflight(request,profile,api):
    repo,folder,registry=_validate(request,profile)
    if git(repo,'rev-parse','HEAD')!=request['source_revision'] or git(repo,'status','--porcelain'):
        raise ValueError('stale or dirty submission source')
    base,issue,login=_scope(profile)
    user=api.get('/user');remote=api.get(base);item=api.get(base+'/issues/'+str(issue))
    if (user['login'].casefold()!=login.casefold() or type(user['id']) is not int
            or remote['full_name'].casefold()!=profile['repository'].casefold()
            or type(remote['id']) is not int or remote['id']<1
            or remote.get('private') is not False or item['number']!=issue or item['state']!='open'
            or api.get(_branch_path(profile))['object']['sha']!=request['source_revision']):
        raise ValueError('submission identity/source not current')
    return {'id':user['id'],'repository_id':remote['id']}


def _observe(api,base,issue,marker,body,user):
    values=api.get(base+'/issues/'+str(issue)+'/comments?per_page=100')
    if not isinstance(values,list) or len(values)>100:raise ValueError('incomplete input observation')
    matches=[v for v in values if marker in v.get('body','')]
    if not matches:return None,'absent'
    if len(matches)!=1:return None,'conflict'
    value=matches[0]
    if (value['body']!=body or value['user']['id']!=user['id']
            or value['issue_url']!='https://api.github.com'+base+'/issues/'+str(issue)
            or type(value['id']) is not int or value['id']<1):
        return None,'conflict'
    return value,'exact'


def submit(submission_id,task,source_revision,profile,*,api=None):
    cfg=profile['github']
    if any(cfg.get(k) is not True for k in ('allow_task_comments','allow_comments','allow_execution_refs')):
        raise PermissionError('explicit task/result publication and claim authority required')
    if (not isinstance(submission_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',submission_id)
            or not isinstance(task,str) or not task.strip() or len(task.encode())>2048 or '```' in task):
        raise ValueError('bounded task and stable submission key required')
    base,issue,login=_scope(profile)
    # Profile owns all execution scope and commands. Text cannot grant authority.
    request={'schema':'loop42.handoff.v1','task_id':'submission-preflight',
        'repository':profile['repository'],'source_revision':source_revision,'task':task,
        'paths':list(profile['allowed_paths']),
        'verification_ids':[v['identifier'] for v in profile['verifications']],'require_red':True}
    api=api or GitHubAPI(profile)
    user=_preflight(request,profile,api)
    key='submit-'+digest({'repository_id':user['repository_id'],'issue':issue,'operator':user['id'],'key':submission_id})[:48]
    request['task_id']=key
    marker='<!-- loop42-handoff-input:'+key+' -->'
    body=marker+'\n```loop42-handoff\n'+encoded(request).decode()+'\n```'
    target='github:'+profile['repository']+':issue:'+str(issue)
    intent=SideEffectIntent(key,'github.comment',target,'exact-owned-input-marker',
        digest({'marker':'absent'}),digest({'body':body,'author':user['id']}))
    def observed():return _observe(api,base,issue,marker,body,user)
    def confirmed(value):
        now=datetime.now(timezone.utc)
        observation=SideEffectObservation(now,target,intent.state_scope,intent.desired_fingerprint)
        if reconcile_side_effect(intent,now=now,observation=observation).state is not SideEffectState.APPLIED:
            raise ValueError('input reconciliation not confirmed')
        return {'status':'SUBMITTED','submission_id':key,'comment_id':value['id'],'source_revision':source_revision}
    value,kind=observed()
    if kind=='exact':return confirmed(value)
    if kind=='conflict':return {'status':'UNKNOWN','reason':'input_marker_conflict'}
    folder=Path(profile['state_dir']).resolve()/'submissions'/key
    folder.parent.mkdir(parents=True,exist_ok=True)
    try:folder.mkdir()
    except FileExistsError:return {'status':'UNKNOWN','reason':'submission_incomplete_no_replay'}
    _save(folder/'claim.json',{'identity':digest({'request':request,'profile':profile})})
    try:
        api.reserve(request,profile,folder)
        if _preflight(request,profile,api)!=user:
            raise ValueError('submission operator changed')
    except (ValueError,RuntimeError,OSError):
        return {'status':'UNKNOWN','reason':'submission_claim_or_source_not_confirmed'}
    # No POST replay, including crashes between the durable claim and intent.
    value,kind=observed()
    if kind=='exact':return confirmed(value)
    if kind=='conflict':return {'status':'UNKNOWN','reason':'input_marker_conflict'}
    action=ActionRequest('github.comment',target,ActionEffect.REVERSIBLE_WRITE)
    rule=PolicyRule('explicit-task-input',PolicyDecision.ALLOW,action=action.action,target_prefix=target,effect=action.effect)
    if evaluate_action_policy(action,interactive=False,rules=(rule,)).decision is not PolicyDecision.ALLOW:
        raise PermissionError('input publication policy denied')
    _save(folder/'publication-intent.json',asdict(intent))
    try:
        response=api.post(base+'/issues/'+str(issue)+'/comments',{'body':body})
        check=api.get(base+'/issues/comments/'+str(response['id']))
        if (check['body']!=body or check['user']['id']!=user['id'] or check['id']!=response['id']
                or check['issue_url']!='https://api.github.com'+base+'/issues/'+str(issue)):
            return {'status':'UNKNOWN','reason':'input_readback_mismatch'}
        return confirmed(check)
    except (CapabilityError,TimeoutError,OSError,ValueError,KeyError):
        value,kind=observed()
        if kind=='exact':return confirmed(value)
        return {'status':'UNKNOWN','reason':'ambiguous_input_no_replay'}


def start(submission_id,task,source_revision,profile,*,api=None,provider=None):
    api=api or GitHubAPI(profile)
    submitted=submit(submission_id,task,source_revision,profile,api=api)
    if submitted['status']!='SUBMITTED':return submitted
    return run_comment(submitted['comment_id'],profile,api=api,provider=provider)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('submit','start'))
    parser.add_argument('--profile',required=True)
    parser.add_argument('--submission-id',required=True)
    parser.add_argument('--expected-revision',required=True)
    parser.add_argument('--task-file',required=True,help='approved public UTF-8 text, or - for stdin')
    args=parser.parse_args(argv)
    try:
        profile=strict_json(_read_input(args.profile))
        task=_read_input(args.task_file).decode('utf-8')
        kwargs={'provider':CodexProvider(profile)} if args.operation=='start' else {}
        call=start if args.operation=='start' else submit
        result=call(args.submission_id,task,args.expected_revision,profile,**kwargs)
        print(json.dumps(result,ensure_ascii=True,allow_nan=False))
        return 0 if result['status'] in ('SUBMITTED','DONE_VERIFIED') else 3
    except (CapabilityError,PermissionError) as error:
        print(json.dumps({'status':'BLOCKED_CAPABILITY','reason':type(error).__name__}));return 3
    except (ValueError,KeyError,TypeError,OSError,RuntimeError):
        print(json.dumps({'status':'UNKNOWN','reason':'submission_or_evidence_invalid'}));return 2


if __name__=='__main__':raise SystemExit(main())
