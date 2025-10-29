param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path ".venv/ScriptS/Activate.ps1") -and -not (Test-Path -Path ".venv/Scripts/Activate.ps1")) {
  Write-Host "Virtual environment not found. Creating .venv..."
  python -m venv .venv
}

Write-Host "Activating venv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing/updating dependencies (requirements.txt)..."
pip install -r requirements.txt

Write-Host "Configuring Python for Spark/Flink in this session..."
$py = (python -c "import sys; print(sys.executable)")
$env:PYSPARK_PYTHON = $py
$env:PYSPARK_DRIVER_PYTHON = $py
$env:PYFLINK_CLIENT_EXECUTABLE = $py
$env:PYFLINK_PYTHON = $py

if (-not $env:JAVA_HOME) {
  Write-Host "[Note] JAVA_HOME is not set. Hadoop/Flink may require JDK 17." -ForegroundColor Yellow
}
if (-not $env:HADOOP_STREAMING_JAR) {
  Write-Host "[Note] HADOOP_STREAMING_JAR not set. Hadoop Streaming may be unavailable." -ForegroundColor Yellow
}

Write-Host "Starting server on port $Port"
Write-Host "Open http://127.0.0.1:$Port"
try {
  Start-Process "http://127.0.0.1:$Port" | Out-Null
} catch {}
python -m uvicorn backend.server:app --host 127.0.0.1 --port $Port


  
