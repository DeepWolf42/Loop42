"""Validate one bounded Codex JSON event stream before accepting its proposal."""
import json
from tools.harness.ollama_worker import strict_json

MAX_TRACE_BYTES=1024*1024
MAX_PROPOSAL_BYTES=2*1024*1024


class CodexCompletionError(ValueError):
    """Only fixed diagnostic codes, never provider text, cross this boundary."""


def reject(code):
    raise CodexCompletionError(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def completed_usage(trace, proposal):
    if not isinstance(trace,str) or len(trace.encode('utf-8'))>MAX_TRACE_BYTES:
        reject('CLI_TRACE_BUDGET')
    lines=[line for line in trace.splitlines() if line.strip()]
    if len(lines)>4096:
        reject('CLI_TRACE_BUDGET')
    thread=False;started=False;complete=False;final=False
    pending={};closed=set();usage={}
    for line in lines:
        if complete:
            reject('CLI_EVENT_AFTER_COMPLETION')
        try:
            event=strict_json(line.encode('utf-8'))
        except (ValueError,TypeError,RecursionError):
            reject('CLI_INVALID_EVENT')
        if not isinstance(event,dict) or not isinstance(event.get('type'),str):
            reject('CLI_INVALID_EVENT')
        kind=event['type']
        if kind in ('error','turn.failed'):
            reject('CLI_REPORTED_FAILURE')
        if kind=='thread.started':
            if thread or started or not isinstance(event.get('thread_id'),str) or not 1<=len(event['thread_id'])<=256:
                reject('CLI_INVALID_LIFECYCLE')
            thread=True
        elif kind=='turn.started':
            if not thread or started:
                reject('CLI_INVALID_LIFECYCLE')
            started=True
        elif kind in ('item.started','item.updated','item.completed'):
            if not started or final:
                reject('CLI_INVALID_LIFECYCLE')
            item=event.get('item')
            if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not 1<=len(item['id'])<=256:
                reject('CLI_INVALID_ITEM')
            identity=item['id'];item_type=item.get('type')
            if item_type not in ('reasoning','agent_message'):
                reject('CLI_UNSUPPORTED_ITEM')
            if identity in closed:
                reject('CLI_DUPLICATE_ITEM')
            if kind=='item.started':
                if identity in pending:
                    reject('CLI_DUPLICATE_ITEM')
                pending[identity]=item_type
            elif kind=='item.updated':
                if pending.get(identity)!=item_type:
                    reject('CLI_INVALID_ITEM')
            else:
                if identity in pending and pending.pop(identity)!=item_type:
                    reject('CLI_INVALID_ITEM')
                closed.add(identity)
                if item_type=='agent_message':
                    text=item.get('text')
                    if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_PROPOSAL_BYTES:
                        reject('CLI_INVALID_FINAL_MESSAGE')
                    try:
                        value=strict_json(text.encode('utf-8'))
                    except (ValueError,TypeError,RecursionError):
                        reject('CLI_INVALID_FINAL_MESSAGE')
                    if canonical(value)!=canonical(proposal):
                        reject('CLI_PROPOSAL_MISMATCH')
                    final=True
        elif kind=='turn.completed':
            if not started or not final or pending:
                reject('CLI_INVALID_LIFECYCLE')
            usage=event.get('usage',{})
            if not isinstance(usage,dict):
                reject('CLI_INVALID_USAGE')
            for key in ('input_tokens','output_tokens'):
                value=usage.get(key)
                if value is not None and (type(value) is not int or value<0):
                    reject('CLI_INVALID_USAGE')
            complete=True
        else:
            reject('CLI_UNSUPPORTED_EVENT')
    if not complete:
        reject('CLI_INCOMPLETE_TURN')
    return {key:usage.get(key) for key in ('input_tokens','output_tokens')}
