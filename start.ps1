# start.ps1 - Launch all DRONA services in the correct order.
# Run from the project root:  .\start.ps1
#
# Services started:
#   1. Mosquitto MQTT broker  (Windows service - checked, not spawned)
#   2. Hardhat local EVM node (new window, port 8545)
#   3. DroneRegistry contract deployment
#   4. FastAPI backend         (new window, port 8001)
#   5. Python simulation       (new window, 3 Kolkata drones)
#   6. React/Vite frontend     (new window, port 5173)

$Root = $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DRONA - Decentralized UAV Mesh Tracker   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Mosquitto ─────────────────────────────────────────────────────────────
Write-Host "[1/6] Checking Mosquitto MQTT broker..." -ForegroundColor Yellow
$mosq = Get-Service -Name "mosquitto" -ErrorAction SilentlyContinue
if ($mosq -and $mosq.Status -eq "Running") {
    Write-Host "      OK - Mosquitto is running." -ForegroundColor Green
} elseif ($mosq) {
    Start-Service mosquitto
    Write-Host "      Started Mosquitto service." -ForegroundColor Green
} else {
    Write-Host "      WARNING: Mosquitto service not found." -ForegroundColor Red
    Write-Host "      Install from: https://mosquitto.org/download/" -ForegroundColor Red
    Write-Host "      Then re-run this script." -ForegroundColor Red
    exit 1
}

# ── 2. Hardhat node ──────────────────────────────────────────────────────────
Write-Host "[2/6] Starting Hardhat local EVM node (port 8545)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "Set-Location '$Root'; Write-Host 'HARDHAT NODE' -ForegroundColor Cyan; npx hardhat node" `
    -WindowStyle Normal

# Poll until Hardhat is ready (up to 30 s)
Write-Host "      Waiting for Hardhat node..." -ForegroundColor Gray
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    try {
        $body = '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
        $null = Invoke-WebRequest "http://127.0.0.1:8545" `
            -Method POST -Body $body `
            -ContentType "application/json" `
            -UseBasicParsing -ErrorAction Stop
        $ready = $true
        break
    } catch {}
}
if (-not $ready) {
    Write-Host "      ERROR: Hardhat node did not respond within 30 s." -ForegroundColor Red
    exit 1
}
Write-Host "      OK - Hardhat node ready." -ForegroundColor Green

# ── 3. Deploy contract ───────────────────────────────────────────────────────
Write-Host "[3/6] Deploying DroneRegistry contract..." -ForegroundColor Yellow
Push-Location $Root
$deployOut = & npx hardhat run scripts/deploy.js --network localhost 2>&1
Pop-Location

$deployOut | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }

# Extract the deployed address and patch simulation/config.py
$addrMatch = ($deployOut | Out-String) | Select-String "(0x[0-9a-fA-F]{40})"
if ($addrMatch) {
    $addr = $addrMatch.Matches[0].Groups[1].Value
    Write-Host "      Contract address: $addr" -ForegroundColor Green

    $configPath = Join-Path $Root "simulation\config.py"
    $cfg = Get-Content $configPath -Raw
    $cfg = $cfg -replace '0x[0-9a-fA-F]{40}', $addr
    Set-Content $configPath $cfg
    Write-Host "      simulation/config.py updated with new address." -ForegroundColor Green
} else {
    Write-Host "      WARNING: Could not parse contract address - config.py unchanged." -ForegroundColor Red
}

# ── 4. Backend ───────────────────────────────────────────────────────────────
Write-Host "[4/6] Starting FastAPI backend (port 8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "Set-Location '$Root'; Write-Host 'BACKEND' -ForegroundColor Cyan; .venv\Scripts\python.exe -m uvicorn backend.main:app --port 8001 --reload" `
    -WindowStyle Normal

Write-Host "      Waiting for backend..." -ForegroundColor Gray
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep 1
    try {
        $null = Invoke-WebRequest "http://localhost:8001/health" -UseBasicParsing -ErrorAction Stop
        $ready = $true
        break
    } catch {}
}
if ($ready) {
    Write-Host "      OK - Backend ready." -ForegroundColor Green
} else {
    Write-Host "      WARNING: Backend did not respond within 20 s - continuing anyway." -ForegroundColor Red
}

# ── 5. Simulation ────────────────────────────────────────────────────────────
Write-Host "[5/6] Starting drone simulation (Kolkata, 3 drones)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "Set-Location '$Root'; Write-Host 'SIMULATION' -ForegroundColor Cyan; .venv\Scripts\python.exe simulation\simulator.py" `
    -WindowStyle Normal
Start-Sleep 2

# ── 6. Frontend ──────────────────────────────────────────────────────────────
Write-Host "[6/6] Starting React frontend (port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "Set-Location '$Root\frontend'; Write-Host 'FRONTEND' -ForegroundColor Cyan; npx vite --port 5173" `
    -WindowStyle Normal

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All services launched." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard  ->  http://localhost:5173" -ForegroundColor White
Write-Host "  API docs   ->  http://localhost:8001/docs" -ForegroundColor White
Write-Host "  Health     ->  http://localhost:8001/health" -ForegroundColor White
Write-Host "  EVM node   ->  http://127.0.0.1:8545" -ForegroundColor White
Write-Host "  MQTT       ->  localhost:1883" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to open the dashboard in your browser..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:5173"
