param([int]$Port = 4173)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Aster Performance Lab: http://localhost:$Port/Demo/"
python -m http.server $Port --directory $ProjectRoot
