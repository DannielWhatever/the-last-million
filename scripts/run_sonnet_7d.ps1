<#
  Corre el experimento unos pocos dias con un modelo intermedio (por defecto
  Claude Sonnet) para ver como se comporta antes de gastar en una corrida completa.
  Es una corrida PARCIAL: deja un log incompleto (sin cuestionario ni veredicto).

  Requisitos:
    - ANTHROPIC_API_KEY en .env (o variable de entorno).
    - pip install -r requirements.txt

  Uso (desde la raiz del repo o desde cualquier lado):
    .\scripts\run_sonnet_7d.ps1
    .\scripts\run_sonnet_7d.ps1 -Dias 3
    .\scripts\run_sonnet_7d.ps1 -Modelo claude-sonnet-4-6 -Dias 7
#>
param(
  [string]$Modelo = "claude-sonnet-4-6",
  [int]$Dias = 7
)

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host "[The Last Million] Corriendo $Dias dia(s) con $Modelo (modo real)..." -ForegroundColor Cyan
python -m engine.run --llm anthropic --modelo $Modelo --dias $Dias

if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force -Path samples | Out-Null
  Copy-Item log.json "samples/log_sonnet_${Dias}d.json" -Force
  Write-Host "[The Last Million] Listo. Log activo en log.json (+ visualizer/public/log.json)." -ForegroundColor Green
  Write-Host "[The Last Million] Copia guardada en samples/log_sonnet_${Dias}d.json" -ForegroundColor Green
  Write-Host "[The Last Million] Recarga el visualizador (npm run dev) para verlo." -ForegroundColor Green
} else {
  Write-Host "[The Last Million] Fallo (codigo $LASTEXITCODE). Revisa la API key (.env) y 'pip install -r requirements.txt'." -ForegroundColor Red
}
