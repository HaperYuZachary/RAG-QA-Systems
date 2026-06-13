# 一键启动 RAG QA System 后端
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"
Write-Host "========================================" -ForegroundColor Green
Write-Host "  RAG QA System - 后端启动中..." -ForegroundColor Green
Write-Host "  API 地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
