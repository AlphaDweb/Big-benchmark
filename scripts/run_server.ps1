param(
  [int]$Port = 8000,
  [string]$BindHost = '127.0.0.1',
  [switch]$NoBrowser,
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path ".venv/ScriptS/Activate.ps1") -and -not (Test-Path -Path ".venv/Scripts/Activate.ps1")) {
  Write-Host "Virtual environment not found. Creating .venv..."
  python -m venv .venv
}

Write-Host "Activating venv..."
. .\.venv\Scripts\Activate.ps1

if (-not $SkipInstall) {
  Write-Host "Installing/updating dependencies (requirements.txt)..."
  pip install -r requirements.txt
}

# Ensure uvicorn is available
try { uvicorn --version | Out-Null } catch { pip install "uvicorn[standard]" | Out-Null }

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
  # Try to auto-discover from HADOOP_HOME
  if ($env:HADOOP_HOME -and (Test-Path "$env:HADOOP_HOME\share\hadoop\tools\lib")) {
    $guess = Get-ChildItem "$env:HADOOP_HOME\share\hadoop\tools\lib" -Filter "hadoop-streaming-*.jar" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($guess) {
      $env:HADOOP_STREAMING_JAR = $guess.FullName
      Write-Host "[Info] Using discovered HADOOP_STREAMING_JAR: $($env:HADOOP_STREAMING_JAR)" -ForegroundColor Cyan
    } else {
      Write-Host "[Note] HADOOP_STREAMING_JAR not set and not found under HADOOP_HOME. Hadoop Streaming may be unavailable." -ForegroundColor Yellow
    }
  } else {
    Write-Host "[Note] HADOOP_STREAMING_JAR not set. Hadoop Streaming may be unavailable." -ForegroundColor Yellow
  }
}

Write-Host "Host: $BindHost  Port: $Port"

Write-Host "Starting server on port $Port"
Write-Host ("Open http://{0}:{1}" -f $BindHost, $Port)
if (-not $NoBrowser) {
  try { Start-Process ("http://{0}:{1}" -f $BindHost, $Port) | Out-Null } catch {}
}
python -m uvicorn backend.server:app --host $BindHost --port $Port --no-access-log


  
