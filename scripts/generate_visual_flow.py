# -*- coding: utf-8 -*-
"""
Gerador do Fluxograma Visual Arquitetural Explicativo em alta resolução (PNG)
para a migração do SharePoint para Google Workspace (Português e Inglês).
"""

import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path(r"C:\Users\Cleber\.gemini\antigravity\brain\4349b494-c0ce-4e02-8f40-71dee7388ad6")

HTML_FLOW_PT = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    background: #060911;
    color: #e2e8f0;
    padding: 30px;
    width: 1620px;
    margin: 0 auto;
  }

  /* Header */
  .header-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid #312e81;
    border-radius: 16px;
    padding: 22px 30px;
    margin-bottom: 25px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }
  .title-group h1 {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title-group p {
    font-size: 13px;
    color: #a5b4fc;
    margin-top: 5px;
  }
  .meta-badges {
    display: flex;
    gap: 10px;
  }
  .meta-tag {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
  }
  .meta-tag b { color: #38bdf8; }

  /* Section Title */
  .section-title {
    font-size: 14px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .section-title.current {
    background: rgba(14, 165, 233, 0.15);
    border: 1px solid #0284c7;
    color: #38bdf8;
  }
  .section-title.migration {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid #d97706;
    color: #fbbf24;
    margin-top: 30px;
  }

  /* Horizontal Pipeline Grid (5 Steps) */
  .pipeline-grid {
    display: grid;
    grid-template-columns: 290px 40px 290px 40px 320px 40px 270px 40px 270px;
    align-items: stretch;
    margin-bottom: 25px;
  }

  .step-connector {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    color: #6366f1;
    font-weight: 900;
  }

  .step-col {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 18px 16px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    position: relative;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
  }
  .step-num {
    background: #6366f1;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .step-header h3 {
    font-size: 13px;
    font-weight: 700;
    color: #f1f5f9;
  }

  /* Node Cards */
  .node-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .node-box:last-child { margin-bottom: 0; }

  .node-box.highlight {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #6366f1;
  }
  .node-box.critical {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #ef4444;
  }
  .node-box.sharepoint {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #0284c7;
  }
  .node-box.consumer {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #10b981;
  }

  .node-title {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .node-desc {
    font-size: 11px;
    color: #94a3b8;
    line-height: 1.45;
  }
  .node-desc b { color: #f8fafc; }
  .node-link {
    font-family: monospace;
    font-size: 10px;
    color: #38bdf8;
    background: #090d16;
    padding: 3px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 5px;
    border: 1px solid #1e293b;
    word-break: break-all;
  }

  .pill {
    padding: 2px 6px;
    font-size: 9px;
    font-weight: 700;
    border-radius: 4px;
    text-transform: uppercase;
  }
  .pill.blue { background: #0284c7; color: #fff; }
  .pill.red { background: #dc2626; color: #fff; }
  .pill.green { background: #059669; color: #fff; }
  .pill.purple { background: #7c3aed; color: #fff; }
  .pill.orange { background: #d97706; color: #fff; }

  /* Migration Bottom Questions Grid */
  .migration-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 16px;
  }

  .q-card {
    background: #0f172a;
    border: 1px solid #d97706;
    border-radius: 12px;
    padding: 16px;
    position: relative;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }
  .q-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .q-num {
    background: #f59e0b;
    color: #000;
    font-weight: 900;
    font-size: 11px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .q-title {
    font-size: 12px;
    font-weight: 800;
    color: #fbbf24;
  }
  .q-body {
    font-size: 11px;
    color: #cbd5e1;
    line-height: 1.5;
  }
  .q-body b { color: #ffffff; }

  /* Footer */
  .footer-bar {
    margin-top: 24px;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #94a3b8;
  }
  .footer-bar code { color: #38bdf8; }
</style>
</head>
<body>

<!-- Header -->
<div class="header-banner">
  <div class="title-group">
    <h1>
      <span>🗺️</span> FLUXO ARQUITETURAL VISUAL: SUPORTE CAPTAÇÃO
    </h1>
    <p>Mapeamento de Ponta a Ponta: Como Operamos Hoje no SharePoint e Pontos de Decisão para a Migração ao Google</p>
  </div>
  <div class="meta-badges">
    <div class="meta-tag">Portal: <b>adgbl.sharepoint.com/sites/suportecaptacao</b></div>
    <div class="meta-tag">Service Account: <b>svc.captacao@adgbl.com</b></div>
    <div class="meta-tag">Destinatário TI: <b>ahsan.ataur@fifty5blue.com</b></div>
  </div>
</div>

<!-- ETAPA 1: FLUXO OPERACIONAL ATUAL -->
<div class="section-title current">
  <span>🟦 PARTE 1: FLUXO DE OPERAÇÃO ATUAL (MICROSOFT 365 / SHAREPOINT)</span>
  <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">Sequência ponta a ponta: Entradas ➔ Autenticação ➔ Repositórios ➔ Automação ➔ Áreas Consumidoras</span>
</div>

<div class="pipeline-grid">

  <!-- COL 1: ENTRADAS -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">1</span>
      <h3>Origens & Entradas</h3>
    </div>

    <div class="node-box critical">
      <div class="node-title">
        <span>👨‍💻 Equipe Suporte Captação</span>
        <span class="pill red">Manual</span>
      </div>
      <div class="node-desc">
        A equipe monitora e insere os problemas técnicos, manutenções e quedas ocorridos nos <b>Capture Sites</b>.
      </div>
    </div>

    <div class="node-box highlight" style="margin-top: 10px;">
      <div class="node-title">
        <span>🤖 Ferramenta 'Reporte de Eventos'</span>
        <span class="pill green">Automático</span>
      </div>
      <div class="node-desc">
        Módulos em Python varrem grades esportivas (Streaming, CBF, NBA, YouTube) e geram laudos com prova visual.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 2: SEGURANÇA E AUTENTICAÇÃO -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">2</span>
      <h3>Identidade & Acesso</h3>
    </div>

    <div class="node-box highlight">
      <div class="node-title">
        <span>🔑 Service Principal (SPN)</span>
        <span class="pill purple">App-Only</span>
      </div>
      <div class="node-desc">
        App Registration no Azure AD. Conecta via <b>Microsoft Graph API</b> com Client ID e Secret. Não usa tela interativa.
      </div>
    </div>

    <div class="node-box">
      <div class="node-title">
        <span>👤 svc.captacao@adgbl.com</span>
        <span class="pill blue">Conta Serviço</span>
      </div>
      <div class="node-desc">
        Conta institucional dedicada para controle de permissões de gravação, alertas e disparos de e-mail.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 3: REPOSITÓRIOS SHAREPOINT -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">3</span>
      <h3>Repositórios SharePoint</h3>
    </div>

    <div class="node-box critical">
      <div class="node-title">
        <span>📋 Painel de Ocorrências</span>
        <span class="pill red">Coleta AG</span>
      </div>
      <div class="node-desc">
        Lista onde constam as ações e problemas dos <b>capture sites</b>.<br>
        <span class="node-link">Painel de Ocorrncias/EmandamentoLista.aspx</span>
      </div>
    </div>

    <div class="node-box sharepoint">
      <div class="node-title">
        <span>📅 Programação de Eventos</span>
        <span class="pill blue">Grade</span>
      </div>
      <div class="node-desc">
        Lista com as partidas e transmissões alimentada de forma 100% autônoma pelo software.
      </div>
    </div>

    <div class="node-box sharepoint">
      <div class="node-title">
        <span>📁 Bibliotecas de Documentos</span>
        <span class="pill purple">PDFs</span>
      </div>
      <div class="node-desc">
        Pastas de laudos oficiais: <i>Relatorios_de_Jogos</i>, <i>Relatorios_de_Jogos_NBA</i>, etc.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 4: POWER AUTOMATE -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">4</span>
      <h3>Fluxos Power Automate</h3>
    </div>

    <div class="node-box highlight" style="flex: 1; display: flex; flex-direction: column; justify-content: center;">
      <div class="node-title">
        <span>⚡ Automações & Gatilhos</span>
        <span class="pill orange">svc.captacao</span>
      </div>
      <div class="node-desc" style="margin-top: 8px;">
        Fluxos ativos criados na conta <b>svc.captacao@adgbl.com</b>.<br><br>
        • Monitoram modificações nas listas.<br>
        • Disparam notificações automáticas.<br>
        • Tratam status de incidentes e eventos.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 5: CONSUMIDORES -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">5</span>
      <h3>Áreas Consumidoras</h3>
    </div>

    <div class="node-box consumer">
      <div class="node-title">
        <span>📡 Áreas de Coleta AG</span>
        <span class="pill green">Tempo Real</span>
      </div>
      <div class="node-desc">
        Consultam diretamente o <b>Painel de Ocorrências</b> para atuar e corrigir falhas de captação.
      </div>
    </div>

    <div class="node-box consumer" style="margin-top: 10px;">
      <div class="node-title">
        <span>📊 Equipe da Audiência</span>
        <span class="pill blue">Diário</span>
      </div>
      <div class="node-desc">
        Consomem a <b>Programação de Eventos</b> e os <b>Laudos em PDF</b> para validar a transmissão dos canais.
      </div>
    </div>

    <div class="node-box consumer" style="margin-top: 10px;">
      <div class="node-title">
        <span>🏢 Outras Áreas da Empresa</span>
        <span class="pill purple">Auditoria</span>
      </div>
      <div class="node-desc">
        Acompanham a home do portal e histórico das transmissões.
      </div>
    </div>
  </div>

</div>

<!-- ETAPA 2: O QUE A EQUIPE DE TI PRECISA ORIENTAR NO GOOGLE -->
<div class="section-title migration">
  <span>🟧 PARTE 2: PONTOS CRÍTICOS DE TRANSIÇÃO — O QUE A EQUIPE DE TI (AHSAN) PRECISA DEFINIR NO GOOGLE</span>
  <span style="font-size: 11px; font-weight: normal; color: #fde68a;">Não impomos ferramentas: apresentamos o fluxo atual para que a TI determine o modelo oficial</span>
</div>

<div class="migration-grid">

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">1</span>
      <span class="q-title">Compartilhamento com Coleta AG</span>
    </div>
    <div class="q-body">
      <b>Origem Atual:</b> Lista <i>Painel de Ocorrências</i> compartilhada.<br><br>
      <b>Pergunta para TI:</b> Como ficará mantida esta lista de incidentes dos capture sites no Google e qual ferramenta será disponibilizada para que as <b>Áreas de Coleta AG</b> continuem consultando e interagindo em tempo real?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">2</span>
      <span class="q-title">Ingestão 'Reporte de Eventos'</span>
    </div>
    <div class="q-body">
      <b>Origem Atual:</b> Inserção via Microsoft Graph API em listas e bibliotecas.<br><br>
      <b>Pergunta para TI:</b> Qual ferramenta e API do ecossistema Google as nossas rotinas automáticas deverão alimentar para publicar as <b>grades de eventos</b> e arquivar os <b>laudos PDF</b>?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">3</span>
      <span class="q-title">Autenticação em Background (SPN)</span>
    </div>
    <div class="q-body">
      <b>Origem Atual:</b> Service Principal (SPN) sem intervenção humana.<br><br>
      <b>Pergunta para TI:</b> Como configuraremos a <b>Service Account</b> corporativa no Google Cloud para permitir que nossos scripts continuem gravando dados em segundo plano sem exigir login humano interativo?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">4</span>
      <span class="q-title">Migração do Power Automate</span>
    </div>
    <div class="q-body">
      <b>Origem Atual:</b> Fluxos rodando sob <code>svc.captacao@adgbl.com</code>.<br><br>
      <b>Pergunta para TI:</b> Como a equipe de TI planeja migrar ou reconstruir os fluxos e gatilhos automatizados de notificações existentes na conta institucional?
    </div>
  </div>

</div>

<!-- Footer -->
<div class="footer-bar">
  <div><b>Área Responsável:</b> Suporte Captação & Monitoramento de Esportes | <code>svc.captacao@adgbl.com</code></div>
  <div><b>Status:</b> Mapeamento Técnico de Dependências para Planejamento de Migração Corporativa (v2.0)</div>
</div>

</body>
</html>
"""

HTML_FLOW_EN = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    background: #060911;
    color: #e2e8f0;
    padding: 30px;
    width: 1620px;
    margin: 0 auto;
  }

  /* Header */
  .header-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid #312e81;
    border-radius: 16px;
    padding: 22px 30px;
    margin-bottom: 25px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }
  .title-group h1 {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title-group p {
    font-size: 13px;
    color: #a5b4fc;
    margin-top: 5px;
  }
  .meta-badges {
    display: flex;
    gap: 10px;
  }
  .meta-tag {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 11px;
    color: #cbd5e1;
  }
  .meta-tag b { color: #38bdf8; }

  /* Section Title */
  .section-title {
    font-size: 14px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .section-title.current {
    background: rgba(14, 165, 233, 0.15);
    border: 1px solid #0284c7;
    color: #38bdf8;
  }
  .section-title.migration {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid #d97706;
    color: #fbbf24;
    margin-top: 30px;
  }

  /* Horizontal Pipeline Grid (5 Steps) */
  .pipeline-grid {
    display: grid;
    grid-template-columns: 290px 40px 290px 40px 320px 40px 270px 40px 270px;
    align-items: stretch;
    margin-bottom: 25px;
  }

  .step-connector {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    color: #6366f1;
    font-weight: 900;
  }

  .step-col {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 18px 16px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    position: relative;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
  }
  .step-num {
    background: #6366f1;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .step-header h3 {
    font-size: 13px;
    font-weight: 700;
    color: #f1f5f9;
  }

  /* Node Cards */
  .node-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .node-box:last-child { margin-bottom: 0; }

  .node-box.highlight {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #6366f1;
  }
  .node-box.critical {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #ef4444;
  }
  .node-box.sharepoint {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #0284c7;
  }
  .node-box.consumer {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #10b981;
  }

  .node-title {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .node-desc {
    font-size: 11px;
    color: #94a3b8;
    line-height: 1.45;
  }
  .node-desc b { color: #f8fafc; }
  .node-link {
    font-family: monospace;
    font-size: 10px;
    color: #38bdf8;
    background: #090d16;
    padding: 3px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 5px;
    border: 1px solid #1e293b;
    word-break: break-all;
  }

  .pill {
    padding: 2px 6px;
    font-size: 9px;
    font-weight: 700;
    border-radius: 4px;
    text-transform: uppercase;
  }
  .pill.blue { background: #0284c7; color: #fff; }
  .pill.red { background: #dc2626; color: #fff; }
  .pill.green { background: #059669; color: #fff; }
  .pill.purple { background: #7c3aed; color: #fff; }
  .pill.orange { background: #d97706; color: #fff; }

  /* Migration Bottom Questions Grid */
  .migration-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 16px;
  }

  .q-card {
    background: #0f172a;
    border: 1px solid #d97706;
    border-radius: 12px;
    padding: 16px;
    position: relative;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }
  .q-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .q-num {
    background: #f59e0b;
    color: #000;
    font-weight: 900;
    font-size: 11px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .q-title {
    font-size: 12px;
    font-weight: 800;
    color: #fbbf24;
  }
  .q-body {
    font-size: 11px;
    color: #cbd5e1;
    line-height: 1.5;
  }
  .q-body b { color: #ffffff; }

  /* Footer */
  .footer-bar {
    margin-top: 24px;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #94a3b8;
  }
  .footer-bar code { color: #38bdf8; }
</style>
</head>
<body>

<!-- Header -->
<div class="header-banner">
  <div class="title-group">
    <h1>
      <span>🗺️</span> VISUAL ARCHITECTURE FLOW: CAPTURE SUPPORT
    </h1>
    <p>End-to-End Operational Pipeline: Current SharePoint Setup & Decision Boundaries for Google Migration</p>
  </div>
  <div class="meta-badges">
    <div class="meta-tag">Portal: <b>adgbl.sharepoint.com/sites/suportecaptacao</b></div>
    <div class="meta-tag">Service Account: <b>svc.captacao@adgbl.com</b></div>
    <div class="meta-tag">IT Lead: <b>ahsan.ataur@fifty5blue.com</b></div>
  </div>
</div>

<!-- SECTION 1: CURRENT OPERATIONAL FLOW -->
<div class="section-title current">
  <span>🟦 PART 1: CURRENT OPERATIONAL WORKFLOW (MICROSOFT 365 / SHAREPOINT)</span>
  <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">End-to-End Sequence: Ingestion ➔ Auth Layer ➔ Repositories ➔ Automation ➔ Consumer Teams</span>
</div>

<div class="pipeline-grid">

  <!-- COL 1: INGESTION -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">1</span>
      <h3>Data Sources & Ingestion</h3>
    </div>

    <div class="node-box critical">
      <div class="node-title">
        <span>👨‍💻 Capture Support Team</span>
        <span class="pill red">Manual</span>
      </div>
      <div class="node-desc">
        Team monitors and logs technical issues, maintenance, and outages across <b>Capture Sites</b>.
      </div>
    </div>

    <div class="node-box highlight" style="margin-top: 10px;">
      <div class="node-title">
        <span>🤖 'Sports Event Reporting' Tool</span>
        <span class="pill green">Automated</span>
      </div>
      <div class="node-desc">
        Python daemons continuously scanning sports broadcast grids (Streaming, CBF, NBA, YouTube) and generating visual proof reports.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 2: SECURITY & AUTH -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">2</span>
      <h3>Identity & Access</h3>
    </div>

    <div class="node-box highlight">
      <div class="node-title">
        <span>🔑 Service Principal (SPN)</span>
        <span class="pill purple">App-Only</span>
      </div>
      <div class="node-desc">
        Enterprise App Registration in Azure AD. Connects via <b>Microsoft Graph API</b> using Client ID & Secret. Zero interactive prompts.
      </div>
    </div>

    <div class="node-box">
      <div class="node-title">
        <span>👤 svc.captacao@adgbl.com</span>
        <span class="pill blue">Service Account</span>
      </div>
      <div class="node-desc">
        Dedicated institutional account for write permissions, email dispatches, and trigger monitoring.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 3: SHAREPOINT REPOSITORIES -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">3</span>
      <h3>SharePoint Repositories</h3>
    </div>

    <div class="node-box critical">
      <div class="node-title">
        <span>📋 Incident Panel</span>
        <span class="pill red">AG Collection</span>
      </div>
      <div class="node-desc">
        Shared list tracking actions and outages across <b>capture sites</b>.<br>
        <span class="node-link">Painel de Ocorrncias/EmandamentoLista.aspx</span>
      </div>
    </div>

    <div class="node-box sharepoint">
      <div class="node-title">
        <span>📅 Event Schedule List</span>
        <span class="pill blue">Grid</span>
      </div>
      <div class="node-desc">
        Consolidated sports broadcast schedule automatically populated by the software.
      </div>
    </div>

    <div class="node-box sharepoint">
      <div class="node-title">
        <span>📁 Document Libraries</span>
        <span class="pill purple">PDFs</span>
      </div>
      <div class="node-desc">
        Official audit report archives: <i>Relatorios_de_Jogos</i>, <i>Relatorios_de_Jogos_NBA</i>, etc.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 4: POWER AUTOMATE -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">4</span>
      <h3>Power Automate</h3>
    </div>

    <div class="node-box highlight" style="flex: 1; display: flex; flex-direction: column; justify-content: center;">
      <div class="node-title">
        <span>⚡ Workflows & Triggers</span>
        <span class="pill orange">svc.captacao</span>
      </div>
      <div class="node-desc" style="margin-top: 8px;">
        Active workflows operating under <b>svc.captacao@adgbl.com</b>.<br><br>
        • Monitors modifications in lists.<br>
        • Triggers automatic alert emails.<br>
        • Handles status changes on incidents.
      </div>
    </div>
  </div>

  <div class="step-connector">➔</div>

  <!-- COL 5: CONSUMER TEAMS -->
  <div class="step-col">
    <div class="step-header">
      <span class="step-num">5</span>
      <h3>Consumer Teams</h3>
    </div>

    <div class="node-box consumer">
      <div class="node-title">
        <span>📡 AG Collection Areas</span>
        <span class="pill green">Real-Time</span>
      </div>
      <div class="node-desc">
        Actively query the <b>Incident Panel</b> in real time to intervene and fix capture site issues.
      </div>
    </div>

    <div class="node-box consumer" style="margin-top: 10px;">
      <div class="node-title">
        <span>📊 Audience Team</span>
        <span class="pill blue">Daily</span>
      </div>
      <div class="node-desc">
        Consumes the <b>Event Schedule</b> and <b>PDF Audit Reports</b> daily for transmission compliance.
      </div>
    </div>

    <div class="node-box consumer" style="margin-top: 10px;">
      <div class="node-title">
        <span>🏢 Other Business Units</span>
        <span class="pill purple">Auditing</span>
      </div>
      <div class="node-desc">
        Monitor portal home and historical transmission logs.
      </div>
    </div>
  </div>

</div>

<!-- SECTION 2: WHAT IT NEEDS TO DEFINE IN GOOGLE -->
<div class="section-title migration">
  <span>🟧 PART 2: CRITICAL TRANSITION POINTS — WHAT IT (AHSAN) NEEDS TO DEFINE IN GOOGLE</span>
  <span style="font-size: 11px; font-weight: normal; color: #fde68a;">We do not prescribe tools: we show our current pipeline so IT can define the official target solution</span>
</div>

<div class="migration-grid">

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">1</span>
      <span class="q-title">Sharing with AG Collection</span>
    </div>
    <div class="q-body">
      <b>Current Setup:</b> Shared <i>Incident Panel</i> list.<br><br>
      <b>Question for IT:</b> How will this capture site incident list be maintained in Google, and what tool will be provided so <b>AG Collection Areas</b> continue querying and collaborating in real time?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">2</span>
      <span class="q-title">'Sports Event Reporting' Ingestion</span>
    </div>
    <div class="q-body">
      <b>Current Setup:</b> Ingestion via Microsoft Graph API into lists & document libraries.<br><br>
      <b>Question for IT:</b> What Google tool and API should our automated routines feed to publish <b>event schedule tables</b> and archive <b>PDF audit reports</b>?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">3</span>
      <span class="q-title">Background Authentication (SPN)</span>
    </div>
    <div class="q-body">
      <b>Current Setup:</b> Headless Service Principal (SPN) with zero human intervention.<br><br>
      <b>Question for IT:</b> How will the corporate <b>Service Account</b> in Google Cloud be provisioned so our scripts continue writing data in the background without interactive login?
    </div>
  </div>

  <div class="q-card">
    <div class="q-header">
      <span class="q-num">4</span>
      <span class="q-title">Power Automate Migration</span>
    </div>
    <div class="q-body">
      <b>Current Setup:</b> Automated flows running under <code>svc.captacao@adgbl.com</code>.<br><br>
      <b>Question for IT:</b> How does the IT team plan to migrate or rebuild the automated notification workflows and triggers currently operating under the institutional account?
    </div>
  </div>

</div>

<!-- Footer -->
<div class="footer-bar">
  <div><b>Responsible Team:</b> Capture Support & Sports Monitoring | <code>svc.captacao@adgbl.com</code></div>
  <div><b>Status:</b> Technical Dependency Mapping for Corporate Migration Planning (v2.0)</div>
</div>

</body>
</html>
"""

def render_html_to_png(html_content: str, output_path: Path):
    temp_html = output_path.with_suffix(".html")
    temp_html.write_text(html_content, encoding="utf-8")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--window-size=1680,1100")
    opts.add_argument("--force-device-scale-factor=2")  # 2x Retina resolution

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(f"file:///{temp_html.as_posix()}")
        time.sleep(1.5)
        height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(1680, height + 40)
        time.sleep(0.5)
        driver.save_screenshot(str(output_path))
        print(f"Fluxo visual gerado com sucesso: {output_path} ({output_path.stat().st_size} bytes)")
    finally:
        driver.quit()
        if temp_html.exists():
            try:
                temp_html.unlink()
            except Exception:
                pass

def main():
    print("Iniciando geração dos fluxogramas visuais explicativos...")
    import shutil

    # 1. Versão Português
    out_pt_ws = WORKSPACE_DIR / "fluxo_visual_migracao_sharepoint_google_pt.png"
    out_pt_art = ARTIFACT_DIR / "fluxo_visual_migracao_sharepoint_google_pt.png"
    render_html_to_png(HTML_FLOW_PT, out_pt_ws)
    shutil.copy2(out_pt_ws, out_pt_art)

    # 2. Versão Inglês
    out_en_ws = WORKSPACE_DIR / "visual_workflow_sharepoint_google_migration_en.png"
    out_en_art = ARTIFACT_DIR / "visual_workflow_sharepoint_google_migration_en.png"
    render_html_to_png(HTML_FLOW_EN, out_en_ws)
    shutil.copy2(out_en_ws, out_en_art)

    print("Todos os fluxos visuais foram gerados com sucesso!")

if __name__ == "__main__":
    main()
