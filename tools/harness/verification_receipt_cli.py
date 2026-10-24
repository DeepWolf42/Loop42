"""Validate a saved receipt against consumer-supplied current evidence; no IO actions.

Reads one bounded JSON request from stdin or --input and prints an artifact only
after validation. It never obtains evidence, authenticates a verifier, writes
queues, calls models or posts results. Those remain consumer responsibilities.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys

from tools.harness.verification_receipt import EvidenceRef, parse_receipt, result_artifact_from_receipt
from tools.harness.worker_dispatch_cli import _expect_keys, _load_json, _read_input, _task, _timestamp

SCHEMA = 'loop42.verification-receipt-cli.v1'


def run_request(request: dict) -> dict:
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    _expect_keys(request, required={'schema', 'receipt', 'task', 'subject_fingerprint',
                                  'verifier_id', 'verifier_revision', 'observed_at',
                                  'evidence_fingerprints'}, where='request')
    if request['schema'] != SCHEMA:
        raise ValueError('unsupported receipt CLI schema')
    receipt = parse_receipt(json.dumps(request['receipt'], ensure_ascii=False).encode('utf-8'))
    task = _task(request['task'])
    observed_at = _timestamp(request['observed_at'], 'observed_at')
    if receipt.verified_at > observed_at:
        raise ValueError('receipt verification is later than current observation')
    if (receipt.verifier_id != request['verifier_id']
            or receipt.verifier_revision != request['verifier_revision']):
        raise ValueError('receipt does not match current trusted verifier basis')
    subject = request['subject_fingerprint']
    # The underlying helper allows None for internal use. This recovery boundary
    # deliberately requires a freshly supplied subject digest.
    if not isinstance(subject, str) or len(subject) != 64:
        raise ValueError('current subject fingerprint is required')
    current = request['evidence_fingerprints']
    if not isinstance(current, dict) or len(current) > 128 * 64:
        raise ValueError('current evidence must be a bounded fingerprint object')
    for source, fingerprint in current.items():
        EvidenceRef(source, fingerprint)
    refs = [ref for criterion in receipt.criteria for ref in criterion.evidence]
    if set(current) != {ref.source for ref in refs} or any(
            current[ref.source] != ref.fingerprint for ref in refs):
        raise ValueError('saved receipt evidence differs from current evidence')
    artifact = result_artifact_from_receipt(receipt, task, observed_at=observed_at,
                                            subject_fingerprint=subject)
    value = asdict(artifact)
    value['kind'] = artifact.kind.value
    value['observed_at'] = artifact.observed_at.isoformat()
    return {'schema': SCHEMA, 'artifact': value}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='-', help='JSON request path, or - for stdin')
    args = parser.parse_args()
    try:
        result = run_request(_load_json(_read_input(args.input)))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, TypeError, ValueError, RecursionError, OverflowError) as error:
        print(f'receipt recovery: {type(error).__name__}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
