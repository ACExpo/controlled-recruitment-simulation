import json
from typing import Literal
import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from starlette.middleware.trustedhost import TrustedHostMiddleware

import storage
from local_model import assess
from screening import CASES, ROOT, RUBRIC, VERSION, compare, replay

app = FastAPI(title="Controlled Recruitment Simulation", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    candidate: str
    variant: bool = True
    source: Literal["replay", "local"] = "replay"


@app.get("/")
def home():
    return FileResponse(ROOT / "static/index.html")


@app.get("/api/catalog")
def catalog():
    return {"cases": list(CASES.values()), "rubric": RUBRIC,
            "report": json.loads((ROOT / "reports/replay.json").read_text())}


@app.post("/api/runs")
def run(selection: Selection):
    case = CASES.get(selection.candidate)
    if case is None:
        raise HTTPException(404, "Unknown fictional candidate.")
    if selection.source == "local":
        try:
            output, provenance = assess(case, selection.variant)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, "Local inference unavailable or incomplete. Check Ollama and the installed model.") from exc
    else:
        output = replay(case, selection.variant)
        provenance = {"model": "Scripted fixture v1"}
    snapshot = dict(case=case, selection=selection.model_dump(), rubric=VERSION, output=output,
                    decision=compare(case, output), provenance=provenance)
    return storage.read(storage.save(snapshot))


@app.get("/api/runs/{run_id}")
def history(run_id: str):
    try:
        return storage.read(run_id)
    except KeyError:
        raise HTTPException(404, "Unknown run.")


@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str, authorization: str = Header(default="")):
    try:
        token = authorization[7:] if authorization.startswith("Bearer ") else ""
        storage.approve(run_id, token)
    except PermissionError:
        raise HTTPException(403, "A valid reviewer key is required.")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError:
        raise HTTPException(404, "Unknown run.")
    return storage.read(run_id)
