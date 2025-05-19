$encPath = "debug/encrypted_payload.bin"
$extPath = "debug/extracted_payload.bin"

if (!(Test-Path $encPath)) {
    Write-Output "❌ File not found: $encPath"
    exit
}
if (!(Test-Path $extPath)) {
    Write-Output "❌ File not found: $extPath"
    exit
}

$enc = [System.IO.File]::ReadAllBytes($encPath)
$ext = [System.IO.File]::ReadAllBytes($extPath)

Write-Output "🔍 Read encrypted: $($enc.Length) bytes"
Write-Output "🔍 Read extracted: $($ext.Length) bytes"

if ($enc.Length -ne $ext.Length) {
    Write-Output "❌ Length mismatch: $($enc.Length) vs $($ext.Length)"
    exit
}

$match = $true
for ($i = 0; $i -lt $enc.Length; $i++) {
    if ($enc[$i] -ne $ext[$i]) {
        Write-Output "❌ Content mismatch at byte ${i}: ${enc[$i]} != ${ext[$i]}"
        $match = $false
        break
    }
}

if ($match) {
    Write-Output "✅ Payloads match exactly"
}
