# OpenUp 분할 수집 스크립트 (10등분)
# 각 분할을 순차적으로 실행하고, 완료 후 통합 파일을 생성합니다.

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpenUp 분할 수집 시작 (10등분)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = "collectors\scripts\openup\collect_seongsu_hash_to_sales.py"
$mergeScriptPath = "collectors\scripts\openup\merge_split_collections.py"
$totalSplits = 10

# 세션 시작 시간 기록 (모든 분할이 같은 세션 폴더에 저장되도록)
$sessionTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$env:SPLIT_SESSION_TIMESTAMP = $sessionTimestamp
Write-Host "세션 시작 시간: $sessionTimestamp" -ForegroundColor Green
Write-Host "모든 분할 파일이 같은 세션 폴더에 저장됩니다." -ForegroundColor Green
Write-Host ""

for ($i = 1; $i -le $totalSplits; $i++) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "분할 $i/$totalSplits 수집 시작" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    
    # 분할 수집 실행
    python $scriptPath --split-index $i
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "경고: 분할 $i/$totalSplits 수집 중 오류 발생" -ForegroundColor Red
        Write-Host "계속 진행할까요? (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne "Y" -and $response -ne "y") {
            Write-Host "수집 중단" -ForegroundColor Red
            break
        }
    } else {
        Write-Host ""
        Write-Host "분할 $i/$totalSplits 수집 완료" -ForegroundColor Green
    }
    
    # 다음 분할 전 잠시 대기 (API 부하 방지)
    if ($i -lt $totalSplits) {
        Write-Host "다음 분할 시작 전 5초 대기..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "모든 분할 수집 완료!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 통합 파일 생성
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "분할 파일 통합 시작" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

python $mergeScriptPath --auto

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "통합 완료!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "경고: 통합 중 오류가 발생했습니다." -ForegroundColor Red
    Write-Host "수동으로 통합하려면 다음 명령을 실행하세요:" -ForegroundColor Yellow
    Write-Host "  python $mergeScriptPath --auto" -ForegroundColor Gray
}