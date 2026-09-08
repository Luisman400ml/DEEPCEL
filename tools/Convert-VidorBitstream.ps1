[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputPath,
    [Parameter(Mandatory)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path -LiteralPath $InputPath).Path
$targetPath = [IO.Path]::GetFullPath($OutputPath)
if ($sourcePath -eq $targetPath) { throw 'Input and output must differ.' }
$ttf = [IO.File]::ReadAllText($sourcePath).Trim()
if ($ttf -notmatch '\A\d+(?:\s*,\s*\d+)*\s*,?\z') {
    throw 'Expected a Quartus TTF containing comma-separated decimal bytes.'
}
$tokens = $ttf.TrimEnd(',') -split '\s*,\s*'
$header = [Text.StringBuilder]::new()
for ($index = 0; $index -lt $tokens.Length; $index++) {
    $value = [int]::Parse($tokens[$index].Trim())
    if ($value -lt 0 -or $value -gt 255) { throw "Invalid byte at index $index." }
    # The Vidor upload path requires the bit order reversed within each TTF byte.
    $reversed = 0
    for ($bit = 0; $bit -lt 8; $bit++) {
        $reversed = ($reversed -shl 1) -bor (($value -shr $bit) -band 1)
    }
    [void]$header.Append($reversed).Append(',')
    if (($index + 1) % 16 -eq 0) { [void]$header.AppendLine() }
}
[void]$header.AppendLine()
[IO.File]::WriteAllText($targetPath, $header.ToString(), [Text.Encoding]::ASCII)
Write-Output "Converted $($tokens.Length) bytes: $targetPath"
Get-FileHash -LiteralPath $sourcePath, $targetPath -Algorithm SHA256
