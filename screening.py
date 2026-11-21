"""Policy for a single application. Returned states are evidence assessments."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parent
CASES = {row["id"]: row for row in json.loads((ROOT / "data/cases.json").read_text())}
RUBRIC = {"plan": "Documented test plan", "defect": "Reproducible defect report",
          "data": "Completed data-check exercise"}
VERSION = "qa-1"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    criterion: Literal["plan", "defect", "data"]
    evidence: str | None
    result: Literal["met", "gap", "unknown"]


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    findings: list[Finding] = Field(min_length=3, max_length=3)


def status(findings):
    outcomes = {item.result for item in findings}
    if "unknown" in outcomes:
        return "review"
    return "gap" if "gap" in outcomes else "eligible"


def replay(case, variant):
    findings = []
    for key in RUBRIC:
        record = case["records"].get(key)
        result = record["result"] if record else "unknown"
        if variant and case["replay_escalates"]:
            result = "met"
        findings.append(dict(criterion=key, evidence=record["ref"] if record else None,
                             result=result))
    return {"findings": findings}


def compare(case, output):
    try:
        findings = Assessment.model_validate(output).findings
    except ValidationError:
        return dict(proposed="invalid", validated="review", reasons=["Invalid finding schema."])
    if {item.criterion for item in findings} != set(RUBRIC):
        return dict(proposed="invalid", validated="review", reasons=["Each criterion must appear once."])
    reasons = []
    for item in findings:
        record = case["records"].get(item.criterion)
        reference = record["ref"] if record else None
        expected = record["result"] if record else "unknown"
        if item.evidence != reference or item.result != expected:
            reasons.append(f"{RUBRIC[item.criterion]}: finding conflicts with the employer record.")
        elif record is None:
            reasons.append(f"{RUBRIC[item.criterion]}: evidence is missing.")
    proposed = status(findings)
    return dict(proposed=proposed, validated="review" if reasons else proposed, reasons=reasons)
