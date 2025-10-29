import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict


class HadoopRunner:
    async def run(
        self,
        job: str,
        dataset_mb: int,
        parallelism: int,
        on_progress: Callable[[float], Any],
    ) -> Dict[str, Any]:
        if job != "wordcount":
            raise RuntimeError("Hadoop runner supports only 'wordcount' job")

        # Check availability
        if shutil.which("hadoop") is None:
            raise RuntimeError("hadoop command not found on PATH")

        streaming_jar = os.environ.get("HADOOP_STREAMING_JAR")
        if not streaming_jar or not os.path.exists(streaming_jar):
            # Try to auto-discover from HADOOP_HOME/share/hadoop/tools/lib
            hh = os.environ.get("HADOOP_HOME")
            guessed = None
            if hh:
                tools = os.path.join(hh, "share", "hadoop", "tools", "lib")
                if os.path.isdir(tools):
                    for name in os.listdir(tools):
                        if name.startswith("hadoop-streaming-") and name.endswith(".jar"):
                            guessed = os.path.join(tools, name)
                            break
            if guessed and os.path.exists(guessed):
                streaming_jar = guessed
            else:
                raise RuntimeError("Set HADOOP_STREAMING_JAR to your hadoop-streaming.jar path")

        # Prepare temp dirs and data
        tmpdir = tempfile.mkdtemp(prefix="hadoop_wc_")
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "out")

        # Generate dataset
        await _generate_text_file(input_path, dataset_mb)

        mapper = os.path.abspath("backend/workers/wordcount/mapper.py")
        reducer = os.path.abspath("backend/workers/wordcount/reducer.py")

        # Build mapper/reducer command wrappers to avoid Windows quoting issues with spaces in paths
        py = sys.executable
        mapper_wrapper = os.path.join(tmpdir, "mapper_wrapper.cmd")
        reducer_wrapper = os.path.join(tmpdir, "reducer_wrapper.cmd")
        with open(mapper_wrapper, "w", encoding="utf-8") as f:
            f.write(f'"{py}" "{mapper}"')
        with open(reducer_wrapper, "w", encoding="utf-8") as f:
            f.write(f'"{py}" "{reducer}"')
        # Call the wrapper scripts directly; Hadoop Streaming executes them via the platform shell
        mapper_cmd = f'"{mapper_wrapper}"'
        reducer_cmd = f'"{reducer_wrapper}"'

        # Build a single command line with quoted paths
        def q(p: str) -> str:
            return f'"{p}"'

        cmdline = (
            f"hadoop jar {q(streaming_jar)} "
            f"-mapper {mapper_cmd} -reducer {reducer_cmd} "
            f"-input {q(input_path)} -output {q(output_path)} "
            f"-numReduceTasks {max(1, parallelism // 2)}"
        )

        # Launch via shell because -mapper/-reducer expect single command strings
        proc = await asyncio.create_subprocess_shell(
            cmdline, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # Poll progress naively (no real progress from streaming) — send 0.5 mid-run
        await asyncio.sleep(0.5)
        on_progress(0.5)

        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Hadoop job failed: {stderr.decode(errors='ignore')}")

        # Count records approximated by number of words
        records = await _count_words_in_file(input_path)

        return {
            "records": records,
            "throughput_rps": None,  # computed by orchestrator with elapsed if needed
            "framework_version": await _hadoop_version(),
        }


async def _generate_text_file(path: str, size_mb: int) -> None:
    # Lightweight generator
    line = ("lorem ipsum dolor sit amet consectetur adipiscing elit\n").encode()
    target = size_mb * 1024 * 1024
    written = 0
    loop = asyncio.get_running_loop()
    with open(path, "wb") as f:
        while written < target:
            # Write in chunks to avoid huge memory
            chunk_times = min(1024, (target - written) // len(line) + 1)
            data = line * chunk_times
            await loop.run_in_executor(None, f.write, data)
            written += len(data)


async def _count_words_in_file(path: str) -> int:
    total = 0
    loop = asyncio.get_running_loop()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for chunk in iter(lambda: f.readline(), ""):
            total += len(chunk.split())
    return total


async def _hadoop_version() -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "hadoop", "version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        if out:
            first = out.decode(errors="ignore").splitlines()[0].strip()
            return first
    except Exception:
        pass
    return "unknown"


