[CmdletBinding()]
param(
    [string]$Port = 'COM4',
    [ValidateRange(1,86400)][int]$Seconds = 32,
    [switch]$RunSelfTest,
    [string]$CsvPath,
    [Parameter(Mandatory)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$rawFullPath = [IO.Path]::GetFullPath($OutputPath)
if ($CsvPath) {
    $csvFullPath = [IO.Path]::GetFullPath($CsvPath)
    if ($csvFullPath -eq $rawFullPath) { throw 'CSV and raw log paths must differ.' }
    if (Test-Path -LiteralPath $csvFullPath) { throw "CSV already exists: $csvFullPath" }
}
$serial = [IO.Ports.SerialPort]::new($Port, 9600, 'None', 8, 'One')
$serial.ReadTimeout = 500
$serial.Encoding = [Text.Encoding]::UTF8
$serial.DtrEnable = $true
$serial.RtsEnable = $true
$capture = [Text.StringBuilder]::new()
$csvWriter = $null
$recordCount = 0
$csvFields = @('record', 'time_ms', 'temperature_c', 'humidity_rh_pct', 'prediction_c')
$invariant = [Globalization.CultureInfo]::InvariantCulture
try {
    $serial.Open()
    if ($CsvPath) {
        $csvStream = [IO.File]::Open($csvFullPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
        $csvWriter = [IO.StreamWriter]::new($csvStream, [Text.UTF8Encoding]::new($false))
        $csvWriter.AutoFlush = $true
        $csvWriter.WriteLine('received_at_utc,time_ms,temperature_c,humidity_rh_pct,prediction_c')
    }
    if ($RunSelfTest) { $serial.Write('T') }
    if ($CsvPath) { $serial.Write('C') }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        try {
            $line = $serial.ReadLine().TrimEnd("`r")
            [void]$capture.AppendLine($line)
            Write-Output $line
            if ($csvWriter -and $line.StartsWith('DATA,')) {
                $sample = ConvertFrom-Csv -InputObject $line -Header $csvFields
                $timeMs = [uint32]::Parse($sample.time_ms, $invariant)
                foreach ($field in @('temperature_c', 'humidity_rh_pct', 'prediction_c')) {
                    $value = [double]::Parse($sample.$field, [Globalization.NumberStyles]::Float, $invariant)
                    if ([double]::IsNaN($value) -or [double]::IsInfinity($value)) {
                        throw "Invalid $field in DATA row."
                    }
                }
                $record = [pscustomobject][ordered]@{
                    received_at_utc = [DateTime]::UtcNow.ToString('o', $invariant)
                    time_ms = $timeMs.ToString($invariant)
                    temperature_c = $sample.temperature_c
                    humidity_rh_pct = $sample.humidity_rh_pct
                    prediction_c = $sample.prediction_c
                }
                $csvRow = @($record | ConvertTo-Csv -NoTypeInformation)
                $csvWriter.WriteLine($csvRow[1])
                $recordCount++
            }
        } catch [TimeoutException] {}
    }
} finally {
    if ($serial.IsOpen) {
        try {
            if ($CsvPath) {
                $serial.Write('P')
                $serial.BaseStream.Flush()
            }
        } finally { $serial.Close() }
    }
    $serial.Dispose()
    if ($csvWriter) { $csvWriter.Dispose() }
    [IO.File]::WriteAllText($rawFullPath, $capture.ToString(), [Text.UTF8Encoding]::new($false))
}
if ($CsvPath) {
    if ($recordCount -eq 0) { throw 'No DATA rows were captured.' }
    Write-Output "Saved $recordCount samples to $CsvPath"
}
