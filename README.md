Big Benchmark: Hadoop vs Spark vs Flink (Windows Guide)

Overview

This project runs the same WordCount job on Hadoop, Spark, and Flink, records speed/scalability metrics, and streams live results to a dashboard. If an engine isn’t available, the app continues with the others.

What’s included
- Orchestrator to run identical jobs across engines
- FastAPI backend with WebSocket live metrics
- Simple web dashboard with animated throughput bars and best-performer highlighting

Prerequisites (Windows)
1) Python 3.10 or newer
   - Install from the Microsoft Store or `https://www.python.org/downloads/` (check “Add Python to PATH”).
2) Git (optional, to clone)
   - `https://git-scm.com/download/win`
3) Java JDK 17
   - Install from `https://adoptium.net/` or Oracle JDK 17
   - Verify in PowerShell:
     - `java -version` → should print version
     - `echo $env:JAVA_HOME` → should be like `C:\Program Files\Java\jdk-17`

Install Spark (PySpark)
- Easiest: install PySpark in your venv
  - `pip install pyspark`
- Verify:
  - `python -c "import pyspark; print(pyspark.__version__)"`
- Tip (Windows): ensure workers use your venv Python
  - `$py = (python -c "import sys; print(sys.executable)")`
  - `$env:PYSPARK_PYTHON = $py; $env:PYSPARK_DRIVER_PYTHON = $py`

Install Flink (PyFlink)
- Simple install (may require matching apache-beam version):
  - `pip install apache-flink`
- If you hit version errors, use a compatible pair (example):
  - `pip uninstall -y apache-flink apache-beam`
  - `pip install "apache-flink==1.17.0" "apache-beam==2.43.0"`
- Make PyFlink use your venv Python:
  - `$py = (python -c "import sys; print(sys.executable)")`
  - `$env:PYFLINK_CLIENT_EXECUTABLE = $py; $env:PYFLINK_PYTHON = $py`
- Optional native Flink (Java cluster) is not required for this project.

Get the code
- With git: `git clone <this-repo-url>` then `cd` into the folder
- Or download as ZIP, extract (e.g., `C:\Users\<you>\Desktop\big`) and open PowerShell in that folder

Set up Python
1) Create and activate a virtual environment (PowerShell):
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
2) Install dependencies:
   - `pip install -r requirements.txt`

Run the dashboard
1) Start the server:
   - `.\scripts\run_server.ps1`
2) Open: `http://127.0.0.1:8000`
3) Choose frameworks, Dataset (MB), Parallelism, Iterations → click “Start Run”

Enable engines
Spark (easiest)
- PySpark is installed via requirements. No extra setup required (runs in `local[*]`).
- If you see a Spark Python error, ensure this prints your venv python:
  - `python -c "import sys; print(sys.executable)"` → `.venv\Scripts\python.exe`

Hadoop (Streaming)
1) Download Hadoop 3.4.2 for Windows and extract to `C:\hadoop-3.4.2`
2) In the SAME PowerShell you use to start the server, set:
   - `$env:JAVA_HOME = "C:\Program Files\Java\jdk-17"`
   - `$env:HADOOP_HOME = "C:\hadoop-3.4.2"`
   - `$env:PATH = "$env:JAVA_HOME\bin;$env:HADOOP_HOME\bin;$env:PATH"`
   - `$env:HADOOP_STREAMING_JAR = "C:\hadoop-3.4.2\share\hadoop\tools\lib\hadoop-streaming-3.4.2.jar"`
   - `Test-Path $env:HADOOP_STREAMING_JAR` → should be `True`
3) Confirm:
   - `hadoop version` → prints version (ignore any extra warnings)

Flink (optional)
- PyFlink on Windows can be tricky. The app includes a fallback that returns results even if native PyFlink fails.
- To try native PyFlink, install a compatible pair (example):
  - `pip uninstall -y apache-flink apache-beam`
  - `pip install "apache-flink==1.17.0" "apache-beam==2.43.0"`
- Or run in WSL2/Ubuntu for smoother native Flink.

Using the dashboard
- Check Hadoop, Spark, and/or Flink.
- Pick Dataset (MB), Parallelism, Iterations.
- Click “Start Run”; watch the table and bar chart update live. The fastest per-iteration row is highlighted.

Live Results columns
- Run: short ID for the current benchmark run
- Iteration: iteration index out of total (e.g., 1/3)
- Framework: the engine that was run (Hadoop, Spark, Flink)
- Status: ok, unavailable (engine not configured), or error (failed run)
- Elapsed (s): total wall-clock time the job took, in seconds
- Records: approximate number of records processed (for WordCount: words)
- Throughput (rec/s): Records divided by Elapsed, higher is better

Troubleshooting
- Site doesn’t open: use `http://127.0.0.1:8000` (not `0.0.0.0`).
- “Python was not found”: disable Windows App execution aliases for python/python3, reactivate venv. Optionally set:
  - `$py = (python -c "import sys; print(sys.executable)")`
  - `$env:PYSPARK_PYTHON = $py; $env:PYSPARK_DRIVER_PYTHON = $py`
  - `$env:PYFLINK_CLIENT_EXECUTABLE = $py; $env:PYFLINK_PYTHON = $py`
- Hadoop error `'C:\\Program' is not recognized`: set and use `JAVA_HOME` and PATH in this shell:
  - `$env:JAVA_HOME = "C:\\Program Files\\Java\\jdk-17"`
  - `$env:PATH = "$env:JAVA_HOME\\bin;$env:PATH"`
- Hadoop “Set HADOOP_STREAMING_JAR”: ensure the jar path exists and is set (see Hadoop section above).
- Flink `get_java_function`/collector errors: rely on the built-in fallback or use the compatible versions above or WSL2.

Project layout
- `backend/` — FastAPI app, orchestrator, engine runners
- `frontend/` — dashboard (HTML/JS)
- `scripts/` — helper scripts (e.g., `run_server.ps1`)

Security
- Local-only benchmarking tool. Do not expose publicly.
