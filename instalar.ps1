# Instala tudo que o projeto precisa num computador Windows novo.
# Uso (dentro da pasta do projeto):  powershell -ExecutionPolicy Bypass -File instalar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Tem($cmd) { $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue) }

# 1. Python 3.12 (o "python" da Loja do Windows nao serve)
$pyExe = $null; $pyArgs = @()
if (Tem "py") { try { & py -3.12 --version *> $null; if ($LASTEXITCODE -eq 0) { $pyExe = "py"; $pyArgs = @("-3.12") } } catch {} }
if (-not $pyExe) {
    $local = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (-not (Test-Path $local)) {
        Write-Host "Instalando Python 3.12..."
        winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
    }
    $pyExe = $local
}

# 2. ffmpeg
$ffLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ffmpeg.exe"
if (-not (Tem "ffmpeg") -and -not (Test-Path $ffLink)) {
    Write-Host "Instalando ffmpeg..."
    winget install -e --id Gyan.FFmpeg.Essentials --accept-source-agreements --accept-package-agreements
}

# 3. Ambiente Python do projeto (.venv) e bibliotecas
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Criando o ambiente .venv..."
    & $pyExe @pyArgs -m venv .venv
}
$venv = ".venv\Scripts\python.exe"
& $venv -m pip install --upgrade pip
$nvidia = $null -ne (Get-Command nvidia-smi -ErrorAction SilentlyContinue)
if ($nvidia) {
    & $venv -m pip install -r requirements-travado.txt
} else {
    Write-Host "Sem placa NVIDIA: instalando sem as bibliotecas CUDA (a transcricao roda na CPU)."
    Get-Content requirements-travado.txt | Where-Object { $_ -notmatch "^nvidia-" } | Set-Content -Encoding utf8 "$env:TEMP\req_cpu.txt"
    & $venv -m pip install -r "$env:TEMP\req_cpu.txt"
}

# 4. Modelos pequenos (os de transcricao baixam sozinhos no primeiro uso)
New-Item -ItemType Directory -Force "modelos\modnet" | Out-Null
$modelos = @(
    @{ arq = "modelos\face_detection_yunet_2023mar.onnx"; url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" },
    @{ arq = "modelos\modnet\modnet.onnx"; url = "https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx" }
)
foreach ($m in $modelos) {
    if (-not (Test-Path $m.arq)) {
        Write-Host "Baixando $($m.arq)..."
        Invoke-WebRequest -Uri $m.url -OutFile $m.arq -UseBasicParsing
    }
}

New-Item -ItemType Directory -Force "Bruto", "trabalhos" | Out-Null
Write-Host "`nPronto. Agora rode:  .venv\Scripts\python testar_ambiente.py"
