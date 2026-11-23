<#
.SYNOPSIS
    Script PowerShell para envio automático da Agenda de Transmissões (Hoje e Amanhã) para o Google Chat.
    Espaço: 'Streaming - Gravações' (Suporte Captação LATAM)

.DESCRIPTION
    Substitui o antigo fluxo do Power Automate / Teams.
    Pode ser executado localmente, disparado por tarefas agendadas (Task Scheduler) ou integrado em rotinas de esteira.
    Conecta-se à API REST do Google Apps Script / Portal Google ou lê a base de eventos.

.PARAMETER WebhookUrl
    URL do Webhook do Google Chat gerado no espaço 'Streaming - Gravações'.
    Exemplo: https://chat.googleapis.com/v1/spaces/XXXXX/messages?key=AIzaSy...&token=...

.PARAMETER DataBase
    Data base para pesquisa no formato DD/MM/YYYY. Se omitido, utiliza a data de hoje.

.EXAMPLE
    .\enviar_agenda_google_chat.ps1 -WebhookUrl "https://chat.googleapis.com/v1/spaces/AAA/messages?key=BBB&token=CCC"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$WebhookUrl = "",

    [Parameter(Mandatory=$false)]
    [string]$DataBase = ""
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Carregar Webhook padrão de config se não informado
if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $cfgPath = Join-Path (Split-Path -Parent $scriptDir) "config\google_chat_webhook.json"
    if (Test-Path $cfgPath) {
        try {
            $cfgJson = Get-Content -Path $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $WebhookUrl = $cfgJson.streaming_webhook_url
        } catch {}
    }
}

# Determinar datas de Hoje e Amanhã
if ([string]::IsNullOrWhiteSpace($DataBase)) {
    $dtHoje = Get-Date
} else {
    $dtHoje = [DateTime]::ParseExact($DataBase, "dd/MM/yyyy", [System.Globalization.CultureInfo]::InvariantCulture)
}
$dtAmanha = $dtHoje.AddDays(1)

$hojeStr = $dtHoje.ToString("dd/MM/yyyy")
$amanhaStr = $dtAmanha.ToString("dd/MM/yyyy")

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "📢 AGENDA DE TRANSMISSÕES - GOOGLE CHAT (STREAMING)" -ForegroundColor Cyan
Write-Host "Data Base (Hoje):   $hojeStr" -ForegroundColor Yellow
Write-Host "Data Base (Amanhã): $amanhaStr" -ForegroundColor Yellow
Write-Host "=========================================================="

# Carregar eventos (da API do Portal Google ou cache local)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localJson = Join-Path (Split-Path -Parent $scriptDir) "config\sharepoint_clean_migrated_events.json"

if (Test-Path $localJson) {
    $raw = Get-Content -Path $localJson -Raw -Encoding UTF8
    $allEvents = $raw | ConvertFrom-Json
} else {
    Write-Warning "Arquivo de eventos não encontrado localmente."
    $allEvents = @()
}

$jogosHoje = @()
$jogosAmanha = @()

foreach ($ev in $allEvents) {
    $dataEv = [string]$ev.data
    if ($dataEv -eq $hojeStr) {
        $jogosHoje += [PSCustomObject]@{
            Partida     = $ev.partida
            Horario     = $ev.horario
            Responsavel = if ($ev.responsavel) { $ev.responsavel } else { "Marcos BL01 e Backup" }
            Pvid        = if ($ev.pvid) { $ev.pvid } else { "$($ev.canal) - TV BOX" }
            Canal       = $ev.canal
        }
    } elseif ($dataEv -eq $amanhaStr) {
        $jogosAmanha += [PSCustomObject]@{
            Partida     = $ev.partida
            Horario     = $ev.horario
            Responsavel = if ($ev.responsavel) { $ev.responsavel } else { "Marcos BL01 e Backup" }
            Pvid        = if ($ev.pvid) { $ev.pvid } else { "$($ev.canal) - TV BOX" }
            Canal       = $ev.canal
        }
    }
}

Write-Host "Jogos para Hoje ($hojeStr): $($jogosHoje.Count)" -ForegroundColor Green
foreach ($j in $jogosHoje) {
    Write-Host "  • $($j.Horario) | $($j.Partida) | $($j.Responsavel) | $($j.Pvid)"
}

Write-Host "Jogos para Amanhã ($amanhaStr): $($jogosAmanha.Count)" -ForegroundColor Green
foreach ($j in $jogosAmanha) {
    Write-Host "  • $($j.Horario) | $($j.Partida) | $($j.Responsavel) | $($j.Pvid)"
}

# Construção dos Widgets para o Google Chat Cards v2
$widgetsHoje = @()
if ($jogosHoje.Count -eq 0) {
    $widgetsHoje += @{
        "decoratedText" = @{
            "text" = "<i>Nenhuma transmissão programada para hoje.</i>"
        }
    }
} else {
    foreach ($j in $jogosHoje) {
        $widgetsHoje += @{
            "decoratedText" = @{
                "topLabel"    = "$($j.Horario) • $($j.Responsavel)"
                "text"        = "<b>$($j.Partida)</b>"
                "bottomLabel" = "📺 $($j.Pvid)"
                "wrapText"    = $true
            }
        }
    }
}

$widgetsAmanha = @()
if ($jogosAmanha.Count -eq 0) {
    $widgetsAmanha += @{
        "decoratedText" = @{
            "text" = "<i>Nenhuma transmissão programada para amanhã.</i>"
        }
    }
} else {
    foreach ($j in $jogosAmanha) {
        $widgetsAmanha += @{
            "decoratedText" = @{
                "topLabel"    = "$($j.Horario) • $($j.Responsavel)"
                "text"        = "<b>$($j.Partida)</b>"
                "bottomLabel" = "📺 $($j.Pvid)"
                "wrapText"    = $true
            }
        }
    }
}

# Payload Oficial Google Chat Cards v2
$cardSections = @(
    @{
        "header"  = "Hoje - $hojeStr"
        "widgets" = $widgetsHoje
    },
    @{
        "header"  = "Amanhã - $amanhaStr"
        "widgets" = $widgetsAmanha
    }
)

$payload = @{
    "cardsV2" = @(
        @{
            "cardId" = "agenda-streaming-" + ($hojeStr -replace '/', '-')
            "card"   = @{
                "header" = @{
                    "title"     = "Agenda de Transmissões"
                    "subtitle"  = "Programação de jogos de hoje e amanhã"
                    "imageUrl"  = "https://fonts.gstatic.com/s/i/short-term/release/googlestyles/sports_soccer/default/48px.png"
                    "imageType" = "CIRCLE"
                }
                "sections" = $cardSections
            }
        }
    )
}

$jsonBody = $payload | ConvertTo-Json -Depth 10

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
    Write-Host "`n[MODO SIMULAÇÃO] Payload gerado com sucesso para o Google Chat:" -ForegroundColor Yellow
    Write-Host $jsonBody
    Write-Host "`nPara enviar de verdade, informe o parâmetro -WebhookUrl <URL>" -ForegroundColor Cyan
    return
}

# Disparo HTTP POST para o Google Chat
try {
    Write-Host "`nEnviando mensagem para o Google Chat..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($jsonBody))
    Write-Host "✅ Notificação enviada com sucesso para o grupo 'Streaming - Gravações'!" -ForegroundColor Green
} catch {
    Write-Error "❌ Falha ao enviar para o Google Chat: $_"
}
