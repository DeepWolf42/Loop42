"""CLI/provider boundary tests; stubbed provider process is not live AI evidence."""
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from tools.harness.handoff_cli import CodexProvider
from tools.harness.worker_provider import WorkerRequest, WorkerStatus
from tools.harness.verification_registry import VerificationResult


class HandoffCLITests(unittest.TestCase):
    def request(self, text='Fix addition'):
        return WorkerRequest('example','attempt-1','a'*40,'b'*64,text,
            '{"files":{"answer.py":"wrong"},"file_sha256":{"answer.py":"'+ '0'*64 +'"},"verification_ids":["test:answer"]}',
            ('propose_changes','request_verification'),'coding')

    def test_missing_cli_or_permission_is_blocked_without_call(self):
        with patch('tools.harness.handoff_cli.shutil.which',return_value=None):
            self.assertEqual(CodexProvider({'allow_codex':True})(self.request()).status,WorkerStatus.BLOCKED)
        with patch('tools.harness.handoff_cli.run_verifications') as run:
            self.assertEqual(CodexProvider({})(self.request()).status,WorkerStatus.BLOCKED)
            run.assert_not_called()

    def test_oversized_prompt_blocks_before_execution(self):
        with patch('tools.harness.handoff_cli.shutil.which',return_value='codex'), patch('tools.harness.handoff_cli.run_verifications') as run:
            self.assertEqual(CodexProvider({'allow_codex':True})(self.request('x'*4000)).status,WorkerStatus.BLOCKED)
            run.assert_not_called()

    def test_cli_proposal_is_parsed_and_tool_events_are_rejected(self):
        proposal={'schema':'loop42.changeset.v1','changes':[{'operation':'modify','path':'answer.py',
            'base_sha256':'0'*64,'search':'wrong','replace':'right','expected_matches':1}],
            'requested_verification':['test:answer']}
        for tool in (False,True):
            def transport(workspace, identifiers, registry, **kw):
                argv=registry.specs[0].argv
                self.assertEqual(argv[argv.index('--sandbox')+1],'read-only')
                schema=json.loads(Path(argv[argv.index('--output-schema')+1]).read_bytes())
                self.assertIn('anyOf',schema['properties']['changes']['items'])
                Path(argv[argv.index('--output-last-message')+1]).write_text(json.dumps(proposal))
                event={'type':'item.completed','item':{'type':'command_execution' if tool else 'agent_message'}}
                return (VerificationResult('provider:codex',argv,0,False,json.dumps(event),False),)
            with patch('tools.harness.handoff_cli.shutil.which',return_value='codex'), patch('tools.harness.handoff_cli.run_verifications',side_effect=transport):
                result=CodexProvider({'allow_codex':True})(self.request())
                self.assertEqual(result.status,WorkerStatus.FAILED if tool else WorkerStatus.PROPOSAL)

    def test_missing_output_fails_without_proposal(self):
        def transport(workspace, identifiers, registry, **kw):
            return (VerificationResult('provider:codex',registry.specs[0].argv,1,False,'synthetic failure',False),)
        with patch('tools.harness.handoff_cli.shutil.which',return_value='codex'), patch('tools.harness.handoff_cli.run_verifications',side_effect=transport):
            result=CodexProvider({'allow_codex':True})(self.request())
            self.assertEqual(result.status,WorkerStatus.FAILED)
            self.assertIsNone(result.changeset)


if __name__=='__main__':
    unittest.main()
