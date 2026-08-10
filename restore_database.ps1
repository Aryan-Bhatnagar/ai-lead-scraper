<#
.SYNOPSIS
    Restores the AI Lead Scraper database from backup.

.DESCRIPTION
    This script restores the SQLite database (leads.db) from a backup file.
    It creates a backup of the current database before restoring.

.PARAMETER BackupFile
    Path to the backup database file (.db)

.PARAMETER TargetPath
    Path where the database should be restored (default: data/leads.db)

.PARAMETER Force
    Skip confirmation prompt

.EXAMPLE
    .\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db"

.EXAMPLE
    .\restore_database.ps1 -BackupFile "backups\leads_backup_20260810_161421.db" -TargetPath "data\leads.db" -Force
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    
    [string]$TargetPath = "data\leads.db",
    
    [switch]$Force
)

# Check if backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
    exit 1
}

# Check if target directory exists
$targetDir = Split-Path $TargetPath -Parent
if (-not (Test-Path $targetDir)) {
    Write-Error "Target directory does not exist: $targetDir"
    exit 1
}

# If target exists, create a backup of current database
if (Test-Path $TargetPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $currentBackup = "$targetDir\leads_before_restore_$timestamp.db"
    
    if (-not $Force) {
        $confirm = Read-Host "Target database exists. Backup current to $currentBackup and proceed? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Host "Restore cancelled."
            exit 0
        }
    }
    
    Write-Host "Backing up current database to: $currentBackup"
    Copy-Item $TargetPath $currentBackup -Force
}

# Restore the backup
Write-Host "Restoring database from: $BackupFile"
Write-Host "Target: $TargetPath"
Copy-Item $BackupFile $TargetPath -Force

# Verify restore
Write-Host "Verifying restore..."
$verifyScript = @"
import sqlite3
conn = sqlite3.connect('$TargetPath')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM leads')
leads = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM ai_insights')
insights = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM business_profiles')
profiles = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM enrichment_raw_data')
enrichment = cur.fetchone()[0]
print(f'Leads: {{leads}}')
print(f'AI Insights: {{insights}}')
print(f'Business Profiles: {{profiles}}')
print(f'Enrichment Raw Data: {{enrichment}}')
conn.close()
"@

python -c $verifyScript

Write-Host "Restore completed successfully!"
