$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$proc = Start-Process -FilePath 'D:\Tools\cloud-tools\Scripts\kaggle.exe' `
    -ArgumentList 'kernels', 'logs', 'dheeraj12237/ocean-sentinel-gate-4-3b-live-canary' `
    -RedirectStandardOutput 'D:\Projects\ocean-sentinel\experiments\performance\gate4_3B_live_kaggle_canary_20260908_102118\cloud_execution_v4.log' `
    -RedirectStandardError 'D:\Projects\ocean-sentinel\experiments\performance\gate4_3B_live_kaggle_canary_20260908_102118\cloud_execution_v4_err.log' `
    -NoNewWindow -PassThru -Wait

Write-Output "Exit code: $($proc.ExitCode)"
