# Stop.ps1 - Stop DRONA services started by start.ps1
# Usage:
#   .\Stop
#   .\Stop -StopMosquitto

param(
    [switch]$StopMosquitto
)

$ports = @(5173, 8001, 8545)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DRONA - Stop Services" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Stop services listening on known DRONA ports
foreach ($port in $ports) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    if ($pids) {
        foreach ($procId in $pids) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "Stopped process $procId on port $port" -ForegroundColor Green
            } catch {
                Write-Host "Could not stop process $procId on port $port" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "No listener found on port $port" -ForegroundColor Gray
    }
}

# Stop simulator process if it is still running (it does not expose a TCP port)
$simulators = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "simulation\\simulator.py" }

if ($simulators) {
    foreach ($proc in $simulators) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped simulator process $($proc.ProcessId)" -ForegroundColor Green
        } catch {
            Write-Host "Could not stop simulator process $($proc.ProcessId)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "No simulator process found" -ForegroundColor Gray
}

if ($StopMosquitto) {
    $svc = Get-Service -Name "mosquitto" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        try {
            Stop-Service -Name "mosquitto" -Force -ErrorAction Stop
            Write-Host "Stopped Mosquitto service" -ForegroundColor Green
        } catch {
            Write-Host "Could not stop Mosquitto service (try running as Administrator)" -ForegroundColor Yellow
        }
    } elseif ($svc) {
        Write-Host "Mosquitto service already stopped" -ForegroundColor Gray
    } else {
        Write-Host "Mosquitto service not installed" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
