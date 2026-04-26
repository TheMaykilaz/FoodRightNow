$root = $PSScriptRoot

Write-Host "Starting all microservices..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\order_service'; Write-Host 'ORDER SERVICE :8001' -ForegroundColor Green; python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\courier_service'; Write-Host 'COURIER SERVICE :8002' -ForegroundColor Green; python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\tracking_service'; Write-Host 'TRACKING SERVICE :8003' -ForegroundColor Green; python -m uvicorn main:app --host 0.0.0.0 --port 8003 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\reporting_service'; Write-Host 'REPORTING SERVICE :8004' -ForegroundColor Green; python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; Write-Host 'FRONTEND :8000' -ForegroundColor Green; python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host ""
Write-Host "All services launched!" -ForegroundColor Green
Write-Host "  Frontend:          http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Order Service:     http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "  Courier Service:   http://localhost:8002/docs" -ForegroundColor Yellow
Write-Host "  Tracking Service:  http://localhost:8003/docs" -ForegroundColor Yellow
Write-Host "  Reporting Service: http://localhost:8004/docs" -ForegroundColor Yellow
