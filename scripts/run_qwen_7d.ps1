<#
  Corre el experimento unos pocos dias contra un Ollama remoto -p. ej. un Qwen en
  RunPod-, usando la API NATIVA de Ollama (/api/chat) con think:false.
  Es una corrida PARCIAL: deja un log incompleto (sin cuestionario ni veredicto).

  Por que la API nativa y no la /v1 (OpenAI): este Qwen es "thinking"; por /v1 el
  razonamiento va a un campo aparte y deja content vacio -> el motor no recibe
  accion. /api/chat acepta think:false y devuelve el JSON directo.

  Requisitos:
    - Un Ollama accesible con el modelo ya "pulled" (ollama pull <modelo>).
      En RunPod: Connect -> HTTP Service, puerto 11434.
    - Nada de pip: el cliente Ollama usa solo la stdlib.

  La URL base apunta a la raiz del server (sin /v1; si la pasas con /v1 se recorta).
  Se puede pasar por parametro o dejarla en .env como OLLAMA_BASE_URL / OPENAI_BASE_URL.

  Uso (desde la raiz del repo o desde cualquier lado):
    .\scripts\run_qwen_7d.ps1 -BaseUrl https://<POD-ID>-11434.proxy.runpod.net
    .\scripts\run_qwen_7d.ps1 -Dias 3     # si ya tienes la URL en .env
#>
param(
  [string]$BaseUrl = $(if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { $env:OPENAI_BASE_URL }),
  [string]$Modelo  = "hf.co/HauhauCS/Qwen3.6-27B-Uncensored-HauhauCS-Balanced:IQ4_XS",
  [int]$Dias       = 7
)

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

# Respaldo: si no vino por parametro ni por variable de entorno, leerla del .env.
if (-not $BaseUrl -and (Test-Path "$raiz\.env")) {
  $linea = Select-String -Path "$raiz\.env" -Pattern '^\s*(OLLAMA_BASE_URL|OPENAI_BASE_URL)\s*=' | Select-Object -First 1
  if ($linea) { $BaseUrl = ($linea.Line -replace '^\s*\w+\s*=\s*', '').Trim() }
}

if (-not $BaseUrl) {
  Write-Host "[The Last Million] Falta la URL de Ollama. Pasa -BaseUrl o define OLLAMA_BASE_URL/OPENAI_BASE_URL en .env." -ForegroundColor Red
  Write-Host "            Ej: .\scripts\run_qwen_7d.ps1 -BaseUrl https://<POD-ID>-11434.proxy.runpod.net" -ForegroundColor Red
  exit 1
}

# Normaliza: sin barra final ni sufijo /v1 (la API nativa cuelga de la raiz).
$BaseUrl = $BaseUrl.TrimEnd('/')
if ($BaseUrl -match '/v1$') { $BaseUrl = $BaseUrl.Substring(0, $BaseUrl.Length - 3).TrimEnd('/') }

# El OllamaClient lee la URL de esta variable de entorno.
$env:OLLAMA_BASE_URL = $BaseUrl
# Logs detallados: una linea por hora y una por llamada al LLM (con su duracion).
$env:TLM_VERBOSE = "1"

Write-Host "[The Last Million] Corriendo $Dias dia(s) con '$Modelo' (modo ollama) contra $BaseUrl ..." -ForegroundColor Cyan
python -m engine.run --llm ollama --modelo $Modelo --dias $Dias

if ($LASTEXITCODE -eq 0) {
  New-Item -ItemType Directory -Force -Path samples | Out-Null
  Copy-Item log.json "samples/log_qwen_${Dias}d.json" -Force
  Write-Host "[The Last Million] Listo. Log activo en log.json (+ visualizer/public/log.json)." -ForegroundColor Green
  Write-Host "[The Last Million] Copia guardada en samples/log_qwen_${Dias}d.json" -ForegroundColor Green
  Write-Host "[The Last Million] Recarga el visualizador (npm run dev) para verlo." -ForegroundColor Green
} else {
  Write-Host "[The Last Million] Fallo (codigo $LASTEXITCODE). Revisa que el llama-server responda en $BaseUrl y 'pip install -r requirements.txt'." -ForegroundColor Red
}
