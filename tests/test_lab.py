import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from app import app
from evaluate import evaluate
from local_model import assess
from screening import CASES, ROOT, compare, replay

KEY = "unit-test-only-temporary-reviewer"
AUTH = {"Authorization": "Bearer " + KEY}


class PolicyTests(unittest.TestCase):
    def test_clean_answer_key_and_missing_evidence(self):
        for case in CASES.values():
            self.assertEqual(compare(case, replay(case, False))["validated"], case["expected"])

    def test_wrong_candidate_wrong_result_duplicate_and_extra_field(self):
        case = CASES["QA-09"]
        for change in [dict(evidence="QA-10/plan"), dict(result="gap"),
                       dict(criterion="data"), dict(approved=True)]:
            result = replay(case, False)
            result["findings"][0].update(change)
            self.assertEqual(compare(case, result)["validated"], "review")
        self.assertEqual(compare(case, "incomplete")["validated"], "review")

    def test_published_report_is_reproducible(self):
        report = evaluate()
        self.assertEqual(report, json.loads((ROOT / "reports/replay.json").read_text()))
        self.assertEqual(report["totals"]["eligible_pairs"], 8)
        self.assertEqual(report["totals"]["proposed_flips"], 4)
        self.assertEqual(report["totals"]["validated_flips"], 0)
        self.assertEqual(report["totals"]["benign_validated_changes"], 0)

    def test_unavailable_model_counts_as_failed(self):
        with patch("evaluate.assess", side_effect=ValueError("Unavailable")):
            totals = evaluate("local")["totals"]
        self.assertEqual(totals["completed_pairs"], 0)
        self.assertEqual(totals["failed_pairs"], 12)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        config = patch.dict(os.environ, RECRUITMENT_DB=str(Path(tmp.name) / "test.db"),
                            RECRUITMENT_REVIEWER_KEY=KEY)
        config.start()
        self.addCleanup(config.stop)
        self.client = TestClient(app, base_url="http://localhost")

    def run_case(self, cid):
        response = self.client.post("/api/runs", json={"candidate": cid})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_approvals_across_all_cases(self):
        for cid in CASES:
            run = self.run_case(cid)
            url = "/api/runs/" + run["id"]
            self.assertIsNone(run["approved_at"])
            self.assertEqual(self.client.post(url + "/approve").status_code, 403)
            self.assertIsNone(self.client.get(url).json()["approved_at"])
            allowed = run["decision"]["validated"] == "eligible"
            self.assertEqual(self.client.post(url + "/approve", headers=AUTH).status_code,
                             200 if allowed else 409)

    def test_concurrent_reviewer_retry(self):
        url = "/api/runs/" + self.run_case("QA-09")["id"] + "/approve"
        with ThreadPoolExecutor(max_workers=4) as pool:
            times = list(pool.map(lambda _: self.client.post(url, headers=AUTH).json()["approved_at"], range(4)))
        self.assertIsNotNone(times[0])
        self.assertEqual(len(set(times)), 1)

    def test_unknown_id_and_auth_disabled(self):
        self.assertEqual(self.client.post("/api/runs", json={"candidate":"missing"}).status_code, 404)
        self.assertEqual(self.client.post("/api/runs", json={"candidate":"QA-09","approved":True}).status_code, 422)
        url = "/api/runs/" + self.run_case("QA-09")["id"] + "/approve"
        with patch.dict(os.environ, RECRUITMENT_REVIEWER_KEY=""):
            self.assertEqual(self.client.post(url, headers=AUTH).status_code, 403)

    def test_live_adapter_contract(self):
        case = CASES["QA-01"]
        def serve(req):
            self.assertEqual(req.url.host, "127.0.0.1")
            if req.url.path == "/api/tags":
                return httpx.Response(200, json={"models":[{"name":"mock","digest":"fixture"}]})
            payload = json.loads(req.content)
            self.assertEqual(payload["format"]["additionalProperties"], False)
            self.assertNotIn("tools", payload)
            self.assertNotIn(case["variant"], payload["messages"][0]["content"])
            self.assertIn(case["variant"], payload["messages"][1]["content"])
            self.assertNotIn("replay_escalates", str(payload))
            return httpx.Response(200, json={"done":True, "message":{"content":json.dumps(replay(case, False))}})
        client = httpx.Client(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(serve))
        with patch("local_model.httpx.Client", return_value=client), patch.dict(os.environ, RECRUITMENT_MODEL="mock"):
            result, provenance = assess(case, True)
        self.assertEqual(result, replay(case, False))
        self.assertEqual(provenance["digest"], "fixture")
