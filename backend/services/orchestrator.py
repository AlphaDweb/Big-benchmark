import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi import WebSocket

from ..workers.hadoop_runner import HadoopRunner
from ..workers.spark_runner import SparkRunner
from ..workers.flink_runner import FlinkRunner


@dataclass
class FrameworkSelection:
    use_hadoop: bool
    use_spark: bool
    use_flink: bool


@dataclass
class RunConfig:
    job: str
    dataset_mb: int
    parallelism: int
    iterations: int


class BenchmarkOrchestrator:
    _instance: Optional["BenchmarkOrchestrator"] = None

    @classmethod
    def get_instance(cls) -> "BenchmarkOrchestrator":
        if cls._instance is None:
            cls._instance = BenchmarkOrchestrator()
        return cls._instance

    def __init__(self) -> None:
        self._queue: "asyncio.Queue[Tuple[str, FrameworkSelection, RunConfig]]" = asyncio.Queue()
        self._ws_clients: Dict[str, WebSocket] = {}
        self._loop_task = asyncio.create_task(self._loop())

    def add_ws(self, ws: WebSocket) -> str:
        cid = uuid.uuid4().hex
        self._ws_clients[cid] = ws
        return cid

    def remove_ws(self, client_id: str) -> None:
        self._ws_clients.pop(client_id, None)

    def enqueue_run(self, selection: FrameworkSelection, config: RunConfig) -> str:
        run_id = uuid.uuid4().hex
        self._queue.put_nowait((run_id, selection, config))
        return run_id

    async def _broadcast(self, message: Dict[str, Any]) -> None:
        dead: List[str] = []
        for cid, ws in self._ws_clients.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self._ws_clients.pop(cid, None)

    async def _loop(self) -> None:
        while True:
            run_id, selection, config = await self._queue.get()
            await self._broadcast({
                "type": "run_started",
                "run_id": run_id,
                "config": {
                    "job": config.job,
                    "dataset_mb": config.dataset_mb,
                    "parallelism": config.parallelism,
                    "iterations": config.iterations,
                },
            })
            try:
                await self._execute_run(run_id, selection, config)
            except Exception as e:
                await self._broadcast({"type": "run_error", "run_id": run_id, "error": str(e)})
            finally:
                await self._broadcast({"type": "run_finished", "run_id": run_id})

    async def _execute_run(self, run_id: str, selection: FrameworkSelection, config: RunConfig) -> None:
        jobs: List[Tuple[str, Any]] = []
        if selection.use_hadoop:
            jobs.append(("hadoop", HadoopRunner()))
        if selection.use_spark:
            jobs.append(("spark", SparkRunner()))
        if selection.use_flink:
            jobs.append(("flink", FlinkRunner()))

        for iter_idx in range(config.iterations):
            iter_label = f"{iter_idx + 1}/{config.iterations}"
            await self._broadcast({"type": "iteration_started", "run_id": run_id, "iteration": iter_label})
            for framework_name, runner in jobs:
                await self._broadcast({"type": "job_started", "run_id": run_id, "framework": framework_name, "iteration": iter_label})
                started = time.perf_counter()
                try:
                    result = await runner.run(
                        job=config.job,
                        dataset_mb=config.dataset_mb,
                        parallelism=config.parallelism,
                        on_progress=lambda prog: asyncio.create_task(
                            self._broadcast({
                                "type": "progress",
                                "run_id": run_id,
                                "framework": framework_name,
                                "iteration": iter_label,
                                "progress": prog,
                            })
                        ),
                    )
                    elapsed = time.perf_counter() - started
                    throughput = None
                    if result.get("records") and elapsed > 0:
                        try:
                            throughput = float(result["records"]) / float(elapsed)
                        except Exception:
                            throughput = None

                    await self._broadcast({
                        "type": "job_finished",
                        "run_id": run_id,
                        "framework": framework_name,
                        "iteration": iter_label,
                        "metrics": {
                            "elapsed_sec": elapsed,
                            "throughput_rps": throughput,
                            "records": result.get("records"),
                            "parallelism": config.parallelism,
                            "framework_version": result.get("framework_version"),
                            "status": "ok",
                        },
                    })
                except RuntimeError as e:
                    await self._broadcast({
                        "type": "job_finished",
                        "run_id": run_id,
                        "framework": framework_name,
                        "iteration": iter_label,
                        "metrics": {
                            "status": "unavailable",
                            "reason": str(e),
                            "parallelism": config.parallelism,
                        },
                    })
                except Exception as e:
                    await self._broadcast({
                        "type": "job_finished",
                        "run_id": run_id,
                        "framework": framework_name,
                        "iteration": iter_label,
                        "metrics": {
                            "status": "error",
                            "reason": str(e),
                            "parallelism": config.parallelism,
                        },
                    })


