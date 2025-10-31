import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .services.orchestrator import BenchmarkOrchestrator, FrameworkSelection, RunConfig


app = FastAPI(title="Big Benchmark")


# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class RunRequest(BaseModel):
    frameworks: List[str] = Field(default_factory=lambda: ["spark", "flink"])  # any subset
    dataset_mb: int = 50
    parallelism: int = 4
    iterations: int = 1
    job: str = "wordcount"


class RunResponse(BaseModel):
    run_id: str
    accepted: bool
    message: str


@app.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse(await asyncio.to_thread(lambda: open("frontend/index.html", "r", encoding="utf-8").read()))


# Quiet common browser probes
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def _devtools_probe() -> Dict[str, Any]:
    return {}


@app.get("/favicon.ico")
async def _favicon() -> HTMLResponse:
    # Return a tiny empty icon to avoid 404 noise
    return HTMLResponse(status_code=204)


@app.post("/api/run", response_model=RunResponse)
async def api_run(req: RunRequest) -> RunResponse:
    orchestrator = BenchmarkOrchestrator.get_instance()
    selection = FrameworkSelection(
        use_hadoop=False,
        use_spark="spark" in req.frameworks,
        use_flink="flink" in req.frameworks,
    )
    run_config = RunConfig(
        job=req.job,
        dataset_mb=req.dataset_mb,
        parallelism=req.parallelism,
        iterations=req.iterations,
    )
    run_id = orchestrator.enqueue_run(selection, run_config)
    return RunResponse(run_id=run_id, accepted=True, message="Run enqueued")


@app.websocket("/ws")
async def ws_metrics(ws: WebSocket):
    await ws.accept()
    orchestrator = BenchmarkOrchestrator.get_instance()
    client_id = orchestrator.add_ws(ws)
    try:
        while True:
            # Keep the WS alive; actual messages are pushed by orchestrator
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        orchestrator.remove_ws(client_id)


# Entrypoint for uvicorn
def main() -> None:
    import uvicorn

    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()


