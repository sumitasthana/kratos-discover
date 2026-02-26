# Sync outputs from the main outputs folder to dashboard/public/outputs
# Run this script to update the dashboard with latest extraction results

$sourceDir = "..\outputs"
$targetDir = ".\public\outputs"
$manifestPath = ".\public\outputs-manifest.json"

# Create target directory if it doesn't exist
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# Copy all requirements JSON files
$files = Get-ChildItem -Path $sourceDir -Filter "requirements_*.json" | Sort-Object LastWriteTime -Descending

Write-Host "Found $($files.Count) output files"

# Build manifest
$manifest = @{
    files = @()
}

foreach ($file in $files) {
    # Copy file
    Copy-Item -Path $file.FullName -Destination $targetDir -Force
    Write-Host "Copied: $($file.Name)"
    
    # Parse filename for label
    # Format: requirements_FDIC_Part370_IT_Controls_Enriched_330_20260223_170219_1b9e96d0.json
    $name = $file.BaseName
    $parts = $name -split "_"
    
    # Extract timestamp from filename (format: YYYYMMDD_HHMMSS)
    $dateStr = $parts[-3]
    $timeStr = $parts[-2]
    
    if ($dateStr -match "^\d{8}$" -and $timeStr -match "^\d{6}$") {
        $year = $dateStr.Substring(0, 4)
        $month = $dateStr.Substring(4, 2)
        $day = $dateStr.Substring(6, 2)
        $hour = $timeStr.Substring(0, 2)
        $minute = $timeStr.Substring(2, 2)
        
        $timestamp = "$year-$month-${day}T$hour`:$minute`:00"
        $label = ($parts[1..($parts.Length - 4)] -join " ") + " - $year-$month-$day $hour`:$minute"
    } else {
        $timestamp = $file.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ss")
        $label = $name
    }
    
    $manifest.files += @{
        filename = $file.Name
        label = $label
        timestamp = $timestamp
    }
}

# Write manifest
$manifest | ConvertTo-Json -Depth 3 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "`nManifest updated with $($manifest.files.Count) files"
Write-Host "Dashboard ready - run 'npm run dev' to start"
