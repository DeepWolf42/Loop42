import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.harness.verification_receipt import parse_receipt, receipt_payload, receipt_fingerprint
from tools.harness.verification_receipt_cli import run_request, SCHEMA
from test_verification_receipt import receipt, task, NOW, SUBJECT, EVIDENCE, VERIFIER_REV


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def request():
    current = task()
    return {'schema': SCHEMA, 'receipt': receipt_payload(receipt()),
            'task': {'task_id': current.task_id, 'attempt_id': current.attempt_id,
                     'source_revision': current.source_revision,
                     'context_fingerprint': current.context_fingerprint,
                     'acceptance_criteria': list(current.acceptance_criteria)},
            'subject_fingerprint': SUBJECT, 'verifier_id': 'loop42:test-suite',
            'verifier_revision': VERIFIER_REV, 'observed_at': NOW.isoformat(),
            'evidence_fingerprints': {'test:1': EVIDENCE, 'test:2': EVIDENCE}}


class ReceiptRecoveryTests(unittest.TestCase):
    def test_roundtrip_preserves_exact_receipt_and_fingerprint(self):
        value = receipt()
        restored = parse_receipt(encoded(receipt_payload(value)))
        self.assertEqual(restored, value)
        self.assertEqual(receipt_fingerprint(restored), receipt_fingerprint(value))

    def test_strict_json_and_input_bounds(self):
        for raw in (b'', b' '* (1024*1024+1), b'\xff', b'[]', b'{"schema":1,"schema":2}', b'{"x":NaN}'):
            with self.subTest(raw=raw[:30]), self.assertRaises((TypeError, ValueError)):
                parse_receipt(raw)

    def test_schema_exact_fields_nested_types_and_date(self):
        mutations = [lambda r:r.update(schema='other'), lambda r:r.update(extra=1),
                     lambda r:r.pop('subject_fingerprint'), lambda r:r.update(criteria={}),
                     lambda r:r.update(verified_at='2026-10-01T09:30:00'),
                     lambda r:r.update(verified_at=True), lambda r:r.update(task_id=False),
                     lambda r:r['criteria'][0].update(status='unknown-status'),
                     lambda r:r['criteria'][0].update(extra=1),
                     lambda r:r['criteria'][0].update(evidence={}),
                     lambda r:r['criteria'][0]['evidence'][0].update(extra=1),
                     lambda r:r['criteria'][0]['evidence'][0].update(fingerprint='x')]
        for mutate in mutations:
            raw = receipt_payload(receipt()); mutate(raw)
            with self.subTest(raw=str(raw)[:100]), self.assertRaises((TypeError, ValueError)):
                parse_receipt(encoded(raw))

    def test_collection_limits(self):
        for field in ('criteria', 'evidence'):
            raw = receipt_payload(receipt())
            if field == 'criteria':
                raw['criteria'] = [dict(raw['criteria'][0], criterion=str(i)) for i in range(129)]
            else:
                raw['criteria'][0]['evidence'] = [{'source':str(i),'fingerprint':EVIDENCE} for i in range(65)]
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_receipt(encoded(raw))

    def test_valid_current_basis_becomes_terminal_artifact(self):
        result = run_request(request())
        self.assertTrue(result['artifact']['success'])
        self.assertEqual(result['artifact']['receipt_fingerprint'], receipt_fingerprint(receipt()))
        self.assertEqual(result['artifact']['task_id'], task().task_id)

    def test_changed_attempt_revision_context_criteria_or_subject_cannot_return_success(self):
        changes = [('attempt_id','other'), ('source_revision','f'*40),
                   ('context_fingerprint','f'*64), ('acceptance_criteria',['changed'])]
        for key, value in changes:
            raw = request(); raw['task'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                run_request(raw)
        raw = request(); raw['subject_fingerprint'] = 'f'*64
        with self.assertRaises(ValueError):run_request(raw)

    def test_missing_changed_or_extra_live_evidence_fails(self):
        for evidence in ({}, {'test:1': EVIDENCE, 'test:2':'f'*64},
                         {'test:1': EVIDENCE, 'test:2':EVIDENCE,'extra':EVIDENCE}):
            raw = request(); raw['evidence_fingerprints'] = evidence
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):run_request(raw)

    def test_stale_verifier_or_future_receipt_fails(self):
        for key, value in [('verifier_id','other'), ('verifier_revision','other'),
                           ('observed_at','2026-09-01T00:00:00Z')]:
            raw = request();raw[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):run_request(raw)

    def test_fail_unknown_missing_or_reordered_acceptance_never_succeeds(self):
        for status in ('fail','unknown'):
            raw=request();raw['receipt']['criteria'][0]['status']=status
            with self.subTest(status=status), self.assertRaises(ValueError):run_request(raw)
        for criteria in (request()['receipt']['criteria'][:1],list(reversed(request()['receipt']['criteria']))):
            raw=request();raw['receipt']['criteria']=criteria
            with self.assertRaises(ValueError):run_request(raw)

    def test_cli_is_separate_process_and_fails_without_success_output(self):
        root=Path(__file__).resolve().parents[1]
        command=[sys.executable,'-m','tools.harness.verification_receipt_cli']
        good=subprocess.run(command,cwd=root,input=encoded(request()),capture_output=True)
        self.assertEqual(good.returncode,0,good.stderr)
        self.assertTrue(json.loads(good.stdout)['artifact']['success'])
        raw=request();raw['subject_fingerprint']='f'*64
        bad=subprocess.run(command,cwd=root,input=encoded(raw),capture_output=True)
        self.assertEqual(bad.returncode,2)
        self.assertEqual(bad.stdout,b'')
        self.assertNotIn(b'Traceback',bad.stderr)

    def test_cli_request_fields_are_exact(self):
        for key in ('schema','receipt','task','subject_fingerprint','verifier_id',
                    'verifier_revision','observed_at','evidence_fingerprints'):
            raw=request();raw.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):run_request(raw)
        raw=request();raw['extra']=True
        with self.assertRaises(ValueError):run_request(raw)

    def test_cli_datetime_extremes_are_input_errors_without_traceback(self):
        root=Path(__file__).resolve().parents[1]
        for field in ('verified_at','observed_at'):
            for date in ('0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00'):
                raw=request()
                if field=='verified_at':raw['receipt'][field]=date
                else:raw[field]=date
                result=subprocess.run([sys.executable,'-m','tools.harness.verification_receipt_cli'],
                                      cwd=root,input=encoded(raw),capture_output=True)
                with self.subTest(field=field,date=date):
                    self.assertEqual(result.returncode,2,result.stderr)
                    self.assertEqual(result.stdout,b'')
                    self.assertNotIn(b'Traceback',result.stderr)
