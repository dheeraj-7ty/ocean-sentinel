$creds = Get-Content 'C:\Users\Dheeraj\.kaggle\credentials.json' | ConvertFrom-Json
Write-Output "username_set: $($creds.username -ne $null -and $creds.username.Length -gt 0)"
$klen = if ($creds.key) { $creds.key.Length } else { 0 }
Write-Output "key_length: $klen"
Write-Output "key_set: $($klen -gt 0)"
