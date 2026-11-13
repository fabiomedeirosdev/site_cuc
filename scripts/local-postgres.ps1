param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status',
    [string]$PostgresBin = ''
)

$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $workspacePath '.local\postgres'
$dataPath = Join-Path $statePath 'data'
$envPath = Join-Path $workspacePath 'backend\django_platform\.env'
$port = '55432'

if (-not $PostgresBin) {
    $installation = Get-ChildItem -LiteralPath 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'bin\pg_ctl.exe') } |
        Sort-Object { [int]$_.Name } -Descending | Select-Object -First 1
    if (-not $installation) { throw 'PostgreSQL nao encontrado. Informe -PostgresBin com o diretorio bin instalado.' }
    $PostgresBin = Join-Path $installation.FullName 'bin'
}
$pgCtl = Join-Path $PostgresBin 'pg_ctl.exe'

if ($Action -eq 'status') {
    if (-not (Test-Path -LiteralPath $dataPath)) { Write-Output 'Banco local ainda nao inicializado.'; exit 0 }
    & $pgCtl status -D $dataPath
    exit $LASTEXITCODE
}
if ($Action -eq 'stop') {
    if (-not (Test-Path -LiteralPath $dataPath)) { throw 'Banco local ainda nao inicializado.' }
    & $pgCtl stop -D $dataPath -m fast -w
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar o banco local.' }
    exit 0
}

New-Item -ItemType Directory -Path $statePath -Force | Out-Null
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath (Join-Path $dataPath 'PG_VERSION')) {
        throw 'Cluster existente sem .env. Restaure a configuracao local antes de iniciar.'
    }
    $localPassword = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $envLines = @(
        'DJANGO_DEBUG=1', 'DJANGO_SECRET_KEY=', 'DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost',
        'DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173',
        'POSTGRES_DB=cuc_local', 'POSTGRES_USER=cuc_dev', "POSTGRES_PASSWORD=$localPassword",
        'POSTGRES_HOST=127.0.0.1', "POSTGRES_PORT=$port"
    )
    [IO.File]::WriteAllLines($envPath, $envLines)
}
$localConfig = ConvertFrom-StringData ([IO.File]::ReadAllText($envPath))
if ($localConfig.POSTGRES_HOST -ne '127.0.0.1' -or $localConfig.POSTGRES_PORT -ne $port -or
    $localConfig.POSTGRES_DB -ne 'cuc_local' -or $localConfig.POSTGRES_USER -ne 'cuc_dev' -or
    -not $localConfig.POSTGRES_PASSWORD) {
    throw 'O .env existente nao corresponde ao banco isolado. Nenhum valor foi sobrescrito.'
}
if (-not (Test-Path -LiteralPath (Join-Path $dataPath 'PG_VERSION'))) {
    $passwordPath = Join-Path $statePath 'init-password.tmp'
    try {
        [IO.File]::WriteAllText($passwordPath, $localConfig.POSTGRES_PASSWORD)
        & (Join-Path $PostgresBin 'initdb.exe') -D $dataPath -U cuc_dev -A scram-sha-256 --encoding=UTF8 --locale=C --pwfile=$passwordPath
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao inicializar o PostgreSQL local.' }
    } finally {
        if (Test-Path -LiteralPath $passwordPath) { Remove-Item -LiteralPath $passwordPath }
    }
}
& $pgCtl status -D $dataPath *> $null
if ($LASTEXITCODE -ne 0) {
    if (Test-Path -LiteralPath (Join-Path $dataPath 'postmaster.pid')) {
        throw 'Existe um arquivo de processo, mas o estado nao pode ser confirmado. Verifique as permissoes e o status antes de iniciar outra instancia.'
    }
    & $pgCtl start -D $dataPath -l (Join-Path $statePath 'server.log') -o "-h 127.0.0.1 -p $port" -w
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o banco isolado. Consulte .local/postgres/server.log.' }
}
$previousPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $localConfig.POSTGRES_PASSWORD
    $exists = & (Join-Path $PostgresBin 'psql.exe') -X -w -h 127.0.0.1 -p $port -U cuc_dev -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = 'cuc_local'"
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar o banco local.' }
    if ($exists -ne '1') {
        & (Join-Path $PostgresBin 'createdb.exe') -w -h 127.0.0.1 -p $port -U cuc_dev -O cuc_dev cuc_local
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar cuc_local.' }
    }
} finally { $env:PGPASSWORD = $previousPassword }
Write-Output 'PostgreSQL local pronto em 127.0.0.1:55432 (cuc_local).'
