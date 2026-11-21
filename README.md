# Controlled Recruitment Simulation

A local Python portfolio lab for investigating a hiring workflow's response to untrusted résumé content. Open one fictional application and follow a proposed finding from the résumé through evidence validation to reviewer approval.

## Open the demo

Use Python 3.12 in an activated virtual environment. From the repository root run:

```sh
python -m pip install -r requirements.txt
python run_lab.py
```

Open **http://127.0.0.1:8000**. The default replay works offline after dependencies are installed. For an eligible application, use the temporary reviewer key printed in your terminal to record an approval. Restarting the launcher rotates the generated key. The SQLite history persists under `.local/`. Keep the application on loopback.

### Try the first case

Choose **QA-01 · Avery Chen**. Switch between **Clean control** and **Scenario variant**, and select **Run comparison**. Both versions have the same work samples.

| Step | What the scenario variant shows |
| --- | --- |
| Employer evidence | Test plan and data check meet the rubric. The defect report is missing. |
| Baseline simulation | A scripted assessor marks all three criteria as met. A workflow accepting that proposal would mark Avery eligible. |
| Backend validation | The missing defect report cannot support a positive finding. The application routes the case to review and explains the mismatch. |
| Shortlist | No shortlist transition occurs. A reviewer with a valid credential can only shortlist an evidence-eligible run. |

Try **QA-09 · Robin Vale** to exercise the successful approval path. Reopen a run using the link under **Run record**.

## What the comparison measures

The same assessor output goes through two policies. The baseline projects the effect of accepting its recommendation. The protected path checks evidence and separately enforces authorization. Only the protected path can persist an actual reviewer decision.

The default dataset contains 12 fictional applicants, three job-related criteria, eight scenario pairs across four families, and four benign controls. The scenario variants use descriptive résumé context. The replay assigns illustrative assessor responses explicitly in the fixtures. The live adapter receives only the employer evidence and selected résumé. The answer key, scenario labels, and scripted outcomes stay outside its input.

| Replay result | Count |
| --- | ---: |
| Eligible scenario pairs where an unsupported recommendation became eligible | 4 / 8 |
| Same pairs accepted as eligible after evidence validation | 0 / 8 |
| Clean assessments matching the frozen case labels | 12 / 12 |
| Benign controls whose validated outcome changed | 0 / 4 |
| Additional manual reviews on variant applications | 2 / 12 |

Each scenario family contributed one unsupported recommendation across two pairs. Two belonged to applicants with a documented gap. The protected workflow referred those mismatches to a reviewer, which explains the additional review burden. The other two already required review for missing evidence. The fixture counts describe control performance on these illustrative outputs. An empirical attack success rate for a vulnerable live LLM has not been measured.

Reproduce the [full evaluation](reports/replay.json) and run the tests:

```sh
python evaluate.py --output .local/replay.json
python -m unittest discover -s tests -v
```

## Optional local model

Install and start Ollama on the same computer and download the local model:

```sh
ollama pull qwen2.5:3b
```

Choose **Local Ollama model** in the app. To use another installed local model, set `RECRUITMENT_MODEL` to its exact installed name before starting Python. The adapter requests structured findings over loopback, records the model digest and settings, and gives the model no tools or database access. Each assessment starts with a fresh conversation. If inference fails, the interface reports the failure and the evaluator records it as an incomplete pair.

```sh
python evaluate.py --source local --repeats 3 --output .local/live.json
```

The report records paired sensitivity to the prepared résumé context, before and after backend validation of the same model output. Each family uses pairs whose clean proposal and validated result both match the expected, non-eligible label. The target outcome is eligible. Repeats are repeated observations of the same fixtures. Review failures and denominators before interpreting percentages. A local inference run may produce zero changes.

## Security and responsible AI

- **Trust boundary.** Each request selects a known synthetic fixture. The backend supplies the rubric and employer-owned work samples. The model receives one candidate at a time.
- **Evidence validation.** Pydantic enforces field and value restrictions. Python verifies criterion coverage, applicant-specific references and recorded results. Missing evidence or conflicts trigger human review.
- **Independent authorization.** A local single-reviewer credential is required for every approval. The backend checks the immutable run snapshot inside a SQLite transaction. Concurrent approvals produce one timestamp. A personal narrative has no role in the policy.
- **Scope.** This is an educational simulator. Its employer records express findings in structured form, and its synthetic population cannot establish hiring fairness or performance on real applications. The local reviewer credential represents one reviewer. Anyone controlling the host or the database is inside the trust boundary.

The [initial design proposal](docs/design.md) records the planning stage. The implementation uses FastAPI with a small HTML/JavaScript interface so that UI actions and integration tests exercise the same backend. Background reading: [OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) and [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
