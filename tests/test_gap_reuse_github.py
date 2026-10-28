import io
from http.client import IncompleteRead
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from tools.checks import gap_reuse_github as github


class Response(io.BytesIO):
    def __init__(self, payload, link=""):
        super().__init__(payload)
        self.headers = {"Link": link}


def item(number=12, title="Checkpoint recovery", pr=False):
    kind = "pull" if pr else "issues"
    result = {"number": number, "title": title, "state": "open",
              "html_url": f"https://github.com/example/project/{kind}/{number}"}
    if pr:
        result["pull_request"] = {"url": f"https://api.github.com/repos/example/project/pulls/{number}"}
    return result


class GitHubOpenWorkTests(unittest.TestCase):
    def collect(self, values, link="", target="checkpoint", token=None):
        response = Response(json.dumps(values).encode(), link)
        with patch.object(github, "build_opener") as opener:
            opener.return_value.open.return_value = response
            result = github.collect_open_work("example/project", target=target,
                                              revision="a" * 40, token=token)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.github.com/repos/example/project/issues?state=open&sort=updated&direction=desc&per_page=100&page=1")
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 10)
            opener.return_value.open.assert_called_once()
        return result, request

    def test_live_shape_issues_and_prs_become_untrusted_leads(self):
        result, request = self.collect([item(pr=True), item(13), item(14, "unrelated")])
        self.assertEqual(result["status"], "USEFUL_CANDIDATE")
        self.assertEqual([i["name"] for i in result["items"]],
                         ["PR #12 Checkpoint recovery", "Issue #13 Checkpoint recovery"])
        self.assertEqual(result["revision"], "a" * 40)
        self.assertIn("title", result["source"])
        self.assertIsNone(request.get_header("Authorization"))

    def test_negative_result_is_only_scoped_title_probe(self):
        result, _ = self.collect([item(title="other")])
        self.assertEqual(result["status"], "CHECKED_NO_DELTA")
        self.assertEqual(result["items"], [])
        self.assertIn("title", result["source"])

    def test_token_is_sent_only_in_header_and_not_returned(self):
        result, request = self.collect([], token="synthetic-token")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-token")
        self.assertNotIn("synthetic-token", json.dumps(result))

    def test_pagination_never_claims_complete_negative_or_follows_link(self):
        for values in ([], [item()]):
            with self.subTest(values=values):
                result, _ = self.collect(values, '<https://untrusted.invalid/next>; rel="next"')
                self.assertEqual(result["status"], "BLOCKED_UNKNOWN")
                self.assertIn("page", result["reason"])
                self.assertFalse(result.get("items"))

    def test_candidate_limit_does_not_claim_unsearched_items_are_absent(self):
        result, _ = self.collect([item(n) for n in range(1, 21)])
        self.assertEqual(result["status"], "USEFUL_CANDIDATE")
        self.assertEqual(len(result["items"]), 8)

    def test_http_auth_rate_limit_timeout_and_redirect_are_unknown_without_secret(self):
        for error in (HTTPError("https://api.github.com/", 401, "SECRET", {}, None),
                      HTTPError("https://api.github.com/", 429, "SECRET", {}, None),
                      HTTPError("https://api.github.com/", 301, "SECRET", {}, None),
                      URLError("SECRET"), TimeoutError("SECRET"), IncompleteRead(b"SECRET")):
            with self.subTest(error=type(error)):
                with patch.object(github, "build_opener") as opener:
                    opener.return_value.open.side_effect = error
                    result = github.collect_open_work("example/project", target="checkpoint",
                                                      revision="a" * 40, token="SECRET")
                    self.assertEqual(result["status"], "BLOCKED_UNKNOWN")
                    self.assertNotIn("SECRET", json.dumps(result))
                    opener.return_value.open.assert_called_once()

    def test_invalid_oversized_cross_repo_or_closed_payloads_are_unknown(self):
        bad = [b'{"message":"denied"}', b'[{"number":1,"number":2}]',
               b'[{"number":NaN}]', b'\xff', b'x' * (github.MAX_RESPONSE_BYTES + 1),
               b'[' * 20000 + b']' * 20000]
        for changes in ({"state": "closed"}, {"html_url": "https://github.com/other/repo/issues/12"},
                        {"number": True}, {"title": ""}, {"number": 1.5}):
            bad.append(json.dumps([{**item(), **changes}]).encode())
        for payload in bad:
            with self.subTest(payload=payload[:60]):
                with patch.object(github, "build_opener") as opener:
                    opener.return_value.open.return_value = Response(payload)
                    result = github.collect_open_work("example/project", target="checkpoint", revision="a" * 40)
                    self.assertEqual(result["status"], "BLOCKED_UNKNOWN")
                    self.assertFalse(result.get("items"))

    def test_invalid_repository_or_unsearchable_target_makes_no_request(self):
        for repository, target in (("../secret", "checkpoint"), ("example/project?x", "checkpoint"),
                                   ("example/project", "und the"), ("example/project", "a")):
            with self.subTest(repository=repository, target=target):
                with patch.object(github, "build_opener") as opener:
                    with self.assertRaises(ValueError):
                        github.collect_open_work(repository, target=target, revision="a" * 40)
                    opener.assert_not_called()

    def test_header_injection_and_invalid_revision_rejected_before_request(self):
        for revision, token in (("short", None), ("a" * 40, "token\nInjected: yes")):
            with patch.object(github, "build_opener") as opener:
                with self.assertRaises(ValueError):
                    github.collect_open_work("example/project", target="checkpoint",
                                             revision=revision, token=token)
                opener.assert_not_called()

    def test_redirect_handler_refuses_credential_forwarding(self):
        handler = github.NoRedirect()
        self.assertIsNone(handler.redirect_request(Request("https://api.github.com/"), None, 302,
                                                   "redirect", {}, "https://untrusted.invalid/"))


if __name__ == "__main__":
    unittest.main()
