import hashlib
import json
import unittest
from dataclasses import replace

from tools.harness.local_client_provider import LocalClientChangeSetProvider
from tools.harness.worker_provider import WorkerRequest, WorkerStatus


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class LocalClientProviderTests(unittest.TestCase):
    def request(self, **changes):
        value = WorkerRequest('task-1', 'attempt-1', 'a'*40, 'b'*64,
                              'Korrigiere die Anzeige für München 🦷.', 'Synthetische Quelldaten.',
                              ('propose_changes', 'request_verification'))
        return replace(value, **changes)

    def response(self, raw):
        payload = json.loads(raw)
        proposal = {'schema': 'loop42.changeset.v1', 'changes': [
            {'operation': 'modify', 'path': 'labels.json', 'base_sha256': 'c'*64,
             'search': 'Bereit', 'replace': 'Fehlgeschlagen', 'expected_matches': 1}],
            'requested_verification': ['unit:labels']}
        return {'kind': 'model_proposal', 'profile': 'fast64', 'mode': 'quick', 'format': 'json',
                'inputSha256': hashlib.sha256(raw).hexdigest(),
                'contextSha256': hashlib.sha256(payload['context'].encode()).hexdigest(),
                'usage': {'prompt_tokens': 25, 'completion_tokens': 30},
                'answer': encoded(proposal).decode()}

    def provider(self, change=None):
        self.calls = []
        def transport(raw):
            self.calls.append(raw)
            response = self.response(raw)
            if change:
                change(response)
            return encoded(response)
        return LocalClientChangeSetProvider(transport, profile='fast64', max_tokens=1024)

    def test_valid_unicode_proposal_binds_full_identity_and_usage(self):
        request = self.request()
        result = self.provider().run(request)
        self.assertEqual(result.status, WorkerStatus.PROPOSAL)
        self.assertEqual((result.task_id, result.attempt_id, result.source_revision, result.context_fingerprint),
                         (request.task_id, request.attempt_id, request.source_revision, request.context_fingerprint))
        self.assertEqual(result.usage.input_tokens, 25)
        self.assertIsNone(result.usage.cost_microunits)
        self.assertEqual(result.model, 'fast64')  # Client profile, not an inferred model identity.
        payload = json.loads(self.calls[0])
        context = json.loads(payload['context'])
        self.assertEqual(context['task_id'], request.task_id)
        self.assertEqual(context['attempt_id'], request.attempt_id)
        self.assertEqual(context['source_revision'], request.source_revision)
        self.assertEqual(context['context_fingerprint'], request.context_fingerprint)
        self.assertEqual(context['source_data'], request.context)
        self.assertEqual(len(self.calls), 1)

    def test_missing_proposal_capability_never_calls_transport(self):
        provider = self.provider()
        self.assertEqual(provider.run(self.request(allowed_capabilities=())).status, WorkerStatus.BLOCKED)
        self.assertEqual(self.calls, [])

    def test_verification_capability_is_enforced(self):
        with self.assertRaises(ValueError):
            self.provider().run(self.request(allowed_capabilities=('propose_changes',)))

    def test_wrong_envelope_identity_or_mode_fails(self):
        for key, value in [('inputSha256', 'd'*64), ('contextSha256', 'd'*64),
                           ('profile', 'other'), ('mode', 'reasoning'), ('format', 'text'),
                           ('kind', 'verified')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.provider(lambda r: r.update({key:value})).run(self.request())

    def test_missing_binding_fields_fail(self):
        for key in ('inputSha256', 'contextSha256', 'profile', 'mode', 'format', 'kind', 'answer'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.provider(lambda r: r.pop(key)).run(self.request())

    def test_replayed_response_from_other_attempt_fails(self):
        first = self.provider()
        first.run(self.request())
        stale = encoded(self.response(self.calls[0]))
        provider = LocalClientChangeSetProvider(lambda _: stale, profile='fast64')
        with self.assertRaises(ValueError):
            provider.run(self.request(attempt_id='attempt-2'))

    def test_duplicate_keys_and_non_json_fail(self):
        for raw in (b'{"answer":1,"answer":2}', b'{"x":NaN}', b'[]', b'```json\n{}\n```', b'\xff', '{}'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                LocalClientChangeSetProvider(lambda _: raw, profile='fast64').run(self.request())

    def test_invalid_nested_json_or_schema_fails(self):
        for answer in ('{"changes":[],"changes":[]}', '{"x":NaN}', '{}', '[]',
                       '{"schema":"loop42.changeset.v1","changes":[],"requested_verification":[]}'):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                self.provider(lambda r: r.update(answer=answer)).run(self.request())

    def test_invalid_usage_fails(self):
        for usage in ({'prompt_tokens': True}, {'completion_tokens': -1}, {'prompt_tokens': 2.5}, []):
            with self.subTest(usage=usage), self.assertRaises((ValueError, TypeError)):
                self.provider(lambda r: r.update(usage=usage)).run(self.request())

    def test_response_limit_fails(self):
        with self.assertRaises(ValueError):
            LocalClientChangeSetProvider(lambda _: b' '* (4*1024*1024+1), profile='fast64').run(self.request())

    def test_input_limits_fail_before_transport(self):
        for request in (self.request(task='x'*8000), self.request(context='x'*1048576)):
            with self.subTest(size=len(request.context)), self.assertRaises(ValueError):
                self.provider().run(request)
            self.assertEqual(self.calls, [])

    def test_configuration_limits(self):
        for tokens in (True, 7, 4097, 1.5):
            with self.subTest(tokens=tokens), self.assertRaises((TypeError, ValueError)):
                LocalClientChangeSetProvider(lambda _: b'', profile='fast64', max_tokens=tokens)
        for profile in ('', ' ', 'x'*257):
            with self.assertRaises(ValueError):
                LocalClientChangeSetProvider(lambda _: b'', profile=profile)
        with self.assertRaises(TypeError):
            LocalClientChangeSetProvider(None, profile='fast64')

    def test_node_utf16_task_limit_blocks_astral_characters_before_transport(self):
        provider = self.provider()
        with self.assertRaises(ValueError):
            provider.run(self.request(task='🦷'*4000))
        self.assertEqual(self.calls, [])

    def test_transport_failure_propagates_without_retry(self):
        calls = []
        def unavailable(raw):
            calls.append(raw)
            raise TimeoutError('synthetic timeout')
        with self.assertRaises(TimeoutError):
            LocalClientChangeSetProvider(unavailable, profile='fast64').run(self.request())
        self.assertEqual(len(calls), 1)
