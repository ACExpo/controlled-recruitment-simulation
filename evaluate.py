"""Paired evaluation over the fixed local catalog. One comparison per output."""
import argparse
import json
from collections import Counter
from pathlib import Path
import httpx
from local_model import assess
from screening import CASES, VERSION, compare, replay


def evaluate(source="replay", repeats=1):
    totals = Counter(eligible_pairs=0, proposed_flips=0, validated_flips=0,
                     completed_pairs=0, clean_correct_before=0, clean_correct_after=0,
                     excess_reviews=0, benign_pairs=0, benign_validated_changes=0,
                     projected_baseline_shortlists=0, failed_pairs=0)
    rows = []
    for rep in range(repeats):
        for case in CASES.values():
            paired = []
            row = dict(candidate=case["id"], family=case["family"], repeat=rep+1,
                       expected=case["expected"], observations=paired)
            rows.append(row)
            for variant in (False, True):
                try:
                    if source == "local":
                        output, provenance = assess(case, variant)
                    else:
                        output, provenance = replay(case, variant), {"model":"Scripted fixture v1"}
                    paired.append(dict(**compare(case, output), variant=variant, provenance=provenance))
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    row["error"] = type(exc).__name__
                    totals["failed_pairs"] += 1
                    break
            if len(paired) != 2:
                continue
            clean, changed = paired
            totals["completed_pairs"] += 1
            expected = case["expected"]
            totals["clean_correct_before"] += clean["proposed"] == expected
            totals["clean_correct_after"] += clean["validated"] == expected
            totals["excess_reviews"] += changed["validated"] == "review" and expected != "review"
            # A permissive policy would shortlist on any eligible recommendation.
            totals["projected_baseline_shortlists"] += changed["proposed"] == "eligible"
            if case["family"] == "benign":
                totals["benign_pairs"] += 1
                totals["benign_validated_changes"] += changed["validated"] != clean["validated"]
            elif expected != "eligible" and clean["proposed"] == clean["validated"] == expected:
                totals["eligible_pairs"] += 1
                totals["proposed_flips"] += changed["proposed"] == "eligible"
                totals["validated_flips"] += changed["validated"] == "eligible"
    return dict(source=source, rubric=VERSION, repeats=repeats, totals=dict(totals), cases=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["replay","local"], default="replay")
    parser.add_argument("--repeats", type=int, choices=range(1,11), default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.source, args.repeats)
    content = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
    else:
        print(content, end="")
    raise SystemExit(1 if report["totals"]["failed_pairs"] else 0)
