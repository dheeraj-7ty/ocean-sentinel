$u = [System.Environment]::GetEnvironmentVariable('KAGGLE_USERNAME','User')
$m = [System.Environment]::GetEnvironmentVariable('KAGGLE_USERNAME','Machine')
$k = [System.Environment]::GetEnvironmentVariable('KAGGLE_KEY','User')
Write-Output "KAGGLE_USERNAME_User: $u"
Write-Output "KAGGLE_USERNAME_Machine: $m"
if ($k) { Write-Output "KAGGLE_KEY_User: SET" } else { Write-Output "KAGGLE_KEY_User: NOT_SET" }

# Check upload_harness for stored credentials
$harness = Get-Content 'D:\Projects\ocean-sentinel\src\ocean_sentinel\cloud\upload_harness.py' -ErrorAction SilentlyContinue
if ($harness) {
    $lines = $harness | Select-String "KAGGLE_USERNAME|KAGGLE_KEY" | Select-Object -First 5
    Write-Output "upload_harness credential references: $lines"
}
