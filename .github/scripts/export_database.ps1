# ==============================================================================
# Overrevving - Local Database & Excel/CSV Exporter
# Generates multi-year JSONs, Tidy CSVs for BI dashboards, and Master Excel
# ==============================================================================

$baseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dataDir = Join-Path $baseDir "data"
$exportsDir = Join-Path $baseDir "exports"
$csvDir = Join-Path $exportsDir "csv"

# 1. Directory creation
$categories = @('motogp', 'moto2', 'moto3', 'sbk', 'f1', 'mxgp', 'mx2')
foreach ($cat in $categories) {
    $catFolder = Join-Path $dataDir $cat
    if (-not (Test-Path $catFolder)) { New-Item -ItemType Directory -Path $catFolder -Force | Out-Null }
}
if (-not (Test-Path $csvDir)) { New-Item -ItemType Directory -Path $csvDir -Force | Out-Null }

# 2. Load standings_latest.json
$standingsLatestPath = Join-Path $dataDir "standings_latest.json"
if (-not (Test-Path $standingsLatestPath)) {
    Write-Error "standings_latest.json not found at $standingsLatestPath"
    exit 1
}
$record = Get-Content $standingsLatestPath -Raw | ConvertFrom-Json

# Calendars 2026
$CALENDARS_2026 = @{
    motogp = @(
        @{ round = 1; name = 'Thailand'; date = '2026-03-01'; weather = 'Dry' },
        @{ round = 2; name = 'Brazil'; date = '2026-03-22'; weather = 'Dry' },
        @{ round = 3; name = 'USA'; date = '2026-03-29'; weather = 'Dry' },
        @{ round = 4; name = 'Spain'; date = '2026-04-26'; weather = 'Dry' },
        @{ round = 5; name = 'France'; date = '2026-05-10'; weather = 'Dry' },
        @{ round = 6; name = 'Catalonia'; date = '2026-05-17'; weather = 'Dry' },
        @{ round = 7; name = 'Italy'; date = '2026-05-31'; weather = 'Dry' },
        @{ round = 8; name = 'Hungary'; date = '2026-06-07'; weather = 'Dry' },
        @{ round = 9; name = 'Czechia'; date = '2026-06-21'; weather = 'Dry' },
        @{ round = 10; name = 'Netherlands'; date = '2026-06-28'; weather = 'Dry' },
        @{ round = 11; name = 'Germany'; date = '2026-07-12'; weather = 'Dry' },
        @{ round = 12; name = 'Great Britain'; date = '2026-08-09'; weather = 'Dry' },
        @{ round = 13; name = 'Aragon'; date = '2026-08-30'; weather = 'Dry' },
        @{ round = 14; name = 'San Marino'; date = '2026-09-13'; weather = 'Dry' },
        @{ round = 15; name = 'Austria'; date = '2026-09-20'; weather = 'Dry' },
        @{ round = 16; name = 'Japan'; date = '2026-10-04'; weather = 'Dry' },
        @{ round = 17; name = 'Indonesia'; date = '2026-10-11' },
        @{ round = 18; name = 'Australia'; date = '2026-10-25' },
        @{ round = 19; name = 'Malaysia'; date = '2026-11-01' },
        @{ round = 20; name = 'Qatar'; date = '2026-11-08' },
        @{ round = 21; name = 'Portugal'; date = '2026-11-22' },
        @{ round = 22; name = 'Valencia'; date = '2026-11-29' }
    );
    moto2 = @(
        @{ round = 1; name = 'Thailand'; date = '2026-03-01' },
        @{ round = 2; name = 'Brazil'; date = '2026-03-22' },
        @{ round = 3; name = 'USA'; date = '2026-03-29' },
        @{ round = 4; name = 'Spain'; date = '2026-04-26' },
        @{ round = 5; name = 'France'; date = '2026-05-10' },
        @{ round = 6; name = 'Catalonia'; date = '2026-05-17' },
        @{ round = 7; name = 'Italy'; date = '2026-05-31' },
        @{ round = 8; name = 'Hungary'; date = '2026-06-07' },
        @{ round = 9; name = 'Czechia'; date = '2026-06-21' },
        @{ round = 10; name = 'Netherlands'; date = '2026-06-28' },
        @{ round = 11; name = 'Germany'; date = '2026-07-12' },
        @{ round = 12; name = 'Great Britain'; date = '2026-08-09' },
        @{ round = 13; name = 'Aragon'; date = '2026-08-30' },
        @{ round = 14; name = 'San Marino'; date = '2026-09-13' },
        @{ round = 15; name = 'Austria'; date = '2026-09-20' },
        @{ round = 16; name = 'Japan'; date = '2026-10-04' },
        @{ round = 17; name = 'Indonesia'; date = '2026-10-11' },
        @{ round = 18; name = 'Australia'; date = '2026-10-25' },
        @{ round = 19; name = 'Malaysia'; date = '2026-11-01' },
        @{ round = 20; name = 'Qatar'; date = '2026-11-08' },
        @{ round = 21; name = 'Portugal'; date = '2026-11-22' },
        @{ round = 22; name = 'Valencia'; date = '2026-11-29' }
    );
    moto3 = @(
        @{ round = 1; name = 'Thailand'; date = '2026-03-01' },
        @{ round = 2; name = 'Brazil'; date = '2026-03-22' },
        @{ round = 3; name = 'USA'; date = '2026-03-29' },
        @{ round = 4; name = 'Spain'; date = '2026-04-26' },
        @{ round = 5; name = 'France'; date = '2026-05-10' },
        @{ round = 6; name = 'Catalonia'; date = '2026-05-17' },
        @{ round = 7; name = 'Italy'; date = '2026-05-31' },
        @{ round = 8; name = 'Hungary'; date = '2026-06-07' },
        @{ round = 9; name = 'Czechia'; date = '2026-06-21' },
        @{ round = 10; name = 'Netherlands'; date = '2026-06-28' },
        @{ round = 11; name = 'Germany'; date = '2026-07-12' },
        @{ round = 12; name = 'Great Britain'; date = '2026-08-09' },
        @{ round = 13; name = 'Aragon'; date = '2026-08-30' },
        @{ round = 14; name = 'San Marino'; date = '2026-09-13' },
        @{ round = 15; name = 'Austria'; date = '2026-09-20' },
        @{ round = 16; name = 'Japan'; date = '2026-10-04' },
        @{ round = 17; name = 'Indonesia'; date = '2026-10-11' },
        @{ round = 18; name = 'Australia'; date = '2026-10-25' },
        @{ round = 19; name = 'Malaysia'; date = '2026-11-01' },
        @{ round = 20; name = 'Qatar'; date = '2026-11-08' },
        @{ round = 21; name = 'Portugal'; date = '2026-11-22' },
        @{ round = 22; name = 'Valencia'; date = '2026-11-29' }
    );
    sbk = @(
        @{ round = 1; name = 'Australia'; date = '2026-02-22' },
        @{ round = 2; name = 'Portugal'; date = '2026-03-29' },
        @{ round = 3; name = 'Netherlands'; date = '2026-04-19' },
        @{ round = 4; name = 'Hungary'; date = '2026-05-03' },
        @{ round = 5; name = 'Most'; date = '2026-05-17' },
        @{ round = 6; name = 'Aragon'; date = '2026-05-31' },
        @{ round = 7; name = 'Misano'; date = '2026-06-14' },
        @{ round = 8; name = 'Donington'; date = '2026-07-12' },
        @{ round = 9; name = 'Magny-Cours'; date = '2026-09-27' },
        @{ round = 10; name = 'Cremona'; date = '2026-10-11' },
        @{ round = 11; name = 'Estoril'; date = '2026-10-18' },
        @{ round = 12; name = 'Jerez'; date = '2026-10-18' }
    );
    mxgp = @(
        @{ round = 1; name = 'Argentina'; date = '2026-03-08' },
        @{ round = 2; name = 'Andalucia'; date = '2026-03-22' },
        @{ round = 3; name = 'Switzerland'; date = '2026-03-29' },
        @{ round = 4; name = 'Sardegna'; date = '2026-04-12' },
        @{ round = 5; name = 'Trentino'; date = '2026-04-19' },
        @{ round = 6; name = 'France'; date = '2026-05-24' },
        @{ round = 7; name = 'Germany'; date = '2026-05-31' },
        @{ round = 8; name = 'Latvia'; date = '2026-06-07' },
        @{ round = 9; name = 'Italy'; date = '2026-06-21' },
        @{ round = 10; name = 'Portugal'; date = '2026-06-28' },
        @{ round = 11; name = 'South Africa'; date = '2026-07-05' },
        @{ round = 12; name = 'Great Britain'; date = '2026-07-19' },
        @{ round = 13; name = 'Czech Republic'; date = '2026-07-26' },
        @{ round = 14; name = 'Flanders'; date = '2026-08-02' },
        @{ round = 15; name = 'Sweden'; date = '2026-08-16' },
        @{ round = 16; name = 'Netherlands'; date = '2026-08-23' },
        @{ round = 17; name = 'Turkey'; date = '2026-09-06' }
    );
    mx2 = @(
        @{ round = 1; name = 'Argentina'; date = '2026-03-08' },
        @{ round = 2; name = 'Andalucia'; date = '2026-03-22' },
        @{ round = 3; name = 'Switzerland'; date = '2026-03-29' },
        @{ round = 4; name = 'Sardegna'; date = '2026-04-12' },
        @{ round = 5; name = 'Trentino'; date = '2026-04-19' },
        @{ round = 6; name = 'France'; date = '2026-05-24' },
        @{ round = 7; name = 'Germany'; date = '2026-05-31' },
        @{ round = 8; name = 'Latvia'; date = '2026-06-07' },
        @{ round = 9; name = 'Italy'; date = '2026-06-21' },
        @{ round = 10; name = 'Portugal'; date = '2026-06-28' },
        @{ round = 11; name = 'South Africa'; date = '2026-07-05' },
        @{ round = 12; name = 'Great Britain'; date = '2026-07-19' },
        @{ round = 13; name = 'Czech Republic'; date = '2026-07-26' },
        @{ round = 14; name = 'Flanders'; date = '2026-08-02' },
        @{ round = 15; name = 'Sweden'; date = '2026-08-16' },
        @{ round = 16; name = 'Netherlands'; date = '2026-08-23' },
        @{ round = 17; name = 'Turkey'; date = '2026-09-06' }
    );
    f1 = @(
        @{ round = 1; name = 'Australia'; date = '2026-03-08' },
        @{ round = 2; name = 'China'; date = '2026-03-15' },
        @{ round = 3; name = 'Japan'; date = '2026-03-29' },
        @{ round = 4; name = 'Bahrain'; date = '2026-04-12' },
        @{ round = 5; name = 'Saudi Arabia'; date = '2026-04-19' },
        @{ round = 6; name = 'Miami'; date = '2026-05-03' },
        @{ round = 7; name = 'Canada'; date = '2026-05-24' },
        @{ round = 8; name = 'Monaco'; date = '2026-06-07' },
        @{ round = 9; name = 'Spain'; date = '2026-06-14' },
        @{ round = 10; name = 'Austria'; date = '2026-06-28' },
        @{ round = 11; name = 'Great Britain'; date = '2026-07-05' },
        @{ round = 12; name = 'Belgium'; date = '2026-07-19' },
        @{ round = 13; name = 'Netherlands'; date = '2026-08-23' },
        @{ round = 14; name = 'Italy'; date = '2026-09-06' },
        @{ round = 15; name = 'Madrid'; date = '2026-09-13' },
        @{ round = 16; name = 'Azerbaijan'; date = '2026-09-20' },
        @{ round = 17; name = 'Singapore'; date = '2026-10-04' },
        @{ round = 18; name = 'Austin'; date = '2026-10-25' },
        @{ round = 19; name = 'Mexico'; date = '2026-11-01' },
        @{ round = 20; name = 'São Paulo'; date = '2026-11-08' },
        @{ round = 21; name = 'Las Vegas'; date = '2026-11-21' },
        @{ round = 22; name = 'Qatar'; date = '2026-11-29' },
        @{ round = 23; name = 'Abu Dhabi'; date = '2026-12-06' }
    )
}

# 3. Create data/<category>/2026.json
Write-Host "1. Writing category-specific JSON databases..."
foreach ($cat in $categories) {
    $catData = @{
        season = 2026
        category = $cat
        lastUpdated = $record._updated
        calendar = $CALENDARS_2026[$cat]
        riders = $record.$cat
        constructors = $record."$($cat)_constructors"
        teams = $record."$($cat)_teams"
    }
    $targetPath = Join-Path $dataDir "$cat\2026.json"
    $catData | ConvertTo-Json -Depth 6 | Set-Content -Path $targetPath -Encoding utf8
    Write-Host "   -> $cat/2026.json"
}

# 4. Generate CSVs
Write-Host "2. Generating Tidy CSVs for BI dashboards (Tableau/Grafana)..."

# A. Season Standings
$standingsRows = @()
foreach ($cat in $categories) {
    $riders = $record.$cat
    if ($riders) {
        $leaderPts = if ($riders.Count -gt 0) { $riders[0].pts } else { 0 }
        $rank = 1
        foreach ($r in $riders) {
            $gap = if ($rank -eq 1) { 0 } else { $leaderPts - $r.pts }
            $standingsRows += [PSCustomObject]@{
                Season = 2026
                Category = $cat.ToUpper()
                Rank = $rank
                Rider_Name = $r.name
                Total_Points = $r.pts
                Gap_To_Leader = $gap
                Sprint_Points = if ($r.sprint_pts) { $r.sprint_pts } else { "" }
                Main_Race_Points = if ($r.long_pts) { $r.long_pts } else { "" }
            }
            $rank++
        }
    }
}
$standingsCsvPath = Join-Path $csvDir "season_standings.csv"
$standingsRows | Export-Csv -Path $standingsCsvPath -NoTypeInformation -Encoding utf8
Write-Host "   -> season_standings.csv ($($standingsRows.Count) rows)"

# B. Calendars 2026 CSV
$calendarRows = @()
foreach ($cat in $categories) {
    $cal = $CALENDARS_2026[$cat]
    if ($cal) {
        foreach ($ev in $cal) {
            $calendarRows += [PSCustomObject]@{
                Season = 2026
                Category = $cat.ToUpper()
                Round_Number = $ev.round
                Event_Name = $ev.name
                Date = $ev.date
                Weather = if ($ev.weather) { $ev.weather } else { "TBD" }
            }
        }
    }
}
$calendarCsvPath = Join-Path $csvDir "calendar_events.csv"
$calendarRows | Export-Csv -Path $calendarCsvPath -NoTypeInformation -Encoding utf8
Write-Host "   -> calendar_events.csv ($($calendarRows.Count) rows)"

# C. Race Results Granular
$granularRows = @()
foreach ($cat in @('motogp', 'moto2', 'moto3')) {
    $riders = $record.$cat
    $cal = $CALENDARS_2026[$cat]
    if ($riders -and $riders.Count -gt 0 -and $riders[0].history) {
        $numRounds = $riders[0].history.Count
        for ($roundIdx = 0; $roundIdx -lt $numRounds; $roundIdx++) {
            $roundNum = $roundIdx + 1
            $evName = if ($cal -and $roundIdx -lt $cal.Count) { $cal[$roundIdx].name } else { "Round $roundNum" }
            $evDate = if ($cal -and $roundIdx -lt $cal.Count) { $cal[$roundIdx].date } else { "" }
            $evWeather = if ($cal -and $roundIdx -lt $cal.Count -and $cal[$roundIdx].weather) { $cal[$roundIdx].weather } else { "Dry" }

            $roundCumScores = @()
            foreach ($r in $riders) {
                $cum = 0
                for ($k = 0; $k -le $roundIdx; $k++) {
                    if ($k -lt $r.history.Count) { $cum += $r.history[$k] }
                }
                $roundCumScores += $cum
            }
            $roundLeaderCum = if ($roundCumScores.Count -gt 0) { ($roundCumScores | Measure-Object -Maximum).Maximum } else { 0 }

            foreach ($r in $riders) {
                $ptsEarned = if ($roundIdx -lt $r.history.Count) { $r.history[$roundIdx] } else { 0 }
                $sprPts = if ($r.sprint_history -and $roundIdx -lt $r.sprint_history.Count) { $r.sprint_history[$roundIdx] } else { 0 }
                $longPts = if ($r.long_history -and $roundIdx -lt $r.long_history.Count) { $r.long_history[$roundIdx] } else { $ptsEarned - $sprPts }

                $cumPts = 0
                for ($k = 0; $k -le $roundIdx; $k++) {
                    if ($k -lt $r.history.Count) { $cumPts += $r.history[$k] }
                }
                $gap = $roundLeaderCum - $cumPts

                $granularRows += [PSCustomObject]@{
                    Season = 2026
                    Category = $cat.ToUpper()
                    Round_Number = $roundNum
                    Event_Name = $evName
                    Date = $evDate
                    Rider_Name = $r.name
                    Sprint_Points = $sprPts
                    Main_Race_Points = $longPts
                    Points_Earned = $ptsEarned
                    Cumulative_Points = $cumPts
                    Gap_To_Leader = if ($gap -eq 0) { 0 } else { -$gap }
                    Is_Zero_Points = if ($ptsEarned -eq 0) { 1 } else { 0 }
                    Weather = $evWeather
                }
            }
        }
    }
}
$granularCsvPath = Join-Path $csvDir "race_results_points.csv"
$granularRows | Export-Csv -Path $granularCsvPath -NoTypeInformation -Encoding utf8
Write-Host "   -> race_results_points.csv ($($granularRows.Count) rows)"

# 5. Generate Master Excel if Excel COM is available
Write-Host "3. Generating Master Excel workbook..."
$xlsxPath = Join-Path $exportsDir "motorsport_database_2026.xlsx"
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false

    $masterWb = $excel.Workbooks.Add()
    $csvFiles = @(
        @{ Path = $standingsCsvPath; Name = "Season_Standings" },
        @{ Path = $granularCsvPath; Name = "Race_Results_Granular" },
        @{ Path = $calendarCsvPath; Name = "Calendars_2026" }
    )

    foreach ($item in $csvFiles) {
        if (Test-Path $item.Path) {
            $tempWb = $excel.Workbooks.Open($item.Path)
            $ws = $tempWb.Sheets.Item(1)
            $ws.Copy($masterWb.Sheets.Item(1))
            $copiedSheet = $masterWb.Sheets.Item(1)
            $copiedSheet.Name = $item.Name
            $copiedSheet.UsedRange.Columns.AutoFit() | Out-Null
            $tempWb.Close($false)
        }
    }

    $toDelete = @()
    foreach ($s in $masterWb.Sheets) {
        if ($s.Name -match '^Sheet\d+|^Foglio\d+') { $toDelete += $s }
    }
    foreach ($s in $toDelete) { try { $s.Delete() } catch {} }

    if (Test-Path $xlsxPath) { Remove-Item $xlsxPath -Force }
    $masterWb.SaveAs($xlsxPath, 51) # 51 = xlOpenXMLWorkbook (.xlsx)
    $masterWb.Close()
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    Write-Host "   -> motorsport_database_2026.xlsx created successfully! ($((Get-Item $xlsxPath).Length) bytes)"
} catch {
    Write-Warning "Excel COM not available or encountered an error: $_"
}

Write-Host "Database export completed successfully!"
