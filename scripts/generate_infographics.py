# -*- coding: utf-8 -*-
"""
Gerador de infográficos visuais em alta resolução (PNG) para a comunicação
da migração do SharePoint para Google Workspace (Português e Inglês).
"""

import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path(r"C:\Users\Cleber\.gemini\antigravity\brain\4349b494-c0ce-4e02-8f40-71dee7388ad6")

HTML_TEMPLATE_PT = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    background: #090d16;
    color: #e2e8f0;
    padding: 35px;
    width: 1400px;
    margin: 0 auto;
  }
  .header-card {
    background: linear-gradient(135deg, #131d33 0%, #0d1527 100%);
    border: 1px solid #1e2d4d;
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 25px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  }
  .title-group h1 {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title-group p {
    font-size: 14px;
    color: #94a3b8;
    margin-top: 6px;
  }
  .badge-tag {
    display: inline-block;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    border-radius: 6px;
    background: #0284c7;
    color: #ffffff;
    vertical-align: middle;
  }
  .meta-pills {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
  }
  .meta-pill {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    color: #cbd5e1;
  }
  .meta-pill b { color: #38bdf8; }

  /* Grid Layout */
  .grid-container {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 25px;
  }

  .column-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  .col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 2px solid #1e293b;
    margin-bottom: 20px;
  }
  .col-header h2 {
    font-size: 18px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .col-header.current h2 { color: #38bdf8; }
  .col-header.target h2 { color: #f59e0b; }

  /* Sub-blocos */
  .section-label {
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #64748b;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .card-highlight {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #0284c7;
  }
  .card-critical {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #ef4444;
  }
  .card-question {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(30, 41, 59, 0.9) 100%);
    border: 1px solid #d97706;
    margin-bottom: 14px;
  }

  .card-title {
    font-size: 14px;
    font-weight: 700;
    color: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .card-desc {
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.5;
  }
  .card-desc b { color: #e2e8f0; }

  .tag-mini {
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
    border-radius: 4px;
    background: #334155;
    color: #f1f5f9;
  }
  .tag-mini.blue { background: #0284c7; }
  .tag-mini.green { background: #059669; }
  .tag-mini.orange { background: #d97706; }
  .tag-mini.red { background: #dc2626; }
  .tag-mini.purple { background: #7c3aed; }

  .url-text {
    font-family: monospace;
    font-size: 11px;
    color: #38bdf8;
    background: #090d16;
    padding: 3px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 4px;
    border: 1px solid #1e293b;
    word-break: break-all;
  }

  .flow-arrow {
    text-align: center;
    color: #64748b;
    font-size: 16px;
    margin: 4px 0 8px 0;
  }

  .stakeholders-box {
    background: #131d33;
    border: 1px solid #223558;
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 14px;
  }

  .stakeholder-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #1e293b;
    font-size: 12px;
    line-height: 1.4;
  }
  .stakeholder-item:first-child {
    border-top: none;
    margin-top: 4px;
    padding-top: 0;
  }
  .stakeholder-icon {
    font-size: 15px;
    flex-shrink: 0;
  }

  .question-badge {
    background: #f59e0b;
    color: #000;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 12px;
    margin-right: 8px;
  }

  .footer-note {
    margin-top: 25px;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 12px;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
</style>
</head>
<body>

<div class="header-card">
  <div class="title-group">
    <h1>
      <span>📊</span> Mapeamento de Arquitetura: Suporte Captação
      <span class="badge-tag">Migração M365 ➔ Google Workspace</span>
    </h1>
    <p>Operação atual no Microsoft SharePoint e pontos de alinhamento técnico para o novo ambiente</p>
  </div>
  <div class="meta-pills">
    <div class="meta-pill">Portal SharePoint: <b>adgbl.sharepoint.com/sites/suportecaptacao</b></div>
    <div class="meta-pill">Conta de Serviço: <b>svc.captacao@adgbl.com</b> (SPN Autônomo)</div>
    <div class="meta-pill">Destinatário Técnico: <b>ahsan.ataur@fifty5blue.com</b></div>
  </div>
</div>

<div class="grid-container">

  <!-- COLUNA 1: COMO OPERAMOS HOJE -->
  <div class="column-box">
    <div class="col-header current">
      <h2><span>🟦</span> 1. Como Operamos Hoje (Ambiente Microsoft 365)</h2>
      <span class="tag-mini blue">Arquitetura Ativa</span>
    </div>

    <!-- Origens -->
    <div class="section-label"><span>📥</span> Origens & Alimentação de Dados</div>
    
    <div class="card card-critical">
      <div class="card-title">
        <span>👨‍💻 Equipe Suporte Captação (Ocorrências Manuais)</span>
        <span class="tag-mini red">Crítico Operacional</span>
      </div>
      <div class="card-desc">
        A equipe registra diretamente as ações tomadas e problemas/quedas ocorridos nos <b>Capture Sites</b>.
      </div>
    </div>

    <div class="card card-highlight">
      <div class="card-title">
        <span>🤖 Ferramenta 'Reporte de Eventos Esportivos'</span>
        <span class="tag-mini green">Automação Contínua</span>
      </div>
      <div class="card-desc">
        Rotinas em segundo plano que varrem grades esportivas (Streaming, CBF, NBA, YouTube) e geram laudos com prova visual.
      </div>
    </div>

    <div class="flow-arrow">▼ Autenticação & Processamento ▼</div>

    <!-- Camada de Autenticação -->
    <div class="section-label"><span>🔐</span> Autenticação de Fundo & Regras de Negócio</div>
    <div class="card">
      <div class="card-title">
        <span>🔑 Service Principal (SPN) & App Registration</span>
        <span class="tag-mini purple">App-Only / Sem Login Humano</span>
      </div>
      <div class="card-desc">
        Comunicação direta via <b>Microsoft Graph API</b> utilizando Client ID e Secret corporativo.<br>
        Conta de Serviço: <b>svc.captacao@adgbl.com</b> para controle de permissões e envios.
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>⚡ Fluxos no Power Automate</span>
        <span class="tag-mini orange">Gatilhos Ativos</span>
      </div>
      <div class="card-desc">
        Automações configuradas sob a conta <b>svc.captacao@adgbl.com</b> que monitoram eventos nas listas, processam dados e disparam notificações.
      </div>
    </div>

    <div class="flow-arrow">▼ Armazenamento e Consulta no SharePoint ▼</div>

    <!-- Repositórios SharePoint -->
    <div class="section-label"><span>📁</span> Repositórios do Portal Suporte Captação</div>
    
    <div class="card card-critical">
      <div class="card-title">
        <span>📋 Lista: Painel de Ocorrências (Capture Sites)</span>
        <span class="tag-mini red">Compartilhamento AG</span>
      </div>
      <div class="card-desc">
        Acompanhamento de incidentes técnicos nos capture sites.<br>
        <span class="url-text">/Lists/Painel de Ocorrncias/EmandamentoLista.aspx</span>
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>📅 Lista: Programação de Eventos Esportivos</span>
        <span class="tag-mini blue">Grade Consolidada</span>
      </div>
      <div class="card-desc">
        Alimentada 100% de forma automatizada pelo nosso sistema com eventos de streaming e emissoras.
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>📚 Bibliotecas de Documentos (Relatórios de Jogos)</span>
        <span class="tag-mini purple">Armazenamento PDF</span>
      </div>
      <div class="card-desc">
        Guarda laudos oficiais com carimbo técnico e comprovação visual: <i>Relatorios_de_Jogos</i>, <i>Relatorios_de_Jogos_NBA</i>, etc.
      </div>
    </div>

    <!-- Áreas Consumidoras -->
    <div class="stakeholders-box">
      <div class="section-label" style="color: #38bdf8;"><span>👥</span> Interdependências & Consumidores das Informações</div>
      
      <div class="stakeholder-item">
        <div class="stakeholder-icon">📡</div>
        <div><b>Áreas de Coleta AG:</b> Consultam ativamente o <u>Painel de Ocorrências</u> em tempo real para tomada de ação nos capture sites.</div>
      </div>
      
      <div class="stakeholder-item">
        <div class="stakeholder-icon">📊</div>
        <div><b>Equipe da Audiência:</b> Consome diariamente a <u>Programação de Eventos</u> e os <u>Relatórios de Jogos</u> para auditoria de transmissão.</div>
      </div>

      <div class="stakeholder-item">
        <div class="stakeholder-icon">🏢</div>
        <div><b>Outras Áreas da Empresa:</b> Monitoram a estabilidade da captação e o histórico das grades pelo portal.</div>
      </div>
    </div>

  </div>

  <!-- COLUNA 2: TRANSIÇÃO E DÚVIDAS PARA O GOOGLE -->
  <div class="column-box">
    <div class="col-header target">
      <h2><span>🟧</span> 2. O que a Equipe de TI precisa Orientar</h2>
      <span class="tag-mini orange">Definições Pendentes</span>
    </div>

    <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 18px; line-height: 1.5;">
      Não temos preferências pré-definidas de ferramentas Google. Apresentamos nosso fluxo atual para que a <b>equipe de transição defina a arquitetura oficial</b> que devemos adotar:
    </p>

    <!-- Pergunta 1 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">1</span> Compartilhamento com Coleta AG</span>
        <span class="tag-mini red">Impacto Operacional</span>
      </div>
      <div class="card-desc">
        Como ficará mantida a lista do <b>Painel de Ocorrências</b> dos capture sites? Qual ferramenta do Google será disponibilizada para manter o compartilhamento e a consulta pelas <b>Áreas de Coleta AG</b>?
      </div>
    </div>

    <!-- Pergunta 2 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">2</span> Ingestão do 'Reporte de Eventos'</span>
        <span class="tag-mini green">Integração de Software</span>
      </div>
      <div class="card-desc">
        Qual ferramenta e API do ecossistema Google nossas rotinas automáticas deverão alimentar para manter atualizadas as <b>listas de programação</b> e o arquivamento dos <b>relatórios em PDF</b>?
      </div>
    </div>

    <!-- Pergunta 3 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">3</span> Autenticação em Background (SPN)</span>
        <span class="tag-mini purple">Segurança & Acesso</span>
      </div>
      <div class="card-desc">
        Como será configurada a <b>Service Account</b> corporativa no Google Cloud para substituir o atual Service Principal (SPN), permitindo que nossas rotinas publiquem dados em segundo plano sem login interativo?
      </div>
    </div>

    <!-- Pergunta 4 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">4</span> Migração do Power Automate</span>
        <span class="tag-mini orange">Gatilhos & Alertas</span>
      </div>
      <div class="card-desc">
        Como a equipe de TI planeja migrar os fluxos e gatilhos automatizados que hoje rodam sob a conta de serviço <b>svc.captacao@adgbl.com</b>?
      </div>
    </div>

    <div style="background: #1e293b; border-left: 4px solid #f59e0b; padding: 14px; border-radius: 6px; margin-top: 20px;">
      <div style="font-size: 12px; font-weight: 700; color: #f59e0b; margin-bottom: 4px;">🎯 Objetivo do Alinhamento:</div>
      <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
        Garantir antecedência técnica para adaptação do código e validação da segurança, assegurando <b>zero minutos de indisponibilidade</b> para a Equipe de Audiência e Áreas de Coleta.
      </div>
    </div>

  </div>

</div>

<div class="footer-note">
  <div><b>Área Responsável:</b> Suporte Captação & Monitoramento de Esportes | <code>svc.captacao@adgbl.com</code></div>
  <div><b>Documento Técnico:</b> Mapeamento de Dependências para Migração Corporativa (v1.0)</div>
</div>

</body>
</html>
"""

HTML_TEMPLATE_EN = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    background: #090d16;
    color: #e2e8f0;
    padding: 35px;
    width: 1400px;
    margin: 0 auto;
  }
  .header-card {
    background: linear-gradient(135deg, #131d33 0%, #0d1527 100%);
    border: 1px solid #1e2d4d;
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 25px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  }
  .title-group h1 {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title-group p {
    font-size: 14px;
    color: #94a3b8;
    margin-top: 6px;
  }
  .badge-tag {
    display: inline-block;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    border-radius: 6px;
    background: #0284c7;
    color: #ffffff;
    vertical-align: middle;
  }
  .meta-pills {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
  }
  .meta-pill {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    color: #cbd5e1;
  }
  .meta-pill b { color: #38bdf8; }

  /* Grid Layout */
  .grid-container {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 25px;
  }

  .column-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  .col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 2px solid #1e293b;
    margin-bottom: 20px;
  }
  .col-header h2 {
    font-size: 18px;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .col-header.current h2 { color: #38bdf8; }
  .col-header.target h2 { color: #f59e0b; }

  /* Sub-blocos */
  .section-label {
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #64748b;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .card-highlight {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #0284c7;
  }
  .card-critical {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid #ef4444;
  }
  .card-question {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(30, 41, 59, 0.9) 100%);
    border: 1px solid #d97706;
    margin-bottom: 14px;
  }

  .card-title {
    font-size: 14px;
    font-weight: 700;
    color: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .card-desc {
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.5;
  }
  .card-desc b { color: #e2e8f0; }

  .tag-mini {
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
    border-radius: 4px;
    background: #334155;
    color: #f1f5f9;
  }
  .tag-mini.blue { background: #0284c7; }
  .tag-mini.green { background: #059669; }
  .tag-mini.orange { background: #d97706; }
  .tag-mini.red { background: #dc2626; }
  .tag-mini.purple { background: #7c3aed; }

  .url-text {
    font-family: monospace;
    font-size: 11px;
    color: #38bdf8;
    background: #090d16;
    padding: 3px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 4px;
    border: 1px solid #1e293b;
    word-break: break-all;
  }

  .flow-arrow {
    text-align: center;
    color: #64748b;
    font-size: 16px;
    margin: 4px 0 8px 0;
  }

  .stakeholders-box {
    background: #131d33;
    border: 1px solid #223558;
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 14px;
  }

  .stakeholder-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #1e293b;
    font-size: 12px;
    line-height: 1.4;
  }
  .stakeholder-item:first-child {
    border-top: none;
    margin-top: 4px;
    padding-top: 0;
  }
  .stakeholder-icon {
    font-size: 15px;
    flex-shrink: 0;
  }

  .question-badge {
    background: #f59e0b;
    color: #000;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 12px;
    margin-right: 8px;
  }

  .footer-note {
    margin-top: 25px;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 12px;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
</style>
</head>
<body>

<div class="header-card">
  <div class="title-group">
    <h1>
      <span>📊</span> Architecture Mapping: Capture Support
      <span class="badge-tag">M365 ➔ Google Workspace Migration</span>
    </h1>
    <p>Current Microsoft SharePoint operating model and technical alignment topics for the target environment</p>
  </div>
  <div class="meta-pills">
    <div class="meta-pill">SharePoint Site: <b>adgbl.sharepoint.com/sites/suportecaptacao</b></div>
    <div class="meta-pill">Service Account: <b>svc.captacao@adgbl.com</b> (Autonomous SPN)</div>
    <div class="meta-pill">Technical Contact: <b>ahsan.ataur@fifty5blue.com</b></div>
  </div>
</div>

<div class="grid-container">

  <!-- COLUMN 1: HOW WE OPERATE TODAY -->
  <div class="column-box">
    <div class="col-header current">
      <h2><span>🟦</span> 1. How We Operate Today (Microsoft 365 / SharePoint)</h2>
      <span class="tag-mini blue">Active Architecture</span>
    </div>

    <!-- Data Ingestion -->
    <div class="section-label"><span>📥</span> Data Sources & Ingestion</div>
    
    <div class="card card-critical">
      <div class="card-title">
        <span>👨‍💻 Capture Support Team (Manual Incident Logging)</span>
        <span class="tag-mini red">Operationally Critical</span>
      </div>
      <div class="card-desc">
        Team logs real-time operational actions, outages, and issues occurring across <b>Capture Sites</b>.
      </div>
    </div>

    <div class="card card-highlight">
      <div class="card-title">
        <span>🤖 'Sports Event Reporting' Tool</span>
        <span class="tag-mini green">Continuous Automation</span>
      </div>
      <div class="card-desc">
        Automated background engines scanning sports broadcasts (Streaming, CBF, NBA, YouTube) and generating visual audit reports.
      </div>
    </div>

    <div class="flow-arrow">▼ Authentication & Automation Layer ▼</div>

    <!-- Authentication Layer -->
    <div class="section-label"><span>🔐</span> Background Auth & Business Workflows</div>
    <div class="card">
      <div class="card-title">
        <span>🔑 Service Principal (SPN) & App Registration</span>
        <span class="tag-mini purple">App-Only / Headless Execution</span>
      </div>
      <div class="card-desc">
        Direct ingestion via <b>Microsoft Graph API</b> using Client ID and Enterprise Secret.<br>
        Service Account: <b>svc.captacao@adgbl.com</b> for permissions, alerting, and dispatch.
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>⚡ Power Automate Workflows</span>
        <span class="tag-mini orange">Active Triggers</span>
      </div>
      <div class="card-desc">
        Automations running under <b>svc.captacao@adgbl.com</b> monitoring list modifications, processing schemas, and triggering alerts.
      </div>
    </div>

    <div class="flow-arrow">▼ SharePoint Repositories & Storage ▼</div>

    <!-- SharePoint Repositories -->
    <div class="section-label"><span>📁</span> Repositories on Capture Support Site</div>
    
    <div class="card card-critical">
      <div class="card-title">
        <span>📋 List: Incident Panel (Capture Sites Outages)</span>
        <span class="tag-mini red">AG Collection Sharing</span>
      </div>
      <div class="card-desc">
        Centralized log of technical incidents and resolutions across capture sites.<br>
        <span class="url-text">/Lists/Painel de Ocorrncias/EmandamentoLista.aspx</span>
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>📅 List: Sports Event Schedule</span>
        <span class="tag-mini blue">Consolidated Grid</span>
      </div>
      <div class="card-desc">
        100% automated schedule populated by our background system across multiple platforms.
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>📚 Document Libraries (Match Audit Reports)</span>
        <span class="tag-mini purple">PDF Storage</span>
      </div>
      <div class="card-desc">
        Stores formal audit reports with visual proof snapshots: <i>Relatorios_de_Jogos</i>, <i>Relatorios_de_Jogos_NBA</i>, etc.
      </div>
    </div>

    <!-- Stakeholders -->
    <div class="stakeholders-box">
      <div class="section-label" style="color: #38bdf8;"><span>👥</span> Cross-Departmental Interdependencies</div>
      
      <div class="stakeholder-item">
        <div class="stakeholder-icon">📡</div>
        <div><b>AG Collection Areas:</b> Actively query the <u>Incident Panel</u> in real time for capture site intervention and monitoring.</div>
      </div>
      
      <div class="stakeholder-item">
        <div class="stakeholder-icon">📊</div>
        <div><b>Audience Team:</b> Consumes the <u>Event Schedule</u> and <u>Audit Reports</u> daily for broadcasting compliance.</div>
      </div>

      <div class="stakeholder-item">
        <div class="stakeholder-icon">🏢</div>
        <div><b>Other Business Units:</b> Track operational stability and transmission logs through the portal.</div>
      </div>
    </div>

  </div>

  <!-- COLUMN 2: TRANSITION & QUESTIONS FOR GOOGLE -->
  <div class="column-box">
    <div class="col-header target">
      <h2><span>🟧</span> 2. What IT Needs to Guide Us On</h2>
      <span class="tag-mini orange">Pending Architecture Decisions</span>
    </div>

    <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 18px; line-height: 1.5;">
      We have no predefined preference regarding Google tools. We are detailing our current operation so that <b>your team can specify the official target architecture</b> we must implement:
    </p>

    <!-- Question 1 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">1</span> Sharing with AG Collection Areas</span>
        <span class="tag-mini red">Operational Continuity</span>
      </div>
      <div class="card-desc">
        How will the <b>Incident Panel list</b> be maintained? Which Google tool will be provided to ensure ongoing sharing and visibility for the <b>AG Collection Areas</b>?
      </div>
    </div>

    <!-- Question 2 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">2</span> 'Sports Event Reporting' Ingestion</span>
        <span class="tag-mini green">Software Integration</span>
      </div>
      <div class="card-desc">
        Which Google tool and API should our automated background scripts target to continuously populate <b>event schedule tables</b> and archive <b>PDF reports</b>?
      </div>
    </div>

    <!-- Question 3 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">3</span> Headless Authentication (SPN Equivalent)</span>
        <span class="tag-mini purple">Security & Access</span>
      </div>
      <div class="card-desc">
        How will the corporate <b>Service Account</b> in Google Cloud be provisioned to replace our Azure AD Service Principal (SPN), allowing automated daemons to write data without human login?
      </div>
    </div>

    <!-- Question 4 -->
    <div class="card card-question">
      <div class="card-title">
        <span><span class="question-badge">4</span> Power Automate Migration</span>
        <span class="tag-mini orange">Triggers & Alerts</span>
      </div>
      <div class="card-desc">
        How does the IT team plan to migrate or replace the automated workflows and triggers currently operating under <b>svc.captacao@adgbl.com</b>?
      </div>
    </div>

    <div style="background: #1e293b; border-left: 4px solid #f59e0b; padding: 14px; border-radius: 6px; margin-top: 20px;">
      <div style="font-size: 12px; font-weight: 700; color: #f59e0b; margin-bottom: 4px;">🎯 Goal of this Alignment:</div>
      <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
        Ensure timely technical preparation to adapt codebase and security configurations, guaranteeing <b>zero downtime</b> for both the Audience Team and AG Collection Areas.
      </div>
    </div>

  </div>

</div>

<div class="footer-note">
  <div><b>Responsible Team:</b> Capture Support & Sports Monitoring | <code>svc.captacao@adgbl.com</code></div>
  <div><b>Technical Document:</b> Corporate Migration Dependency Mapping (v1.0)</div>
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
    opts.add_argument("--window-size=1470,1200")
    opts.add_argument("--force-device-scale-factor=2")  # 2x Retina resolution

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(f"file:///{temp_html.as_posix()}")
        time.sleep(1.5)
        # Ajusta a altura da janela ao tamanho real do conteúdo
        height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        driver.set_window_size(1470, height + 40)
        time.sleep(0.5)
        driver.save_screenshot(str(output_path))
        print(f"Infográfico gerado com sucesso: {output_path} ({output_path.stat().st_size} bytes)")
    finally:
        driver.quit()
        if temp_html.exists():
            try:
                temp_html.unlink()
            except Exception:
                pass

def main():
    print("Iniciando geração dos infográficos de alta resolução...")
    
    # 1. Versão Português
    out_pt_ws = WORKSPACE_DIR / "infografico_migracao_sharepoint_google_pt.png"
    out_pt_art = ARTIFACT_DIR / "infografico_migracao_sharepoint_google_pt.png"
    render_html_to_png(HTML_TEMPLATE_PT, out_pt_ws)
    import shutil
    shutil.copy2(out_pt_ws, out_pt_art)
    
    # 2. Versão Inglês
    out_en_ws = WORKSPACE_DIR / "infographic_sharepoint_google_migration_en.png"
    out_en_art = ARTIFACT_DIR / "infographic_sharepoint_google_migration_en.png"
    render_html_to_png(HTML_TEMPLATE_EN, out_en_ws)
    shutil.copy2(out_en_ws, out_en_art)
    
    print("Todos os infográficos foram gerados e sincronizados com sucesso!")

if __name__ == "__main__":
    main()
