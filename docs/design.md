# Controlled Recruitment Simulation

Design proposal for discussion. The project will use fictional applicants and local inference. The central question is whether changing a résumé while holding qualifications constant can influence a model recommendation or a recorded shortlist decision.

## Scope and threat model

A fictional recruiter screens candidates for a Junior QA Analyst role. Applicants control only their résumé text. The employer controls the rubric, work-sample records, reviewer identities, and audit history. Each run uses one candidate and starts with fresh state.

The proposed rubric covers a test plan, a reproducible defect report, and a data-check exercise. Documented gaps and missing records have distinct labels. Missing evidence goes to review.

## Proposed architecture

| Component | Responsibility |
| --- | --- |
| Streamlit interface | Show the résumé, rubric, work samples, model findings, and recorded decision side by side. |
| Local LLM | Assess a single fictional application. Log the model version and inference settings. |
| Baseline simulation | Record the model recommendation in a disposable simulation run. |
| Secured workflow | Isolate candidate content, require structured findings, and check each criterion and evidence reference in Python. Bind each reference to the correct candidate and verify that the record supports the finding. |
| Authorization | Require a permitted reviewer action for a shortlist transition. Give the model no write access. |
| SQLite | Store local run records and decision history. Keep the versioned rubric, synthetic fixtures, and aggregate evaluation report in GitHub. |

## Evaluation plan

Prepare paired résumés covering authority claims, context changes, emotional appeals, and applicant-authored assessments. Hold qualifications constant across each pair. Include benign controls such as quoted feedback and personal statements. A personal circumstance must never count against an applicant.

Freeze an answer key and the target outcome for each case before running the comparison. Use the same candidates and model settings in both workflows. Report counts and denominators for changes in model recommendations, unauthorized shortlist transitions, clean-case accuracy, and unnecessary referrals. Document exclusions, failed runs, and variability across repeats.

## Proposed milestones

1. Agree on the rubric, expected outcomes, and fictional cases.
2. Build one end-to-end comparison that a reviewer can inspect.
3. Implement and verify evidence validation and independent authorization.
4. Expand the evaluation to 12 fictional applicants and publish observed results.
5. Package local setup instructions, tests, a screenshot, and a reproducible report for the portfolio.

This draft records design choices only. Implementation and empirical results are pending.
