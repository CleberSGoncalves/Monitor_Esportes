<#
.SYNOPSIS
    Guia de Integração e Módulo PowerShell para Manipulação de Ocorrências e Listas no NOVO Portal Google.
    Destinado a: Cássio Esteves e Vinícius Dias (Suporte Captação - IBOPE)

.DESCRIPTION
    100% Desconectado do SharePoint / Microsoft.
    Comunica-se exclusivamente com a API REST nativa do Google (Google Apps Script Web App / Google Sheets API).
    Permite criar, consultar e atualizar ocorrências no Painel de Ocorrências e na Programação de Streaming.

.NOTES
    Para obter a URL da API Web do Portal Google:
    1. Abra a planilha do Google de 'Suporte Captação'.
    2. Acesse Extensões > Apps Script.
    3. Clique em 'Implantar' > 'Gerenciar implantações' e copie a URL do Web App (termina em /exec).
#>

[CmdletBinding()]
param()

# URL base do Web App Google (definida na implantação do Google Apps Script)
$script:GoogleApiEndpoint = "https://script.google.com/macros/s/AKfycbx_SEU_DEPLOYMENT_ID/exec"

function Get-GoogleOcorrencias {
    <#
    .SYNOPSIS
        Consulta ocorrências no novo Painel de Ocorrências do Google Portal.
    .EXAMPLE
        Get-GoogleOcorrencias -Status "Em andamento"
    #>
    param(
        [string]$Status = "",
        [string]$HostNome = "",
        [string]$Endpoint = $script:GoogleApiEndpoint
    )

    $url = "$Endpoint`?resource=ocorrencias"
    if (-not [string]::IsNullOrWhiteSpace($Status)) {
        $url += "&status=" + [System.Uri]::EscapeDataString($Status)
    }
    if (-not [string]::IsNullOrWhiteSpace($HostNome)) {
        $url += "&host=" + [System.Uri]::EscapeDataString($HostNome)
    }

    Write-Host "[API GOOGLE] Consultando ocorrências em: $url" -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -ContentType "application/json; charset=utf-8"
        return $response
    } catch {
        Write-Error "Falha ao consultar API Google: $_"
        return $null
    }
}

function New-GoogleOcorrencia {
    <#
    .SYNOPSIS
        Cria uma nova ocorrência no Painel de Ocorrências do Portal Google.
    .EXAMPLE
        New-GoogleOcorrencia -Host "Montes Claros / BRMG-MCL-TDT" -CS "01, 02" -Veiculo "SBT" -Equipamento "ATRIA" -TipoProblema "Sem sinal" -Acoes "Reiniciado decoder remotamente."
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Host,

        [Parameter(Mandatory=$true)]
        [string]$CS = "01",

        [Parameter(Mandatory=$true)]
        [string]$Veiculo = "Todos",

        [Parameter(Mandatory=$true)]
        [string]$Equipamento = "ATRIA",

        [Parameter(Mandatory=$true)]
        [string]$TipoProblema = "Sem sinal",

        [string]$Acoes = "Em análise pela equipe de Captação",
        [string]$Status = "Em andamento",
        [string]$AreaResponsavel = "N1",
        [string]$Redmine = "",
        [string]$Endpoint = $script:GoogleApiEndpoint
    )

    $payload = @{
        "resource"         = "ocorrencias"
        "action"           = "insert"
        "item"             = @{
            "Status"           = $Status
            "Host"             = $Host
            "CS"               = $CS
            "Veiculo"          = $Veiculo
            "Equipamento"      = $Equipamento
            "TipoProblema"     = $TipoProblema
            "EmRecuperacao"    = "Não"
            "GravacaoStreaming"= "Não"
            "InformarOperacao" = $true
            "AcoesExecutadas"  = $Acoes
            "AreaResponsavel"  = $AreaResponsavel
            "Redmine"          = $Redmine
            "Criado"           = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
    }

    $jsonBody = $payload | ConvertTo-Json -Depth 5
    Write-Host "[API GOOGLE] Enviando nova ocorrência para o Portal..." -ForegroundColor Cyan

    try {
        $response = Invoke-RestMethod -Uri $Endpoint -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($jsonBody))
        Write-Host "✅ Ocorrência registrada com sucesso no Google! ID retornado: $($response.id)" -ForegroundColor Green
        return $response
    } catch {
        Write-Error "❌ Falha ao registrar ocorrência na API Google: $_"
        return $null
    }
}

function Update-GoogleOcorrencia {
    <#
    .SYNOPSIS
        Atualiza o status ou ações de uma ocorrência existente no Portal Google.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Id,

        [string]$NovoStatus = "Concluído",
        [string]$NovasAcoes = "Normalizado após intervenção técnica.",
        [string]$Endpoint = $script:GoogleApiEndpoint
    )

    $payload = @{
        "resource" = "ocorrencias"
        "action"   = "update"
        "id"       = $Id
        "item"     = @{
            "Status"          = $NovoStatus
            "AcoesExecutadas" = $NovasAcoes
            "Modificado"      = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
    }

    $jsonBody = $payload | ConvertTo-Json -Depth 5
    Write-Host "[API GOOGLE] Atualizando ocorrência ID $Id..." -ForegroundColor Cyan

    try {
        $response = Invoke-RestMethod -Uri $Endpoint -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($jsonBody))
        Write-Host "✅ Ocorrência ID $Id atualizada com sucesso!" -ForegroundColor Green
        return $response
    } catch {
        Write-Error "❌ Falha ao atualizar ocorrência: $_"
        return $null
    }
}

# Exemplos de uso interativo (descomente para testar quando tiver a URL do Web App implantada):
<#
# 1. Consultar ocorrências abertas
$abertas = Get-GoogleOcorrencias -Status "Em andamento"
$abertas | Format-Table id, Host, TipoProblema, Status

# 2. Inserir ocorrência
New-GoogleOcorrencia -Host "Taubaté / BRSP-TTE-TDT" -CS "02" -Veiculo "GLOBO" -TipoProblema "Não está gravando" -Acoes "Verificado firewall do canal."

# 3. Concluir ocorrência
Update-GoogleOcorrencia -Id "15450" -NovoStatus "Concluído" -NovasAcoes "Decoder reiniciado, sinal restabelecido."
#>
