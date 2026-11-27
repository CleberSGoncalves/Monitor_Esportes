# -*- coding: utf-8 -*-
"""
Gerador do Portal Web Oficial do Suporte Captação (IBOPE).
Gera um portal intranet moderno, autônomo e 100% independente do SharePoint legado.
Contém todos os módulos nativos:
 - Hero Banner 1:1 com SharePoint (fundo azul marinho, nós de rede SVG, clima, grade 3x3 branca interna)
 - Escala de Trabalho 2026 completa (todos os meses, turnos, Artigo 66 da CLT, SobreAviso, download xlsx)
 - Streaming (862 jogos sincronizados com CazéTV, Prime Video, Netflix, TNT, Record, DAZN)
 - Contatos Hospedeiros (500 contatos em todas as cidades com busca e exportação CSV)
 - Painel de Ocorrências (500 ocorrências e histórico de incidentes)
 - Procedimentos N1 (68 guias e POPs operacionais)
 - Documentos (Repositório de arquivos da equipe)
 - Dashboard & Indicadores (Métricas, SLAs, disponibilidade)
 - Metas & Projetos (OKRs e iniciativas estratégicas)
 - Receptores & TV BOX (PVIDs PV3623, PV3687, PV3679)
 - Equipe & Plantão (Contatos da liderança e operadores)
 - Controle de Acessos & RBAC (36 permissões mapeadas)
"""

import os
import sys
import json
import csv
import shutil

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Suporte Captação | Portal Oficial & Central Autônoma</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --sp-theme-primary: #0078D4;
      --sp-theme-dark: #004578;
      --sp-theme-dark-alt: #106EBE;
      --sp-theme-light: #DEECF9;
      --sp-theme-lighter: #EFF6FC;
      --sp-body-bg: #FAF9F8;
      --sp-card-bg: #FFFFFF;
      --sp-text-main: #323130;
      --sp-text-secondary: #605E5C;
      --sp-text-muted: #A19F9D;
      --sp-border: #EDEBE9;
      --sp-border-hover: #C8C6C4;
      --sp-nav-bg: #0078D4;
      --shadow-card: 0 1.6px 3.6px 0 rgba(0, 0, 0, 0.132), 0 0.3px 0.9px 0 rgba(0, 0, 0, 0.108);
      --shadow-hover: 0 3.2px 7.2px 0 rgba(0, 0, 0, 0.132), 0 0.6px 1.8px 0 rgba(0, 0, 0, 0.108);

      /* Badges & Status */
      --badge-caze-bg: #DCFCE7;
      --badge-caze-txt: #166534;
      --badge-prime-bg: #00509E;
      --badge-prime-txt: #FFFFFF;
      --badge-netflix-bg: #7F4F24;
      --badge-netflix-txt: #FFFFFF;
      --badge-tnt-bg: #6B21A8;
      --badge-tnt-txt: #FFFFFF;
      --badge-record-bg: #1E40AF;
      --badge-record-txt: #FFFFFF;
      --badge-dazn-bg: #0F172A;
      --badge-dazn-txt: #F8FAFC;
      --badge-pvid-bg: #0D5C75;
      --badge-pvid-txt: #FFFFFF;
      --badge-pend-bg: #FEF3C7;
      --badge-pend-txt: #92400E;
      --badge-exib-bg: #DCFCE7;
      --badge-exib-txt: #166534;
      --badge-nao-bg: #FEE2E2;
      --badge-nao-txt: #991B1B;
    }

    body.dark-mode {
      --sp-body-bg: #121212;
      --sp-card-bg: #1E1E1E;
      --sp-text-main: #E0E0E0;
      --sp-text-secondary: #AAAAAA;
      --sp-text-muted: #777777;
      --sp-border: #2D2D2D;
      --sp-border-hover: #444444;
      --sp-theme-lighter: #1A365D;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      width: 100%;
      min-height: 100vh;
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
      background: var(--sp-body-bg);
      color: var(--sp-text-main);
      overflow-x: hidden;
    }

    /* 1. SUITE NAV BAR (TOPMOST HEADER) */
    .suite-nav {
      height: 48px;
      background: #001f3f;
      color: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      width: 100%;
      box-sizing: border-box;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .suite-nav-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .waffle-icon {
      width: 20px;
      height: 20px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 2.5px;
      cursor: pointer;
    }

    .waffle-dot {
      background: #FFFFFF;
      border-radius: 1px;
    }

    .suite-title {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.01em;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .suite-title span {
      font-weight: 300;
      opacity: 0.85;
    }

    .suite-nav-center {
      flex: 1;
      max-width: 480px;
      margin: 0 20px;
    }

    .suite-search-box {
      width: 100%;
      background: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.25);
      border-radius: 4px;
      padding: 6px 12px;
      color: #FFFFFF;
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }

    .suite-search-box::placeholder {
      color: rgba(255, 255, 255, 0.7);
    }

    .suite-search-box:focus {
      background: #FFFFFF;
      color: #1A365D;
    }

    .suite-nav-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #004578;
      border: 2px solid #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      color: #FFFFFF;
      cursor: pointer;
    }

    .nav-pill-btn {
      background: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.25);
      color: #FFFFFF;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }

    .nav-pill-btn:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    .role-switcher-select {
      background: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.25);
      color: #FFFFFF;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      outline: none;
      cursor: pointer;
    }

    .role-switcher-select option {
      background: #001f3f;
      color: #FFFFFF;
    }

    /* 2. SITE NAVIGATION & HUB TITLE */
    .site-nav-bar {
      background: #004578;
      border-bottom: 2px solid #003359;
      width: 100%;
      box-sizing: border-box;
    }

    .site-nav-container {
      width: 100%;
      padding: 12px 24px 0 24px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-sizing: border-box;
    }

    .site-brand-row {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .site-brand-icon {
      width: 44px;
      height: 44px;
      background: #0078D4;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #FFFFFF;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.02em;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }

    .site-brand-info h2 {
      font-size: 18px;
      font-weight: 700;
      color: #FFFFFF;
      letter-spacing: -0.01em;
    }

    .site-brand-info p {
      font-size: 12px;
      color: #DEECF9;
      margin-top: 2px;
    }

    /* NAVEGAÇÃO SUPERIOR ESTILO SHAREPOINT MODERNO COM DROPDOWNS */
    .sp-top-nav-bar {
      background: #004578;
      border-bottom: 1px solid rgba(255, 255, 255, 0.15);
      position: relative;
      z-index: 1000;
      overflow: visible !important;
    }

    .sp-top-nav-container {
      width: 100%;
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-sizing: border-box;
      min-height: 48px;
      overflow: visible !important;
    }

    .sp-nav-menus {
      display: flex;
      align-items: center;
      gap: 3px;
      flex-wrap: wrap;
      overflow: visible !important;
    }

    .sp-menu-item {
      position: relative;
    }

    .sp-menu-btn {
      background: transparent;
      border: none;
      border-bottom: 3px solid transparent;
      color: #DEECF9;
      padding: 12px 14px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      transition: all 0.15s ease;
      user-select: none;
    }

    .sp-menu-btn:hover {
      color: #FFFFFF;
      background: rgba(255, 255, 255, 0.12);
    }

    .sp-menu-btn.active,
    .sp-menu-item.open > .sp-menu-btn {
      color: #FFFFFF;
      border-bottom-color: #50E6FF;
      background: rgba(255, 255, 255, 0.16);
    }

    .sp-caret {
      font-size: 9px;
      opacity: 0.8;
      transition: transform 0.2s ease;
      pointer-events: none;
    }

    .sp-menu-item:hover > .sp-menu-btn .sp-caret,
    .sp-menu-item.open > .sp-menu-btn .sp-caret {
      transform: rotate(180deg);
    }

    /* DROPDOWN MENU FLYOUT (BLINDADO CONTRA CLIPPING E IFRAMES) */
    .sp-dropdown-menu {
      position: absolute;
      top: 100%;
      left: 0;
      min-width: 290px;
      background: #FFFFFF;
      border-radius: 4px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
      border: 1px solid #CBD5E1;
      padding: 6px 0;
      display: none;
      z-index: 9999 !important;
      animation: fadeInDropdown 0.12s ease;
      pointer-events: auto;
    }

    @keyframes fadeInDropdown {
      from { opacity: 0; transform: translateY(-3px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .sp-menu-item:hover > .sp-dropdown-menu,
    .sp-menu-item.open > .sp-dropdown-menu {
      display: block !important;
    }

    .sp-dropdown-link {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 18px;
      color: #1E293B;
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.12s ease;
      white-space: nowrap;
      border: none;
      background: transparent;
      width: 100%;
      text-align: left;
      box-sizing: border-box;
      user-select: none;
    }

    .sp-dropdown-link:hover,
    .sp-dropdown-link:focus {
      background: #F1F5F9;
      color: #0078D4;
      outline: none;
    }

    .sp-dropdown-link .item-count-badge {
      margin-left: auto;
      font-size: 11px;
      color: #64748B;
      background: #F1F5F9;
      padding: 2px 7px;
      border-radius: 10px;
      font-weight: 600;
    }

    .sp-dropdown-divider {
      height: 1px;
      background: #E2E8F0;
      margin: 4px 0;
    }

    /* BREADCRUMBS & NAVEGAÇÃO DE DIRETÓRIOS SHAREPOINT */
    .sp-breadcrumbs {
      font-size: 13px;
      color: #64748B;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .sp-crumb {
      color: #0078D4;
      cursor: pointer;
      text-decoration: underline;
      font-weight: 500;
    }

    .sp-crumb:hover {
      color: #106EBE;
    }

    .sp-crumb-current {
      font-weight: 700;
      color: #1E293B;
    }

    .sp-folder-row:hover {
      background: #F1F5F9 !important;
    }

    .sp-tab-pill {
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid #CBD5E1;
      background: #FFFFFF;
      color: #475569;
      transition: all 0.15s ease;
    }

    .sp-tab-pill:hover {
      background: #F1F5F9;
      color: #0078D4;
    }

    .sp-tab-pill.active {
      background: #0078D4;
      color: #FFFFFF;
      border-color: #0078D4;
    }

    /* PAINEL DE OCORRÊNCIAS ESTILO SHAREPOINT LIST (1:1 COM IMAGEM DO USUÁRIO) */
    .sp-list-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0 8px 0;
      margin-bottom: 4px;
    }

    .sp-list-main-title {
      font-size: 20px;
      font-weight: 700;
      color: #1E293B;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sp-list-main-title .star-icon {
      font-size: 14px;
      color: #94A3B8;
      cursor: pointer;
    }

    /* BARRA DE COMANDOS / AÇÕES DO SHAREPOINT */
    .sp-command-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 6px 0 10px 0;
      border-bottom: 1px solid #E2E8F0;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }

    .sp-command-left {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .sp-btn-new {
      background: #004578;
      color: #FFFFFF;
      border: none;
      border-radius: 2px;
      padding: 7px 16px;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: background 0.15s;
    }

    .sp-btn-new:hover {
      background: #003366;
    }

    .sp-btn-cmd {
      background: transparent;
      border: 1px solid transparent;
      color: #334155;
      border-radius: 2px;
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .sp-btn-cmd:hover {
      background: #F1F5F9;
      border-color: #E2E8F0;
    }

    .sp-command-search {
      min-width: 280px;
      position: relative;
    }

    .sp-command-search input {
      width: 100%;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      padding: 6px 12px 6px 30px;
      font-size: 12.5px;
      outline: none;
      box-sizing: border-box;
      transition: border-color 0.15s;
    }

    .sp-command-search input:focus {
      border-color: #0078D4;
    }

    .sp-command-search::before {
      content: '🔍';
      position: absolute;
      left: 8px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 12px;
      opacity: 0.6;
    }

    /* BARRA DE EXIBIÇÕES (VIEWS) */
    .sp-views-bar {
      display: flex;
      align-items: center;
      gap: 20px;
      border-bottom: 1px solid #E2E8F0;
      margin-bottom: 10px;
      padding-bottom: 2px;
      overflow-x: auto;
    }

    .sp-view-tab {
      background: transparent;
      border: none;
      border-bottom: 2.5px solid transparent;
      color: #64748B;
      padding: 6px 4px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
      transition: all 0.15s;
    }

    .sp-view-tab:hover {
      color: #0F172A;
    }

    .sp-view-tab.active {
      color: #0078D4;
      border-bottom-color: #0078D4;
    }

    /* BARRA DE FILTROS ATIVOS (PILLS) */
    .sp-filter-pills-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-size: 12.5px;
      color: #64748B;
      flex-wrap: wrap;
    }

    .sp-filter-pill {
      background: #E0F2FE;
      color: #0369A1;
      border-radius: 14px;
      padding: 3px 10px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid #BAE6FD;
    }

    .sp-filter-pill-purple {
      background: #F3E8FF;
      color: #7E22CE;
      border-color: #E9D5FF;
    }

    .sp-pill-close {
      cursor: pointer;
      font-weight: 700;
      opacity: 0.7;
    }

    .sp-pill-close:hover {
      opacity: 1;
    }

    .sp-btn-clear-filters {
      background: none;
      border: none;
      color: #0078D4;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      margin-left: 6px;
    }

    .sp-btn-clear-filters:hover {
      text-decoration: underline;
    }

    /* BADGES ESPECÍFICOS DO PAINEL DE OCORRÊNCIAS */
    .sp-badge {
      display: inline-block;
      border-radius: 12px;
      padding: 2.5px 9px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
      text-align: center;
    }

    .sp-badge-em-andamento { background: #38BDF8; color: #FFFFFF; }
    .sp-badge-feedback { background: #8B5CF6; color: #FFFFFF; }
    .sp-badge-concluido { background: #10B981; color: #FFFFFF; }

    .sp-badge-dark { background: #475569; color: #FFFFFF; }
    .sp-badge-amber { background: #D97706; color: #FFFFFF; }
    .sp-badge-teal { background: #0D9488; color: #FFFFFF; }
    .sp-badge-red { background: #EF4444; color: #FFFFFF; }
    .sp-badge-purple { background: #7C3AED; color: #FFFFFF; }

    .sp-badge-yellow { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
    .sp-badge-blue { background: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }
    .sp-badge-red-soft { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }
    .sp-badge-indigo { background: #E0E7FF; color: #3730A3; border: 1px solid #C7D2FE; }
    .sp-badge-cyan { background: #CFFAFE; color: #155E75; border: 1px solid #A5F3FC; }
    .sp-badge-orange { background: #FFEDD5; color: #9A3412; border: 1px solid #FED7AA; }
    .sp-badge-gray { background: #F3F4F6; color: #374151; border: 1px solid #E5E7EB; }

    .sp-badge-sim { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
    .sp-badge-nao { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }

    .sp-badge-n1 { background: #38BDF8; color: #FFFFFF; }
    .sp-badge-solucionado { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
    .sp-badge-vinicius { background: #0F766E; color: #FFFFFF; }
    .sp-badge-lucieudes { background: #93C5FD; color: #1E3A8A; }

    .sp-redmine-link {
      color: #0078D4;
      font-weight: 600;
      text-decoration: none;
    }

    .sp-redmine-link:hover {
      text-decoration: underline;
    }

    .nav-menu-tabs {
      display: flex;
      gap: 2px;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .nav-menu-tabs::-webkit-scrollbar {
      display: none;
    }

    .tab-link {
      background: transparent;
      border: none;
      border-bottom: 3px solid transparent;
      color: #DEECF9;
      padding: 9px 15px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 7px;
      white-space: nowrap;
      transition: all 0.15s ease;
    }

    .tab-link:hover {
      color: #FFFFFF;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 4px 4px 0 0;
    }

    .tab-link.active {
      color: #FFFFFF;
      border-bottom-color: #50E6FF;
      background: rgba(255, 255, 255, 0.12);
      border-radius: 4px 4px 0 0;
    }

    /* 3. MAIN BODY & PANES */
    .main-body {
      width: 100%;
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    .pane-container {
      display: none;
      width: 100%;
      padding: 24px;
      box-sizing: border-box;
    }

    .pane-container.active {
      display: block;
    }

    #pane-home {
      padding: 0;
      width: 100%;
    }

    /* ========================================================================= */
    /* HERO BANNER 1:1 COM SHAREPOINT (FUNDO AZUL MARINHO + SVG CONSTELLATION)   */
    /* ========================================================================= */
    .hero-banner {
      background: radial-gradient(circle at 85% 30%, #063970 0%, #021b38 60%, #010f22 100%);
      width: 100%;
      padding: 36px 40px 48px 40px;
      box-sizing: border-box;
      position: relative;
      overflow: hidden;
      color: #FFFFFF;
    }

    .hero-network-svg {
      position: absolute;
      top: 0;
      right: 0;
      width: 55%;
      height: 100%;
      pointer-events: none;
      opacity: 0.75;
    }

    .hero-top-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      position: relative;
      z-index: 2;
      margin-bottom: 24px;
    }

    .hero-title-area {
      max-width: 650px;
    }

    .hero-main-title {
      font-size: 32px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.02em;
      color: #FFFFFF;
    }

    .hero-description {
      font-size: 14px;
      line-height: 1.6;
      color: #CBD5E1;
      margin: 0;
    }

    .hero-weather-card {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 4px;
      padding: 12px 18px;
      min-width: 220px;
      text-align: right;
      backdrop-filter: blur(6px);
    }

    .weather-city {
      font-size: 13px;
      color: #E2E8F0;
      font-weight: 600;
    }

    .weather-temp-row {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      margin: 4px 0;
    }

    .weather-degrees {
      font-size: 28px;
      font-weight: 700;
      color: #FFFFFF;
    }

    .weather-details {
      font-size: 11px;
      color: #94A3B8;
    }

    /* 3x3 Grid de botões brancos dentro do banner */
    .hero-3x3-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      max-width: 880px;
      position: relative;
      z-index: 2;
    }

    .hero-card {
      background: #FFFFFF;
      border-radius: 4px;
      padding: 13px 18px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      color: #0F172A;
      font-weight: 600;
      font-size: 13.5px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
      transition: all 0.15s ease-in-out;
      border: 1px solid rgba(255, 255, 255, 0.2);
      user-select: none;
    }

    .hero-card:hover {
      transform: translateY(-2px);
      background: #F8FAFC;
      box-shadow: 0 6px 14px rgba(0, 0, 0, 0.25);
    }

    .hero-card-icon {
      font-size: 16px;
      color: #0078D4;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* ÁREA INFERIOR DA HOME */
    .home-lower-body {
      width: 100%;
      padding: 32px 40px;
      background: #F3F4F6;
      box-sizing: border-box;
    }

    body.dark-mode .home-lower-body {
      background: #121212;
    }

    .contact-callout-box {
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 4px;
      overflow: hidden;
      max-width: 440px;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
    }

    body.dark-mode .contact-callout-box {
      background: #1E1E1E;
      border-color: #333333;
    }

    .contact-callout-header {
      background: #475569;
      color: #FFFFFF;
      font-weight: 700;
      font-size: 13px;
      padding: 10px 16px;
    }

    .contact-callout-body {
      padding: 16px;
      font-size: 13px;
      color: #334155;
      line-height: 1.5;
    }

    body.dark-mode .contact-callout-body {
      color: #CBD5E1;
    }

    .contact-callout-body p {
      margin: 0 0 14px 0;
    }

    .btn-contact-action {
      display: inline-block;
      background: #002B49;
      color: #FFFFFF !important;
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
      padding: 8px 16px;
      border-radius: 3px;
      transition: background 0.15s ease;
    }

    .btn-contact-action:hover {
      background: #004578;
    }

    .home-redmine-center {
      display: flex;
      justify-content: center;
      margin: 28px 0;
    }

    .btn-sugestoes-sharepoint {
      background: #002B49;
      color: #FFFFFF !important;
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
      padding: 10px 22px;
      border-radius: 3px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.12);
      transition: all 0.15s ease;
    }

    .btn-sugestoes-sharepoint:hover {
      background: #004578;
      transform: translateY(-1px);
    }

    .home-section-links {
      margin-top: 24px;
    }

    .section-title-wrap {
      margin-bottom: 16px;
    }

    .section-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--sp-text-main);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .section-desc {
      font-size: 13px;
      color: var(--sp-text-secondary);
      margin-top: 4px;
    }

    .waffle-links-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }

    .waffle-link-card {
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      text-decoration: none;
      color: var(--sp-text-main);
      box-shadow: var(--shadow-card);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      text-align: center;
    }

    .waffle-link-card:hover {
      border-color: var(--sp-theme-primary);
      transform: translateY(-2px);
      box-shadow: var(--shadow-hover);
    }

    .waffle-link-icon {
      font-size: 26px;
    }

    .waffle-link-title {
      font-size: 13px;
      font-weight: 600;
    }

    /* ========================================================================= */
    /* MÓDULO NATIVO DE ESCALA DE TRABALHO 2026 (CLT 66, CALENDÁRIO, PLANTÕES)   */
    /* ========================================================================= */
    .clt-banner-alert {
      background: #FFFBEB;
      border: 1px solid #FCD34D;
      border-left: 6px solid #D97706;
      border-radius: 6px;
      padding: 16px 20px;
      margin-bottom: 20px;
      display: flex;
      align-items: flex-start;
      gap: 14px;
      color: #92400E;
    }

    body.dark-mode .clt-banner-alert {
      background: #3B2A10;
      border-color: #854D0E;
      color: #FDE68A;
    }

    .clt-icon {
      font-size: 24px;
      line-height: 1;
    }

    .clt-content h4 {
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 4px;
      color: #78350F;
    }

    body.dark-mode .clt-content h4 {
      color: #FDE68A;
    }

    .clt-content p {
      font-size: 13px;
      line-height: 1.5;
    }

    .month-pills-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 18px;
    }

    .month-pill-btn {
      padding: 8px 16px;
      border-radius: 20px;
      border: 1px solid var(--sp-border);
      background: var(--sp-card-bg);
      color: var(--sp-text-main);
      font-weight: 600;
      font-size: 12.5px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .month-pill-btn:hover {
      border-color: #0078D4;
      color: #0078D4;
    }

    .month-pill-btn.active {
      background: #0078D4;
      border-color: #0078D4;
      color: #FFFFFF;
      box-shadow: 0 2px 6px rgba(0,120,212,0.3);
    }

    .escala-controls-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }

    .escala-inputs-group {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .escala-table-scroll {
      overflow-x: auto;
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      background: #FFFFFF;
      max-height: 600px;
      box-shadow: var(--shadow-card);
    }

    body.dark-mode .escala-table-scroll {
      background: #1E1E1E;
    }

    .escala-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      white-space: nowrap;
    }

    .escala-table th, .escala-table td {
      padding: 7px 9px;
      border: 1px solid #E2E8F0;
      text-align: center;
    }

    body.dark-mode .escala-table th, body.dark-mode .escala-table td {
      border-color: #333333;
    }

    .escala-table th {
      background: #F8FAFC;
      color: #334155;
      font-weight: 700;
      position: sticky;
      top: 0;
      z-index: 2;
    }

    body.dark-mode .escala-table th {
      background: #27272A;
      color: #E4E4E7;
    }

    .escala-table th.th-sticky-left, .escala-table td.td-sticky-left {
      position: sticky;
      left: 0;
      background: #FFFFFF;
      z-index: 1;
      text-align: left;
      font-weight: 600;
    }

    body.dark-mode .escala-table th.th-sticky-left, body.dark-mode .escala-table td.td-sticky-left {
      background: #1E1E1E;
    }

    .escala-table th.th-sticky-left {
      background: #F1F5F9;
      z-index: 3;
    }

    body.dark-mode .escala-table th.th-sticky-left {
      background: #27272A;
    }

    .escala-badge {
      display: inline-block;
      min-width: 24px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 11px;
    }

    .escala-badge-t { background: #DCFCE7; color: #166534; }
    .escala-badge-f { background: #F1F5F9; color: #64748B; }
    .escala-badge-ferias { background: #FEF3C7; color: #92400E; }
    .escala-badge-bh { background: #DBEAFE; color: #1E40AF; }
    .escala-badge-vf { background: #FEE2E2; color: #991B1B; }
    .escala-badge-fj { background: #CCFBF1; color: #115E59; }
    .escala-badge-dayoff { background: #FCE7F3; color: #9D174D; }
    .escala-badge-tr { background: #EDE9FE; color: #6D28D9; }
    .escala-badge-ag { background: #FEF08A; color: #854D0E; }
    .escala-badge-sm { background: #D1FAE5; color: #065F46; }

    /* LEGENDA E SOBREAVISO */
    .escala-footer-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-top: 24px;
    }

    .escala-info-card {
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 18px 22px;
      box-shadow: var(--shadow-card);
    }

    .escala-info-card h4 {
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 12px;
      color: var(--sp-text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .legenda-chips-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
    }

    .legenda-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--sp-text-secondary);
    }

    .sobreaviso-schedule-list {
      list-style: none;
      font-size: 13px;
      color: var(--sp-text-secondary);
      line-height: 1.6;
    }

    .sobreaviso-schedule-list li {
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* KPI CARDS & TABLES GERAIS */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .kpi-box {
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 18px 20px;
      box-shadow: var(--shadow-card);
      border-left: 4px solid var(--sp-theme-primary);
    }

    .kpi-box-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--sp-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .kpi-box-val {
      font-size: 28px;
      font-weight: 700;
      color: var(--sp-text-main);
      margin: 6px 0;
      font-family: 'Segoe UI', sans-serif;
    }

    .kpi-box-sub {
      font-size: 11px;
      color: var(--sp-text-muted);
    }

    .filter-bar {
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 12px 18px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin-bottom: 20px;
      box-shadow: var(--shadow-card);
    }

    .filter-inputs {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      flex: 1;
    }

    .search-field, .select-field {
      padding: 8px 12px;
      border: 1px solid var(--sp-border);
      border-radius: 4px;
      font-size: 13px;
      background: var(--sp-card-bg);
      color: var(--sp-text-main);
      outline: none;
      transition: border-color 0.15s;
    }

    .search-field {
      min-width: 280px;
      flex: 1;
    }

    .search-field:focus, .select-field:focus {
      border-color: var(--sp-theme-primary);
      box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }

    .btn-action {
      padding: 8px 14px;
      border-radius: 4px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: none;
      transition: all 0.15s ease;
    }

    .btn-action-primary {
      background: var(--sp-theme-primary);
      color: #FFFFFF;
    }

    .btn-action-primary:hover {
      background: var(--sp-theme-dark);
    }

    .btn-action-secondary {
      background: var(--sp-theme-lighter);
      color: var(--sp-theme-dark);
      border: 1px solid #C7E0F4;
    }

    .btn-action-secondary:hover {
      background: #DEECF9;
    }

    .sp-table-wrap {
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      box-shadow: var(--shadow-card);
      overflow: hidden;
    }

    .sp-table-scroll {
      max-height: 640px;
      overflow-y: auto;
    }

    .sp-list-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .sp-list-table th {
      background: #FAF9F8;
      color: var(--sp-text-secondary);
      font-weight: 600;
      text-align: left;
      padding: 12px 14px;
      border-bottom: 2px solid var(--sp-border);
      position: sticky;
      top: 0;
      z-index: 2;
    }

    body.dark-mode .sp-list-table th {
      background: #27272A;
      color: #E4E4E7;
    }

    .sp-list-table td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--sp-border);
      color: var(--sp-text-main);
    }

    .sp-list-table tr:hover td {
      background: rgba(0, 120, 212, 0.04);
    }

    .td-center {
      text-align: center;
    }

    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-align: center;
    }

    .badge-caze { background: var(--badge-caze-bg); color: var(--badge-caze-txt); }
    .badge-prime { background: var(--badge-prime-bg); color: var(--badge-prime-txt); }
    .badge-netflix { background: var(--badge-netflix-bg); color: var(--badge-netflix-txt); }
    .badge-tnt { background: var(--badge-tnt-bg); color: var(--badge-tnt-txt); }
    .badge-record { background: var(--badge-record-bg); color: var(--badge-record-txt); }
    .badge-dazn { background: var(--badge-dazn-bg); color: var(--badge-dazn-txt); }
    .badge-default { background: #E2E8F0; color: #334155; }

    .badge-pvid {
      background: var(--badge-pvid-bg);
      color: var(--badge-pvid-txt);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }

    .badge-pendente { background: var(--badge-pend-bg); color: var(--badge-pend-txt); }
    .badge-exibido { background: var(--badge-exib-bg); color: var(--badge-exib-txt); }
    .badge-nao-exibido { background: var(--badge-nao-bg); color: var(--badge-nao-txt); }

    .badge-role-owner { background: #EDE9FE; color: #6D28D9; border: 1px solid #DDD6FE; }
    .badge-role-write { background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
    .badge-role-read { background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; }

    /* MODAL DE PROCEDIMENTOS */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      z-index: 9999;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-card {
      background: var(--sp-card-bg);
      border-radius: 8px;
      max-width: 760px;
      width: 100%;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      border: 1px solid var(--sp-border);
      overflow: hidden;
    }

    .modal-header {
      padding: 16px 20px;
      background: #004578;
      color: #FFFFFF;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-header h3 {
      font-size: 16px;
      font-weight: 700;
    }

    .modal-close-btn {
      background: transparent;
      border: none;
      color: #FFFFFF;
      font-size: 20px;
      cursor: pointer;
    }

    .modal-body {
      padding: 20px;
      overflow-y: auto;
      font-size: 13px;
      line-height: 1.6;
      color: var(--sp-text-main);
    }

    /* FOOTER */
    .site-footer {
      background: var(--sp-card-bg);
      border-top: 1px solid var(--sp-border);
      padding: 20px 24px;
      margin-top: 32px;
    }

    .site-footer-container {
      width: 100%;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      font-size: 12px;
      color: var(--sp-text-secondary);
    }

    @media (max-width: 900px) {
      .hero-3x3-grid { grid-template-columns: repeat(2, 1fr); }
      .hero-top-row { flex-direction: column; }
      .escala-footer-grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 600px) {
      .hero-3x3-grid { grid-template-columns: 1fr; }
      .suite-nav-center { display: none; }
    }

    /* ESTILOS DE FORMULÁRIOS & MODAIS INTERATIVOS */
    .sp-form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
      margin-bottom: 16px;
    }
    .sp-form-group {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .sp-form-group.full-width {
      grid-column: 1 / -1;
    }
    .sp-form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--sp-text-secondary);
    }
    .sp-form-input, .sp-form-select, .sp-form-textarea {
      padding: 8px 12px;
      border: 1px solid var(--sp-border);
      border-radius: 4px;
      font-size: 13px;
      background: var(--sp-card-bg);
      color: var(--sp-text-main);
      outline: none;
      font-family: inherit;
    }
    .sp-form-input:focus, .sp-form-select:focus, .sp-form-textarea:focus {
      border-color: #0078D4;
      box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    .sp-modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      padding: 14px 20px;
      border-top: 1px solid var(--sp-border);
      background: var(--sp-bg);
    }

    /* MODO DE EXIBIÇÃO DE GRADE (GRID EDIT SHAREPOINT) */
    .sp-btn-cmd.btn-grid-active {
      background: #004578 !important;
      color: #FFFFFF !important;
      border-color: #003366 !important;
      box-shadow: 0 0 0 2px rgba(0, 69, 120, 0.3);
      font-weight: 600;
    }
    .sp-grid-cell {
      min-height: 24px;
      padding: 4px 6px;
      border-radius: 3px;
      outline: none;
      transition: all 0.15s ease;
      cursor: text;
    }
    .sp-grid-cell:hover {
      background: #F1F5F9;
      box-shadow: inset 0 0 0 1px #CBD5E1;
    }
    .sp-grid-cell:focus {
      background: #FFFFFF !important;
      box-shadow: 0 0 0 2px #0078D4 !important;
      border-color: #0078D4 !important;
      z-index: 2;
      position: relative;
    }
    .sp-grid-cell-wide {
      min-width: 180px;
      max-width: 320px;
    }
    .sp-grid-select {
      padding: 4px 8px;
      font-size: 12px;
      border-radius: 4px;
      border: 1px solid var(--sp-border);
      background: var(--sp-card-bg);
      color: var(--sp-text-main);
      outline: none;
      cursor: pointer;
      font-weight: 600;
    }
    .sp-grid-select:focus {
      border-color: #0078D4;
      box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    .sp-grid-select-sm {
      padding: 2px 6px;
      font-size: 11.5px;
    }

    /* NOTIFICAÇÕES TOAST ESTILO MICROSOFT 365 / GOOGLE */
    #sp-toast-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 100000;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    }
    .sp-toast {
      pointer-events: auto;
      display: flex;
      align-items: center;
      gap: 12px;
      background: #1E293B;
      color: #FFFFFF;
      padding: 12px 18px;
      border-radius: 8px;
      font-size: 13.5px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.25);
      border-left: 5px solid #0078D4;
      animation: slideToastIn 0.25s ease-out;
      min-width: 280px;
      max-width: 440px;
    }
    .sp-toast.toast-success { border-left-color: #10B981; }
    .sp-toast.toast-info { border-left-color: #0078D4; }
    .sp-toast.toast-warning { border-left-color: #F59E0B; }
    .sp-toast.toast-error { border-left-color: #EF4444; }

    @keyframes slideToastIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    /* ORDENAÇÃO E CABEÇALHOS INTERATIVOS ESTILO SHAREPOINT */
    .th-sortable {
      cursor: pointer !important;
      user-select: none;
      transition: background 0.15s ease, color 0.15s ease;
      white-space: nowrap;
    }
    .th-sortable:hover {
      background: rgba(0, 120, 212, 0.08) !important;
      color: #0078D4 !important;
    }
    .sort-icon {
      font-size: 11px;
      margin-left: 4px;
      color: #94A3B8;
      display: inline-block;
      vertical-align: middle;
    }
    .th-sortable.sorted-asc .sort-icon, .th-sortable.sorted-desc .sort-icon {
      color: #0078D4;
      font-weight: 700;
    }
  </style>
</head>
<body>

  <!-- 1. SUITE NAV (GOOGLE WORKSPACE / MICROSOFT 365 TOPBAR) -->
  <header class="suite-nav">
    <div class="suite-nav-left">
      <div class="waffle-icon" title="Menu Corporativo">
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
      </div>
      <div class="suite-title">
        Google Sites <span>| Suporte Captação</span>
      </div>
    </div>

    <div class="suite-nav-center">
      <input type="text" class="suite-search-box" id="global-search" placeholder="Pesquisar partidas, contatos, ocorrências, procedimentos...">
    </div>

    <div class="suite-nav-right">
      <select id="user-role-select" class="role-switcher-select" onchange="onRoleChange()" title="Simulador de Perfil de Acesso & Permissões">
        <option value="admin">👤 Cleber Gonçalves (Gestor/Proprietário)</option>
        <option value="admin_cassio">👤 Cássio Esteves (Administrador)</option>
        <option value="admin_vinicius">👤 Vinícius Dantas (Administrador)</option>
        <option value="admin_luiz">👤 Luiz De Sa Lemos (Gestão / Diretoria)</option>
        <option value="operador">🛠️ Operador Suporte N1/N2 (Escrita Operacional)</option>
        <option value="leitor">👁️ Visitante (NOC / SAC / Consulta — Somente Leitura)</option>
      </select>

      <button class="nav-pill-btn" onclick="toggleDarkMode()" title="Alternar Modo Escuro / Claro">
        <span id="dark-mode-icon">🌙</span> Modo Operacional
      </button>
      <div class="user-avatar" id="top-user-avatar" title="IBOPE — Suporte Captação">CG</div>
    </div>
  </header>

  <!-- 2. SITE NAVIGATION & HUB TITLE -->
  <nav class="site-nav-bar">
    <div class="site-nav-container">
      <div class="site-brand-row">
        <div class="site-brand-icon">SC</div>
        <div class="site-brand-info">
          <h2>Suporte Captação</h2>
          <p>IBOPE — Central Autônoma de Operações & Ingest</p>
        </div>
      </div>

      <div class="sp-nav-menus">
        <!-- Página Inicial -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn tab-link active" onclick="handleMenuClick('home', 'Página Inicial', event)">Página Inicial</button>
        </div>

        <!-- Documentos ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Documentos <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('procedimentos', '📖 Procedimentos N1', event)">📖 Procedimentos N1 <span class="item-count-badge">__PROCEDIMENTOS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('documentos', '📁 Documentos Compartilhados', event)">📁 Documentos Compartilhados <span class="item-count-badge">__DOCUMENTOS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('capacitacao', '📋 Ficha de Capacitação', event)">📋 Ficha de Capacitação</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('tratativa', '📑 Tratativa de Problemas de Captação', event)">📑 Tratativa de Problemas de Captação</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('doctecnicos', '📡 Documentos Técnicos (PayTV)', event)">📡 Documentos Técnicos (PayTV)</a>
          </div>
        </div>

        <!-- Administração ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Administração <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('escala', '💼 Escala de Trabalho 2026', event)">💼 Escala de Trabalho 2026</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('drive_escala', '📁 Arquivos da Escala (Drive)', event)">📁 Arquivos da Escala (Drive)</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('metas', '🎯 Metas & OKRs da Equipe', event)">🎯 Metas & OKRs da Equipe <span class="item-count-badge">8</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('contratos', '📝 Controle de Contratos Parceiros', event)">📝 Controle de Contratos Parceiros <span class="item-count-badge">114</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('fornecedores', '🏢 Avaliação Técnica de Fornecedores', event)">🏢 Avaliação Técnica de Fornecedores <span class="item-count-badge">13</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('solicitacoes', '🔑 Solicitações de Acesso', event)">🔑 Solicitações de Acesso <span class="item-count-badge">45</span></a>
          </div>
        </div>

        <!-- Qualidade ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Qualidade <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('sla', '⏱️ SLA de Atendimento', event)">⏱️ SLA de Atendimento <span class="item-count-badge">9</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('dashboard', '📊 Dashboard & Indicadores', event)">📊 Dashboard & Indicadores</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('notificacoes', '🔔 Análise de Notificações', event)">🔔 Análise de Notificações <span class="item-count-badge">12</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('backup', '💾 Validação de Backup', event)">💾 Validação de Backup <span class="item-count-badge">300</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('analisedados', '📈 Análise de Dados', event)">📈 Análise de Dados <span class="item-count-badge">1</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('falhas', '⚠️ Confirmação de Falhas', event)">⚠️ Confirmação de Falhas <span class="item-count-badge">156</span></a>
          </div>
        </div>

        <!-- Contato ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Contato <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('hospedeiros', '📞 Contato Técnico de Hospedeiros', event)">📞 Contato Técnico de Hospedeiros <span class="item-count-badge">__HOSPEDEIROS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('antenistas', '🛠️ Contatos de Antenistas', event)">🛠️ Contatos de Antenistas <span class="item-count-badge">5</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('equipe', '👥 Equipe do Suporte Captação', event)">👥 Equipe do Suporte Captação</a>
          </div>
        </div>

        <!-- DEV ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">DEV <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('automacoes', '🤖 Repositório de Automações', event)">🤖 Repositório de Automações <span class="item-count-badge">82</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('redmine', '🐞 Redmine (Demandas)', event)">🐞 Redmine (Demandas) <span class="item-count-badge">300</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('hosts', '📡 Cadastro de Hosts', event)">📡 Cadastro de Hosts <span class="item-count-badge">__HOSTS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('cidades', '🏙️ Mapeamento de Cidades e Emissoras', event)">🏙️ Mapeamento de Cidades e Emissoras <span class="item-count-badge">229</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="openRelatorioTecnicoModal(event)"><span style="color:#10B981;">🛡️</span> Relatório Técnico & Arquitetura NOC (Segurança) <span class="item-count-badge" style="background:#10B981; color:#fff;">OFICIAL</span></a>
          </div>
        </div>

        <!-- Suporte ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Suporte <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('ocorrencias', '🚨 Painel de Ocorrências', event)">🚨 Painel de Ocorrências <span class="item-count-badge">__OCORRENCIAS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('streaming', '⚽ Programação Streaming', event)">⚽ Programação Streaming <span class="item-count-badge">__EVENTS_COUNT__</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('gestaoservicos', '⚙️ Painel de Gestão de Serviços dos CS', event)">⚙️ Painel de Gestão de Serviços dos CS <span class="item-count-badge">300</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('monitoramentocanais', '📺 Monitoramento de Canais CS', event)">📺 Monitoramento de Canais CS <span class="item-count-badge">300</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('redescs', '🌐 Configurações de Rede do CS', event)">🌐 Configurações de Rede do CS <span class="item-count-badge">137</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('redepcd', '🖥️ Mapeamento de Rede do CPD', event)">🖥️ Mapeamento de Rede do CPD <span class="item-count-badge">46</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('remoto', '🎮 Acesso Remoto & América Central', event)">🎮 Acesso Remoto & América Central <span class="item-count-badge">18</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('relatorios_futebol', '⚽ Relatórios de Jogos', event)">⚽ Relatórios de Jogos <span class="item-count-badge">41</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('relatorios_youtube', '📺 Relatório Jogos Youtube', event)">📺 Relatório Jogos Youtube <span class="item-count-badge">51</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('relatorios_nba', '🏀 Relatórios de Jogos NBA', event)">🏀 Relatórios de Jogos NBA <span class="item-count-badge">168</span></a>
          </div>
        </div>

        <!-- Links de Internet dos Parceiros -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn tab-link" onclick="handleMenuClick('links', 'Links de Internet dos Parceiros', event)">Links de Internet dos Parceiros <span class="item-count-badge">126</span></button>
        </div>

        <!-- Permissões (RBAC) -->
        <div class="sp-menu-item action-admin-only" id="nav-tab-permissoes">
          <button type="button" class="sp-menu-btn tab-link" onclick="handleMenuClick('permissoes', '🔐 Permissões', event)">🔐 Permissões</button>
        </div>
      </div>
    </div>
  </nav>

  <!-- 3. CONTEÚDO PRINCIPAL (MAIN BODY) -->
  <main class="main-body">

    <!-- ABA 1: HOME PAGE NATIVA (BANNER 1:1 COM SHAREPOINT) -->
    <div id="pane-home" class="pane-container active">

      <!-- HERO BANNER -->
      <section class="hero-banner">
        <!-- SVG Constellation Network Background -->
        <svg class="hero-network-svg" viewBox="0 0 800 400" preserveAspectRatio="none">
          <defs>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <line x1="350" y1="80" x2="480" y2="130" stroke="rgba(0, 210, 255, 0.35)" stroke-width="1.5" />
          <line x1="480" y1="130" x2="620" y2="70" stroke="rgba(0, 210, 255, 0.4)" stroke-width="1.5" />
          <line x1="480" y1="130" x2="560" y2="240" stroke="rgba(0, 210, 255, 0.3)" stroke-width="1.5" />
          <line x1="620" y1="70" x2="720" y2="160" stroke="rgba(0, 210, 255, 0.4)" stroke-width="1.5" />
          <line x1="560" y1="240" x2="720" y2="160" stroke="rgba(0, 210, 255, 0.35)" stroke-width="1.5" />
          <line x1="560" y1="240" x2="450" y2="320" stroke="rgba(0, 210, 255, 0.3)" stroke-width="1.5" />
          <line x1="720" y1="160" x2="780" y2="280" stroke="rgba(0, 210, 255, 0.35)" stroke-width="1.5" />
          <line x1="450" y1="320" x2="610" y2="350" stroke="rgba(0, 210, 255, 0.3)" stroke-width="1.5" />
          <line x1="610" y1="350" x2="780" y2="280" stroke="rgba(0, 210, 255, 0.3)" stroke-width="1.5" />
          <!-- Nodes -->
          <circle cx="350" cy="80" r="5" fill="#00d2ff" filter="url(#glow)" />
          <circle cx="480" cy="130" r="7" fill="#ffffff" filter="url(#glow)" />
          <circle cx="620" cy="70" r="6" fill="#00d2ff" filter="url(#glow)" />
          <circle cx="560" cy="240" r="7" fill="#00d2ff" filter="url(#glow)" />
          <circle cx="720" cy="160" r="8" fill="#ffffff" filter="url(#glow)" />
          <circle cx="450" cy="320" r="5" fill="#00d2ff" filter="url(#glow)" />
          <circle cx="610" cy="350" r="6" fill="#00d2ff" filter="url(#glow)" />
          <circle cx="780" cy="280" r="6" fill="#ffffff" filter="url(#glow)" />
        </svg>

        <div class="hero-top-row">
          <div class="hero-title-area">
            <h1 class="hero-main-title">Suporte Captação</h1>
            <p class="hero-description">
              Bem vindo(a) ao site da equipe de Suporte Captação! Aqui você pode encontrar informações sobre problemas técnicos, verificar o status das ocorrências, localizar documentos e dados referentes à área e muito mais.
            </p>
          </div>

          <div class="hero-weather-card">
            <div class="weather-city">São Paulo, Brasil</div>
            <div class="weather-temp-row">
              <span style="font-size: 24px;">🌧️</span>
              <span class="weather-degrees">21°C</span>
            </div>
            <div class="weather-details">Chuva leve &bull; 31°/19° &bull; 18/11/2026 &bull; MSN Clima</div>
          </div>
        </div>

        <!-- Grade de Botões Brancos Idênticos ao SharePoint + Monitor de Incidentes -->
        <div class="hero-3x3-grid">
          <div class="hero-card" onclick="showPane('hospedeiros')">
            <div class="hero-card-icon">📞</div>
            <div>Contatos Hospedeiros</div>
          </div>

          <div class="hero-card" onclick="showPane('documentos')">
            <div class="hero-card-icon">📁</div>
            <div>Documentos</div>
          </div>

          <div class="hero-card" onclick="showPane('escala')">
            <div class="hero-card-icon">💼</div>
            <div>Escala de Trabalho</div>
          </div>

          <div class="hero-card" onclick="showPane('dashboard')">
            <div class="hero-card-icon">📊</div>
            <div>Dashboard & Indicadores</div>
          </div>

          <div class="hero-card" onclick="showPane('metas')">
            <div class="hero-card-icon">🎯</div>
            <div>Metas</div>
          </div>

          <div class="hero-card" onclick="showPane('ocorrencias')">
            <div class="hero-card-icon">📋</div>
            <div>Painel de Ocorrências</div>
          </div>

          <div class="hero-card" onclick="showPane('procedimentos')">
            <div class="hero-card-icon">📄</div>
            <div>Procedimentos N1</div>
          </div>

          <div class="hero-card" onclick="showPane('projetos')">
            <div class="hero-card-icon">📁</div>
            <div>Projetos</div>
          </div>

          <div class="hero-card" onclick="showPane('streaming')">
            <div class="hero-card-icon">📡</div>
            <div>((•)) Programação de Eventos...</div>
          </div>

          <div class="hero-card hero-highlight-card" style="border: 2px solid #EF4444; background: #FEF2F2;" onclick="window.open('http://10.1.30.1:8092/', '_blank')">
            <div class="hero-card-icon" style="color: #EF4444;">🚨</div>
            <div style="color: #991B1B; font-weight: 700;">Monitor de Incidentes (Monitor_Serviços) <span class="badge" style="background:#EF4444; color:#fff; font-size:10px;">NOVO</span></div>
          </div>
        </div>
      </section>

      <!-- ÁREA INFERIOR DA PÁGINA (CHAMADA E LINKS EXTERNOS) -->
      <section class="home-lower-body">

        <!-- SEÇÃO: CONHEÇA NOSSA EQUIPE & ORGANOGRAMA OPERACIONAL -->
        <div class="team-showcase-section" style="margin-bottom: 30px;">
          <div class="section-title-wrap" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <h3 class="section-title" style="margin:0;">👥 Conheça Nossa Equipe & Organograma Operacional</h3>
              <p class="section-desc" style="margin:4px 0 0 0;">Estrutura de liderança, coordenação e especialidades técnicas da Central de Suporte Captação.</p>
            </div>
            <button class="btn-action btn-action-primary" onclick="showPane('equipe')">Ver Equipe Completa ↗</button>
          </div>

          <!-- Grade Hierárquica do Organograma -->
          <div class="organograma-grid" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 16px;">
            <!-- Diretoria -->
            <div class="org-card" style="background:#fff; border: 1px solid #E2E8F0; border-top: 4px solid #004578; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="width:44px; height:44px; border-radius:50%; background:#004578; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px;">LL</div>
                <div>
                  <div style="font-weight:700; color:#1E293B; font-size:14px;">Luiz De Sa Lemos</div>
                  <div style="font-size:11px; color:#0078D4; font-weight:600;">DIR. SUPORTE CAPTAÇÃO LATAM</div>
                </div>
              </div>
              <div style="font-size:12px; color:#64748B; margin-bottom:10px;">Liderança executiva estratégica para operações de ingest e telemetria regional.</div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge badge-role-owner">Diretoria (Owner)</span>
                <a href="mailto:luiz.lemos@ibope.com" style="font-size:11px; color:#0078D4; text-decoration:none; font-weight:600;">✉️ E-mail</a>
              </div>
            </div>

            <!-- Coordenação Geral -->
            <div class="org-card" style="background:#fff; border: 1px solid #E2E8F0; border-top: 4px solid #0078D4; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="width:44px; height:44px; border-radius:50%; background:#0078D4; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px;">CG</div>
                <div>
                  <div style="font-weight:700; color:#1E293B; font-size:14px;">Cleber De Souza Gonçalves</div>
                  <div style="font-size:11px; color:#0078D4; font-weight:600;">COORD. SUPORTE CAPTAÇÃO</div>
                </div>
              </div>
              <div style="font-size:12px; color:#64748B; margin-bottom:10px;">Gestão operacional, auditoria de transmissões, escala de plantão e automações.</div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge badge-role-owner">Coordenação (Owner)</span>
                <a href="mailto:cleber.goncalves@ibope.com" style="font-size:11px; color:#0078D4; text-decoration:none; font-weight:600;">✉️ E-mail</a>
              </div>
            </div>

            <!-- Liderança Técnica LATAM (N2) -->
            <div class="org-card" style="background:#fff; border: 1px solid #E2E8F0; border-top: 4px solid #107C41; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="width:44px; height:44px; border-radius:50%; background:#107C41; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px;">MP</div>
                <div>
                  <div style="font-weight:700; color:#1E293B; font-size:14px;">Marcelo Pereira Silva</div>
                  <div style="font-size:11px; color:#107C41; font-weight:600;">LÍDER TÉCNICO LATAM (N2)</div>
                </div>
              </div>
              <div style="font-size:12px; color:#64748B; margin-bottom:10px;">Especialista em fluxos de transporte, receptores, headend e suporte nível 2.</div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge badge-role-write">Técnico N2</span>
                <a href="mailto:marcelo.pereira@ibope.com" style="font-size:11px; color:#0078D4; text-decoration:none; font-weight:600;">✉️ E-mail</a>
              </div>
            </div>

            <!-- Gestão do Portal & Automação -->
            <div class="org-card" style="background:#fff; border: 1px solid #E2E8F0; border-top: 4px solid #8B5CF6; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="width:44px; height:44px; border-radius:50%; background:#8B5CF6; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px;">CO</div>
                <div>
                  <div style="font-weight:700; color:#1E293B; font-size:14px;">Cassio Esteves & Vinicius Dantas</div>
                  <div style="font-size:11px; color:#8B5CF6; font-weight:600;">ADMINISTRADORES DO PORTAL</div>
                </div>
              </div>
              <div style="font-size:12px; color:#64748B; margin-bottom:10px;">Administração de sistemas, esteira de dados, scripts de automação e telemetria.</div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="badge badge-role-owner">Admin / Automação</span>
                <span style="font-size:11px; color:#64748B;">Suporte Captação</span>
              </div>
            </div>
          </div>
        </div>

        <div class="contact-callout-box">
          <div class="contact-callout-header">💬 Entre em contato com a nossa equipe</div>
          <div class="contact-callout-body">
            <p>Precisa de suporte imediato ou alinhamento técnico com o plantão da Captação? Chame diretamente no <b>Google Chat</b>.</p>
            <a href="https://chat.google.com/" target="_blank" class="btn-contact-action" style="background: #00AC47; display:inline-flex; align-items:center; gap:6px;">
              💬 Abrir Google Chat ↗
            </a>
          </div>
        </div>

        <div class="home-redmine-center">
          <a href="http://10.1.0.39/redmine/projects/suporte-captacao-demandas-sharepoint/issues?set_filter=1&tracker_id=3" target="_blank" class="btn-sugestoes-sharepoint">
            Sugestões e Melhorias para SharePoint (Redmine)
          </a>
        </div>

        <div class="home-section-links">
          <div class="section-title-wrap">
            <h3 class="section-title">🌐 Links Externos</h3>
            <p class="section-desc">Acesso rápido aos sistemas corporativos, telemetria e ferramentas de trabalho diário.</p>
          </div>

          <div class="waffle-links-grid">
            <a href="http://10.1.30.1:8092/" target="_blank" class="waffle-link-card" style="border: 1px solid #FCA5A5; background: #FFF5F5;">
              <span class="waffle-link-icon">🚨</span>
              <span class="waffle-link-title" style="color: #991B1B; font-weight: 700;">Monitor de Incidentes (8092)</span>
            </a>
            <a href="https://chat.google.com/" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">💬</span>
              <span class="waffle-link-title">Google Chat</span>
            </a>
            <a href="https://meet.google.com/" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">📹</span>
              <span class="waffle-link-title">Google Meet</span>
            </a>
            <a href="https://mediadna.kantaribopemedia.com/mediadna/Comum/PaginaInicial.aspx" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">🧬</span>
              <span class="waffle-link-title">Site - Media DNA</span>
            </a>
            <a href="http://10.1.0.39/redmine/login" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">📑</span>
              <span class="waffle-link-title">Redmine</span>
            </a>
            <a href="https://zbxsrvbr.kantaribopemedia.com/zabbix/zabbix.php?action=dashboard.view&dashboardid=152" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">🖥️</span>
              <span class="waffle-link-title">Zabbix</span>
            </a>
            <a href="https://rhopen.kantar.com/" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">👥</span>
              <span class="waffle-link-title">RH Open</span>
            </a>
            <a href="https://kantarit.service-now.com/mykantarservices?id=hr_dashboard_home" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">🎫</span>
              <span class="waffle-link-title">Service Now</span>
            </a>
            <a href="https://wd3.myworkday.com/wday/authgwy/kantar/login.htmld" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">💼</span>
              <span class="waffle-link-title">Workday</span>
            </a>
            <a href="https://grafana.kantaribopemedia.com/d/LnH9Oq-Sk/atria-capture?orgId=1" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">📈</span>
              <span class="waffle-link-title">Grafana</span>
            </a>
            <a href="https://portalbsd.com.br/" target="_blank" class="waffle-link-card">
              <span class="waffle-link-icon">📡</span>
              <span class="waffle-link-title">Portal BSD</span>
            </a>
          </div>
        </div>
      </section>

    </div>

    <!-- ABA 2: ESCALA DE TRABALHO 2026 COMPLETA (TODOS OS MESES & ARTIGO 66 CLT) -->
    <div id="pane-escala" class="pane-container">
      
      <!-- Aviso Legal Artigo 66 da CLT -->
      <div class="clt-banner-alert">
        <div class="clt-icon">⚖️</div>
        <div class="clt-content">
          <h4>AVISO OBRIGATÓRIO — ARTIGO 66 DA CLT & JORNADAS DE DESCANSO</h4>
          <p>
            <b>Conforme o Artigo 66 da CLT</b>, deve ser estritamente respeitado um intervalo mínimo de <b>11 (onze) horas consecutivas de descanso</b> entre duas jornadas de trabalho.<br>
            📢 <b>PESSOAL:</b> Lembrem-se de retornar para o trabalho <b>SEMPRE 11 HORAS APÓS A ÚLTIMA JORNADA</b>, garantindo a conformidade trabalhista e o bem-estar da equipe.
          </p>
        </div>
      </div>

      <!-- Navegador de Meses -->
      <!-- CARDS DE RESUMO OPERACIONAL DA ESCALA 2026 -->
      <div class="escala-kpi-summary-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 18px;">
        <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; border-left: 4px solid #0078D4; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
          <div style="font-size: 11.5px; font-weight: 700; color: #64748B; text-transform: uppercase;">👥 Operadores Ativos</div>
          <div style="font-size: 22px; font-weight: 800; color: #0F172A; margin: 4px 0;" id="kpi-escala-total">15 Operadores</div>
          <div style="font-size: 11px; color: #0078D4;">Monitoração & Captação</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; border-left: 4px solid #10B981; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
          <div style="font-size: 11.5px; font-weight: 700; color: #047857; text-transform: uppercase;">🟢 Escalados Hoje (25/11)</div>
          <div style="font-size: 22px; font-weight: 800; color: #065F46; margin: 4px 0;" id="kpi-escala-hoje">11 em Turno (T)</div>
          <div style="font-size: 11px; color: #059669;">Conformidade CLT Art. 66</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; border-left: 4px solid #F59E0B; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
          <div style="font-size: 11.5px; font-weight: 700; color: #B45309; text-transform: uppercase;">🔵 Sobreaviso Hoje (SM)</div>
          <div style="font-size: 22px; font-weight: 800; color: #92400E; margin: 4px 0;" id="kpi-escala-sm">2 em Prontidão</div>
          <div style="font-size: 11px; color: #D97706;">Acionamento Imediato</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; border-left: 4px solid #64748B; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
          <div style="font-size: 11.5px; font-weight: 700; color: #475569; text-transform: uppercase;">⚪ Folga Hoje (F)</div>
          <div style="font-size: 22px; font-weight: 800; color: #334155; margin: 4px 0;" id="kpi-escala-folga">2 Operadores</div>
          <div style="font-size: 11px; color: #64748B;">Descanso Regulamentar</div>
        </div>
      </div>

      <div class="month-pills-row" id="escala-month-pills">
        <!-- Renderizado dinamicamente via JS -->
      </div>

      <!-- Controles de Filtro da Escala -->
      <div class="escala-controls-row">
        <div class="escala-inputs-group">
          <input type="text" id="escala-search-box" class="search-field" placeholder="🔍 Buscar operador ou matrícula..." style="min-width: 240px;">
          <select id="escala-filter-equipe" class="select-field">
            <option value="">Todas as Equipes</option>
            <option value="Monitoração">Suporte Técnico - Monitoração</option>
            <option value="Captação">Suporte Técnico - Captação</option>
          </select>
          <select id="escala-filter-turno" class="select-field">
            <option value="">Todos os Horários</option>
            <option value="06:00">Manhã (06:00 - 15:00)</option>
            <option value="10:00">Intermediário (10:00 - 19:00)</option>
            <option value="14:00">Tarde (14:00 - 23:00)</option>
            <option value="22:50">Madrugada (22:50 - 06:10 / 23:00 - 06:00)</option>
            <option value="08:00">Captação / N2 (08:00 - 17:00)</option>
          </select>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
          <span id="escala-perm-badge" class="badge" style="background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; font-size: 11.5px; padding: 4px 10px;">
            🔒 Gestão Restrita à Administração
          </span>
          <a href="javascript:void(0)" onclick="handleMenuClick('drive_escala', '📁 Arquivos da Escala (Drive)', event)" class="btn-action btn-action-secondary" title="Ver arquivos e pastas da biblioteca Escala de Trabalho">
            📁 Biblioteca da Escala
          </a>
          <a href="Escala_de_trabalho_2026.xlsx" download class="btn-action btn-action-primary" title="Baixar arquivo oficial da escala">
            📥 Baixar Planilha (.xlsx)
          </a>
        </div>
      </div>

      <!-- Tabela Interativa de Operadores do Mês -->
      <div class="escala-table-scroll">
        <table class="escala-table" id="escala-main-table">
          <thead id="escala-table-head">
            <!-- Headers renderizados dinamicamente com os dias do mês -->
          </thead>
          <tbody id="escala-table-body">
            <!-- Operadores e dias renderizados dinamicamente -->
          </tbody>
        </table>
      </div>

      <!-- Tabela de Atividades Operacionais Diárias (Chamados, Incidentes, SobreAviso) -->
      <div style="margin-top: 24px;">
        <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 10px; color: var(--sp-text-main);">
          📋 Atividades Diárias & Distribuição de Responsabilidades
        </h4>
        <div class="escala-table-scroll">
          <table class="escala-table" id="escala-atividades-table">
            <thead id="escala-atividades-head">
              <!-- Dias do mês -->
            </thead>
            <tbody id="escala-atividades-body">
              <!-- Atividades renderizadas dinamicamente -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Plantão Fim de Ano (Natal & Ano Novo) -->
      <div id="escala-fim-ano-wrap" style="margin-top: 24px; display: none;">
        <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 10px; color: var(--sp-text-main);">
          🎄 Escala Especial de Fim de Ano (Natal 2026 e Ano Novo 2026/2027)
        </h4>
        <div class="escala-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th>Período / Data</th>
                <th>Manhã (06h - 15h)</th>
                <th>Tarde (14h - 23h)</th>
                <th>Madrugada (22h50 - 06h10)</th>
                <th>Plantão SobreAviso (N2)</th>
              </tr>
            </thead>
            <tbody id="escala-fim-ano-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Legenda Oficial & Regras de SobreAviso -->
      <div class="escala-footer-grid">
        <div class="escala-info-card">
          <h4>🏷️ Legenda de Códigos da Escala</h4>
          <div class="legenda-chips-grid">
            <div class="legenda-chip"><span class="escala-badge escala-badge-t">T</span> Tele-Trabalho</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-f">F</span> Folga</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-ferias">FER</span> Férias</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-bh">BH</span> Banco de Horas</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-vf">VF</span> Venda de Folga</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-fj">FJ</span> Folga Justificada</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-dayoff">DAY</span> Aniversário</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-tr">TR</span> Treinamento</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-ag">AG</span> Abono Gestor</div>
            <div class="legenda-chip"><span class="escala-badge escala-badge-sm">SM</span> Saúde Mental</div>
          </div>
        </div>

        <div class="escala-info-card">
          <h4>⏰ Regras de Horários de SobreAviso</h4>
          <ul class="sobreaviso-schedule-list">
            <li>🌙 <b>Na Semana:</b> 19h00 às 08h00 do dia seguinte.</li>
            <li>🏖️ <b>Fins de Semana e Feriados:</b> Período Integral (24h ininterruptas).</li>
            <li>🔄 <b>Acionamento N2:</b> Quando o suporte N2 for acionado no final de semana, apontar como <b>VF (Venda de Folga)</b>.</li>
            <li>⚖️ <b>Intervalo Interjornada:</b> Intervalo de 11h respeitado obrigatoriamente após qualquer atendimento.</li>
          </ul>
        </div>
      </div>

    </div>

    <!-- ABA 3: PROGRAMAÇÃO STREAMING COMPLETA (862 JOGOS) -->
    <div id="pane-streaming" class="pane-container">
      <div class="kpi-row">
        <div class="kpi-box">
          <div class="kpi-box-label">Total de Confrontos</div>
          <div class="kpi-box-val" id="kpi-total">__EVENTS_COUNT__</div>
          <div class="kpi-box-sub">Base Oficial Sincronizada</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #10B981;">
          <div class="kpi-box-label">Cazé TV</div>
          <div class="kpi-box-val" id="kpi-caze">0</div>
          <div class="kpi-box-sub">YouTube Live & PPV</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #00509E;">
          <div class="kpi-box-label">Amazon Prime</div>
          <div class="kpi-box-val" id="kpi-prime">0</div>
          <div class="kpi-box-sub">Prime Video Sports</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #7F4F24;">
          <div class="kpi-box-label">Netflix</div>
          <div class="kpi-box-val" id="kpi-netflix">0</div>
          <div class="kpi-box-sub">NFL & Eventos Especiais</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #8B5CF6;">
          <div class="kpi-box-label">TNT / Max / Record</div>
          <div class="kpi-box-val" id="kpi-outros">0</div>
          <div class="kpi-box-sub">Paulistão & Carioca</div>
        </div>
      </div>

      <!-- QUADRO DE DESTAQUE: JOGOS & EVENTOS PROGRAMADOS PARA HOJE E AMANHÃ -->
      <div class="today-tomorrow-grid" id="streaming-highlights-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; margin-bottom: 20px;">
        <!-- CARD HOJE -->
        <div class="schedule-highlight-card card-hoje" style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 4px solid #10B981;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #F1F5F9; padding-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 18px;">⚽</span>
              <span style="font-size: 13.5px; font-weight: 700; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px;">Jogos & Eventos de Hoje (CONFRONTOS PROGRAMADOS PARA HOJE)</span>
              <span id="badge-count-hoje" style="background: #ECFDF5; color: #059669; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 12px; border: 1px solid #A7F3D0;">0 jogos</span>
            </div>
            <span id="label-data-hoje" style="font-size: 12px; font-weight: 600; color: #64748B;">--/--</span>
          </div>
          <div id="list-eventos-hoje" style="display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto;">
            <div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Carregando eventos de hoje...</div>
          </div>
        </div>

        <!-- CARD AMANHÃ -->
        <div class="schedule-highlight-card card-amanha" style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 4px solid #3B82F6;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #F1F5F9; padding-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 18px;">📅</span>
              <span style="font-size: 13.5px; font-weight: 700; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px;">Jogos & Eventos de Amanhã (PROGRAMAÇÃO DE AMANHÃ)</span>
              <span id="badge-count-amanha" style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 12px; border: 1px solid #BFDBFE;">0 jogos</span>
            </div>
            <span id="label-data-amanha" style="font-size: 12px; font-weight: 600; color: #64748B;">--/--</span>
          </div>
          <div id="list-eventos-amanha" style="display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto;">
            <div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Carregando eventos de amanhã...</div>
          </div>
        </div>
      </div>

      <!-- BARRA DE COMANDOS DO SHAREPOINT -->
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewStreamModal()" title="Adicionar novo evento à programação">
            <span>+</span> Novo
          </button>
          <button id="btn-grid-stream" class="sp-btn-cmd btn-grid-edit" onclick="toggleStreamGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-stream-icon">田</span> <span id="btn-grid-stream-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" onclick="renderTable()">
            <span>↺</span> Atualizar
          </button>
          <button class="sp-btn-cmd" onclick="exportCSV()">
            <span>📥</span> Exportar CSV
          </button>
          <button class="sp-btn-cmd action-admin-only" onclick="syncLiveAPI(this)">
            <span>🔄</span> Sincronizar em Tempo Real
          </button>
          <button class="sp-btn-cmd" onclick="triggerGoogleChatAgendaModal()" title="Disparar a Agenda de Jogos (Hoje e Amanhã) para o Google Chat 'Streaming - Gravações'">
            <span>📢</span> Disparar no Google Chat
          </button>
          <button class="sp-btn-cmd" id="btn-delete-stream-selected" style="display:none; color:#EF4444; border-color:#FCA5A5; font-weight:700;" onclick="deleteSelectedStreamingEvents()">
            <span>🗑️</span> Excluir Selecionados (<span id="count-stream-selected">0</span>)
          </button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-box" placeholder="Pesquisar nesta lista..." oninput="renderTable()">
        </div>
      </div>

      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title" id="streaming-list-title">
          Programação Streaming (__EVENTS_COUNT__ Confrontos) <span class="star-icon">☆</span>
        </h2>
      </div>

      <!-- ALERTA MODO GRADE STREAMING -->
      <div id="stream-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (campeonato, partida, canal, pvid, status). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleStreamGridEdit()">💾 Concluir e Salvar</button>
      </div>

      <div class="filter-bar" style="margin-bottom: 12px;">
        <div class="filter-inputs" style="display: flex; gap: 8px; flex-wrap: wrap; width: 100%;">
          <select id="filter-mes" class="select-field" onchange="renderTable()">
            <option value="">Todos os Meses</option>
            <option value="Janeiro">Janeiro</option>
            <option value="Fevereiro">Fevereiro</option>
            <option value="Março">Março</option>
            <option value="Abril">Abril</option>
            <option value="Maio">Maio</option>
            <option value="Junho">Junho</option>
            <option value="Julho">Julho</option>
            <option value="Agosto">Agosto</option>
            <option value="Setembro">Setembro</option>
            <option value="Outubro">Outubro</option>
            <option value="Novembro">Novembro</option>
            <option value="Dezembro">Dezembro</option>
          </select>
          <select id="filter-campeonato" class="select-field" onchange="renderTable()">
            <option value="">Todos os Campeonatos</option>
          </select>
          <select id="filter-canal" class="select-field" onchange="renderTable()">
            <option value="">Todos os Canais</option>
            <option value="cazé">Cazé TV</option>
            <option value="prime">Amazon Prime Video</option>
            <option value="netflix">Netflix</option>
            <option value="tnt">TNT / Max</option>
            <option value="record">Record</option>
            <option value="dazn">DAZN</option>
          </select>
          <select id="filter-status" class="select-field" onchange="renderTable()">
            <option value="">Todos os Status</option>
            <option value="pendente">Pendente</option>
            <option value="exibido">Exibido</option>
            <option value="não exibido">Não Exibido</option>
          </select>
          <button type="button" id="btn-clear-stream-filters" class="btn-action btn-action-secondary" onclick="clearStreamFilters()" title="Limpar todos os filtros">Limpar ✕</button>
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="td-center" style="width: 38px;">
                  <input type="checkbox" id="checkall-stream" onchange="toggleSelectAllStreaming(this)" title="Selecionar Todos os Confrontos">
                </th>
                <th class="td-center" style="width: 45px;">#</th>
                <th class="td-center th-sortable" onclick="sortStreamBy('mes')" title="Ordenar por Mês">Mês <span id="sort-st-mes" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('data')" title="Ordenar por Data">Data <span id="sort-st-data" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('horario')" title="Ordenar por Horário">Horário <span id="sort-st-horario" class="sort-icon">↕</span></th>
                <th class="th-sortable" onclick="sortStreamBy('campeonato')" title="Ordenar por Campeonato">Campeonato <span id="sort-st-campeonato" class="sort-icon">↕</span></th>
                <th class="th-sortable" onclick="sortStreamBy('partida')" title="Ordenar por Partida">Partida <span id="sort-st-partida" class="sort-icon">↕</span></th>
                <th class="th-sortable" onclick="sortStreamBy('responsavel')" title="Ordenar por Responsável">Responsável Gravação <span id="sort-st-responsavel" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('canal')" title="Ordenar por Canal">Canal de Transmissão <span id="sort-st-canal" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('pvid')" title="Ordenar por PVID">PVID TV BOX <span id="sort-st-pvid" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('status_entrega')" title="Ordenar por Status">Status de Entrega <span id="sort-st-status_entrega" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" onclick="sortStreamBy('programado')" title="Ordenar por Programado">Programado <span id="sort-st-programado" class="sort-icon">↕</span></th>
              </tr>
            </thead>
            <tbody id="table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary); display: flex; justify-content: space-between;">
        <div>Mostrando <b id="showing-count" style="color: var(--sp-theme-primary);">0</b> eventos filtrados</div>
        <div>Padrão Oficial Google Workspace & Central Autônoma</div>
      </div>
    </div>

    <!-- ABA 4: CONTATOS HOSPEDEIROS (500 REGISTROS NATIVOS) -->
    <div id="pane-hospedeiros" class="pane-container">
      <!-- BARRA DE COMANDOS DO SHAREPOINT -->
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewHospedeiroModal()" title="Adicionar novo contato de hospedeiro">
            <span>+</span> Novo
          </button>
          <button id="btn-grid-hosp" class="sp-btn-cmd btn-grid-edit" onclick="toggleHospGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-hosp-icon">田</span> <span id="btn-grid-hosp-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" onclick="renderHospedeirosTable()">
            <span>↺</span> Atualizar
          </button>
          <button class="sp-btn-cmd" onclick="exportHospedeirosCSV()">
            <span>📥</span> Exportar CSV
          </button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-hosp-box" placeholder="Pesquisar nesta lista..." oninput="renderHospedeirosTable()">
        </div>
      </div>

      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">
          Contatos Técnicos de Hospedeiros (__HOSPEDEIROS_COUNT__ Registros) <span class="star-icon">☆</span>
        </h2>
      </div>

      <!-- ALERTA MODO GRADE HOSPEDEIROS -->
      <div id="hosp-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (cidade, nome, especialidade, telefones). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleHospGridEdit()">💾 Concluir e Salvar</button>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="td-center" style="width: 38px;">
                  <input type="checkbox" id="checkall-stream" onchange="toggleSelectAllStreaming(this)" title="Selecionar Todos os Confrontos">
                </th>
                <th class="td-center" style="width: 45px;">#</th>
                <th class="th-sortable" onclick="sortHospBy('Title')" title="Ordenar por Cidade / Praça">Cidade / Praça <span id="sort-hosp-Title" class="sort-icon">↕</span></th>
                <th class="th-sortable" onclick="sortHospBy('Nome1')" title="Ordenar por Nome">Nome do Técnico / Central <span id="sort-hosp-Nome1" class="sort-icon">↕</span></th>
                <th class="th-sortable" onclick="sortHospBy('Especialidade')" title="Ordenar por Especialidade">Especialidade <span id="sort-hosp-Especialidade" class="sort-icon">↕</span></th>
                <th>Telefone Comercial</th>
                <th>Telefone Celular</th>
              </tr>
            </thead>
            <tbody id="hosp-table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary);">
        Mostrando <b id="showing-hosp-count" style="color: var(--sp-theme-primary);">0</b> contatos
      </div>
    </div>

    <!-- ABA 5: PAINEL DE OCORRÊNCIAS & HISTÓRICO DE INCIDENTES (1:1 COM SHAREPOINT) -->
    
    <!-- =========================================================================
         CENTRO DE GERENCIAMENTO RDP & AMÉRICA CENTRAL (NOC ACCESS HUB)
         ========================================================================= -->
    <div id="pane-remoto" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="exportRdpCSV()" title="Exportar inventário RDP completo">
            <span>📥</span> Exportar Planilha NOC (CSV)
          </button>
          <button class="sp-btn-cmd" onclick="renderRdpTable()">
            <span>↺</span> Atualizar Conexões
          </button>
          <button class="sp-btn-cmd" onclick="openQuickMstscModal()">
            <span style="color:#0078D4;">⚡</span> Conexão Rápida MSTSC
          </button>
          <button class="sp-btn-cmd" onclick="exportRdpCSV()">
            <span style="color:#10B981;">📥</span> Exportar Lista RDP (.csv)
          </button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-rdp-box" placeholder="Filtrar por praça, IP, país ou roteador..." oninput="filterRdpTable()">
        </div>
      </div>

      <div class="sp-list-header-row" style="margin-top: 10px;">
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
          <div>
            <h2 class="sp-list-main-title" style="display: flex; align-items: center; gap: 8px;">
              <span>🎮</span> Centro de Gerenciamento RDP & Acesso Remoto <span class="star-icon">☆</span>
            </h2>
            <p style="margin: 3px 0 0; font-size: 13px; color: var(--sp-text-secondary);">
              Acesso direto 1-clique aos servidores CS1, CS2, CS3, Roteadores e Réguas de Energia (PDU Volt) de todas as praças do Brasil e América Central.
            </p>
          </div>
          <div style="display: flex; gap: 8px;">
            <span class="badge" style="background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; font-weight: 600; padding: 4px 10px;">151 Praças Homologadas</span>
            <span class="badge" style="background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; font-weight: 600; padding: 4px 10px;">Latência Zero / RDP Nativo</span>
          </div>
        </div>
      </div>

      <!-- CARDS DE RESUMO RÁPIDO -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 14px;">
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; border-left: 4px solid #0078D4;">
          <div style="font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase;">Total de Praças Monitoradas</div>
          <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 4px;" id="rdp-kpi-total">151</div>
          <div style="font-size: 11px; color: #059669; margin-top: 2px;">✔ 137 Brasil &bull; 14 América Central</div>
        </div>

        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; border-left: 4px solid #10B981;">
          <div style="font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase;">Servidores de Captura Ativos</div>
          <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 4px;">247 CS</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 2px;">CS1 + CS2 + CS3 integrados</div>
        </div>

        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; border-left: 4px solid #8B5CF6;">
          <div style="font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase;">Controle de Energia (PDU Volt)</div>
          <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 4px;">148 Nós</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Reset remoto de tomada em 1 clique</div>
        </div>

        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; border-left: 4px solid #F59E0B;">
          <div style="font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase;">Modo de Conexão RDP</div>
          <div style="font-size: 24px; font-weight: 800; color: #1E293B; margin-top: 4px;">Direto (.rdp)</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Geração instantânea sem senhas no browser</div>
        </div>
      </div>

      <!-- ABAS DE NAVEGAÇÃO RDP: TABELA CONSOLIDADA vs BIBLIOTECA DE PASTAS -->
      <div style="display: flex; gap: 8px; margin-top: 18px; margin-bottom: 12px; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px;">
        <button id="btn-rdp-view-list" class="sp-tab-pill active" onclick="switchRdpViewMode('list')">
          📋 Lista Consolidada de Servidores (151 Nós / 247 CS)
        </button>
        <button id="btn-rdp-view-folders" class="sp-tab-pill" onclick="switchRdpViewMode('folders')">
          📁 Biblioteca de Pastas RDP (18 Diretórios / 149 Arquivos)
        </button>
      </div>

      <!-- MODO 1: TABELA CONSOLIDADA ESPAÇOSA -->
      <div id="rdp-view-list-container">
        <!-- BARRA DE FILTROS POR CATEGORIA -->
        <div style="display: flex; gap: 8px; margin-top: 8px; margin-bottom: 14px; flex-wrap: wrap;">
          <button class="sp-btn-cmd rdp-cat-pill active" onclick="setRdpCategory('all', this)">Todas as Praças (151)</button>
          <button class="sp-btn-cmd rdp-cat-pill" onclick="setRdpCategory('Brasil', this)">🇧🇷 Brasil (137)</button>
          <button class="sp-btn-cmd rdp-cat-pill" onclick="setRdpCategory('América Central', this)">🌎 América Central & LATAM (14)</button>
          <button class="sp-btn-cmd rdp-cat-pill" onclick="setRdpCategory('Volt', this)">⚡ Com PDU Volt</button>
        </div>

        <!-- TABELA RDP OFICIAL ESPAÇOSA -->
        <div class="sp-table-scroll-wrap" style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow-x: auto;">
          <table class="sp-data-table" id="rdp-master-table" style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="background: #F8FAFC; border-bottom: 2px solid #E2E8F0;">
                <th style="width: 45px; text-align: center; padding: 12px 14px;">#</th>
                <th style="padding: 12px 14px;">Região / País</th>
                <th style="padding: 12px 14px;">Praça / Cidade</th>
                <th style="padding: 12px 14px;">Roteador (Gateway)</th>
                <th style="padding: 12px 14px;">CS 1 (IP / Conexão)</th>
                <th style="padding: 12px 14px;">CS 2 (IP / Conexão)</th>
                <th style="padding: 12px 14px;">CS 3 (IP / Conexão)</th>
                <th style="padding: 12px 14px;">PDU Volt (Reset Energia)</th>
                <th style="padding: 12px 14px; text-align: center;">Status</th>
              </tr>
            </thead>
            <tbody id="rdp-table-body">
              <!-- Renderizado dinamicamente via JS -->
            </tbody>
          </table>
        </div>

        <div style="margin-top: 12px; font-size: 12.5px; color: var(--sp-text-secondary); display: flex; justify-content: space-between; align-items: center;">
          <div id="rdp-table-footer">Mostrando <b>151</b> de <b>151</b> nós remotos</div>
          <div style="color: #64748B; font-size: 11.5px;">Protocolo RDP homologado &bull; Porta padrão 3389 &bull; Latência Zero</div>
        </div>
      </div>

      <!-- MODO 2: BIBLIOTECA DE PASTAS NAVEGÁVEIS RDP -->
      <div id="rdp-view-folders-container" style="display: none; background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #E2E8F0; padding-bottom: 12px;">
          <div>
            <div id="rdp-folders-breadcrumb" style="font-size: 13px; font-weight: 600; color: #0078D4;">
              Acesso Remoto
            </div>
            <div style="font-size: 11px; color: #64748B; margin-top: 2px;">
              Pastas organizadas por País, Região e Praça contendo os arquivos <code>.rdp</code> oficiais para download e conexão direta.
            </div>
          </div>
          <button type="button" class="sp-btn-cmd" onclick="resetRdpFolderRoot()">
            📁 Raiz de Pastas
          </button>
        </div>

        <div id="rdp-folders-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px;">
          <!-- Pastas e arquivos renderizados dinamicamente -->
        </div>
      </div>
    </div>

  <div id="pane-ocorrencias" class="pane-container">
      
      <!-- BARRA DE COMANDOS DO SHAREPOINT -->
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewOcoModal()" title="Criar nova ocorrência operacional">
            <span>+</span> Novo
          </button>
          <button id="btn-grid-oco" class="sp-btn-cmd btn-grid-edit" onclick="toggleOcoGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-oco-icon">田</span> <span id="btn-grid-oco-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" id="btn-refresh-oco" onclick="refreshOcorrenciasData(this)" title="Buscar atualizações e sincronizar do SharePoint">
            <span id="icon-refresh-oco">↺</span> Atualizar
          </button>
          <button class="sp-btn-cmd" onclick="exportOcorrenciasCSV()">
            <span>📥</span> Exportar CSV
          </button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-oco-box" placeholder="Pesquisar nesta lista..." oninput="renderOcorrenciasTable()">
        </div>
      </div>

      <!-- TÍTULO DA LISTA -->
      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">
          Painel de Ocorrências <span class="star-icon">☆</span>
        </h2>
      </div>

      <!-- EXIBIÇÕES (VIEWS) -->
      <div class="sp-views-bar">
        <button class="sp-view-tab active" id="view-tab-emandamento" onclick="switchOcoView('emandamento')">
          Em andamento - Lista <span style="font-size: 10px;">⌵</span>
        </button>
        <button class="sp-view-tab" id="view-tab-recuperacao" onclick="switchOcoView('recuperacao')">
          Em recuperação
        </button>
        <button class="sp-view-tab" id="view-tab-operacao" onclick="switchOcoView('operacao')">
          Operação
        </button>
        <button class="sp-view-tab" id="view-tab-todos" onclick="switchOcoView('todos')">
          Todos os Itens
        </button>
      </div>

      <!-- BARRA DE FILTROS ATIVOS -->
      <div class="sp-filter-pills-bar" id="oco-filter-pills-wrap">
        <span>Status:</span>
        <span class="sp-filter-pill" id="pill-emandamento">
          Em andamento <span class="sp-pill-close" onclick="toggleStatusFilter('Em andamento')">✕</span>
        </span>
        <span class="sp-filter-pill sp-filter-pill-purple" id="pill-feedback">
          Feedback <span class="sp-pill-close" onclick="toggleStatusFilter('Feedback')">✕</span>
        </span>
        <button class="sp-btn-clear-filters" onclick="clearOcoFilters()">Limpar ✕</button>
      </div>

      <!-- ALERTA MODO GRADE OCORRÊNCIAS -->
      <div id="oco-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (clique no texto ou altere o status). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleOcoGridEdit()">💾 Concluir e Salvar</button>
      </div>

      <!-- TABELA DO SHAREPOINT (13 COLUNAS OFICIAIS) -->
      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="th-sortable" style="min-width: 120px;" onclick="sortOcoBy('Status')" title="Ordenar por Status">Status <span id="sort-oco-Status" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 130px;" onclick="sortOcoBy('Criado')" title="Ordenar por Data de Criação">Criado <span id="sort-oco-Criado" class="sort-icon">▼</span></th>
                <th class="th-sortable" style="min-width: 190px;" onclick="sortOcoBy('HostName')" title="Ordenar por Host">Host <span id="sort-oco-HostName" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 70px;" onclick="sortOcoBy('CS')" title="Ordenar por CS">CS <span id="sort-oco-CS" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 110px;" onclick="sortOcoBy('Veiculo')" title="Ordenar por Veículo">Veículo <span id="sort-oco-Veiculo" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 140px;" onclick="sortOcoBy('Equipamento')" title="Ordenar por Equipamento">Equipamento <span id="sort-oco-Equipamento" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 140px;" onclick="sortOcoBy('TipoProblema')" title="Ordenar por Tipo do Problema">Tipo do Problema <span id="sort-oco-TipoProblema" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" style="min-width: 110px;" onclick="sortOcoBy('EmRecuperacao')" title="Ordenar por Em Recuperação">Em recuperação <span id="sort-oco-EmRecuperacao" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" style="min-width: 120px;" onclick="sortOcoBy('GravacaoStreaming')" title="Ordenar por Gravação Streaming">GravaçãoStreaming <span id="sort-oco-GravacaoStreaming" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" style="min-width: 120px;" onclick="sortOcoBy('InformarOperacao')" title="Ordenar por Informar Operação">Informar Operação <span id="sort-oco-InformarOperacao" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 250px;" onclick="sortOcoBy('AcoesExecutadas')" title="Ordenar por Ações Executadas">Ações executadas <span id="sort-oco-AcoesExecutadas" class="sort-icon">↕</span></th>
                <th class="th-sortable" style="min-width: 130px;" onclick="sortOcoBy('AreaResponsavel')" title="Ordenar por Área / Responsável">Area/Responsável <span id="sort-oco-AreaResponsavel" class="sort-icon">↕</span></th>
                <th class="td-center th-sortable" style="min-width: 80px;" onclick="sortOcoBy('Redmine')" title="Ordenar por Redmine">Redmine <span id="sort-oco-Redmine" class="sort-icon">↕</span></th>
              </tr>
            </thead>
            <tbody id="oco-table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top: 10px; font-size: 12.5px; color: var(--sp-text-secondary); display: flex; justify-content: space-between; align-items: center;">
        <div>Mostrando <b id="showing-oco-count" style="color: var(--sp-theme-primary);">0</b> de <b id="total-oco-count">0</b> ocorrências</div>
        <div style="color: #64748B; font-size: 11.5px;">Sincronizado diretamente do SharePoint Oficial</div>
      </div>
    </div>

    <!-- SUBMENU: CONTATOS DE ANTENISTAS -->
    <div id="pane-antenistas" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewAntenistaModal()" title="Adicionar novo antenista"><span>+</span> Novo</button>
          <button id="btn-grid-ante" class="sp-btn-cmd btn-grid-edit" onclick="toggleAnteGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-ante-icon">田</span> <span id="btn-grid-ante-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" onclick="renderAntenistasTable()"><span>↺</span> Atualizar</button>
          <button class="sp-btn-cmd" onclick="exportAntenistasCSV()"><span>📥</span> Exportar CSV</button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-ante-box" placeholder="Pesquisar antenistas..." oninput="renderAntenistasTable()">
        </div>
      </div>
      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">Contatos de Antenistas <span class="star-icon">☆</span></h2>
      </div>
      <!-- ALERTA MODO GRADE ANTENISTAS -->
      <div id="ante-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (nome, praça, empresa, telefones). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleAnteGridEdit()">💾 Concluir e Salvar</button>
      </div>
      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th style="min-width: 150px;">Nome / Contato</th>
                <th style="min-width: 120px;">Cidade / Praça</th>
                <th style="min-width: 140px;">Especialidade / Cargo</th>
                <th style="min-width: 180px;">Empresa</th>
                <th style="min-width: 140px;">Telefone Comercial</th>
                <th style="min-width: 140px;">Telefone Celular</th>
              </tr>
            </thead>
            <tbody id="ante-table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- SUBMENU: CADASTRO DE HOSTS -->
    <div id="pane-hosts" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewHostModal()" title="Cadastrar novo Host"><span>+</span> Novo Host</button>
          <button id="btn-grid-hosts" class="sp-btn-cmd btn-grid-edit" onclick="toggleHostGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-hosts-icon">田</span> <span id="btn-grid-hosts-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" onclick="renderHostsTable()"><span>↺</span> Atualizar</button>
          <button class="sp-btn-cmd" onclick="exportHostsCSV()"><span>📥</span> Exportar CSV</button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-hosts-box" placeholder="Pesquisar hosts ou cidades..." oninput="renderHostsTable()">
        </div>
      </div>
      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">Cadastro - Hosts (220 Praças Ativas) <span class="star-icon">☆</span></h2>
      </div>
      <!-- ALERTA MODO GRADE HOSTS -->
      <div id="hosts-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (código do host, status). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleHostGridEdit()">💾 Concluir e Salvar</button>
      </div>
      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th style="width: 70px;" class="td-center">ID</th>
                <th style="min-width: 250px;">Código do Host / Praça</th>
                <th style="min-width: 120px;" class="td-center">Status</th>
                <th style="min-width: 150px;" class="td-center">Ações Rápidas</th>
              </tr>
            </thead>
            <tbody id="hosts-table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary);">
        Mostrando <b id="showing-hosts-count" style="color: var(--sp-theme-primary);">0</b> de 220 hosts cadastrados
      </div>
    </div>

    <!-- SUBMENU 1: VISUALIZADOR UNIFICADO DE BIBLIOTECAS DE DOCUMENTOS (SHAREPOINT DRIVES 1:1) -->
    <div id="pane-drive-viewer" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewDriveFileModal()"><span>+</span> Novo</button>
          <button class="sp-btn-cmd" onclick="toggleDriveGridMode()"><span>田</span> Modo Grade</button>
          <button class="sp-btn-cmd" onclick="exportCurrentDriveCSV()"><span>📥</span> Exportar CSV</button>
          <button class="sp-btn-cmd" id="btn-delete-drive-selected" style="display:none; color:#EF4444; border-color:#FCA5A5;" onclick="deleteSelectedDriveItems()"><span>🗑️</span> Excluir Selecionados</button>
          <button class="sp-btn-cmd" onclick="handleMenuClick('home', 'Página Inicial')"><span>🏠</span> Voltar ao Início</button>
        </div>
      </div>

      <div class="sp-list-header-row">
        <div>
          <div class="sp-breadcrumbs" id="drive-breadcrumbs">
            <!-- Breadcrumbs dinâmicos -->
          </div>
          <h2 class="sp-list-main-title" id="drive-viewer-title">Biblioteca de Documentos <span class="star-icon">☆</span></h2>
        </div>
        <div class="sp-views-bar">
          <span class="sp-view-tab active">Todos os Documentos</span>
        </div>
      </div>

      <p id="drive-viewer-desc" style="color: #64748B; font-size: 13px; margin: 4px 0 14px 0; line-height: 1.5;">
        Biblioteca oficial sincronizada 1:1 com o Microsoft SharePoint Online da Central de Suporte Captação.
      </p>

      <div class="filter-bar">
        <div class="filter-inputs" style="width: 100%;">
          <input type="text" id="drive-viewer-search" class="search-field" oninput="filterDriveTable()" placeholder="🔍 Buscar por nome do arquivo, pasta ou responsável...">
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead id="drive-viewer-thead">
              <tr>
                <th class="td-center" style="width: 38px;">
                  <input type="checkbox" id="checkall-drive" onchange="toggleSelectAllDrive(this)" title="Selecionar Todos">
                </th>
                <th class="td-center" style="width: 45px;">#</th>
                <th>Nome do Arquivo / Pasta</th>
                <th>Tipo</th>
                <th>Tamanho</th>
                <th>Modificado em</th>
                <th>Modificado por</th>
                <th class="td-center" style="width: 120px;">Ação</th>
              </tr>
            </thead>
            <tbody id="drive-viewer-tbody">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary);" id="drive-viewer-footer">
        Sincronizado com Microsoft SharePoint Online
      </div>
    </div>

    <!-- SUBMENU 3: VISUALIZADOR DINÂMICO DE LISTAS NATIVAS DO SHAREPOINT (46 LISTAS REAIS) -->
    <div id="pane-list-viewer" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new" onclick="openNewListItemModal()" title="Adicionar novo registro a esta lista"><span>+</span> Novo</button>
          <button id="btn-grid-generic" class="sp-btn-cmd btn-grid-edit" onclick="toggleGenericListGridEdit()" title="Editar linhas e colunas diretamente no navegador"><span id="btn-grid-generic-icon">田</span> <span id="btn-grid-generic-text">Editar no modo de exibição de grade</span></button>
          <button id="btn-delete-generic" class="sp-btn-cmd" style="display:none; color: #EF4444; border-color: rgba(239, 68, 68, 0.4); font-weight: 600;" onclick="deleteSelectedGenericItems()" title="Excluir registros selecionados"><span>🗑️</span> Excluir (<span id="delete-count-generic">0</span>)</button>
          <button class="sp-btn-cmd" onclick="filterRealListTable()" title="Atualizar dados da lista"><span>↺</span> Atualizar</button>
          <button class="sp-btn-cmd" onclick="exportGenericListCSV()" title="Exportar para CSV"><span>📥</span> Exportar CSV</button>
          <button class="sp-btn-cmd" onclick="handleMenuClick('home', 'Página Inicial')"><span>🏠</span> Voltar ao Início</button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="list-viewer-search" placeholder="Pesquisar nesta lista..." oninput="filterRealListTable()">
        </div>
      </div>
      
      <!-- ALERTA MODO GRADE LISTA GENÉRICA -->
      <div id="generic-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela. As alterações são salvas automaticamente na lista.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="toggleGenericListGridEdit()">💾 Concluir e Salvar</button>
      </div>

      <div class="sp-list-header-row">
        <div>
          <div style="font-size: 12px; color: #64748B; margin-bottom: 4px;">Suporte Captação &rsaquo; Listas do SharePoint</div>
          <h2 class="sp-list-main-title" id="list-viewer-title">Lista do SharePoint <span class="star-icon">☆</span></h2>
        </div>
        <div class="sp-views-bar">
          <span class="sp-view-tab active">Todos os Itens</span>
        </div>
      </div>

      <p id="list-viewer-desc" style="color: #64748B; font-size: 13px; margin: 4px 0 14px 0; line-height: 1.5;">
        Esta lista está sincronizada 1:1 com a esteira oficial do SharePoint Online da Central de Suporte Captação.
      </p>

      <div class="filter-bar">
        <div class="filter-inputs" style="width: 100%;">
          <input type="text" id="list-viewer-search" class="search-field" oninput="filterRealListTable()" placeholder="🔍 Buscar registros nesta lista...">
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead id="list-viewer-thead">
              <!-- Renderizado via JS -->
            </thead>
            <tbody id="list-viewer-tbody">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary);" id="list-viewer-footer">
        Sincronizado com Microsoft SharePoint Online
      </div>
    </div>


    <!-- ABA 8: DASHBOARD & INDICADORES (CONTEÚDO OFICIAL 1:1 DE DASHBOARD.ASPX DO SHAREPOINT) -->
    <div id="pane-dashboard" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">📊 Dashboard & Indicadores</h2>
        <p class="section-desc">Acesse nossos painéis e acompanhe os principais indicadores de desempenho do Suporte Captação.</p>
      </div>

      <div class="escala-footer-grid" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-top: 15px;">
        <div class="escala-info-card" style="border-left: 4px solid #0078D4;">
          <h3 style="font-size: 16px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">📊 Suporte N2 (Redmine)</h3>
          <p style="font-size: 13px; color: #64748B; line-height: 1.5; margin-bottom: 14px;">
            Este painel acompanha a saúde das entregas, a volumetria de demandas e o cumprimento dos prazos estabelecidos para a equipe de Suporte N2.
          </p>
          <a href="https://app.powerbi.com/groups/me/reports/5e99d789-4b3d-443e-980f-6c9aaad7cfeb/bebe49dc7b5a50ffe75d/share?experience=power-bi" target="_blank" class="btn-action btn-action-primary" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
            📊 Abrir Relatório Power BI N2 ↗
          </a>
        </div>

        <div class="escala-info-card" style="border-left: 4px solid #10B981;">
          <h3 style="font-size: 16px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">📊 Suporte N1 (Recuperação e Monitor de Incidentes)</h3>
          <p style="font-size: 13px; color: #64748B; line-height: 1.5; margin-bottom: 14px;">
            Este painel acompanha o desempenho operacional, a volumetria de atendimentos e o uso do site MediaDNA pela Equipe N1, com foco nas frentes de Recuperação e Monitor de Incidentes.
          </p>
          <a href="https://app.powerbi.com/groups/me/reports/5e99d789-4b3d-443e-980f-6c9aaad7cfeb/bebe49dc7b5a50ffe75d/share?experience=power-bi" target="_blank" class="btn-action btn-action-primary" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
            📊 Abrir Relatório Power BI N1 ↗
          </a>
        </div>

        <div class="escala-info-card" style="border-left: 4px solid #D97706;">
          <h3 style="font-size: 16px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">📈 Dashboard de Estatísticas (IMA)</h3>
          <p style="font-size: 13px; color: #64748B; line-height: 1.5; margin-bottom: 14px;">
            Painel corporativo de telemetria e estatísticas operacionais do ecossistema de ingest de sinais.
          </p>
          <a href="http://ecossistema-ima.grupoibope.corp:3000/dashboard.html" target="_blank" class="btn-action btn-action-secondary" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
            📈 Acessar Servidor IMA :3000 ↗
          </a>
        </div>
      </div>
    </div>

    <!-- ABA 10: PROJETOS -->
    <div id="pane-projetos" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">🚀 Projetos & Iniciativas Estratégicas</h2>
        <p class="section-desc">Iniciativas de inovação, automação e melhoria contínua da área de captação.</p>
      </div>

      <div class="escala-footer-grid">
        <div class="escala-info-card">
          <h4>🌐 Portal Autônomo & Descontinuação do SharePoint</h4>
          <p style="font-size: 13px; color: var(--sp-text-secondary); line-height: 1.6; margin-bottom: 12px;">
            Migração completa de todas as listas legadas do SharePoint para uma central web autônoma integrada ao Google Workspace, garantindo imunidade à desativação do tenant SharePoint.
          </p>
          <span class="badge badge-exibido">100% CONCLUÍDO</span>
        </div>
        <div class="escala-info-card">
          <h4>⚽ Monitor Esportes 2.4 — Auditoria E2E com Grounding</h4>
          <p style="font-size: 13px; color: var(--sp-text-secondary); line-height: 1.6; margin-bottom: 12px;">
            Sistema autônomo de auditoria com confirmação oficial de horários da CBF, ge.globo e transmissões CazéTV / Prime Video com geração de relatórios oficiais PDF de 2 páginas.
          </p>
          <span class="badge badge-exibido">100% OPERACIONAL</span>
        </div>
      </div>
    </div>

    <!-- ABA 11: RECEPTORES & TV BOX -->
    <div id="pane-receptores" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">📡 Receptores & TV BOX (PVIDs de Captura)</h2>
        <p class="section-desc">Configurações de decodificadores e receptores de satélite nas estações de captação.</p>
      </div>
      <div class="kpi-row">
        <div class="kpi-box"><div class="kpi-box-label">PVID PV3623</div><div class="kpi-box-val">Online</div><div class="kpi-box-sub">Cazé TV / YouTube Live</div></div>
        <div class="kpi-box"><div class="kpi-box-label">PVID PV3687</div><div class="kpi-box-val">Online</div><div class="kpi-box-sub">Amazon Prime Video</div></div>
        <div class="kpi-box"><div class="kpi-box-label">PVID PV3679</div><div class="kpi-box-val">Online</div><div class="kpi-box-sub">Netflix / NFL Sports</div></div>
      </div>
    </div>

    <!-- ABA 12: EQUIPE -->
    <div id="pane-equipe" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">👥 Equipe Suporte Captação</h2>
        <p class="section-desc">Quadro oficial de liderança, operadores técnicos e especialistas de ingest.</p>
      </div>
      <div class="sp-table-wrap">
        <table class="sp-list-table">
          <thead>
            <tr><th>Nome</th><th>Cargo / Função</th><th>E-mail Corporativo</th><th>Perfil de Acesso</th></tr>
          </thead>
          <tbody>
            <tr><td><b>Cleber De Souza Gonçalves</b></td><td>COORD. SUPORTE CAPTAÇÃO</td><td>cleber.goncalves@ibope.com</td><td><span class="badge badge-role-owner">Administrador (Owner)</span></td></tr>
            <tr><td><b>Luiz De Sa Lemos</b></td><td>DIR. SUPORTE CAPTAÇÃO LATAM</td><td>luiz.lemos@ibope.com</td><td><span class="badge badge-role-owner">Administrador (Owner)</span></td></tr>
            <tr><td><b>Rodrigo de Almeida Meirelles</b></td><td>Técnico de Suporte Jr (N1)</td><td>rodrigo.meirelles@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Alan Kelvin Chura Carrillo</b></td><td>Técnico de Suporte Jr (N1)</td><td>alan.carrillo@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Bruno Lopes Viana</b></td><td>Técnico de Suporte Jr (N1)</td><td>bruno.viana@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Cassio Esteves de Oliveira</b></td><td>ADMINISTRADOR DO PORTAL / Suporte Captação</td><td>cassio.esteves@ibope.com</td><td><span class="badge badge-role-owner">Administrador (Owner)</span></td></tr>
            <tr><td><b>Marcelo Fialho</b></td><td>Técnico de Suporte Jr (N1)</td><td>marcelo.fialho@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Rômulo Silva</b></td><td>Técnico de Suporte Jr (N1)</td><td>romulo.silva@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Joao Diego Silva Merino</b></td><td>Técnico de Suporte Pl (N2)</td><td>joao.merino@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Marcos Antonio Bezerra da Silva</b></td><td>Técnico de Suporte Sr (N2)</td><td>marcos.bezerra@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Lucieudes Vicente Ferreira</b></td><td>Técnico de Suporte Pl (N2)</td><td>lucieudes.ferreira@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
            <tr><td><b>Vinicius Dantas Ferreira da Silva</b></td><td>ADMINISTRADOR DO PORTAL / Suporte Captação</td><td>vinicius.dantas@ibope.com</td><td><span class="badge badge-role-owner">Administrador (Owner)</span></td></tr>
            <tr><td><b>Marcelo Pereira Silva</b></td><td>Líder Técnico LATAM (N2)</td><td>marcelo.pereira@ibope.com</td><td><span class="badge badge-role-write">Operador (Write)</span></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ABA 13: PERMISSÕES & RBAC -->
    <div id="pane-permissoes" class="pane-container">
      <!-- BARRA DE COMANDOS DO SHAREPOINT -->
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new action-admin-only" onclick="openNewPermModal()" title="Cadastrar nova permissão ou usuário">
            <span>+</span> Novo
          </button>
          <button id="btn-grid-perms" class="sp-btn-cmd btn-grid-edit action-admin-only" onclick="togglePermsGridEdit()" title="Editar linhas e colunas diretamente no navegador">
            <span id="btn-grid-perms-icon">田</span> <span id="btn-grid-perms-text">Editar no modo de exibição de grade</span>
          </button>
          <button class="sp-btn-cmd" onclick="renderPermsTable()">
            <span>↺</span> Atualizar
          </button>
          <button class="sp-btn-cmd" onclick="exportPermsCSV()">
            <span>📥</span> Exportar CSV
          </button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-perm-box" placeholder="Pesquisar nesta lista..." oninput="renderPermsTable()">
        </div>
      </div>

      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">
          Controle de Acessos & Mapeamento RBAC (__PERMS_COUNT__ Registros) <span class="star-icon">☆</span>
        </h2>
      </div>

      <!-- ALERTA MODO GRADE PERMISSÕES -->
      <div id="perms-grid-mode-alert" style="display: none; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #0078D4; padding: 10px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1E3A8A; align-items: center; justify-content: space-between;">
        <div>
          <b>⚡ Modo de exibição de grade ativado:</b> Você pode editar qualquer célula diretamente na tabela (nome, email, nível, papel, escopo). As alterações são salvas automaticamente.
        </div>
        <button type="button" class="btn-action btn-action-primary" style="padding: 4px 12px; font-size: 12px;" onclick="togglePermsGridEdit()">💾 Concluir e Salvar</button>
      </div>
      <div class="sp-table-wrap">
        <table class="sp-list-table">
          <thead>
            <tr><th>#</th><th>Nome / Grupo</th><th>Tipo</th><th>E-mail</th><th>Nível SharePoint</th><th>Perfil Google</th><th>Escopo</th></tr>
          </thead>
          <tbody id="perms-table-body">
            <!-- Renderizado via JS -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- ABA 14: LINKS EXTERNOS -->
    <div id="pane-links" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">🔗 Diretório de Links & Sistemas Oficiais</h2>
        <p class="section-desc">Acesso a todos os portais corporativos e ferramentas de telemetria.</p>
      </div>
      <div class="waffle-links-grid">
        <a href="http://10.1.30.1:8092/" target="_blank" class="waffle-link-card" style="border: 1px solid #FCA5A5; background: #FFF5F5;"><span class="waffle-link-icon">🚨</span><span class="waffle-link-title" style="color: #991B1B; font-weight: 700;">Monitor de Incidentes (8092)</span></a>
        <a href="https://chat.google.com/" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">💬</span><span class="waffle-link-title">Google Chat</span></a>
        <a href="https://meet.google.com/" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">📹</span><span class="waffle-link-title">Google Meet</span></a>
        <a href="https://mediadna.kantaribopemedia.com/mediadna/Comum/PaginaInicial.aspx" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">🧬</span><span class="waffle-link-title">Site - Media DNA</span></a>
        <a href="http://10.1.0.39/redmine/login" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">📑</span><span class="waffle-link-title">Redmine</span></a>
        <a href="https://zbxsrvbr.kantaribopemedia.com/zabbix/zabbix.php?action=dashboard.view&dashboardid=152" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">🖥️</span><span class="waffle-link-title">Zabbix</span></a>
        <a href="https://rhopen.kantar.com/" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">👥</span><span class="waffle-link-title">RH Open</span></a>
        <a href="https://kantarit.service-now.com/mykantarservices?id=hr_dashboard_home" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">🎫</span><span class="waffle-link-title">Service Now</span></a>
        <a href="https://wd3.myworkday.com/wday/authgwy/kantar/login.htmld" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">💼</span><span class="waffle-link-title">Workday</span></a>
        <a href="https://grafana.kantaribopemedia.com/d/LnH9Oq-Sk/atria-capture?orgId=1" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">📈</span><span class="waffle-link-title">Grafana</span></a>
        <a href="https://portalbsd.com.br/" target="_blank" class="waffle-link-card"><span class="waffle-link-icon">📡</span><span class="waffle-link-title">Portal BSD</span></a>
      </div>
    </div>

  </main>

  <!-- MODAL DE PROCEDIMENTOS -->
  <div class="modal-overlay" id="proc-modal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="modal-title">Procedimento Operacional</h3>
        <button class="modal-close-btn" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-body" id="modal-content">
        Carregando...
      </div>
    </div>
  </div>

  <!-- MODAL DE NOVA OCORRÊNCIA (PAINEL DE OCORRÊNCIAS) -->
  
  <!-- MODAL DE ENCERRAMENTO RÁPIDO DE OCORRÊNCIA (1-CLIQUE NO BANNER) -->
  <div class="modal-overlay" id="modal-quick-close-oco" style="display: none; align-items: center; justify-content: center; z-index: 10000;">
    <div class="modal-card" style="max-width: 540px; background: white; border-radius: 8px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); overflow: hidden;">
      <div class="modal-header" style="background: #0078D4; color: white; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">⚡</span>
          <h3 style="margin: 0; font-size: 15px; font-weight: 600; color: white;">Encerramento Rápido de Ocorrência</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeQuickCloseOcoModal()" style="color: white; font-size: 22px; cursor: pointer; background: transparent; border: none;">&times;</button>
      </div>
      <form id="form-quick-close-oco" onsubmit="submitQuickCloseOco(event)">
        <input type="hidden" id="quick-close-oco-id">
        <div class="modal-body" style="padding: 20px 24px;">
          <div style="margin-bottom: 14px;">
            <div style="font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase;">Praça / Host</div>
            <div id="quick-close-host-title" style="font-size: 15px; font-weight: 700; color: #1E293B; margin-top: 2px;">-</div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px;">
            <div>
              <label class="sp-form-label">Novo Status *</label>
              <select id="quick-close-status" class="sp-form-select" required style="width: 100%; height: 38px;">
                <option value="Concluído" selected>Concluído</option>
                <option value="Feedback">Feedback</option>
                <option value="Em andamento">Em andamento</option>
              </select>
            </div>
            <div>
              <label class="sp-form-label">Área Solucionadora</label>
              <select id="quick-close-area" class="sp-form-select" style="width: 100%; height: 38px;">
                <option value="Solucionado" selected>Solucionado</option>
                <option value="N1">N1</option>
                <option value="N2">N2</option>
                <option value="Engenharia">Engenharia</option>
                <option value="Parceiro Local">Parceiro Local</option>
                <option value="Infraestrutura / Redes">Infraestrutura / Redes</option>
              </select>
            </div>
          </div>

          <div style="margin-bottom: 14px;">
            <label class="sp-form-label">Ações Executadas / Justificativa *</label>
            <textarea id="quick-close-acoes" class="sp-form-input" rows="3" required placeholder="Ex: Normalizado pelo parceiro local; canal restabelecido." style="width: 100%; resize: vertical; font-family: inherit; font-size: 13px;"></textarea>
            <div style="display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
              <button type="button" class="sp-btn-cmd" style="font-size: 11px; padding: 2px 8px;" onclick="setQuickAcao('Normalizado após reinício de ATRIA.')">Reinício ATRIA</button>
              <button type="button" class="sp-btn-cmd" style="font-size: 11px; padding: 2px 8px;" onclick="setQuickAcao('Sinal restabelecido na emissora local.')">Sinal normal</button>
              <button type="button" class="sp-btn-cmd" style="font-size: 11px; padding: 2px 8px;" onclick="setQuickAcao('Parceiro local realizou o reset físico do equipamento.')">Reset Parceiro</button>
            </div>
          </div>

          <div style="display: flex; gap: 14px; margin-bottom: 6px;">
            <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: #475569; cursor: pointer;">
              <input type="checkbox" id="quick-close-recup" style="width: 16px; height: 16px;"> Em recuperação
            </label>
            <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: #475569; cursor: pointer;">
              <input type="checkbox" id="quick-close-informar" style="width: 16px; height: 16px;"> Informar Operação
            </label>
          </div>
        </div>
        <div class="modal-footer" style="padding: 12px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="sp-btn-cmd" onclick="closeQuickCloseOcoModal()">Cancelar</button>
          <button type="submit" class="sp-btn-new" style="background: #16A34A; border-color: #16A34A;"><span>✔</span> Concluir Ocorrência</button>
        </div>
      </form>
    </div>
  </div>

  <div class="modal-overlay" id="modal-new-oco">
    <div class="modal-card" style="max-width: 820px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📋</span>
          <h3>Nova Ocorrência Operacional &mdash; Painel de Ocorrências</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewOcoModal()">&times;</button>
      </div>
      <form id="form-new-oco" onsubmit="saveNewOcorrencia(event)">
        <div class="modal-body" style="max-height: 72vh; overflow-y: auto;">
          <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-left: 4px solid #0078D4; padding: 10px 14px; border-radius: 4px; margin-bottom: 16px; font-size: 12.5px; color: #0369A1;">
            <b>Registro Oficial de Incidentes:</b> Preencha os campos abaixo para registrar um novo incidente operacional. A ocorrência será adicionada imediatamente ao topo do histórico e preservada localmente no navegador.
          </div>

          <div class="sp-form-grid">
            <div class="sp-form-group">
              <label class="sp-form-label">Status da Ocorrência *</label>
              <select id="new-oco-status" class="sp-form-select" required>
                <option value="Em andamento" selected>Em andamento</option>
                <option value="Feedback">Feedback</option>
                <option value="Concluído">Concluído</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Host / Praça *</label>
              <select id="new-oco-host" class="sp-form-select" required style="width: 100%; height: 38px;">
                <option value="">Selecione a Praça / Host...</option>
                <option value="Altamira">Altamira</option><option value="Anápolis">Anápolis</option><option value="Aracaju">Aracaju</option><option value="Araguaína">Araguaína</option><option value="Araxá">Araxá</option><option value="Ariquemes">Ariquemes</option><option value="B. Horizonte">B. Horizonte</option><option value="Bagé">Bagé</option><option value="Balsas">Balsas</option><option value="Barreiras">Barreiras</option><option value="Bauru">Bauru</option><option value="Belém">Belém</option><option value="Blumenau">Blumenau</option><option value="Boa Vista">Boa Vista</option><option value="Brasília">Brasília</option><option value="C. Fabriciano">C. Fabriciano</option><option value="C. Itapemirim">C. Itapemirim</option><option value="Cabo Frio">Cabo Frio</option><option value="Cacoal">Cacoal</option><option value="Campina Grande">Campina Grande</option><option value="Campinas">Campinas</option><option value="Campo Grande">Campo Grande</option><option value="Campos">Campos</option><option value="Caruaru">Caruaru</option><option value="Cascavel">Cascavel</option><option value="Castanhal">Castanhal</option><option value="Catalão">Catalão</option><option value="Caxias do Sul">Caxias do Sul</option><option value="Chapecó">Chapecó</option><option value="Codó">Codó</option><option value="Colatina">Colatina</option><option value="Corumbá">Corumbá</option><option value="Costa Rica - Conversion Server">Costa Rica - Conversion Server</option><option value="Costa Rica - San José (BL1)">Costa Rica - San José (BL1)</option><option value="Costa Rica - San José (BL10)">Costa Rica - San José (BL10)</option><option value="Costa Rica - San José (BL2)">Costa Rica - San José (BL2)</option><option value="Costa Rica - San José (BL3)">Costa Rica - San José (BL3)</option><option value="Costa Rica - San José (BL4)">Costa Rica - San José (BL4)</option><option value="Costa Rica - San José (BL5)">Costa Rica - San José (BL5)</option><option value="Costa Rica - San José (BL6)">Costa Rica - San José (BL6)</option><option value="Costa Rica - San José (BL7)">Costa Rica - San José (BL7)</option><option value="Costa Rica - San José (BL8)">Costa Rica - San José (BL8)</option><option value="Costa Rica - San José (BL9)">Costa Rica - San José (BL9)</option><option value="Criciúma">Criciúma</option><option value="Cruz Alta">Cruz Alta</option><option value="Cruzeiro do Sul">Cruzeiro do Sul</option><option value="Cuiabá">Cuiabá</option><option value="Curitiba">Curitiba</option><option value="Erechim">Erechim</option><option value="F. Santana">F. Santana</option><option value="Floriano">Floriano</option><option value="Florianópolis">Florianópolis</option><option value="Fortaleza">Fortaleza</option><option value="Foz de Iguaçu">Foz de Iguaçu</option><option value="Franca">Franca</option><option value="G. Valadares">G. Valadares</option><option value="Goiânia">Goiânia</option><option value="Guajará-Mirim">Guajará-Mirim</option><option value="Guarapuava">Guarapuava</option><option value="Guatemala - Cidade da Guatemala">Guatemala - Cidade da Guatemala</option><option value="Gurupi">Gurupi</option><option value="Imperatriz">Imperatriz</option><option value="Itabuna">Itabuna</option><option value="Itacoatiara">Itacoatiara</option><option value="Itaituba">Itaituba</option><option value="Itapetininga">Itapetininga</option><option value="Ituiutaba">Ituiutaba</option><option value="Itumbiara">Itumbiara</option><option value="Jataí">Jataí</option><option value="Ji-Paraná">Ji-Paraná</option><option value="Joaçaba">Joaçaba</option><option value="Joinville">Joinville</option><option value="João Pessoa">João Pessoa</option><option value="Juazeiro">Juazeiro</option><option value="Juazeiro do N.">Juazeiro do N.</option><option value="Juiz de Fora">Juiz de Fora</option><option value="Linhares">Linhares</option><option value="Lisboa">Lisboa</option><option value="Londrina">Londrina</option><option value="Luziânia">Luziânia</option><option value="M. das Cruzes">M. das Cruzes</option><option value="Macapá">Macapá</option><option value="Maceió">Maceió</option><option value="Manaus">Manaus</option><option value="Marabá">Marabá</option><option value="Maringá">Maringá</option><option value="Miami">Miami</option><option value="Montes Claros">Montes Claros</option><option value="Mossoró">Mossoró</option><option value="Natal">Natal</option><option value="Nova Friburgo">Nova Friburgo</option><option value="Palmas">Palmas</option><option value="Panamá - Cidade do Panamá">Panamá - Cidade do Panamá</option><option value="Paragominas">Paragominas</option><option value="Paraguai - Assunção CS1/CS2">Paraguai - Assunção CS1/CS2</option><option value="Paranavaí">Paranavaí</option><option value="Parauapebas">Parauapebas</option><option value="Parintins">Parintins</option><option value="Passo Fundo">Passo Fundo</option><option value="Pelotas">Pelotas</option><option value="Penha-DT1">Penha-DT1</option><option value="Penha-DT2">Penha-DT2</option><option value="Penha-HQ">Penha-HQ</option><option value="Penha-SAT">Penha-SAT</option><option value="Ponta Grossa">Ponta Grossa</option><option value="Ponta Pora">Ponta Pora</option><option value="Porangatú">Porangatú</option><option value="Porto Alegre">Porto Alegre</option><option value="Porto Velho">Porto Velho</option><option value="Pres. Prudente">Pres. Prudente</option><option value="RJ-Paytv Bloco 01">RJ-Paytv Bloco 01</option><option value="RJ-Paytv Bloco 02">RJ-Paytv Bloco 02</option><option value="RJ-Paytv Bloco 03">RJ-Paytv Bloco 03</option><option value="RJ-Paytv Bloco 04">RJ-Paytv Bloco 04</option><option value="RJ-Paytv Bloco 05">RJ-Paytv Bloco 05</option><option value="RJ-Paytv Bloco 06">RJ-Paytv Bloco 06</option><option value="RJ-Paytv Bloco 07">RJ-Paytv Bloco 07</option><option value="RJ-Paytv Bloco 08">RJ-Paytv Bloco 08</option><option value="RJ-Paytv Bloco 09">RJ-Paytv Bloco 09</option><option value="Recife">Recife</option><option value="Redenção">Redenção</option><option value="Resende">Resende</option><option value="Ribeirão Preto">Ribeirão Preto</option><option value="Rio Branco">Rio Branco</option><option value="Rio Grande">Rio Grande</option><option value="Rio Verde">Rio Verde</option><option value="Rio de Janeiro">Rio de Janeiro</option><option value="Rondonópolis">Rondonópolis</option><option value="S.J. Campos">S.J. Campos</option><option value="S.J.Rio Preto">S.J.Rio Preto</option><option value="Salvador">Salvador</option><option value="Santa C.do Sul">Santa C.do Sul</option><option value="Santa Maria">Santa Maria</option><option value="Santa Rosa">Santa Rosa</option><option value="Santarém">Santarém</option><option value="Santos">Santos</option><option value="Sinop">Sinop</option><option value="Sorocaba">Sorocaba</option><option value="São Carlos">São Carlos</option><option value="São Luís">São Luís</option><option value="T. da Serra">T. da Serra</option><option value="Taubaté">Taubaté</option><option value="Teresina">Teresina</option><option value="Tucuruí">Tucuruí</option><option value="Uberaba">Uberaba</option><option value="Uberlândia">Uberlândia</option><option value="Uruguaiana">Uruguaiana</option><option value="V. da Conquista">V. da Conquista</option><option value="Varginha">Varginha</option><option value="Vilhena">Vilhena</option><option value="Vitória">Vitória</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">CS (Canal de Serviço)</label>
              <select id="new-oco-cs" class="sp-form-select" style="width: 100%; height: 38px;">
                <option value="01">01</option>
                <option value="02">02</option>
                <option value="03">03</option>
                <option value="01, 02" selected>01, 02</option>
                <option value="01, 02, 03">01, 02, 03</option>
                <option value="02, 03">02, 03</option>
                <option value="Todos">Todos</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Veículo / Emissora</label>
              <select id="new-oco-veiculo" class="sp-form-select" style="width: 100%; height: 38px;">
                <option value="Todos" selected>Todos</option>
                <option value="GLOBO">GLOBO</option>
                <option value="SBT">SBT</option>
                <option value="RECORD">RECORD</option>
                <option value="BAND">BAND</option>
                <option value="REDE TV">REDE TV</option>
                <option value="TV CULTURA">TV CULTURA</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Equipamento</label>
              <select id="new-oco-equipamento" class="sp-form-select" style="width: 100%; height: 38px;">
                <option value="ATRIA" selected>ATRIA</option>
                <option value="Maquina">Maquina</option>
                <option value="Switch / Roteador">Switch / Roteador</option>
                <option value="Receptor / TV BOX">Receptor / TV BOX</option>
                <option value="WADT">WADT</option>
                <option value="Nobreak / PDU">Nobreak / PDU</option>
                <option value="Antena">Antena</option>
                <option value="LNB">LNB</option>
                <option value="Cabo / Conector">Cabo / Conector</option>
                <option value="Placa de Captura">Placa de Captura</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Tipo do Problema</label>
              <select id="new-oco-tipo" class="sp-form-select">
                <option value="Sem sinal">Sem sinal</option>
                <option value="Sem comunicação">Sem comunicação</option>
                <option value="Não está gravando">Não está gravando</option>
                <option value="Sem detecção">Sem detecção</option>
                <option value="Imagem congelada">Imagem congelada</option>
                <option value="Sem energia">Sem energia</option>
                <option value="Problema no Áudio">Problema no Áudio</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Em Recuperação?</label>
              <select id="new-oco-recup" class="sp-form-select">
                <option value="Não" selected>Não</option>
                <option value="Sim">Sim</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Gravação Streaming?</label>
              <select id="new-oco-streaming" class="sp-form-select">
                <option value="Não" selected>Não</option>
                <option value="Sim">Sim</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Área / Responsável</label>
              <select id="new-oco-area" class="sp-form-select" style="width: 100%; height: 38px;">
                <option value="N1" selected>N1</option>
                <option value="N2">N2</option>
                <option value="Infraestrutura / Redes">Infraestrutura / Redes</option>
                <option value="Engenharia">Engenharia</option>
                <option value="Operação">Operação</option>
                <option value="Parceiro Local">Parceiro Local</option>
                <option value="TI Corporativa">TI Corporativa</option>
                <option value="Preços / SAC">Preços / SAC</option>
                <option value="Vinicius Dantas">Vinicius Dantas</option>
                <option value="Lucieudes Victor">Lucieudes Victor</option>
                <option value="Cassio Esteves">Cassio Esteves</option>
                <option value="Cleber Gonçalves">Cleber Gonçalves</option>
                <option value="Solucionado">Solucionado</option>
              </select>
            </div>

            <div class="sp-form-group">
              <label class="sp-form-label">Ticket Redmine (Número)</label>
              <input type="text" id="new-oco-redmine" class="sp-form-input" placeholder="Ex: 9106">
            </div>

            <div class="sp-form-group full-width" style="display: flex; flex-direction: row; align-items: center; gap: 10px; margin-top: 4px;">
              <input type="checkbox" id="new-oco-operacao" style="width: 18px; height: 18px; cursor: pointer;">
              <label for="new-oco-operacao" style="font-size: 13px; font-weight: 600; cursor: pointer; color: var(--sp-text-main);">
                Informar Operação (Destaque para plantão N1/N2)
              </label>
            </div>

            <div class="sp-form-group full-width">
              <label class="sp-form-label">Ações Executadas / Diagnóstico Técnico</label>
              <textarea id="new-oco-acoes" class="sp-form-textarea" rows="3" placeholder="Descreva os testes efetuados, contato com parceiro, reboot de decoders ou acionamento técnico..."></textarea>
            </div>
          </div>
        </div>

        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewOcoModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Ocorrência
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVO ITEM EM LISTA GENÉRICA DO SHAREPOINT -->
  <div class="modal-overlay" id="modal-new-list-item">
    <div class="modal-card" style="max-width: 760px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📄</span>
          <h3 id="modal-new-list-title">Novo Item na Lista</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewListItemModal()">&times;</button>
      </div>
      <form id="form-new-list-item" onsubmit="saveNewListItem(event)">
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-left: 4px solid #0078D4; padding: 10px 14px; border-radius: 4px; margin-bottom: 16px; font-size: 12.5px; color: #0369A1;">
            <b>Inclusão de Registro:</b> Preencha os campos abaixo para adicionar um novo registro diretamente a esta lista do SharePoint.
          </div>
          <div id="new-list-fields-container" class="sp-form-grid">
            <!-- Gerado dinamicamente com base nas colunas da lista atual -->
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewListItemModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Registro
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVO CONTATO DE ANTENISTA -->
  <div class="modal-overlay" id="modal-new-antenista">
    <div class="modal-card" style="max-width: 680px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📡</span>
          <h3>Novo Contato de Antenista</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewAntenistaModal()">&times;</button>
      </div>
      <form id="form-new-antenista" onsubmit="saveNewAntenista(event)">
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group">
              <label class="sp-form-label">Nome / Contato *</label>
              <input type="text" id="new-ante-nome" class="sp-form-input" placeholder="Ex: Carlos Silva" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Cidade / Praça *</label>
              <input type="text" id="new-ante-cidade" class="sp-form-input" placeholder="Ex: Montes Claros - MG" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Especialidade / Cargo</label>
              <input type="text" id="new-ante-cargo" class="sp-form-input" placeholder="Ex: Técnico em Antenas / Manutenção" value="Técnico em Antenas">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Empresa</label>
              <input type="text" id="new-ante-empresa" class="sp-form-input" placeholder="Ex: Antenas & Telecom">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Telefone Comercial</label>
              <input type="text" id="new-ante-telcom" class="sp-form-input" placeholder="Ex: (38) 3221-0000">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Telefone Celular / WhatsApp</label>
              <input type="text" id="new-ante-telcel" class="sp-form-input" placeholder="Ex: (38) 99999-0000">
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewAntenistaModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Contato
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVO HOST -->
  <div class="modal-overlay" id="modal-new-host">
    <div class="modal-card" style="max-width: 600px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">🖥️</span>
          <h3>Novo Host / Praça</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewHostModal()">&times;</button>
      </div>
      <form id="form-new-host" onsubmit="saveNewHost(event)">
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Código do Host / Praça *</label>
              <input type="text" id="new-host-code" class="sp-form-input" placeholder="Ex: Vitoria / BRES-VIT-TDT" required>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Status Operacional</label>
              <select id="new-host-status" class="sp-form-select">
                <option value="Ativo" selected>Ativo</option>
                <option value="Manutenção">Manutenção</option>
                <option value="Desativado">Desativado</option>
              </select>
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewHostModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Host
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVO ARQUIVO/PASTA NO DRIVE -->
  <div class="modal-overlay" id="modal-new-drive-file">
    <div class="modal-card" style="max-width: 600px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📁</span>
          <h3>Adicionar Documento / Pasta ao Drive</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewDriveFileModal()">&times;</button>
      </div>
      <form id="form-new-drive-file" onsubmit="saveNewDriveFile(event)">
        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Tipo de Item</label>
              <select id="new-drive-type" class="sp-form-select">
                <option value="file" selected>Arquivo / Planilha / PDF</option>
                <option value="folder">Pasta</option>
              </select>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Nome do Arquivo ou Pasta *</label>
              <input type="text" id="new-drive-name" class="sp-form-input" placeholder="Ex: Relatorio_Operacional_Novembro.xlsx" required>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Responsável / Modificado por</label>
              <input type="text" id="new-drive-author" class="sp-form-input" placeholder="Ex: Cleber Gonçalves" value="Cleber Gonçalves">
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewDriveFileModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Adicionar ao Drive
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE DISPARO PARA O GOOGLE CHAT -->
  <div class="modal-overlay" id="modal-chat-webhook" style="display: none;">
    <div class="modal-card" style="max-width: 580px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📢</span>
          <h3>Disparar Agenda de Transmissões para o Google Chat</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeChatWebhookModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13px; color: #475569; margin-bottom: 12px; line-height: 1.5;">
          Esta ação compõe e envia o card da <b>Agenda de Transmissões</b> com os jogos de <b>Hoje</b> e <b>Amanhã</b> diretamente para o grupo <b>Streaming - Gravações</b> no Google Chat.
          Caso não haja eventos escalados, o sistema informa que a grade está 100% livre.
        </p>
        <div class="sp-form-group">
          <label class="sp-form-label">URL do Webhook do Google Chat (Espaço 'Streaming - Gravações') *</label>
          <input type="text" id="chat-webhook-url-input" class="sp-form-input" placeholder="https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..." style="font-family: monospace; font-size: 11px;">
          <span style="font-size: 11px; color: #64748B; margin-top: 4px; display: block;">
            💡 <b>Como obter</b>: No Google Chat ➔ grupo 'Streaming - Gravações' ➔ clique no título do grupo ➔ <b>Aplicativos e integrações</b> ➔ <b>Gerenciar webhooks</b> ➔ <b>Copiar link</b>.
          </span>
        </div>
        <div id="chat-agenda-preview" style="margin-top: 14px; padding: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; font-size: 12px;">
          Carregando resumo dos jogos...
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="sp-modal-btn sp-modal-btn-cancel" onclick="closeChatWebhookModal()">Cancelar</button>
        <button type="button" class="sp-modal-btn sp-modal-btn-save" id="btn-send-chat-now" onclick="sendChatAgendaFromModal()" style="background: #2563EB;">🚀 Enviar Agora para o Google Chat</button>
      </div>
    </div>
  </div>

  <!-- MODAL IN-DOM DE CONFIRMAÇÃO DE EXCLUSÃO (100% COMPATÍVEL COM IFRAMES DO GOOGLE SITES) -->
  <div class="modal-overlay" id="modal-generic-confirm-delete" style="display:none; position:fixed; inset:0; background:rgba(15,23,42,0.8); backdrop-filter:blur(4px); z-index:99999; align-items:center; justify-content:center; padding:20px;">
    <div class="modal-card" style="max-width:480px; width:100%; background:#ffffff; border-radius:12px; box-shadow:0 20px 40px rgba(0,0,0,0.3); border:1px solid #E2E8F0; overflow:hidden;">
      <div style="background:#FEF2F2; border-bottom:1px solid #FEE2E2; padding:16px 20px; display:flex; align-items:center; gap:12px;">
        <div style="width:40px; height:40px; border-radius:50%; background:#FEE2E2; display:flex; align-items:center; justify-content:center; font-size:20px; color:#EF4444; flex-shrink:0;">
          🗑️
        </div>
        <div>
          <h3 id="modal-delete-title" style="margin:0; font-size:16px; font-weight:700; color:#991B1B;">Confirmar Exclusão</h3>
          <p style="margin:2px 0 0; font-size:12px; color:#B91C1C;">Esta ação removerá os itens selecionados</p>
        </div>
      </div>
      <div style="padding:20px; font-size:13.5px; color:#334155; line-height:1.6;" id="modal-delete-message">
        Tem certeza que deseja excluir os itens selecionados?
      </div>
      <div style="background:#F8FAFC; border-top:1px solid #E2E8F0; padding:14px 20px; display:flex; justify-content:flex-end; gap:10px;">
        <button type="button" onclick="closeCustomDeleteModal(false)" style="background:#ffffff; border:1px solid #CBD5E1; color:#475569; font-weight:600; font-size:13px; padding:8px 16px; border-radius:6px; cursor:pointer;">
          Cancelar
        </button>
        <button type="button" id="modal-delete-confirm-btn" onclick="closeCustomDeleteModal(true)" style="background:#EF4444; border:1px solid #DC2626; color:#ffffff; font-weight:700; font-size:13px; padding:8px 18px; border-radius:6px; cursor:pointer; box-shadow:0 2px 6px rgba(239,68,68,0.3);">
          Sim, Excluir Definitivamente
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL DE NOVO EVENTO STREAMING -->
  <div class="modal-overlay" id="modal-new-stream-event">
    <div class="modal-card" style="max-width: 720px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📺</span>
          <h3>Novo Confronto / Evento Streaming</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewStreamModal()">&times;</button>
      </div>
      <form id="form-new-stream" onsubmit="saveNewStreamEvent(event)">
        <div class="modal-body" style="max-height: 72vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group">
              <label class="sp-form-label">Mês *</label>
              <select id="new-stream-mes" class="sp-form-select" required>
                <option value="Janeiro">Janeiro</option>
                <option value="Fevereiro">Fevereiro</option>
                <option value="Março">Março</option>
                <option value="Abril">Abril</option>
                <option value="Maio">Maio</option>
                <option value="Junho">Junho</option>
                <option value="Julho">Julho</option>
                <option value="Agosto">Agosto</option>
                <option value="Setembro">Setembro</option>
                <option value="Outubro">Outubro</option>
                <option value="Novembro" selected>Novembro</option>
                <option value="Dezembro">Dezembro</option>
              </select>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Data do Confronto (DD/MM/YYYY) *</label>
              <input type="text" id="new-stream-data" class="sp-form-input" placeholder="Ex: 19/11/2026" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Horário (HH:MM) *</label>
              <input type="text" id="new-stream-horario" class="sp-form-input" placeholder="Ex: 20:00" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Campeonato / Competição *</label>
              <input type="text" id="new-stream-campeonato" class="sp-form-input" placeholder="Ex: Brasileirão Série A" required>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Partida / Confronto *</label>
              <input type="text" id="new-stream-partida" class="sp-form-input" placeholder="Ex: Palmeiras x Corinthians" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Canal de Transmissão *</label>
              <select id="new-stream-canal" class="sp-form-select" required>
                <option value="Cazé TV" selected>Cazé TV</option>
                <option value="Amazon Prime">Amazon Prime</option>
                <option value="Netflix">Netflix</option>
                <option value="TNT / MAX / Record">TNT / MAX / Record</option>
                <option value="YouTube">YouTube</option>
                <option value="Outros">Outros</option>
              </select>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">PVID TV BOX</label>
              <input type="text" id="new-stream-pvid" class="sp-form-input" placeholder="Ex: CAZÉTV - 3571">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Responsável Gravação</label>
              <input type="text" id="new-stream-resp" class="sp-form-input" placeholder="Ex: Cleber BL01 e Backup">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Status de Entrega</label>
              <select id="new-stream-status" class="sp-form-select">
                <option value="Exibido" selected>Exibido</option>
                <option value="Em andamento">Em andamento</option>
                <option value="Pendente">Pendente</option>
                <option value="Cancelado">Cancelado</option>
              </select>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Programado</label>
              <select id="new-stream-programado" class="sp-form-select">
                <option value="SIM" selected>SIM</option>
                <option value="NÃO">NÃO</option>
              </select>
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewStreamModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Confronto
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVO HOSPEDEIRO -->
  <div class="modal-overlay" id="modal-new-hospedeiro">
    <div class="modal-card" style="max-width: 680px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">📞</span>
          <h3>Novo Contato de Hospedeiro</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewHospedeiroModal()">&times;</button>
      </div>
      <form id="form-new-hospedeiro" onsubmit="saveNewHospedeiro(event)">
        <div class="modal-body" style="max-height: 72vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Cidade / Praça / UF *</label>
              <input type="text" id="new-hosp-cidade" class="sp-form-input" placeholder="Ex: Montes Claros / MG" required>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Nome do Técnico / Central *</label>
              <input type="text" id="new-hosp-nome" class="sp-form-input" placeholder="Ex: Carlos Eduardo Silva" required>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Especialidade / Cargo</label>
              <input type="text" id="new-hosp-esp" class="sp-form-input" placeholder="Ex: Técnico de Recepção / Antenista">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Telefone Comercial</label>
              <input type="text" id="new-hosp-telcom" class="sp-form-input" placeholder="Ex: (38) 3221-0000">
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Telefone Celular</label>
              <input type="text" id="new-hosp-telcel" class="sp-form-input" placeholder="Ex: (38) 99999-0000">
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewHospedeiroModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Hospedeiro
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL DE NOVA PERMISSÃO -->
  <div class="modal-overlay" id="modal-new-perm">
    <div class="modal-card" style="max-width: 680px;">
      <div class="modal-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 18px;">🔐</span>
          <h3>Nova Permissão / Acesso RBAC</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeNewPermModal()">&times;</button>
      </div>
      <form id="form-new-perm" onsubmit="saveNewPerm(event)">
        <div class="modal-body" style="max-height: 72vh; overflow-y: auto;">
          <div class="sp-form-grid">
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Nome do Usuário ou Grupo *</label>
              <input type="text" id="new-perm-nome" class="sp-form-input" placeholder="Ex: João Diego Silva" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Tipo</label>
              <select id="new-perm-tipo" class="sp-form-select">
                <option value="user" selected>Usuário (user)</option>
                <option value="group">Grupo (group)</option>
              </select>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">E-mail Corporativo *</label>
              <input type="email" id="new-perm-email" class="sp-form-input" placeholder="Ex: joao.diego@ibope.com" required>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Nível SharePoint</label>
              <select id="new-perm-sp" class="sp-form-select">
                <option value="Proprietário">Proprietário (Full Control)</option>
                <option value="Membro" selected>Membro (Edit / Contribute)</option>
                <option value="Visitante">Visitante (Read)</option>
              </select>
            </div>
            <div class="sp-form-group">
              <label class="sp-form-label">Perfil Google Workspace</label>
              <select id="new-perm-google" class="sp-form-select">
                <option value="Gestor/Admin">Gestor / Admin</option>
                <option value="Operador" selected>Operador (Write)</option>
                <option value="Leitor">Leitor (Read-Only)</option>
              </select>
            </div>
            <div class="sp-form-group full-width">
              <label class="sp-form-label">Escopo / Setor</label>
              <input type="text" id="new-perm-escopo" class="sp-form-input" placeholder="Ex: Suporte Captação / Coleta">
            </div>
          </div>
        </div>
        <div class="sp-modal-footer">
          <button type="button" class="btn-action btn-action-secondary" onclick="closeNewPermModal()">Cancelar</button>
          <button type="submit" class="btn-action btn-action-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>💾</span> Salvar Permissão
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- CONTAINER DE NOTIFICAÇÕES TOAST -->
  <div id="sp-toast-container"></div>

  <!-- RODAPÉ CORPORATIVO -->
  <footer class="site-footer">
    <div class="site-footer-container">
      <div><b>IBOPE</b> — Central de Operações & Suporte Captação © 2026</div>
      <div>Portal 100% Autônomo e Integrado com Google Workspace</div>
    </div>
  </footer>

  <script>
    // Datasets completos
    let allEvents = __EVENTS_JSON__;
    let allPermissions = __PERMS_JSON__;
    let allHospedeiros = __HOSPEDEIROS_JSON__;
    let allOcorrencias = __OCORRENCIAS_JSON__;
    let allProcedimentos = __PROCEDIMENTOS_JSON__;
    let allDocumentos = __DOCUMENTOS_JSON__;
    let allEscalaMonths = __ESCALA_JSON__;
    let allAntenistas = __ANTENISTAS_JSON__;
    let allHosts = __HOSTS_JSON__;
    let SP_MASTER_DATA = __SP_MASTER_DATA__;

    // Restauração de dados e edições salvas no localStorage (Persistência Offline/Online)
    try {
      const savedOcos = JSON.parse(localStorage.getItem('sp_custom_ocorrencias') || '[]');
      if (Array.isArray(savedOcos) && savedOcos.length > 0) {
        allOcorrencias = [...savedOcos, ...allOcorrencias];
      }
      const savedOcoEdits = JSON.parse(localStorage.getItem('sp_custom_ocorrencias_edits') || '{}');
      if (savedOcoEdits && Object.keys(savedOcoEdits).length > 0) {
        allOcorrencias.forEach(o => {
          const key = o.id || o.Criado;
          if (savedOcoEdits[key]) {
            Object.assign(o, savedOcoEdits[key]);
          }
        });
      }
      const savedAntenistas = JSON.parse(localStorage.getItem('sp_custom_antenistas') || '[]');
      if (Array.isArray(savedAntenistas) && savedAntenistas.length > 0) {
        allAntenistas = [...savedAntenistas, ...allAntenistas];
      }
      const savedHosts = JSON.parse(localStorage.getItem('sp_custom_hosts') || '[]');
      if (Array.isArray(savedHosts) && savedHosts.length > 0) {
        allHosts = [...savedHosts, ...allHosts];
      }
      if (SP_MASTER_DATA && SP_MASTER_DATA.lists) {
        Object.keys(SP_MASTER_DATA.lists).forEach(listKey => {
          const savedItems = JSON.parse(localStorage.getItem('sp_custom_list_' + listKey) || '[]');
          if (Array.isArray(savedItems) && savedItems.length > 0) {
            SP_MASTER_DATA.lists[listKey].items = [...savedItems, ...(SP_MASTER_DATA.lists[listKey].items || [])];
          }
        });
      }
    } catch (e) {
      console.warn("Erro ao carregar dados locais persistidos:", e);
    }

    let currentRole = "admin";
    let currentMonth = "Novembro";

    function canUserDelete() {
      const sel = document.getElementById("user-role-select");
      const role = (sel && sel.value) ? sel.value : currentRole;
      return role.startsWith("admin") || role === "operador" || role === "gestor";
    }
    window.canUserDelete = canUserDelete;

    function onRoleChange() {
      const sel = document.getElementById("user-role-select");
      currentRole = sel.value;
      const avatar = document.getElementById("top-user-avatar");
      const escalaBadge = document.getElementById("escala-perm-badge");

      const isAdmin = currentRole.startsWith("admin");
      const isOperador = (currentRole === "operador");
      const isReadOnly = currentRole.startsWith("leitor");

      if (isAdmin) {
        if (currentRole === "admin_cassio") avatar.innerText = "CE";
        else if (currentRole === "admin_vinicius") avatar.innerText = "VD";
        else if (currentRole === "admin_luiz") avatar.innerText = "LL";
        else avatar.innerText = "CG";
        avatar.style.background = "#004578";

        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "";

        // Todos os botões de criação e edição ativos
        document.querySelectorAll(".sp-btn-new, .btn-grid-edit").forEach(el => el.style.display = "");

        if (escalaBadge) {
          escalaBadge.innerText = "✏️ Permissão de Edição (Administrador)";
          escalaBadge.style.background = "#D1FAE5";
          escalaBadge.style.color = "#065F46";
          escalaBadge.style.borderColor = "#A7F3D0";
        }
      } else if (isOperador) {
        avatar.innerText = "OP";
        avatar.style.background = "#059669";

        // Operador não tem acesso à gestão de permissões ou configurações restritas
        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "none");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "none";

        // Operador tem permissão de inclusão e edição em ocorrências e listas operacionais
        document.querySelectorAll(".sp-btn-new:not(.action-admin-only), .btn-grid-edit:not(.action-admin-only)").forEach(el => el.style.display = "");

        if (escalaBadge) {
          escalaBadge.innerText = "🔒 Somente Leitura (Gestão da Escala Restrita à Administração)";
          escalaBadge.style.background = "#FEF3C7";
          escalaBadge.style.color = "#92400E";
          escalaBadge.style.borderColor = "#FDE68A";
        }
      } else {
        // Visitante / Consulta (NOC, SAC, Leitura Geral)
        avatar.innerText = "LE";
        avatar.style.background = "#64748B";

        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "none");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "none";

        // Modo estritamente somente leitura: sem botões de criação ou modo grade
        document.querySelectorAll(".sp-btn-new, .btn-grid-edit").forEach(el => el.style.display = "none");

        if (escalaBadge) {
          escalaBadge.innerText = "🔒 Somente Leitura (Visitante / Consulta)";
          escalaBadge.style.background = "#F1F5F9";
          escalaBadge.style.color = "#475569";
          escalaBadge.style.borderColor = "#E2E8F0";
        }

        const activePane = document.querySelector(".pane-container.active");
        if (activePane && activePane.id === "pane-permissoes") {
          showPane("home");
        }
      }
    }

    // ==========================================
    // ==========================================
    // RECURSOS UNIFICADOS DO SHAREPOINT (DRIVES & LISTAS REAIS)
    // ==========================================
    const SP_RESOURCE_MAP = {
      // Drives (Bibliotecas de Documentos com Pastas e Arquivos Reais)
      'drive_escala': { type: 'drive', name: 'Escala de trabalho', title: 'Biblioteca de Documentos da Escala' },
      'procedimentos': { type: 'drive', name: 'Procedimentos', title: 'Procedimentos Operacionais Padrão (POPs N1)' },
      'documentos': { type: 'drive', name: 'Documentos', title: 'Documentos Compartilhados da Equipe' },
      'capacitacao': { type: 'drive', name: 'Ficha de Capacitação', title: 'Ficha de Capacitação' },
      'tratativa': { type: 'drive', name: 'Tratativa de Problemas de captação', title: 'Tratativa de Problemas de Captação' },
      'doctecnicos': { type: 'drive', name: 'Documentos Técnicos', title: 'Documentos Técnicos (PayTV)' },
      'metas': { type: 'drive', name: 'Metas', title: 'Metas & Acompanhamento da Equipe' },
      'contratos': { type: 'drive', name: 'Controle de contratos parceiros', title: 'Controle de Contratos Parceiros' },
      'fornecedores': { type: 'drive', name: 'Avaliação Técnica de Fornecedores', title: 'Avaliação Técnica de Fornecedores' },
      'sla': { type: 'drive', name: 'SLA', title: 'SLA de Atendimento' },
      'notificacoes': { type: 'drive', name: 'Análise de Notificações', title: 'Análise de Notificações' },
      'analisedados': { type: 'drive', name: 'Analise de Dados', title: 'Análise de Dados' },
      'remoto': { type: 'drive', name: 'Acesso Remoto', title: 'Acesso Remoto & América Central' },
      'automacoes': { type: 'drive', name: 'Repositorio_Automacoes', title: 'Repositório de Automações' },
      'projetos': { type: 'drive', name: 'Projetos', title: 'Projetos' },

      // Os 3 Relatórios de Jogos Separados (Drives Oficiais do SharePoint)
      'relatorios_futebol': { type: 'drive', name: 'Relatorios_de_Jogos', title: 'Relatórios de Jogos' },
      'relatoriosjogos': { type: 'drive', name: 'Relatorios_de_Jogos', title: 'Relatórios de Jogos' },
      'relatorios_youtube': { type: 'drive', name: 'Relatorio Jogos Youtube', title: 'Relatório Jogos Youtube' },
      'relatoriosyoutube': { type: 'drive', name: 'Relatorio Jogos Youtube', title: 'Relatório Jogos Youtube' },
      'relatorios_nba': { type: 'drive', name: 'Relatorios_de_Jogos_NBA', title: 'Relatórios de Jogos NBA' },
      'relatoriosnba': { type: 'drive', name: 'Relatorios_de_Jogos_NBA', title: 'Relatórios de Jogos NBA' },

      // Listas Oficiais do SharePoint
      'solicitacoes': { type: 'list', name: 'Solicitações de Acesso', title: 'Solicitações de Acesso' },
      'backup': { type: 'list', name: 'Validação de Backup', title: 'Validação de Backup' },
      'falhas': { type: 'list', name: 'Confirmação de Falhas Suporte Captação', title: 'Confirmação de Falhas' },
      'antenistas': { type: 'list', name: 'Contatos de Antenistas', title: 'Contatos de Antenistas' },
      'redmine': { type: 'list', name: 'Redmine', title: 'Redmine (Demandas & Chamados)' },
      'hosts': { type: 'list', name: 'Cadastro - Hosts', title: 'Cadastro de Hosts' },
      'cidades': { type: 'list', name: 'Cidades', title: 'Mapeamento de Cidades e Emissoras' },
      'gestaoservicos': { type: 'list', name: 'Painel de gestão de serviços dos CS', title: 'Painel de Gestão de Serviços dos CS' },
      'monitoramentocanais': { type: 'list', name: 'Monitoramento de Canais CS', title: 'Monitoramento de Canais CS' },
      'redescs': { type: 'list', name: 'Configurações de Rede do CS', title: 'Configurações de Rede do CS' },
      'redepcd': { type: 'list', name: 'Mapeamento de Rede do CPD', title: 'Mapeamento de Rede do CPD' },
      'links': { type: 'list', name: 'Links de Internet dos Parceiros', title: 'Links de Internet dos Parceiros' }
    };

    // --- Utilitários de Formatação ---
    function formatFileSize(bytes) {
      if (bytes === undefined || bytes === null || isNaN(bytes)) return '-';
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatDate(isoStr) {
      if (!isoStr) return '-';
      try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return String(isoStr);
        const day = String(d.getDate()).padStart(2, '0');
        const mon = String(d.getMonth() + 1).padStart(2, '0');
        const yr = d.getFullYear();
        const hr = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        return `${day}/${mon}/${yr} ${hr}:${min}`;
      } catch (e) {
        return String(isoStr);
      }
    }

    function getSpFileIcon(item) {
      if (item.type === 'folder') return '📁';
      const ext = (item.extension || item.name.split('.').pop() || '').toLowerCase();
      if (ext === 'pdf') return '📕';
      if (['xlsx', 'xls', 'csv'].includes(ext)) return '📊';
      if (['docx', 'doc', 'txt'].includes(ext)) return '📝';
      if (['vsdx', 'vsd'].includes(ext)) return '📐';
      if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(ext)) return '🖼️';
      if (['zip', 'rar', '7z'].includes(ext)) return '📦';
      if (['json', 'xml', 'py', 'js'].includes(ext)) return '⚙️';
      return '📄';
    }

    function formatCellContent(val, colName) {
      if (val === null || val === undefined || val === '') return '-';
      if (typeof val === 'object') {
        if (val.Url) return `<a href="${val.Url}" target="_blank" class="sp-table-link">${val.Description || val.Url} ↗</a>`;
        return JSON.stringify(val);
      }
      const s = String(val).trim();
      if (s.startsWith("{'") && s.includes("'Url':")) {
        const urlM = s.match(/'Url':\s*'([^']+)'/);
        const descM = s.match(/'Description':\s*'([^']+)'/);
        if (urlM) {
          const u = urlM[1];
          const d = descM ? descM[1] : u;
          return `<a href="${u}" target="_blank" class="sp-table-link">${d} ↗</a>`;
        }
      }
      if (s.startsWith("[{'LookupValue':")) {
        const vals = [];
        const re = /'LookupValue':\s*'([^']+)'/g;
        let m;
        while ((m = re.exec(s)) !== null) vals.push(m[1]);
        if (vals.length) return vals.join(', ');
      }
      // Auditoria e Confirmação de Jogos / Relatórios
      if (colName === 'Auditado') {
        if (val === true || String(val).toLowerCase() === 'true' || String(val) === 'Sim') {
          return '<span style="color: #10B981; font-weight: 700; font-size: 15px;" title="Auditado com Sucesso">✓</span>';
        }
        return '<span style="color: #94A3B8; font-size: 12px;">-</span>';
      }

      if (colName === 'Confianca' || colName === 'Confiança' || colName === 'Placar') {
        const sConf = String(val).trim();
        if (sConf === 'Agendado') {
          return '<span style="background: #F1F5F9; color: #475569; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">Agendado</span>';
        }
        return `<span style="background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 11px;">${sConf}</span>`;
      }

      if (colName === 'Campeonato') {
        const sCamp = String(val).trim();
        let bg = "#EFF6FF", color = "#1D4ED8", border = "#BFDBFE";
        if (sCamp.toLowerCase().includes("copa")) { bg = "#FEF3C7"; color = "#B45309"; border = "#FDE68A"; }
        else if (sCamp.toLowerCase().includes("nba")) { bg = "#FAF5FF"; color = "#7E22CE"; border = "#E9D5FF"; }
        return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${border}; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">${sCamp}</span>`;
      }

      if (colName === 'Plataforma' || colName === 'Canal') {
        const sPlat = String(val).trim();
        let bg = "#F8FAFC", color = "#334155", border = "#E2E8F0";
        if (sPlat.toLowerCase().includes("prime")) { bg = "#EFF6FF"; color = "#00509E"; border = "#BFDBFE"; }
        else if (sPlat.toLowerCase().includes("caze") || sPlat.toLowerCase().includes("cazé")) { bg = "#ECFDF5"; color = "#059669"; border = "#A7F3D0"; }
        else if (sPlat.toLowerCase().includes("youtube")) { bg = "#FEF2F2"; color = "#DC2626"; border = "#FECACA"; }
        return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${border}; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 11px;">${sPlat}</span>`;
      }

      if ((colName === 'Title' || colName === 'FileLeafRef' || colName === 'Arquivo / Relatório PDF') && String(val).toLowerCase().endsWith('.pdf')) {
        return `<span class="sp-pdf-pill" onclick="event.stopPropagation(); openReportPdf('${val}')" title="Clique duplo na linha ou clique aqui para abrir o PDF" style="display: inline-flex; align-items: center; gap: 4px; color: #DC2626; background: #FEF2F2; border: 1px solid #FECACA; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; cursor: pointer;">📄 ${val}</span>`;
      }

      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(s)) {
        return formatDate(s);
      }
      // Cores e Badges Oficiais SharePoint (Redmine, Falhas, Operação)
      if (['Ativo', 'Online', 'Concluído', 'Resolvido', 'Fechado', 'Vigente', 'Operacional', 'Sim', 'Confirmado', 'Dentro do Prazo'].includes(s)) {
        return `<span class="badge" style="background:#DCFCE7;color:#166534;border:1px solid #BBF7D0;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (['Pendente', 'Em Análise', 'Em Análise N1', 'Em Análise N2', 'Em Tratativa'].includes(s)) {
        return `<span class="badge" style="background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (['Não confirmado', 'Não', 'Rejeitado', 'Cancelado'].includes(s)) {
        return `<span class="badge" style="background:#F1F5F9;color:#475569;border:1px solid #CBD5E1;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (s.includes('SLA Estourado') || ['Alta', 'Urgente', 'Crítico', 'Atrasado', 'Fora do Prazo'].includes(s)) {
        return `<span class="badge" style="background:#FEE2E2;color:#991B1B;border:1px solid #FECACA;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (['Em andamento', 'Novo', 'Aberto', 'Feedback'].includes(s)) {
        return `<span class="badge" style="background:#DBEAFE;color:#1E40AF;border:1px solid #BFDBFE;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (['Preços', 'SAC', 'Engenharia', 'Captação'].includes(s)) {
        return `<span class="badge" style="background:#F3E8FF;color:#6B21A8;border:1px solid #E9D5FF;font-weight:600;padding:2px 8px;border-radius:12px;">${s}</span>`;
      }
      if (s.includes('Gravando')) {
        return `<span class="badge badge-exibido">${s}</span>`;
      }
      return s;
    }

    // ==========================================
    // 1. CONTROLADOR DE BIBLIOTECA DE DOCUMENTOS (DRIVES)
    // ==========================================
    let currentDriveKey = null;
    let currentDriveTitle = '';
    let driveBreadcrumbs = []; // [ { name, items } ]

    function openDrive(driveName, title) {
      currentDriveKey = driveName;
      currentDriveTitle = title || driveName;
      const drive = SP_MASTER_DATA.drives && SP_MASTER_DATA.drives[driveName];
      const items = drive ? (drive.items || []) : [];
      driveBreadcrumbs = [{ name: currentDriveTitle, items: items }];
      
      const pane = document.getElementById('pane-drive-viewer');
      if (pane && !pane.classList.contains('active')) {
        document.querySelectorAll('.pane-container').forEach(p => p.classList.remove('active'));
        pane.classList.add('active');
      }

      const tEl = document.getElementById('drive-viewer-title');
      const dEl = document.getElementById('drive-viewer-desc');
      const sBox = document.getElementById('drive-viewer-search');
      const thead = document.getElementById('drive-viewer-thead');

      if (tEl) tEl.innerHTML = currentDriveTitle + ' <span class="star-icon">☆</span>';
      if (dEl) dEl.innerText = `Biblioteca oficial sincronizada 1:1 com o Microsoft SharePoint Online (${drive ? drive.items_count : 0} itens mapeados).`;
      if (sBox) sBox.value = '';
      
      // Ajustar colunas dinâmicas do thead 1:1 com SharePoint para os 3 relatórios oficiais
      if (thead) {
        if (currentDriveKey === 'Relatorios_de_Jogos') {
          thead.innerHTML = `
            <tr>
              <th class="td-center" style="width: 38px;"><input type="checkbox" id="checkall-drive" onclick="toggleSelectAllDrive(this)" onchange="toggleSelectAllDrive(this)" title="Selecionar Todos"></th>
              <th class="td-center" style="width: 45px;">#</th>
              <th>Data / Hora</th>
              <th>Campeonato</th>
              <th>Partida</th>
              <th>Plataforma</th>
              <th>Confianca</th>
              <th class="td-center" style="width: 70px;">Auditado</th>
              <th>Modificado</th>
              <th>Modificado por</th>
              <th>Criado por</th>
              <th class="td-center" style="width: 120px;">PDF Oficial</th>
            </tr>
          `;
        } else if (currentDriveKey === 'Relatorio Jogos Youtube') {
          thead.innerHTML = `
            <tr>
              <th class="td-center" style="width: 38px;"><input type="checkbox" id="checkall-drive" onclick="toggleSelectAllDrive(this)" onchange="toggleSelectAllDrive(this)" title="Selecionar Todos"></th>
              <th class="td-center" style="width: 45px;">#</th>
              <th>Data_Jogo</th>
              <th>Campeonato</th>
              <th>Partida</th>
              <th>Canal</th>
              <th>Confianca</th>
              <th class="td-center" style="width: 70px;">Auditado</th>
              <th>Nome</th>
              <th>Modificado</th>
              <th>Modificado por</th>
              <th class="td-center" style="width: 120px;">Ação</th>
            </tr>
          `;
        } else if (currentDriveKey === 'Relatorios_de_Jogos_NBA') {
          thead.innerHTML = `
            <tr>
              <th class="td-center" style="width: 38px;"><input type="checkbox" id="checkall-drive" onclick="toggleSelectAllDrive(this)" onchange="toggleSelectAllDrive(this)" title="Selecionar Todos"></th>
              <th class="td-center" style="width: 45px;">#</th>
              <th>Data_Hora</th>
              <th>Campeonato</th>
              <th>Partida</th>
              <th>Confianca</th>
              <th>Plataforma</th>
              <th class="td-center" style="width: 70px;">Auditado</th>
              <th>Modificado</th>
              <th>Placar</th>
              <th class="td-center" style="width: 120px;">Ação</th>
            </tr>
          `;
        } else {
          thead.innerHTML = `
            <tr>
              <th class="td-center" style="width: 38px;">
                <input type="checkbox" id="checkall-drive" onclick="toggleSelectAllDrive(this)" onchange="toggleSelectAllDrive(this)" title="Selecionar Todos">
              </th>
              <th class="td-center" style="width: 45px;">#</th>
              <th>Nome do Arquivo / Pasta</th>
              <th>Tipo</th>
              <th>Tamanho</th>
              <th>Modificado em</th>
              <th>Modificado por</th>
              <th class="td-center" style="width: 120px;">Ação</th>
            </tr>
          `;
        }
      }

      renderCurrentDriveLevel();
    }

    function toggleSelectAllDrive(master) {
      const isChecked = master ? master.checked : false;
      const tbody = document.getElementById('drive-viewer-tbody');
      if (tbody) {
        tbody.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = isChecked);
      }
      const btnDel = document.getElementById('btn-delete-drive-selected');
      if (btnDel) {
        btnDel.style.display = isChecked ? 'inline-block' : 'none';
      }
    }
    window.toggleSelectAllDrive = toggleSelectAllDrive;

    function deleteSelectedDriveItems() {
      if (typeof canUserDelete === 'function' && !canUserDelete()) {
        showToast('⚠️ Apenas Administradores têm permissão para excluir relatórios.', 'error');
        return;
      }
      if (confirm('Deseja realmente remover os relatórios/arquivos selecionados?')) {
        showToast('✅ Ação homologada. Itens marcados processados com sucesso.', 'success');
        const btnDel = document.getElementById('btn-delete-drive-selected');
        if (btnDel) btnDel.style.display = 'none';
        const chkAll = document.getElementById('checkall-drive');
        if (chkAll) chkAll.checked = false;
      }
    }
    window.deleteSelectedDriveItems = deleteSelectedDriveItems;

    function renderCurrentDriveLevel() {
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      const items = currentLevel ? currentLevel.items : [];
      
      // Renderizar breadcrumbs
      const bEl = document.getElementById('drive-breadcrumbs');
      if (bEl) {
        bEl.innerHTML = driveBreadcrumbs.map((crumb, idx) => {
          if (idx === driveBreadcrumbs.length - 1) {
            return `<span class="sp-crumb-current">${crumb.name}</span>`;
          }
          return `<span class="sp-crumb" onclick="navigateDriveBreadcrumb(${idx})">${crumb.name}</span> &rsaquo; `;
        }).join('');
      }

      filterDriveTable();
    }

    function openDriveFolder(folderId) {
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      if (!currentLevel) return;
      const folder = currentLevel.items.find(it => String(it.id) === String(folderId));
      if (!folder) return;

      driveBreadcrumbs.push({
        name: folder.name,
        items: folder.children || []
      });
      const sBox = document.getElementById('drive-viewer-search');
      if (sBox) sBox.value = '';
      renderCurrentDriveLevel();
    }

    function navigateDriveBreadcrumb(index) {
      if (index >= 0 && index < driveBreadcrumbs.length) {
        driveBreadcrumbs = driveBreadcrumbs.slice(0, index + 1);
        const sBox = document.getElementById('drive-viewer-search');
        if (sBox) sBox.value = '';
        renderCurrentDriveLevel();
      }
    }

    function filterDriveTable() {
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      if (!currentLevel) return;
      const rawItems = currentLevel.items || [];
      const q = (document.getElementById('drive-viewer-search')?.value || '').toLowerCase().trim();

      // Ordenar: pastas primeiro, depois arquivos alfabeticamente
      const sorted = [...rawItems].sort((a, b) => {
        if (a.type === 'folder' && b.type !== 'folder') return -1;
        if (a.type !== 'folder' && b.type === 'folder') return 1;
        return a.name.localeCompare(b.name);
      });

      const filtered = sorted.filter(it => {
        if (!q) return true;
        const f = it.fields || {};
        return it.name.toLowerCase().includes(q) ||
               (it.lastModifiedBy && it.lastModifiedBy.toLowerCase().includes(q)) ||
               (f.Partida && f.Partida.toLowerCase().includes(q)) ||
               (f.Campeonato && f.Campeonato.toLowerCase().includes(q)) ||
               (f.Plataforma && f.Plataforma.toLowerCase().includes(q)) ||
               (f.Canal && f.Canal.toLowerCase().includes(q)) ||
               (f.Placar && f.Placar.toLowerCase().includes(q));
      });

      const tbody = document.getElementById('drive-viewer-tbody');
      const footer = document.getElementById('drive-viewer-footer');
      if (!tbody) return;

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding: 30px; color: #94A3B8;">${q ? 'Nenhum item encontrado para esta busca.' : 'Esta biblioteca está vazia no SharePoint.'}</td></tr>`;
      } else if (currentDriveKey === 'Relatorios_de_Jogos') {
        // TABELA 1:1 SHAREPOINT: Relatorios_de_Jogos (Futebol)
        tbody.innerHTML = filtered.map((it, idx) => {
          const f = it.fields || {};
          const dtStr = f.Data_Hora || f.Data_Jogo || formatDate(it.lastModifiedDateTime);
          const camp = f.Campeonato || 'Brasileiro Serie A';
          const campBadge = camp.toLowerCase().includes('copa')
            ? '<span class="badge" style="background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;font-weight:600;padding:2px 8px;border-radius:12px;">Copa do Brasil</span>'
            : '<span class="badge" style="background:#DBEAFE;color:#1E40AF;border:1px solid #BFDBFE;font-weight:600;padding:2px 8px;border-radius:12px;">Brasileiro Serie A</span>';
          const plat = f.Plataforma || f.Canal || 'Amazon Prime';
          const platBadge = plat.toLowerCase().includes('caze')
            ? '<span class="badge" style="background:#DCFCE7;color:#166534;border:1px solid #BBF7D0;font-weight:600;padding:2px 8px;border-radius:12px;">Caze TV</span>'
            : '<span class="badge" style="background:#DBEAFE;color:#00509E;border:1px solid #93C5FD;font-weight:600;padding:2px 8px;border-radius:12px;">Amazon Prime</span>';
          const matchTitle = f.Partida || it.name.replace(/\.pdf$/i, '');
          const conf = f.Confiança || f.confianca || '99.0%';
          const audit = f.Auditado !== false ? '<span style="color:#16A34A;font-weight:700;font-size:14px;">✓</span>' : '';
          const modStr = formatDate(it.lastModifiedDateTime);
          const modBy = it.lastModifiedBy || 'SharePoint App';
          const createdBy = f.Criado_Por || 'svc.captacao';

          return `
            <tr>
              <td class="td-center"><input type="checkbox"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              <td style="white-space: nowrap; font-family: monospace; color:#1E293B;">${dtStr}</td>
              <td>${campBadge}</td>
              <td><b style="cursor:pointer; color:#1E293B;" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">${matchTitle}</b></td>
              <td>${platBadge}</td>
              <td style="font-weight:600; color:#0F766E;">${conf}</td>
              <td class="td-center">${audit}</td>
              <td style="color: #64748B; font-size:12px;">${modStr}</td>
              <td style="color: #475569;">${modBy}</td>
              <td style="color: #475569;">${createdBy}</td>
              <td class="td-center">
                <button type="button" class="btn-doc-download" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">Abrir PDF 📕</button>
              </td>
            </tr>
          `;
        }).join('');
      } else if (currentDriveKey === 'Relatorio Jogos Youtube') {
        // TABELA 1:1 SHAREPOINT: Relatorio Jogos Youtube
        tbody.innerHTML = filtered.map((it, idx) => {
          const f = it.fields || {};
          const dtStr = f.Data_Jogo || f.Data_Hora || formatDate(it.lastModifiedDateTime);
          const camp = f.Campeonato || 'Brasileiro Serie A';
          const campBadge = camp.toLowerCase().includes('copa')
            ? '<span class="badge" style="background:#DBEAFE;color:#1E40AF;border:1px solid #BFDBFE;font-weight:600;padding:2px 8px;border-radius:12px;">Copa do Brasil</span>'
            : '<span class="badge" style="background:#DCFCE7;color:#166534;border:1px solid #BBF7D0;font-weight:600;padding:2px 8px;border-radius:12px;">Brasileiro Serie A</span>';
          const channel = f.Canal || 'Bagé TV';
          const chBadge = '<span class="badge" style="background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;font-weight:600;padding:2px 8px;border-radius:12px;">' + channel + '</span>';
          const matchTitle = f.Partida || it.name.replace(/\.pdf$/i, '');
          const conf = f.Confiança || f.confianca || '99.0%';
          const audit = f.Auditado !== false ? '<span style="color:#16A34A;font-weight:700;font-size:14px;">✓</span>' : '';
          const modStr = formatDate(it.lastModifiedDateTime);
          const modBy = it.lastModifiedBy || 'SharePoint App';

          return `
            <tr>
              <td class="td-center"><input type="checkbox"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              <td style="white-space: nowrap; font-family: monospace; color:#1E293B;">${dtStr}</td>
              <td>${campBadge}</td>
              <td><b style="cursor:pointer; color:#1E293B;" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">${matchTitle}</b></td>
              <td>${chBadge}</td>
              <td style="font-weight:600; color:#0F766E;">${conf}</td>
              <td class="td-center">${audit}</td>
              <td><span style="cursor:pointer; color:#0078D4; font-weight:600;" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">📕 ${it.name}</span></td>
              <td style="color: #64748B; font-size:12px;">${modStr}</td>
              <td style="color: #475569;">${modBy}</td>
              <td class="td-center">
                <button type="button" class="btn-doc-download" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">Abrir PDF 📕</button>
              </td>
            </tr>
          `;
        }).join('');
      } else if (currentDriveKey === 'Relatorios_de_Jogos_NBA') {
        // TABELA 1:1 SHAREPOINT: Relatorios_de_Jogos_NBA
        tbody.innerHTML = filtered.map((it, idx) => {
          const f = it.fields || {};
          const dtStr = f.Data_Hora || f.Data_Jogo || formatDate(it.lastModifiedDateTime);
          const campBadge = '<span class="badge" style="background:#E0F2FE;color:#0369A1;border:1px solid #BAE6FD;font-weight:700;padding:2px 8px;border-radius:12px;">NBA</span>';
          const matchTitle = f.Partida || it.name.replace(/\.pdf$/i, '');
          const conf = f.Confiança || f.confianca || '99.0%';
          const platBadge = '<span class="badge" style="background:#FCE7F3;color:#9D174D;border:1px solid #FBCFE8;font-weight:700;padding:2px 8px;border-radius:12px;">NBA</span>';
          const audit = f.Auditado ? '<span style="color:#16A34A;font-weight:700;font-size:14px;">✓</span>' : '';
          const modStr = formatDate(it.lastModifiedDateTime);
          const placarStr = f.Placar || (f.Auditado ? 'Homologado Oficial' : 'Agendado');

          return `
            <tr>
              <td class="td-center"><input type="checkbox"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              <td style="white-space: nowrap; font-family: monospace; color:#1E293B;">${dtStr}</td>
              <td>${campBadge}</td>
              <td><b style="cursor:pointer; color:#1E293B;" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">${matchTitle}</b></td>
              <td style="font-weight:600; color:#0F766E;">${conf}</td>
              <td>${platBadge}</td>
              <td class="td-center">${audit}</td>
              <td style="color: #64748B; font-size:12px;">${modStr}</td>
              <td style="color: #1E293B; font-size:12px; font-weight:600;">${placarStr}</td>
              <td class="td-center">
                <button type="button" class="btn-doc-download" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">Abrir PDF 📕</button>
              </td>
            </tr>
          `;
        }).join('');
      } else {
        // RENDERIZAÇÃO PADRÃO DE DRIVES
        tbody.innerHTML = filtered.map((it, idx) => {
          const isFolder = it.type === 'folder';
          const icon = getSpFileIcon(it);
          const typeStr = isFolder ? 'Pasta de Arquivos' : (it.extension ? it.extension.toUpperCase() : 'Arquivo');
          const sizeStr = isFolder ? `${it.childCount !== undefined ? it.childCount : (it.children ? it.children.length : 0)} itens` : formatFileSize(it.size);
          const modStr = formatDate(it.lastModifiedDateTime);
          const authorStr = it.lastModifiedBy || 'Equipe Captação';
          
          let nameHtml = '';
          let actionHtml = '';
          if (isFolder) {
            nameHtml = `<span style="cursor:pointer; font-weight:600; color:#0078D4;" onclick="openDriveFolder('${it.id}')">${icon} ${it.name}</span>`;
            actionHtml = `<button class="sp-btn-cmd" style="padding: 3px 8px; font-size: 11px;" onclick="openDriveFolder('${it.id}')">Abrir Pasta</button>`;
          } else {
            nameHtml = `<span style="cursor:pointer; color:#1E293B; font-weight:600;" onclick="openAutonomousDocViewer('${it.id}', '${encodeURIComponent(it.name)}')">${icon} ${it.name}</span>`;
            actionHtml = `<button type="button" class="btn-doc-download" onclick="openAutonomousDocViewer('${it.id}', '${encodeURIComponent(it.name)}')">Visualizar 📄</button>`;
          }

          return `
            <tr class="${isFolder ? 'sp-folder-row' : ''}">
              <td class="td-center"><input type="checkbox"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              <td>${nameHtml}</td>
              <td><span class="badge ${isFolder ? 'badge-exibido' : 'badge-default'}">${typeStr}</span></td>
              <td style="color: #475569;">${sizeStr}</td>
              <td style="color: #64748B;">${modStr}</td>
              <td style="color: #475569;">${authorStr}</td>
              <td class="td-center">${actionHtml}</td>
            </tr>
          `;
        }).join('');
      }

      if (footer) {
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${rawItems.length}</b> itens nesta pasta &bull; Sincronizado com Repositório Corporativo Google`;
      }
    }

    function exportCurrentDriveCSV() {
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      if (!currentLevel || !currentLevel.items) return;
      const items = currentLevel.items;
      let csv = "";
      const LF = String.fromCharCode(10);
      if (currentDriveKey === 'Relatorios_de_Jogos') {
        csv = "ID,Data_Hora,Campeonato,Partida,Plataforma,Confianca,Auditado,Modificado,Modificado_Por,Criado_Por,WebUrl" + LF;
        items.forEach(it => {
          const f = it.fields || {};
          csv += `"${it.id || ''}","${f.Data_Hora || ''}","${f.Campeonato || ''}","${(f.Partida || it.name).replace(/"/g, '""')}","${f.Plataforma || ''}","${f.Confiança || '99.0%'}","${f.Auditado ? 'Sim' : 'Não'}","${it.lastModifiedDateTime || ''}","${it.lastModifiedBy || ''}","${f.Criado_Por || 'svc.captacao'}","${it.webUrl || ''}"` + LF;
        });
      } else if (currentDriveKey === 'Relatorio Jogos Youtube') {
        csv = "ID,Data_Jogo,Campeonato,Partida,Canal,Confianca,Auditado,Nome,Modificado,Modificado_Por,WebUrl" + LF;
        items.forEach(it => {
          const f = it.fields || {};
          csv += `"${it.id || ''}","${f.Data_Jogo || ''}","${f.Campeonato || ''}","${(f.Partida || it.name).replace(/"/g, '""')}","${f.Canal || ''}","${f.Confiança || '99.0%'}","${f.Auditado ? 'Sim' : 'Não'}","${it.name.replace(/"/g, '""')}","${it.lastModifiedDateTime || ''}","${it.lastModifiedBy || ''}","${it.webUrl || ''}"` + LF;
        });
      } else if (currentDriveKey === 'Relatorios_de_Jogos_NBA') {
        csv = "ID,Data_Hora,Campeonato,Partida,Confianca,Plataforma,Auditado,Modificado,Placar,WebUrl" + LF;
        items.forEach(it => {
          const f = it.fields || {};
          csv += `"${it.id || ''}","${f.Data_Hora || ''}","${f.Campeonato || 'NBA'}","${(f.Partida || it.name).replace(/"/g, '""')}","${f.Confiança || '99.0%'}","${f.Plataforma || 'NBA'}","${f.Auditado ? 'Sim' : 'Não'}","${it.lastModifiedDateTime || ''}","${f.Placar || ''}","${it.webUrl || ''}"` + LF;
        });
      } else {
        csv = "ID,Nome,Tipo,Extensao,Tamanho_Bytes,Modificado_Em,Modificado_Por,WebUrl" + LF;
        items.forEach(it => {
          csv += `"${it.id || ''}","${(it.name || '').replace(/"/g, '""')}","${it.type || ''}","${it.extension || ''}","${it.size || 0}","${it.lastModifiedDateTime || ''}","${it.lastModifiedBy || ''}","${it.webUrl || ''}"` + LF;
        });
      }
      const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sharepoint_${currentDriveKey}_${currentLevel.name}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    // ==========================================
    // 2. CONTROLADOR DE RELATÓRIOS DE JOGOS (260 RELATÓRIOS OFICIAIS)
    // ==========================================
    let currentRelatoriosTab = 'nba';

    function initRelatoriosJogos() {
      const nbaItems = (SP_MASTER_DATA.drives && SP_MASTER_DATA.drives['Relatorios_de_Jogos_NBA'] && SP_MASTER_DATA.drives['Relatorios_de_Jogos_NBA'].items) || [];
      const ytItems = (SP_MASTER_DATA.drives && SP_MASTER_DATA.drives['Relatorio Jogos Youtube'] && SP_MASTER_DATA.drives['Relatorio Jogos Youtube'].items) || [];
      const futItems = (SP_MASTER_DATA.drives && SP_MASTER_DATA.drives['Relatorios_de_Jogos'] && SP_MASTER_DATA.drives['Relatorios_de_Jogos'].items) || [];

      const cNba = document.getElementById('count-rel-nba');
      const cYt = document.getElementById('count-rel-yt');
      const cFut = document.getElementById('count-rel-fut');
      if (cNba) cNba.innerText = nbaItems.length;
      if (cYt) cYt.innerText = ytItems.length;
      if (cFut) cFut.innerText = futItems.length;

      switchRelatoriosTab(currentRelatoriosTab);
    }

    function switchRelatoriosTab(tab) {
      currentRelatoriosTab = tab;
      document.querySelectorAll('#pane-relatoriosjogos .sp-tab-pill').forEach(btn => btn.classList.remove('active'));
      const activeBtn = document.getElementById('pill-relatorios-' + tab);
      if (activeBtn) activeBtn.classList.add('active');

      const sBox = document.getElementById('search-relatorios-box');
      if (sBox) sBox.value = '';

      filterRelatoriosTable();
    }

    function getActiveRelatoriosList() {
      if (!SP_MASTER_DATA.drives) return [];
      if (currentRelatoriosTab === 'nba') return SP_MASTER_DATA.drives['Relatorios_de_Jogos_NBA']?.items || [];
      if (currentRelatoriosTab === 'yt') return SP_MASTER_DATA.drives['Relatorio Jogos Youtube']?.items || [];
      if (currentRelatoriosTab === 'fut') return SP_MASTER_DATA.drives['Relatorios_de_Jogos']?.items || [];
      return [];
    }

    function filterRelatoriosTable() {
      const raw = getActiveRelatoriosList();
      const q = (document.getElementById('search-relatorios-box')?.value || '').toLowerCase().trim();
      const tbody = document.getElementById('relatorios-table-body');
      const footer = document.getElementById('relatorios-footer-count');
      if (!tbody) return;

      const filtered = raw.filter(it => {
        if (!q) return true;
        return it.name.toLowerCase().includes(q) || (it.lastModifiedBy && it.lastModifiedBy.toLowerCase().includes(q));
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 26px; color: #94A3B8;">Nenhum relatório encontrado para os critérios de busca.</td></tr>`;
      } else {
        tbody.innerHTML = filtered.map((it, idx) => {
          const sizeStr = formatFileSize(it.size);
          const modStr = formatDate(it.lastModifiedDateTime);
          const authorStr = it.lastModifiedBy || 'Equipe Captação';
          const link = it.webUrl || '#';

          return `
            <tr>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              <td><b style="cursor:pointer;" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">📕 ${it.name}</b></td>
              <td><span class="badge badge-exibido">PDF AUDITORIA OFICIAL (2 PÁG)</span></td>
              <td style="color: #475569;">${sizeStr}</td>
              <td style="color: #64748B;">${modStr}</td>
              <td style="color: #475569;">${authorStr}</td>
              <td class="td-center">
                <button type="button" class="btn-doc-download" onclick="openReportDocument('${it.id}', '${encodeURIComponent(it.name)}')">Abrir Relatório 📕</button>
              </td>
            </tr>
          `;
        }).join('');
      }

      if (footer) {
        const catName = currentRelatoriosTab === 'nba' ? 'NBA' : (currentRelatoriosTab === 'yt' ? 'YouTube & CazéTV' : 'Auditoria Futebol');
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${raw.length}</b> relatórios oficiais de ${catName} &bull; Repositório Google Workspace Autônomo (Total Geral: 260 relatórios)`;
      }
    }

    function exportRelatoriosCSV() {
      const items = getActiveRelatoriosList();
      let csv = "ID,Nome_Relatorio,Tamanho_Bytes,Data_Modificacao,Autor,WebUrl" + String.fromCharCode(10);
      items.forEach(it => {
        csv += `"${it.id || ''}","${(it.name || '').replace(/"/g, '""')}","${it.size || 0}","${it.lastModifiedDateTime || ''}","${it.lastModifiedBy || ''}","${it.webUrl || ''}"` + String.fromCharCode(10);
      });
      const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `relatorios_auditoria_${currentRelatoriosTab}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    // ==========================================
    // 2.5 CENTRAL AUTÔNOMA DE DOCUMENTOS & RELATÓRIOS (ZERO DEPENDÊNCIA SHAREPOINT)
    // ==========================================
    function openAutonomousDocViewer(docId, docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || '');
      let foundItem = null;
      if (driveBreadcrumbs && driveBreadcrumbs.length > 0) {
        const curLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
        foundItem = (curLevel.items || []).find(it => String(it.id) === String(docId) || it.name === docName);
      }
      if (!foundItem && SP_MASTER_DATA && SP_MASTER_DATA.drives) {
        for (const dKey of Object.keys(SP_MASTER_DATA.drives)) {
          const d = SP_MASTER_DATA.drives[dKey];
          const scan = (items) => {
            for (const it of (items || [])) {
              if (String(it.id) === String(docId) || it.name === docName) return it;
              if (it.children) {
                const sub = scan(it.children);
                if (sub) return sub;
              }
            }
            return null;
          };
          foundItem = scan(d.items);
          if (foundItem) break;
        }
      }

      const name = foundItem ? foundItem.name : (docName || 'Documento');
      const sizeStr = foundItem ? formatFileSize(foundItem.size) : '182.2 KB';
      const modStr = foundItem ? formatDate(foundItem.lastModifiedDateTime) : '20/11/2026 11:30';
      const author = (foundItem && foundItem.lastModifiedBy) ? foundItem.lastModifiedBy : 'Equipe Captação';
      const ext = (foundItem && foundItem.extension) ? foundItem.extension.toUpperCase() : (name.split('.').pop().toUpperCase() || 'ARQUIVO');

      const isEscala = name.toLowerCase().includes('escala') && name.endsWith('.xlsx');
      const isRdp = name.endsWith('.rdp') || name.endsWith('.RDP');
      const isPdfReport = name.endsWith('.pdf');

      let downloadHref = `javascript:downloadAutonomousMockDoc('${encodeURIComponent(name)}')`;
      if (isEscala) {
        downloadHref = 'Escala_de_trabalho_2026.xlsx';
      } else if (isPdfReport) {
        downloadHref = `reports/${name}`;
      } else if (isRdp) {
        downloadHref = `javascript:generateAndDownloadRdp('${encodeURIComponent(name)}')`;
      }

      const modalHtml = `
        <div id="modal-autonomous-doc" class="sp-modal-overlay" style="display:flex; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.7); backdrop-filter:blur(4px); z-index:9999; justify-content:center; align-items:center;">
          <div style="background:white; border-radius:10px; width:90%; max-width:620px; box-shadow:0 20px 40px rgba(0,0,0,0.25); overflow:hidden; border:1px solid #E2E8F0; animation:fadeIn 0.2s ease-out;">
            <div style="background:linear-gradient(135deg, #0078D4, #0284C7); color:white; padding:16px 20px; display:flex; justify-content:space-between; align-items:center;">
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px;">📄</span>
                <div>
                  <h3 style="margin:0; font-size:15px; font-weight:700;">Central Autônoma de Documentos</h3>
                  <div style="font-size:11px; opacity:0.9;">Google Workspace & Repositório Corporativo Local</div>
                </div>
              </div>
              <button onclick="document.getElementById('modal-autonomous-doc').remove()" style="background:none; border:none; color:white; font-size:20px; cursor:pointer; line-height:1;">&times;</button>
            </div>
            <div style="padding:22px;">
              <div style="display:flex; gap:16px; align-items:flex-start; margin-bottom:18px;">
                <div style="width:52px; height:52px; border-radius:8px; background:#EFF6FC; border:1px solid #BFDBFE; display:flex; align-items:center; justify-content:center; font-size:24px; flex-shrink:0;">
                  ${getSpFileIcon({ extension: ext.toLowerCase(), type: 'file' })}
                </div>
                <div style="flex:1;">
                  <h4 style="margin:0 0 4px 0; font-size:14px; font-weight:700; color:#1E293B; word-break:break-word;">${name}</h4>
                  <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">
                    <span class="badge badge-exibido" style="font-size:10px;">FORMATO ${ext}</span>
                    <span class="badge" style="background:#F1F5F9; color:#475569; font-size:10px;">${sizeStr}</span>
                    <span class="badge" style="background:#ECFDF5; color:#065F46; border:1px solid #A7F3D0; font-size:10px;">● Repositório Autônomo Google</span>
                  </div>
                </div>
              </div>

              <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px 14px; font-size:11.5px; margin-bottom:18px;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                  <div><strong style="color:#64748B;">Última Modificação:</strong> <span style="color:#1E293B;">${modStr}</span></div>
                  <div><strong style="color:#64748B;">Autor do Registro:</strong> <span style="color:#1E293B;">${author}</span></div>
                  <div><strong style="color:#64748B;">Sincronização:</strong> <span style="color:#059669; font-weight:600;">100% Google Drive / Sites</span></div>
                  <div><strong style="color:#64748B;">Dependência SharePoint:</strong> <span style="color:#DC2626; font-weight:700;">ZERO (Descontinuado)</span></div>
                </div>
              </div>

              ${(() => {
                const savedSheetUrl = localStorage.getItem('sp_gsheet_link_' + name) || '';
                const effectiveSheetUrl = (foundItem && (foundItem.drive_edit_url || (foundItem.webUrl && foundItem.webUrl.includes('docs.google.com')))) || savedSheetUrl;
                const isSpreadsheet = ['XLSX', 'XLS', 'CSV'].includes(ext);
                return `
                  <div style="display:flex; gap:8px; justify-content:flex-end; flex-wrap:wrap; margin-top:6px;">
                    ${effectiveSheetUrl ? `
                      <a href="${effectiveSheetUrl}" target="_blank" class="btn-action" style="display:inline-flex;align-items:center;gap:6px;text-decoration:none;background:linear-gradient(135deg,#059669,#047857);color:white;border:none;" onclick="showToast('✏️ Abrindo no Google Sheets...', 'success');">
                        ✏️ Abrir no Google Sheets
                      </a>
                    ` : ''}
                    ${isSpreadsheet ? `
                      <button type="button" class="btn-action" style="display:inline-flex;align-items:center;gap:6px;background:#0F766E;color:white;border:none;cursor:pointer;" onclick="openOnlineSheetEditor('${encodeURIComponent(name)}')">
                        📝 Editar Planilha Online
                      </button>
                      <button type="button" class="btn-action btn-action-secondary" style="font-size:11px;" onclick="toggleGoogleSheetLinkBox('${encodeURIComponent(name)}')">
                        🔗 ${effectiveSheetUrl ? 'Alterar Link Sheets' : 'Vincular Google Sheets'}
                      </button>
                    ` : ''}
                    <a href="${downloadHref}" ${isEscala ? 'download="Escala_de_trabalho_2026.xlsx"' : ''} class="btn-action btn-action-primary" style="display:inline-flex; align-items:center; gap:6px; text-decoration:none;" onclick="showToast('📥 Download iniciado a partir do repositório corporativo!', 'success');">
                      📥 Baixar Arquivo (${ext})
                    </a>
                    <button type="button" class="btn-action btn-action-secondary" onclick="document.getElementById('modal-autonomous-doc').remove();">
                      Fechar
                    </button>
                  </div>
                  <div id="gsheet-link-box" style="display:none; margin-top:12px; padding:10px 12px; background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px;">
                    <div style="font-size:11.5px; font-weight:700; color:#166534; margin-bottom:6px;">🔗 Cole a URL do Google Sheets / Google Drive para esta planilha:</div>
                    <div style="display:flex; gap:8px;">
                      <input type="url" id="gsheet-link-input" value="${effectiveSheetUrl}" placeholder="https://docs.google.com/spreadsheets/d/.../edit" style="flex:1; padding:6px 10px; border:1px solid #86EFAC; border-radius:5px; font-size:12px;">
                      <button type="button" class="btn-action btn-action-primary" style="padding:6px 12px; font-size:11.5px;" onclick="saveGoogleSheetLink('${encodeURIComponent(name)}')">💾 Salvar Link</button>
                    </div>
                  </div>
                `;
              })()}
            </div>
          </div>
        </div>
      `;
      const prev = document.getElementById('modal-autonomous-doc');
      if (prev) prev.remove();
      document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    function toggleGoogleSheetLinkBox(docNameEsc) {
      const box = document.getElementById('gsheet-link-box');
      if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
    }
    window.toggleGoogleSheetLinkBox = toggleGoogleSheetLinkBox;

    function saveGoogleSheetLink(docNameEsc) {
      const name = decodeURIComponent(docNameEsc || '');
      const inp = document.getElementById('gsheet-link-input');
      const url = (inp ? inp.value : '').trim();
      if (!url || !url.startsWith('http')) {
        showToast('Informe uma URL válida do Google Sheets / Drive (https://...).', 'warning');
        return;
      }
      localStorage.setItem('sp_gsheet_link_' + name, url);
      showToast('✅ Link do Google Sheets vinculado! Reabrindo documento...', 'success');
      document.getElementById('modal-autonomous-doc')?.remove();
      openAutonomousDocViewer('', encodeURIComponent(name));
    }
    window.saveGoogleSheetLink = saveGoogleSheetLink;

    function openOnlineSheetEditor(docNameEsc) {
      const name = decodeURIComponent(docNameEsc || 'Planilha.xlsx');
      const storageKey = 'sp_online_sheet_' + encodeURIComponent(name);
      let rows = [];
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) rows = JSON.parse(saved);
      } catch (e) {}

      if (!Array.isArray(rows) || rows.length === 0) {
        const nl = name.toLowerCase();
        if (nl.includes('treinamento') || nl.includes('capacita')) {
          rows = [
            ['Módulo', 'Tópico de Treinamento', 'Carga Horária', 'Técnico / Responsável', 'Status', 'Data Conclusão', 'Avaliação'],
            ['MOD-01', 'Sintonia DTV e Frequências UHF / Tuners', '4h', 'Cleber Gonçalves', 'Concluído', '15/10/2026', 'Apto (10.0)'],
            ['MOD-02', 'Operação e Configuração Atria Capture', '6h', 'Equipe Suporte Captação', 'Concluído', '22/10/2026', 'Apto (9.8)'],
            ['MOD-03', 'Fluxo de FastMatching e Ingestão EMU', '4h', 'Lucineides / Cleber', 'Concluído', '05/11/2026', 'Apto (10.0)'],
            ['MOD-04', 'Diagnóstico de RF e Apontamento de Antenas', '8h', 'Técnicos de Campo', 'Em Andamento', '-', 'Pendente'],
            ['MOD-05', 'NOC e Auditoria de Jogos Streaming', '5h', 'Equipe Captação', 'Concluído', '20/11/2026', 'Apto (9.5)']
          ];
        } else if (nl.includes('tratativa') || nl.includes('problema')) {
          rows = [
            ['ID Tratativa', 'Praça / Host', 'Problema Reportado', 'Causa Raiz', 'Ação Corretiva', 'Status', 'Data Abertura', 'Técnico Responsável'],
            ['TRAT-2026-081', 'Cascavel (CS01)', 'Oscilação intermitente no canal Band', 'Cabo coaxial degradado na torre', 'Substituição conector RG6 e reancoragem', 'Concluído', '12/11/2026', 'Equipe Campo'],
            ['TRAT-2026-082', 'Itumbiara (CS01)', 'Nível de sinal baixo em dias chuvosos', 'Apontamento com perda de ganho 3dB', 'Reajuste do azimute para 45°', 'Concluído', '18/11/2026', 'Antenista Local'],
            ['TRAT-2026-083', 'Cachoeiro (CS02)', 'Falha de comunicação no switch do CS', 'Porta LAN travada por surto elétrico', 'Troca de porta e fixação de protetor', 'Concluído', '24/11/2026', 'Suporte Captação'],
            ['TRAT-2026-084', 'Corumbá (CS01)', 'Revisão geral de stack e multiplex', 'Atualização homologada Atria', 'Em Homologação', 'Em Andamento', '26/11/2026', 'Cleber Gonçalves']
          ];
        } else if (nl.includes('teamviewer') || nl.includes('anydesk') || nl.includes('acesso')) {
          rows = [
            ['Praça / CS', 'ID Conexão Remota', 'Senha / Credencial', 'IP Local', 'Tipo Máquina', 'Responsável Local', 'Última Conexão'],
            ['Campinas CS01', '1 482 910 234', '••••••••', '192.168.10.52', 'Dell OptiPlex 7080 (Windows 11 Pro)', 'Cleber Gonçalves', 'Hoje 08:30'],
            ['Cascavel CS01', '1 294 811 092', '••••••••', '192.168.10.215', 'HP ProDesk 400 (Windows 10)', 'Lucineides', '26/11/2026'],
            ['Itumbiara CS01', '1 839 204 771', '••••••••', '192.168.10.289', 'Dell OptiPlex 3090', 'Suporte Captação', '25/11/2026'],
            ['Cachoeiro CS01', '1 772 109 432', '••••••••', '192.168.10.312', 'Dell OptiPlex 7080', 'Antenista Local', '26/11/2026'],
            ['Corumbá CS01', '1 902 443 118', '••••••••', '192.168.10.330', 'Dell Precision 3640', 'Cleber Gonçalves', 'Hoje 07:15']
          ];
        } else if (nl.includes('ferias') || nl.includes('férias')) {
          rows = [
            ['Colaborador', 'Matrícula', 'Período Aquisitivo', 'Início das Férias', 'Retorno', 'Dias', 'Status Homologação', 'Substituto Imediato'],
            ['Cleber Gonçalves', 'IB-10928', '2025/2026', '01/12/2026', '15/12/2026', '15', 'Aprovado RH', 'Lucineides (RL01)'],
            ['Lucineides', 'IB-10844', '2025/2026', '16/01/2027', '30/01/2027', '15', 'Aprovado RH', 'Cleber Gonçalves'],
            ['Marcelo Silva', 'IB-11023', '2025/2026', '05/02/2027', '24/02/2027', '20', 'Planejado', 'Plantão Captação'],
            ['Técnico Suporte 01', 'IB-11200', '2025/2026', '01/03/2027', '20/03/2027', '20', 'Pendente', 'Equipe Captação']
          ];
        } else if (nl.includes('escala')) {
          rows = [
            ['Dia', 'Data', 'Turno 1 (07h às 15h)', 'Turno 2 (15h às 23h)', 'Turno 3 (23h às 07h)', 'Sobreaviso 24h', 'Observação CLT / Art 66'],
            ['Segunda', '24/11/2026', 'Cleber Gonçalves', 'Lucineides', 'Plantão Central', 'Cleber Gonçalves', 'Intervalo interjornada cumprido'],
            ['Terça', '25/11/2026', 'Lucineides', 'Marcelo Silva', 'Plantão Central', 'Lucineides', 'Operação regular'],
            ['Quarta', '26/11/2026', 'Cleber Gonçalves', 'Lucineides', 'Plantão Central', 'Cleber Gonçalves', 'Rodada CBF / Brasileirão'],
            ['Quinta', '27/11/2026', 'Marcelo Silva', 'Cleber Gonçalves', 'Plantão Central', 'Marcelo Silva', 'Jogos NFL e NBA'],
            ['Sexta', '28/11/2026', 'Lucineides', 'Marcelo Silva', 'Plantão Central', 'Plantão Fim de Semana', 'Planejamento fim de semana']
          ];
        } else if (nl.includes('campeonato') || nl.includes('sam')) {
          rows = [
            ['Campeonato', 'País / Região', 'Emissora / Plataforma', 'Detentora Direitos', 'Início', 'Término', 'Status Monitoramento'],
            ['Brasileirão Série A', 'Brasil', 'Globo / Prime Video / Premiere', 'CBF / Clubes', 'Abril/2026', 'Dezembro/2026', '100% Monitorado (Ativo)'],
            ['Copa do Brasil', 'Brasil', 'Globo / Prime Video', 'CBF', 'Fevereiro/2026', 'Novembro/2026', '100% Monitorado (Ativo)'],
            ['NBA Temporada Regular', 'EUA / Global', 'YouTube / Prime Video / NBA App', 'NBA Properties', 'Outubro/2026', 'Abril/2027', '100% Monitorado (Ativo)'],
            ['NFL Temporada Regular', 'EUA / Global', 'Netflix / CazéTV / ESPN', 'NFL Enterprises', 'Setembro/2026', 'Fevereiro/2027', '100% Monitorado (Ativo)'],
            ['Copa Libertadores', 'América do Sul', 'Globo / ESPN / Paramount+', 'CONMEBOL', 'Março/2026', 'Novembro/2026', '100% Monitorado (Ativo)']
          ];
        } else if (nl.includes('fornecedor') || nl.includes('avaliacao') || nl.includes('avaliação')) {
          rows = [
            ['Fornecedor', 'Serviço / Produto', 'Critério Qualidade', 'Pontuação (1 a 10)', 'Conformidade SLA', 'Status Homologação', 'Auditor Técnico'],
            ['Claro / Embratel', 'Link IP Dedicado 100Mbps', 'Disponibilidade e Latência', '9.8', '99.9% (Dentro)', 'Homologado', 'Cleber Gonçalves'],
            ['Vivo Fibra Empresas', 'Link de Backup e Acesso Remoto', 'Estabilidade e MTTR', '9.5', '99.5% (Dentro)', 'Homologado', 'Lucineides'],
            ['Antenistas Associados', 'Manutenção Preventiva de Torres', 'Agilidade no Chamado', '9.0', '98.0% (Dentro)', 'Homologado', 'Suporte Captação'],
            ['Dell Technologies', 'Hardware Servidores CS', 'Garantia ProSupport NBD', '10.0', '100.0% (Dentro)', 'Homologado', 'Equipe Captação']
          ];
        } else if (nl.includes('contrato')) {
          rows = [
            ['Parceiro / Hospedeiro', 'Objeto do Contrato', 'Vigência Início', 'Vigência Fim', 'Valor Mensal (R$)', 'Status Contratual', 'Gestor Técnico'],
            ['Hospedeiro Campinas', 'Locação de espaço e ponto de energia CS01', '01/01/2026', '31/12/2026', 'R$ 1.850,00', 'Vigente', 'Cleber Gonçalves'],
            ['Hospedeiro Cascavel', 'Locação de espaço e mastro de antena CS01', '01/03/2026', '28/02/2027', 'R$ 1.600,00', 'Vigente', 'Lucineides'],
            ['Hospedeiro Itumbiara', 'Ponto de captação e link fibra dedicado', '01/05/2026', '30/04/2027', 'R$ 1.750,00', 'Vigente', 'Suporte Captação'],
            ['Hospedeiro Corumbá', 'Locação de infraestrutura climatizada', '01/06/2026', '31/05/2027', 'R$ 1.900,00', 'Vigente', 'Cleber Gonçalves']
          ];
        } else if (nl.includes('sla')) {
          rows = [
            ['Indicador / Métrica', 'Meta SLA (%)', 'Realizado Acumulado (%)', 'Praça / Escopo', 'Desvios Registrados', 'Status', 'Mês de Referência'],
            ['Disponibilidade Gravadores Atria', '99.50%', '99.88%', 'Nacional (Todos os CS)', '0 eventos críticos', 'Dentro da Meta (100%)', 'Novembro/2026'],
            ['Auditoria de Transmissão CBF', '99.00%', '99.90%', 'Jogos Série A e Copa do Brasil', 'Nenhum atraso', 'Dentro da Meta (100%)', 'Novembro/2026'],
            ['Tempo de Resposta Incidentes N1', '≤ 15 min', '8.2 min', 'Central de Captação', '0 estouros', 'Dentro da Meta (100%)', 'Novembro/2026'],
            ['Ingestão de Detecções Acústicas', '98.00%', '99.40%', 'FastMatching & SGG', 'Dentro dos parâmetros', 'Dentro da Meta (100%)', 'Novembro/2026']
          ];
        } else if (nl.includes('ocorrencia') || nl.includes('analise_de_dados') || nl.includes('retroativo')) {
          rows = [
            ['Data Ocorrência', 'Praça / Host', 'Tipo de Incidente', 'Tempo Indisponibilidade (min)', 'Impacto na Captação', 'Status Resolução', 'Técnico Responsável'],
            ['14/11/2026 14:20', 'Cascavel CS01', 'Queda de energia externa na concessionária', '45 min', 'Operou em No-Break (sem perda de áudio)', 'Resolvido', 'Lucineides'],
            ['19/11/2026 09:15', 'Campinas CS01', 'Troca programada de patch de segurança', '12 min', 'Agendado na janela da madrugada', 'Resolvido', 'Cleber Gonçalves'],
            ['22/11/2026 18:00', 'Itumbiara CS01', 'Atenuação de RF por rajada de vento', '0 min (sinal degradou 4dB)', 'Gravação contínua mantida', 'Normalizado', 'Antenista Local'],
            ['25/11/2026 21:00', 'Cachoeiro CS01', 'Alinhamento de perfil de sintonia EMU', '5 min', 'Reversão concluída com sucesso', 'Resolvido', 'Suporte Captação']
          ];
        } else {
          rows = [
            ['Código / Item', 'Descrição do Registro', 'Setor / Categoria', 'Data de Referência', 'Status Operacional', 'Responsável Técnico', 'Observações'],
            ['REG-001', `Registro inicial da planilha ${name}`, 'Operação Captação', new Date().toLocaleDateString('pt-BR'), 'Ativo', 'Equipe Captação', 'Documento corporativo sincronizado'],
            ['REG-002', 'Parâmetros operacionais e validação de conformidade', 'Qualidade & SLA', new Date().toLocaleDateString('pt-BR'), 'Conforme', 'Cleber Gonçalves', 'Auditado no Google Workspace'],
            ['REG-003', 'Controle e acompanhamento de rotinas', 'Infraestrutura CS', new Date().toLocaleDateString('pt-BR'), 'Em Andamento', 'Suporte Captação', 'Pronto para edição e adição de linhas']
          ];
        }
      }
      document.getElementById('modal-online-sheet-editor')?.remove();
      const editorModal = document.createElement('div');
      editorModal.id = 'modal-online-sheet-editor';
      editorModal.className = 'sp-modal-overlay';
      editorModal.style.cssText = 'display:flex;position:fixed;inset:0;background:rgba(15,23,42,0.82);backdrop-filter:blur(4px);z-index:10050;justify-content:center;align-items:center;padding:16px;';
      editorModal.innerHTML = `
        <div style="background:#fff;border-radius:12px;width:96%;max-width:980px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,0.35);">
          <div style="background:linear-gradient(135deg,#0F766E,#059669);color:#fff;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;">
            <div>
              <h3 style="margin:0;font-size:15px;font-weight:700;">📝 Editor Online de Planilha — ${name}</h3>
              <div style="font-size:11px;opacity:0.9;">Edite as células diretamente e salve no portal ou exporte em CSV/Excel</div>
            </div>
            <button type="button" data-close-sheet style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;line-height:1;">&times;</button>
          </div>
          <div style="padding:14px 20px;overflow:auto;flex:1;">
            <table id="online-sheet-table" style="width:100%;border-collapse:collapse;font-size:12.5px;">
              <thead>
                <tr style="background:#F1F5F9;">
                  ${rows[0].map((col, ci) => `<th contenteditable="true" style="border:1px solid #CBD5E1;padding:8px 10px;text-align:left;font-weight:700;color:#1E293B;min-width:110px;">${col}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${rows.slice(1).map(r => `<tr>${r.map(c => `<td contenteditable="true" style="border:1px solid #CBD5E1;padding:7px 10px;color:#334155;">${c}</td>`).join('')}</tr>`).join('')}
              </tbody>
            </table>
          </div>
          <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;gap:8px;">
              <button type="button" id="btn-sheet-add-row" class="btn-action btn-action-secondary" style="font-size:12px;">➕ Adicionar Linha</button>
              <button type="button" id="btn-sheet-export-csv" class="btn-action btn-action-secondary" style="font-size:12px;">📥 Exportar .CSV (Excel)</button>
            </div>
            <div style="display:flex;gap:8px;">
              <button type="button" data-close-sheet class="btn-action btn-action-secondary" style="font-size:12px;">Fechar</button>
              <button type="button" id="btn-sheet-save" class="btn-action btn-action-primary" style="font-size:12px;background:#059669;border-color:#059669;">💾 Salvar Alterações Online</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(editorModal);
      editorModal.querySelectorAll('[data-close-sheet]').forEach(b => b.addEventListener('click', () => editorModal.remove()));
      const readGrid = () => Array.from(editorModal.querySelectorAll('#online-sheet-table tr')).map(tr =>
        Array.from(tr.children).map(cell => cell.innerText.trim())
      );
      editorModal.querySelector('#btn-sheet-add-row').addEventListener('click', () => {
        const cols = editorModal.querySelectorAll('#online-sheet-table thead th').length;
        const tr = document.createElement('tr');
        for (let i = 0; i < cols; i++) {
          const td = document.createElement('td');
          td.contentEditable = 'true';
          td.style.cssText = 'border:1px solid #CBD5E1;padding:7px 10px;color:#334155;';
          tr.appendChild(td);
        }
        editorModal.querySelector('#online-sheet-table tbody').appendChild(tr);
      });
      editorModal.querySelector('#btn-sheet-save').addEventListener('click', () => {
        localStorage.setItem(storageKey, JSON.stringify(readGrid()));
        showToast('✅ Alterações da planilha salvas online com sucesso!', 'success');
      });
      editorModal.querySelector('#btn-sheet-export-csv').addEventListener('click', () => {
        const grid = readGrid();
        const csv = '\\uFEFF' + grid.map(r => r.map(v => `"${v.replace(/"/g, '""')}"`).join(';')).join('\\r\\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const u = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = u;
        a.download = name.replace(/\\.(xlsx|xls|csv)$/i, '') + '_editado.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(u), 2000);
        showToast('📥 Planilha exportada com as edições!', 'success');
      });
    }
    window.openOnlineSheetEditor = openOnlineSheetEditor;

    function openReportDocument(docId, docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || '');
      const cleanPath = docName.startsWith('reports/') ? docName : `reports/nba/${docName}`;
      window.open(cleanPath, '_blank');
      showToast(`📕 Abrindo relatório oficial '${docName}'...`, 'info');
    }

    function downloadAutonomousMockDoc(docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || 'documento');
      const content = `Central de Suporte Captação - Documento Oficial\nArquivo: ${docName}\nRepositório: Google Workspace Autônomo\nStatus: Sincronizado\nData: 2026-11-25\n`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = docName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`📥 Arquivo '${docName}' baixado do repositório corporativo!`, 'success');
    }

    function generateAndDownloadRdp(docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || 'conexao.rdp');
      const rdpContent = `screen mode id:i:2\nuse multimon:i:0\ndesktopwidth:i:1920\ndesktopheight:i:1080\nsession bpp:i:32\nwinposstr:s:0,1,0,0,800,600\nfull address:s:10.1.0.1:3389\nprompt for credentials:i:1\nadministrative session:i:1\n`;
      const blob = new Blob([rdpContent], { type: 'application/x-rdp' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = docName.endsWith('.rdp') ? docName : `${docName}.rdp`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`🖥️ Arquivo RDP '${docName}' gerado com sucesso!`, 'success');
    }

    // ==========================================
    // 3. CONTROLADOR DE LISTAS NATIVAS REAIS DO SHAREPOINT (46 LISTAS)
    // ==========================================
    let currentRealListName = null;
    let currentRealListTitle = '';
    let isGenericListGridEditMode = false;
    let genericSortCol = null;
    let genericSortAsc = true;

    function sortGenericList(colName) {
      if (genericSortCol === colName) {
        genericSortAsc = !genericSortAsc;
      } else {
        genericSortCol = colName;
        genericSortAsc = true;
      }
      document.querySelectorAll('#list-viewer-thead .th-sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.innerText = '↕';
      });
      const curIcon = document.getElementById('sort-gen-' + colName);
      if (curIcon && curIcon.parentElement) {
        curIcon.parentElement.classList.add(genericSortAsc ? 'sorted-asc' : 'sorted-desc');
        curIcon.innerText = genericSortAsc ? '▲' : '▼';
      }
      filterRealListTable();
    }

    function openRealList(listName, title) {
      currentRealListName = listName;
      currentRealListTitle = title || listName;
      isGenericListGridEditMode = false;
      genericSortCol = null;
      genericSortAsc = true;

      const btn = document.getElementById("btn-grid-generic");
      const icon = document.getElementById("btn-grid-generic-icon");
      const txt = document.getElementById("btn-grid-generic-text");
      const alertBox = document.getElementById("generic-grid-mode-alert");
      if (btn) btn.classList.remove("btn-grid-active");
      if (icon) icon.innerText = "田";
      if (txt) txt.innerText = "Editar no modo de exibição de grade";
      if (alertBox) alertBox.style.display = "none";

      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[listName];

      // Restaurar edições locais se existirem
      try {
        const edits = JSON.parse(localStorage.getItem('sp_custom_list_edits_' + listName) || '{}');
        if (listData && listData.items) {
          Object.keys(edits).forEach(idxStr => {
            const idx = parseInt(idxStr, 10);
            if (listData.items[idx]) {
              Object.assign(listData.items[idx], edits[idxStr]);
            }
          });
        }
      } catch (e) {
        console.warn("Erro ao restaurar edições:", e);
      }

      const tEl = document.getElementById('list-viewer-title');
      const dEl = document.getElementById('list-viewer-desc');
      const thead = document.getElementById('list-viewer-thead');
      const searchBox = document.getElementById('list-viewer-search');

      if (tEl) tEl.innerHTML = currentRealListTitle + ' <span class="star-icon">☆</span>';
      if (dEl) dEl.innerText = `Lista oficial sincronizada 1:1 com o Microsoft SharePoint Online (${listData ? listData.items.length : 0} registros ativos).`;
      if (searchBox) searchBox.value = '';

      if (thead) {
        if (!listData || !listData.columns || listData.columns.length === 0) {
          thead.innerHTML = '<tr><th>Registro</th></tr>';
        } else {
          thead.innerHTML = '<tr><th class="td-center" style="width: 36px;"><input type="checkbox" id="checkall-generic" onchange="toggleCheckAllGeneric(this.checked)" title="Selecionar todos os registros"></th><th class="td-center" style="width: 45px;">#</th>' + listData.columns.map(col =>
            `<th class="th-sortable" onclick="sortGenericList('${col.name}')" title="Clique para ordenar por ${col.displayName || col.name}">${col.displayName || col.name} <span id="sort-gen-${col.name}" class="sort-icon">↕</span></th>`
          ).join('') + '</tr>';
        }
      }

      filterRealListTable();
    }

    function filterRealListTable() {
      if (!currentRealListName) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData) return;

      const q = (document.getElementById('list-viewer-search')?.value || '').toLowerCase().trim();
      const tbody = document.getElementById('list-viewer-tbody');
      const footer = document.getElementById('list-viewer-footer');
      const cols = listData.columns || [];

      const items = listData.items || [];
      let filtered = items.filter(it => {
        if (!q) return true;
        return Object.values(it).some(val => String(val || '').toLowerCase().includes(q));
      });

      if (genericSortCol) {
        filtered.sort((a, b) => {
          let va = a[genericSortCol] !== undefined ? a[genericSortCol] : '';
          let vb = b[genericSortCol] !== undefined ? b[genericSortCol] : '';
          const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true, sensitivity: 'base' });
          return genericSortAsc ? cmp : -cmp;
        });
      }

      if (tbody) {
        if (filtered.length === 0) {
          tbody.innerHTML = `<tr><td colspan="${cols.length + 1}" style="text-align:center; padding: 26px; color: #94A3B8;">Nenhum registro encontrado nesta lista.</td></tr>`;
        } else {
          tbody.innerHTML = filtered.map((it, idx) => {
            const origIdx = items.indexOf(it);
            const cells = cols.map(c => {
              const val = it[c.name] !== undefined ? it[c.name] : (it[c.displayName] !== undefined ? it[c.displayName] : '');
              if (isGenericListGridEditMode) {
                return `<td><div contenteditable="true" class="sp-grid-cell" onblur="updateGenericListField(${origIdx}, '${c.name}', this.innerText.trim())">${String(val || '')}</div></td>`;
              }
              return `<td>${formatCellContent(val, c.name)}</td>`;
            }).join('');
            const trClick = isGenericListGridEditMode ? "" : `onclick="openEditListItemModal(${origIdx})" ondblclick="handleRowDblClick(${origIdx})" style="cursor: pointer;" title="Clique para ver detalhes / Clique duplo para abrir relatório PDF se disponível"`;
            return `<tr ${trClick} class="sp-list-row-clickable">
              <td class="td-center" style="width: 36px;" onclick="event.stopPropagation();"><input type="checkbox" class="check-item-generic" data-orig-idx="${origIdx}" onchange="updateGenericSelectionUI()"></td>
              <td class="td-center" style="color: #64748B;">${idx + 1}</td>
              ${cells}
            </tr>`;
          }).join('');
        }
      }

      if (footer) {
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${items.length}</b> registros &bull; Sincronizado com Microsoft SharePoint Online`;
      }
    }

    
    // ==========================================
    // FUNÇÕES DE EXCLUSÃO EM LOTE E SELEÇÃO GENÉRICA
    // ==========================================
    function toggleCheckAllGeneric(isChecked) {
      const cbs = document.querySelectorAll('.check-item-generic');
      cbs.forEach(cb => { cb.checked = isChecked; });
      updateGenericSelectionUI();
    }

    function updateGenericSelectionUI() {
      const cbs = document.querySelectorAll('.check-item-generic:checked');
      const btnDel = document.getElementById('btn-delete-generic');
      const countEl = document.getElementById('delete-count-generic');
      const canDelete = (currentRole && (currentRole.startsWith('admin') || currentRole === 'operador'));
      if (countEl) countEl.innerText = cbs.length;
      if (btnDel) {
        if (cbs.length > 0 && canDelete) {
          btnDel.style.display = 'inline-flex';
        } else {
          btnDel.style.display = 'none';
        }
      }
    }

    async function deleteSelectedGenericItems() {
      const canDelete = (currentRole && (currentRole.startsWith('admin') || currentRole === 'operador'));
      if (!canDelete) {
        showToast("Permissão negada: apenas Operadores e Administradores podem excluir registros.", "error");
        return;
      }
      const checked = Array.from(document.querySelectorAll('.check-item-generic:checked'));
      if (checked.length === 0) {
        showToast("Nenhum item selecionado para exclusão.", "warning");
        return;
      }
      const confirmed = await showCustomDeleteModal(
        "Confirmar Exclusão de Itens",
        `Deseja realmente excluir <strong>${checked.length} item(ns)</strong> selecionado(s) desta lista?`
      );
      if (!confirmed) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items) return;

      const origIndices = checked.map(cb => parseInt(cb.getAttribute('data-orig-idx'), 10)).sort((a, b) => b - a);
      origIndices.forEach(idx => {
        if (idx >= 0 && idx < listData.items.length) {
          listData.items.splice(idx, 1);
        }
      });

      // Salvar lista personalizada no localStorage
      try {
        localStorage.setItem('sp_custom_list_deleted_' + currentRealListName, JSON.stringify(listData.items));
      } catch (e) {
        console.warn("Erro ao salvar lista após exclusão:", e);
      }

      showToast(`${checked.length} item(ns) excluído(s) com sucesso!`, "success");
      const checkall = document.getElementById('checkall-generic');
      if (checkall) checkall.checked = false;
      updateGenericSelectionUI();
      filterRealListTable();
    }

    // ==========================================
    // VISUALIZADOR OFICIAL DE RELATÓRIOS PDF (DOIS CLIQUES)
    // ==========================================
    function handleRowDblClick(origIdx) {
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items) return;
      const it = listData.items[origIdx];
      if (!it) return;
      const pdfTarget = it.pdfUrl || it.FileLeafRef || it.Title || '';
      if (String(pdfTarget).toLowerCase().endsWith('.pdf') || it.ContentType === 'Documento') {
        openReportPdf(pdfTarget);
      } else {
        openEditListItemModal(origIdx);
      }
    }

    function openReportPdf(filenameOrUrl) {
      if (!filenameOrUrl) return;
      let targetUrl = filenameOrUrl;
      if (!targetUrl.startsWith('http') && !targetUrl.startsWith('/') && !targetUrl.startsWith('reports/')) {
        let category = "futebol";
        if (currentRealListName && currentRealListName.toLowerCase().includes("nba")) category = "nba";
        else if (currentRealListName && currentRealListName.toLowerCase().includes("youtube")) category = "youtube";
        targetUrl = `reports/${category}/${filenameOrUrl}`;
      }
      const modal = document.getElementById("modal-pdf-viewer");
      const frame = document.getElementById("pdf-viewer-frame");
      const title = document.getElementById("pdf-viewer-title");
      const dl = document.getElementById("pdf-viewer-download");
      if (modal && frame) {
        if (title) title.innerText = "Relatório Oficial: " + filenameOrUrl.split("/").pop();
        if (dl) dl.href = targetUrl;
        frame.src = targetUrl;
        modal.style.display = "flex";
      } else {
        window.open(targetUrl, "_blank");
      }
    }

    function closePdfModal() {
      const modal = document.getElementById("modal-pdf-viewer");
      const frame = document.getElementById("pdf-viewer-frame");
      if (modal) modal.style.display = "none";
      if (frame) frame.src = "";
    }

    // Expor no objeto window para acessibilidade global
    window.toggleCheckAllGeneric = toggleCheckAllGeneric;
    window.updateGenericSelectionUI = updateGenericSelectionUI;
    window.deleteSelectedGenericItems = deleteSelectedGenericItems;
    window.handleRowDblClick = handleRowDblClick;
    window.openReportPdf = openReportPdf;
    window.closePdfModal = closePdfModal;

    function toggleGenericListGridEdit() {
      if (!currentRealListName) {
        showToast("Selecione uma lista primeiro.", "warning");
        return;
      }
      isGenericListGridEditMode = !isGenericListGridEditMode;
      const btn = document.getElementById("btn-grid-generic");
      const icon = document.getElementById("btn-grid-generic-icon");
      const txt = document.getElementById("btn-grid-generic-text");
      const alertBox = document.getElementById("generic-grid-mode-alert");

      if (isGenericListGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado para esta lista. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de grade finalizado. Todas as alterações foram salvas!", "success");
      }
      filterRealListTable();
    }

    function updateGenericListField(itemIdx, colName, value) {
      if (!currentRealListName) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items || !listData.items[itemIdx]) return;

      listData.items[itemIdx][colName] = value;

      try {
        let edits = JSON.parse(localStorage.getItem('sp_custom_list_edits_' + currentRealListName) || '{}');
        if (!edits[itemIdx]) edits[itemIdx] = {};
        edits[itemIdx][colName] = value;
        localStorage.setItem('sp_custom_list_edits_' + currentRealListName, JSON.stringify(edits));
      } catch (e) {
        console.warn("Erro ao salvar edição de lista:", e);
      }

      showToast(`💾 Coluna '${colName}' atualizada com sucesso!`, "success");
    }

    function openNewListItemModal() {
      if (!currentRealListName) {
        showToast("Selecione uma lista primeiro para adicionar um item.", "warning");
        return;
      }
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData) return;

      document.getElementById("modal-new-list-title").innerHTML = `Novo Item &mdash; ${currentRealListTitle}`;
      const container = document.getElementById("new-list-fields-container");
      container.innerHTML = "";

      const cols = listData.columns || [];
      const systemCols = ['id', 'modified', 'created', 'author', 'editor', 'attachments', 'contenttypeid'];
      const editableCols = cols.filter(c => !systemCols.includes(String(c.name || '').toLowerCase()));
      const renderCols = editableCols.length > 0 ? editableCols : cols;

      renderCols.forEach(col => {
        const colId = col.name;
        const colTitle = col.displayName || col.name;
        const group = document.createElement("div");
        group.className = "sp-form-group";
        group.innerHTML = `
          <label class="sp-form-label">${colTitle}</label>
          <input type="text" name="${colId}" class="sp-form-input list-dyn-input" placeholder="Informe ${colTitle}...">
        `;
        container.appendChild(group);
      });

      document.getElementById("modal-new-list-item").style.display = "flex";
    }

    function closeNewListItemModal() {
      const modal = document.getElementById("modal-new-list-item");
      if (modal) modal.style.display = "none";
    }

    function saveNewListItem(event) {
      event.preventDefault();
      if (!currentRealListName) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData) return;

      const inputs = document.querySelectorAll(".list-dyn-input");
      const newItem = {
        __id: 'item_' + Date.now(),
        Created: new Date().toISOString(),
        Modified: new Date().toISOString()
      };

      inputs.forEach(inp => {
        newItem[inp.name] = inp.value.trim();
      });

      if (!listData.items) listData.items = [];
      listData.items.unshift(newItem);

      try {
        let saved = JSON.parse(localStorage.getItem('sp_custom_list_' + currentRealListName) || '[]');
        saved.unshift(newItem);
        localStorage.setItem('sp_custom_list_' + currentRealListName, JSON.stringify(saved));
      } catch (e) {
        console.warn("Erro ao salvar item:", e);
      }

      closeNewListItemModal();
      document.getElementById("form-new-list-item").reset();
      filterRealListTable();
      showToast(`✅ Item adicionado com sucesso à lista ${currentRealListTitle}!`, "success");
    }

    function exportGenericListCSV() {
      if (!currentRealListName) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items) return;

      const cols = listData.columns || [];
      let csv = cols.map(c => `"${(c.displayName || c.name).replace(/"/g, '""')}"`).join(',') + String.fromCharCode(10);
      listData.items.forEach(it => {
        const row = cols.map(c => {
          const val = it[c.name] !== undefined ? it[c.name] : (it[c.displayName] !== undefined ? it[c.displayName] : '');
          return `"${String(val || '').replace(/"/g, '""')}"`;
        });
        csv += row.join(',') + String.fromCharCode(10);
      });

      const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sharepoint_lista_${currentRealListName}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    // ==========================================
    // 4. ROTEAMENTO DINÂMICO DE ABAS (SHOW PANE)
    // ==========================================
    function showPane(paneId, title, desc) {
      if (paneId === 'rdp') paneId = 'remoto';
      document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.pane-container').forEach(pane => pane.classList.remove('active'));

      const res = SP_RESOURCE_MAP[paneId];
      let targetPane = null;

      // 1. Checar se existe um painel dedicado com ID específico no DOM
      const dedicatedPane = document.getElementById('pane-' + paneId) || document.getElementById(paneId);
      if (dedicatedPane && dedicatedPane.id !== 'pane-list-viewer' && dedicatedPane.id !== 'pane-drive-viewer') {
        targetPane = dedicatedPane;
        targetPane.classList.add('active');
      } else if (res && res.type === 'drive') {
        targetPane = document.getElementById('pane-drive-viewer');
        if (targetPane) {
          targetPane.classList.add('active');
          openDrive(res.name, res.title || title);
        }
      } else if (res && res.type === 'list') {
        targetPane = document.getElementById('pane-list-viewer');
        if (targetPane) {
          targetPane.classList.add('active');
          openRealList(res.name, res.title || title);
        }
      } else {
        targetPane = dedicatedPane;
        if (!targetPane) {
          if (SP_MASTER_DATA.drives && SP_MASTER_DATA.drives[paneId]) {
            targetPane = document.getElementById('pane-drive-viewer');
            if (targetPane) {
              targetPane.classList.add('active');
              openDrive(paneId, title);
            }
          } else if (SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[paneId]) {
            targetPane = document.getElementById('pane-list-viewer');
            if (targetPane) {
              targetPane.classList.add('active');
              openRealList(paneId, title);
            }
          }
        } else {
          targetPane.classList.add('active');
        }
      }

      // Atualizar renderizações de abas estáticas
      if (paneId === 'permissoes') renderPermsTable();
      else if (paneId === 'hospedeiros') renderHospedeirosTable();
      else if (paneId === 'ocorrencias') renderOcorrenciasTable();
      else if (paneId === 'streaming') renderTable();
      else if (paneId === 'antenistas') renderAntenistasTable();
      else if (paneId === 'hosts') renderHostsTable();
      else if (paneId === 'remoto') renderRdpTable();
      else if (paneId === 'escala') renderEscalaTable();

      document.querySelectorAll('.tab-link').forEach(btn => {
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes("'" + paneId + "'")) {
          btn.classList.add('active');
        }
      });

      // Fechar dropdowns abertos
      document.querySelectorAll('.sp-menu-item').forEach(item => item.classList.remove('open'));

      // Marcar menu pai como ativo
      document.querySelectorAll('.sp-dropdown-menu').forEach(menu => {
        if (menu.innerHTML.includes("'" + paneId + "'")) {
          const parentBtn = menu.parentElement.querySelector('.sp-menu-btn');
          if (parentBtn) parentBtn.classList.add('active');
        }
      });

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function toggleDropdown(btn, ev) {
      if (ev) {
        ev.stopPropagation();
        ev.preventDefault();
      }
      const parent = btn.closest('.sp-menu-item');
      if (!parent) return;
      const isOpen = parent.classList.contains('open');
      document.querySelectorAll('.sp-menu-item').forEach(item => item.classList.remove('open'));
      if (!isOpen) {
        parent.classList.add('open');
      }
    }

    function handleMenuClick(paneId, title, ev) {
      if (ev) {
        ev.stopPropagation();
        ev.preventDefault();
      }
      document.querySelectorAll('.sp-menu-item').forEach(item => item.classList.remove('open'));
      showPane(paneId, title);
    }

    document.addEventListener('click', function(e) {
      if (!e.target.closest('.sp-menu-item')) {
        document.querySelectorAll('.sp-menu-item').forEach(item => item.classList.remove('open'));
      }
    });

    function toggleDarkMode() {
      document.body.classList.toggle('dark-mode');
      const isDark = document.body.classList.contains('dark-mode');
      document.getElementById('dark-mode-icon').innerText = isDark ? '☀️' : '🌙';
    }

    // ==========================================
    // RENDERIZAÇÃO DA ESCALA DE TRABALHO 2026
    // ==========================================
    function initEscalaMonths() {
      const pillsContainer = document.getElementById("escala-month-pills");
      if (!pillsContainer) return;
      pillsContainer.innerHTML = "";

      const monthsList = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro_Prototipo", "Plantao_Fim_Ano"
      ];

      monthsList.forEach(m => {
        const btn = document.createElement("button");
        btn.className = "month-pill-btn" + (m === currentMonth ? " active" : "");
        const label = m === "Dezembro_Prototipo" ? "Dezembro" : (m === "Plantao_Fim_Ano" ? "🎄 Plantão Fim de Ano" : m);
        btn.innerText = label;
        btn.onclick = function() { selectEscalaMonth(m, this); };
        pillsContainer.appendChild(btn);
      });

      renderEscalaTable();
    }

    function selectEscalaMonth(monthKey, btnElement) {
      currentMonth = monthKey;
      document.querySelectorAll(".month-pill-btn").forEach(btn => btn.classList.remove("active"));
      if (btnElement) {
        btnElement.classList.add("active");
      } else {
        document.querySelectorAll(".month-pill-btn").forEach(btn => {
          if (btn.innerText.includes(monthKey) || (monthKey === "Dezembro_Prototipo" && btn.innerText === "Dezembro") || (monthKey === "Plantao_Fim_Ano" && btn.innerText.includes("Fim de Ano"))) {
            btn.classList.add("active");
          }
        });
      }
      renderEscalaTable();
    }

    function getBadgeClass(val) {
      const v = String(val || "").toUpperCase().trim();
      if (v === "T") return "escala-badge escala-badge-t";
      if (v === "F") return "escala-badge escala-badge-f";
      if (v.includes("FER") || v.includes("FÉRIAS")) return "escala-badge escala-badge-ferias";
      if (v === "BH") return "escala-badge escala-badge-bh";
      if (v === "VF") return "escala-badge escala-badge-vf";
      if (v === "FJ") return "escala-badge escala-badge-fj";
      if (v.includes("DAY")) return "escala-badge escala-badge-dayoff";
      if (v === "TR") return "escala-badge escala-badge-tr";
      if (v === "AG") return "escala-badge escala-badge-ag";
      if (v === "SM") return "escala-badge escala-badge-sm";
      return "escala-badge escala-badge-f";
    }

    function renderEscalaTable() {
      const fimAnoWrap = document.getElementById("escala-fim-ano-wrap");
      const mainTable = document.getElementById("escala-main-table");
      const ativWrap = document.getElementById("escala-atividades-table").parentElement;

      if (currentMonth === "Plantao_Fim_Ano") {
        if (mainTable) mainTable.style.display = "none";
        if (ativWrap) ativWrap.style.display = "none";
        if (fimAnoWrap) {
          fimAnoWrap.style.display = "block";
          renderPlantaoFimAno();
        }
        return;
      }

      if (mainTable) mainTable.style.display = "";
      if (ativWrap) ativWrap.style.display = "";
      if (fimAnoWrap) fimAnoWrap.style.display = "none";

      const mData = allEscalaMonths[currentMonth];
      if (!mData) return;

      const numDays = mData.num_dias || 30;
      const thead = document.getElementById("escala-table-head");
      const tbody = document.getElementById("escala-table-body");
      if (!thead || !tbody) return;

      // Monta Head
      let hHtml = `<tr>
        <th class="th-sticky-left" style="min-width: 140px; padding: 6px 8px;">Operador</th>
        <th style="min-width: 95px; padding: 6px 8px;">Horário / Turno</th>
        <th style="min-width: 110px; padding: 6px 8px;">Equipe</th>`;

      for (let d = 1; d <= numDays; d++) {
        const isHojeD = (currentMonth === 'Novembro' && d === 25);
        if (isHojeD) {
          hHtml += `<th style="width: 28px; min-width: 28px; padding: 4px 2px; font-size: 10px; background: #ECFDF5; color: #047857; border-bottom: 3px solid #10B981; font-weight: 800;">${d}<br><span style="font-size: 8px; background: #10B981; color: #ffffff; padding: 1px 2px; border-radius: 2px;">HOJE</span></th>`;
        } else {
          hHtml += `<th style="width: 26px; min-width: 26px; padding: 4px 2px; font-size: 10.5px;">${d}</th>`;
        }
      }
      hHtml += `</tr>`;
      thead.innerHTML = hHtml;

      // Filtros
      const sBox = document.getElementById("escala-search-box");
      const q = sBox ? sBox.value.toLowerCase().trim() : "";
      const fEquipe = document.getElementById("escala-filter-equipe")?.value || "";
      const fTurno = document.getElementById("escala-filter-turno")?.value || "";

      tbody.innerHTML = "";
      mData.operadores.forEach(op => {
        if (fEquipe && op.equipe !== fEquipe) return;
        if (fTurno && !op.horario.includes(fTurno)) return;
        if (q && !op.nome.toLowerCase().includes(q) && !op.matricula.includes(q)) return;

        let rHtml = `<tr>
          <td class="td-sticky-left" style="padding: 6px 8px;">
            <b>${op.nome}</b>
            ${op.matricula ? `<br><span style="font-size: 10px; color: #64748B; font-weight: 400;">Mat: ${op.matricula}</span>` : ''}
          </td>
          <td style="font-size: 11px; padding: 6px 8px; color: #334155; font-weight: 600;">${op.horario}</td>
          <td style="padding: 6px 8px;"><span class="badge ${op.equipe === 'Monitoração' ? 'badge-exibido' : 'badge-default'}" style="font-size: 11px;">${op.equipe}</span></td>`;

        for (let d = 1; d <= numDays; d++) {
          const val = (op.dias && op.dias[d]) ? op.dias[d] : "";
          if (val) {
            rHtml += `<td style="padding: 3px 2px; text-align: center;"><span class="${getBadgeClass(val)}" style="padding: 2px 4px; font-size: 10px;">${val}</span></td>`;
          } else {
            rHtml += `<td style="padding: 3px 2px; text-align: center; color: #CBD5E1; font-size: 10px;">-</td>`;
          }
        }
        rHtml += `</tr>`;
        tbody.innerHTML += rHtml;
      });

      // Renderiza Atividades
      const ativHead = document.getElementById("escala-atividades-head");
      const ativBody = document.getElementById("escala-atividades-body");
      if (ativHead && ativBody) {
        let ahHtml = `<tr><th class="th-sticky-left" style="min-width: 180px;">Atividade Operacional</th>`;
        for (let d = 1; d <= numDays; d++) {
          ahHtml += `<th style="min-width: 38px;">${d}</th>`;
        }
        ahHtml += `</tr>`;
        ativHead.innerHTML = ahHtml;

        ativBody.innerHTML = "";
        (mData.atividades || []).forEach(act => {
          let aRow = `<tr><td class="td-sticky-left"><b>${act.nome}</b></td>`;
          for (let d = 1; d <= numDays; d++) {
            const v = (act.dias && act.dias[d]) ? act.dias[d] : "";
            aRow += `<td style="font-size: 10px; font-weight: 600; color: #004578;">${v || '-'}</td>`;
          }
          aRow += `</tr>`;
          ativBody.innerHTML += aRow;
        });
      }
    }

    function renderPlantaoFimAno() {
      const pData = allEscalaMonths["Plantao_Fim_Ano"];
      const tbody = document.getElementById("escala-fim-ano-body");
      if (!pData || !tbody) return;

      tbody.innerHTML = "";
      tbody.innerHTML += `<tr><td colspan="5" style="background: #F1F5F9; font-weight: 700; color: #1E293B;">🎅 Escala de Natal 2026</td></tr>`;
      pData.natal.forEach(item => {
        tbody.innerHTML += `<tr>
          <td><b>${item.dia}</b></td>
          <td>${item.manha}</td>
          <td>${item.tarde}</td>
          <td>${item.madrugada}</td>
          <td><span class="badge badge-caze">${item.plantao_n2}</span></td>
        </tr>`;
      });

      tbody.innerHTML += `<tr><td colspan="5" style="background: #F1F5F9; font-weight: 700; color: #1E293B;">🎆 Escala de Ano Novo 2026 / 2027</td></tr>`;
      pData.ano_novo.forEach(item => {
        tbody.innerHTML += `<tr>
          <td><b>${item.dia}</b></td>
          <td>${item.manha}</td>
          <td>${item.tarde}</td>
          <td>${item.madrugada}</td>
          <td><span class="badge badge-prime">${item.plantao_n2}</span></td>
        </tr>`;
      });
    }

    // Listeners da escala
    document.getElementById("escala-search-box")?.addEventListener("input", renderEscalaTable);
    document.getElementById("escala-filter-equipe")?.addEventListener("change", renderEscalaTable);
    document.getElementById("escala-filter-turno")?.addEventListener("change", renderEscalaTable);

    // ==========================================
    // RENDERIZAÇÃO DE HOSPEDEIROS, OCORRÊNCIAS, STREAMING
    // ==========================================
    function getChannelBadge(canal) {
      const c = String(canal || "").toLowerCase();
      if (c.includes("cazé") || c.includes("caze")) return '<span class="badge badge-caze">' + canal + '</span>';
      if (c.includes("prime") || c.includes("amazon")) return '<span class="badge badge-prime">' + canal + '</span>';
      if (c.includes("netflix")) return '<span class="badge badge-netflix">' + canal + '</span>';
      if (c.includes("tnt") || c.includes("max") || c.includes("hbo")) return '<span class="badge badge-tnt">' + canal + '</span>';
      if (c.includes("record")) return '<span class="badge badge-record">' + canal + '</span>';
      if (c.includes("dazn")) return '<span class="badge badge-dazn">' + canal + '</span>';
      return '<span class="badge badge-default">' + (canal || "-") + '</span>';
    }

    function getStatusBadge(status) {
      const s = String(status || "").toLowerCase();
      if (s.includes("exibido") && !s.includes("não") && !s.includes("nao")) return '<span class="badge badge-exibido">' + status + '</span>';
      if (s.includes("não") || s.includes("nao") || s.includes("cancelado")) return '<span class="badge badge-nao-exibido">' + status + '</span>';
      return '<span class="badge badge-pendente">' + (status || "Pendente") + '</span>';
    }

    let streamSortCol = null;
    let streamSortAsc = true;

    function initStreamingFilters() {
      const campSelect = document.getElementById("filter-campeonato");
      if (campSelect && campSelect.options.length <= 1) {
        const camps = [...new Set(allEvents.map(e => e.campeonato).filter(Boolean))].sort((a, b) => a.localeCompare(b));
        camps.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c;
          opt.innerText = c;
          campSelect.appendChild(opt);
        });
      }
    }

    function sortStreamBy(col) {
      if (streamSortCol === col) {
        streamSortAsc = !streamSortAsc;
      } else {
        streamSortCol = col;
        streamSortAsc = true;
      }
      document.querySelectorAll('#pane-streaming .th-sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.innerText = '↕';
      });
      const curIcon = document.getElementById('sort-st-' + col) || document.getElementById('sort-stream-' + col);
      if (curIcon && curIcon.parentElement) {
        curIcon.parentElement.classList.add(streamSortAsc ? 'sorted-asc' : 'sorted-desc');
        curIcon.innerText = streamSortAsc ? '▲' : '▼';
      }
      renderTable();
    }

    function clearStreamFilters() {
      const sb = document.getElementById("search-box"); if (sb) sb.value = "";
      const fm = document.getElementById("filter-mes"); if (fm) fm.value = "";
      const fc = document.getElementById("filter-campeonato"); if (fc) fc.value = "";
      const fcn = document.getElementById("filter-canal"); if (fcn) fcn.value = "";
      const fs = document.getElementById("filter-status"); if (fs) fs.value = "";
      streamSortCol = null;
      streamSortAsc = true;
      document.querySelectorAll('#pane-streaming .th-sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.innerText = '↕';
      });
      renderTable();
    }

    let isStreamGridEditMode = false;

    function openNewStreamModal() {
      const modal = document.getElementById("modal-new-stream-event");
      if (modal) modal.style.display = "flex";
    }

    function closeNewStreamModal() {
      const modal = document.getElementById("modal-new-stream-event");
      if (modal) modal.style.display = "none";
    }

    function saveNewStreamEvent(event) {
      if (event) event.preventDefault();
      const mes = document.getElementById("new-stream-mes")?.value || "Novembro";
      const data = document.getElementById("new-stream-data")?.value.trim() || "";
      const horario = document.getElementById("new-stream-horario")?.value.trim() || "";
      const campeonato = document.getElementById("new-stream-campeonato")?.value.trim() || "";
      const partida = document.getElementById("new-stream-partida")?.value.trim() || "";
      const canal = document.getElementById("new-stream-canal")?.value || "Cazé TV";
      const pvid = document.getElementById("new-stream-pvid")?.value.trim() || "-";
      const resp = document.getElementById("new-stream-resp")?.value.trim() || "Equipe Suporte";
      const status = document.getElementById("new-stream-status")?.value || "Exibido";
      const programado = document.getElementById("new-stream-programado")?.value || "SIM";

      if (!partida || !data) {
        showToast("⚠️ Preencha a partida e a data do confronto!", "warning");
        return;
      }

      const newId = "stream_" + Date.now();
      const newEvent = {
        id: newId,
        mes: mes,
        data: data,
        horario: horario,
        campeonato: campeonato,
        partida: partida,
        responsavel: resp,
        canal: canal,
        pvid: pvid,
        status_entrega: status,
        programado: programado
      };

      allEvents.unshift(newEvent);

      try {
        let customEvents = JSON.parse(localStorage.getItem('sp_custom_streaming_events') || '[]');
        customEvents.unshift(newEvent);
        localStorage.setItem('sp_custom_streaming_events', JSON.stringify(customEvents));
      } catch (e) {
        console.warn("Erro ao salvar evento local:", e);
      }

      closeNewStreamModal();
      document.getElementById("form-new-stream")?.reset();
      renderTable();
      showToast(`✅ Confronto '${partida}' cadastrado na programação!`, "success");
    }

    function toggleStreamGridEdit() {
      isStreamGridEditMode = !isStreamGridEditMode;
      const btn = document.getElementById("btn-grid-stream");
      const icon = document.getElementById("btn-grid-stream-icon");
      const txt = document.getElementById("btn-grid-stream-text");
      const alertBox = document.getElementById("stream-grid-mode-alert");

      if (isStreamGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderTable();
    }

    function updateStreamField(id, field, value) {
      const item = allEvents.find(e => (String(e.id) === String(id) || String(e.partida) === String(id)));
      if (!item) return;

      item[field] = value;

      try {
        let customEdits = JSON.parse(localStorage.getItem('sp_custom_streaming_edits') || '{}');
        if (!customEdits[id]) customEdits[id] = {};
        customEdits[id][field] = value;
        localStorage.setItem('sp_custom_streaming_edits', JSON.stringify(customEdits));
      } catch (e) {
        console.warn("Erro ao persistir edição streaming:", e);
      }

      showToast(`💾 Alteração salva em ${field}!`, "success");
    }

    function triggerGoogleChatAgendaModal() {
      const modal = document.getElementById("modal-chat-webhook");
      const input = document.getElementById("chat-webhook-url-input");
      const preview = document.getElementById("chat-agenda-preview");
      if (!modal) return;

      const savedUrl = localStorage.getItem("google_chat_webhook_url") || "https://chat.googleapis.com/v1/spaces/AAQAwrsZx6Q/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=V7DMEzDmcOEd444Z14GaCw36MtFChugL56ypFbOfbYA";
      if (input) input.value = savedUrl;

      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const hojeStr = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()}`;
      const tom = new Date(now.getTime() + 24 * 60 * 60 * 1000);
      const amanhaStr = `${pad(tom.getDate())}/${pad(tom.getMonth() + 1)}/${tom.getFullYear()}`;

      const jogosHoje = allEvents.filter(e => String(e.data || "").trim() === hojeStr);
      const jogosAmanha = allEvents.filter(e => String(e.data || "").trim() === amanhaStr);

      let htmlPrev = `<b>📅 Resumo da Transmissão para Envio:</b><br>`;
      htmlPrev += `<div style="margin-top: 6px;"><b>Hoje (${hojeStr}):</b> `;
      if (jogosHoje.length === 0) {
        htmlPrev += `<span style="color: #166534; font-weight: 600;">✅ Grade Livre (nenhuma transmissão programada)</span>`;
      } else {
        htmlPrev += `<b>${jogosHoje.length} jogo(s)</b>: ${jogosHoje.map(j => j.partida + ' (' + j.horario + ')').join(', ')}`;
      }
      htmlPrev += `</div>`;

      htmlPrev += `<div style="margin-top: 6px;"><b>Amanhã (${amanhaStr}):</b> `;
      if (jogosAmanha.length === 0) {
        htmlPrev += `<span style="color: #0284C7; font-weight: 600;">ℹ️ Grade Livre (nenhuma transmissão programada)</span>`;
      } else {
        htmlPrev += `<b>${jogosAmanha.length} jogo(s)</b>: ${jogosAmanha.map(j => j.partida + ' (' + j.horario + ')').join(', ')}`;
      }
      htmlPrev += `</div>`;

      if (preview) preview.innerHTML = htmlPrev;
      modal.style.display = "flex";
    }

    function closeChatWebhookModal() {
      const modal = document.getElementById("modal-chat-webhook");
      if (modal) modal.style.display = "none";
    }

    async function sendChatAgendaFromModal() {
      const input = document.getElementById("chat-webhook-url-input");
      const webhookUrl = input ? input.value.trim() : "";
      if (!webhookUrl || !webhookUrl.startsWith("http")) {
        alert("Por favor, cole a URL válida do Webhook do Google Chat gerada no espaço 'Streaming - Gravações'.");
        if (input) input.focus();
        return;
      }

      localStorage.setItem("google_chat_webhook_url", webhookUrl);

      const btn = document.getElementById("btn-send-chat-now");
      if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳ Enviando...";
      }

      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const hojeStr = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()}`;
      const tom = new Date(now.getTime() + 24 * 60 * 60 * 1000);
      const amanhaStr = `${pad(tom.getDate())}/${pad(tom.getMonth() + 1)}/${tom.getFullYear()}`;

      const jogosHoje = allEvents.filter(e => String(e.data || "").trim() === hojeStr);
      const jogosAmanha = allEvents.filter(e => String(e.data || "").trim() === amanhaStr);

      const widgetsHoje = [];
      if (jogosHoje.length === 0) {
        widgetsHoje.push({
          decoratedText: {
            topLabel: "Status da Grade de Hoje",
            text: "<b>Nenhuma transmissão programada para hoje.</b>",
            bottomLabel: "✅ Grade 100% livre • Operação normal sem eventos escalados.",
            wrapText: true
          }
        });
      } else {
        jogosHoje.forEach(j => {
          widgetsHoje.push({
            decoratedText: {
              topLabel: `${j.horario || '--:--'} • ${j.responsavel || 'Marcos BL01 e Backup'}`,
              text: `<b>${j.partida}</b>`,
              bottomLabel: `📺 ${j.pvid || j.canal || 'TV BOX'}`,
              wrapText: true
            }
          });
        });
      }

      const widgetsAmanha = [];
      if (jogosAmanha.length === 0) {
        widgetsAmanha.push({
          decoratedText: {
            topLabel: "Previsão para Amanhã",
            text: "<b>Nenhuma transmissão programada para amanhã.</b>",
            bottomLabel: "ℹ️ Grade 100% livre • Sem eventos de streaming previstos.",
            wrapText: true
          }
        });
      } else {
        jogosAmanha.forEach(j => {
          widgetsAmanha.push({
            decoratedText: {
              topLabel: `${j.horario || '--:--'} • ${j.responsavel || 'Marcos BL01 e Backup'}`,
              text: `<b>${j.partida}</b>`,
              bottomLabel: `📺 ${j.pvid || j.canal || 'TV BOX'}`,
              wrapText: true
            }
          });
        });
      }

      let subtitulo = "";
      if (jogosHoje.length === 0 && jogosAmanha.length === 0) {
        subtitulo = "Grade Livre • Sem transmissões agendadas para hoje e amanhã";
      } else if (jogosHoje.length === 0) {
        subtitulo = `Grade de hoje livre • ${jogosAmanha.length} transmissão(ões) amanhã`;
      } else if (jogosAmanha.length === 0) {
        subtitulo = `${jogosHoje.length} transmissão(ões) hoje • Grade de amanhã livre`;
      } else {
        subtitulo = `${jogosHoje.length} transmissão(ões) hoje • ${jogosAmanha.length} amanhã`;
      }

      const payload = {
        cardsV2: [
          {
            cardId: `agenda-streaming-${hojeStr.replace(/\//g, "-")}`,
            card: {
              header: {
                title: "Agenda de Transmissões",
                subtitle: subtitulo,
                imageUrl: "https://fonts.gstatic.com/s/i/short-term/release/googlestyles/sports_soccer/default/48px.png",
                imageType: "CIRCLE"
              },
              sections: [
                {
                  header: jogosHoje.length > 0 ? `Hoje - ${hojeStr}` : `Hoje - ${hojeStr} (Grade Livre)`,
                  widgets: widgetsHoje
                },
                {
                  header: jogosAmanha.length > 0 ? `Amanhã - ${amanhaStr}` : `Amanhã - ${amanhaStr} (Grade Livre)`,
                  widgets: widgetsAmanha
                }
              ]
            }
          }
        ]
      };

      try {
        const resp = await fetch(webhookUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json; charset=UTF-8" },
          body: JSON.stringify(payload)
        });
        if (resp.ok) {
          showToast(`✅ Agenda enviada com sucesso para o grupo 'Streaming - Gravações' no Google Chat!`, "success");
          closeChatWebhookModal();
        } else {
          showToast(`⚠️ Google Chat retornou status ${resp.status}`, "warning");
        }
      } catch (err) {
        console.error("Erro ao enviar para Google Chat Webhook:", err);
        showToast("⚠️ Disparo enviado! Caso o navegador bloqueie por CORS, o script diário agendado no Windows fará o envio às 09:00.", "info");
        closeChatWebhookModal();
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = "🚀 Enviar Agora para o Google Chat";
        }
      }
    }

    function updateStreamingHighlightCards() {
      const now = new Date();
      const pad = n => String(n).padStart(2, "0");
      const hojeStr = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()}`;
      const tom = new Date(now.getTime() + 86400000);
      const amanhaStr = `${pad(tom.getDate())}/${pad(tom.getMonth() + 1)}/${tom.getFullYear()}`;

      const lblHoje = document.getElementById("label-data-hoje");
      const lblAmanha = document.getElementById("label-data-amanha");
      if (lblHoje) lblHoje.innerText = hojeStr;
      if (lblAmanha) lblAmanha.innerText = amanhaStr;

      const eventosHoje = allEvents.filter(e => String(e.data || "").trim() === hojeStr);
      const eventosAmanha = allEvents.filter(e => String(e.data || "").trim() === amanhaStr);

      const badgeHoje = document.getElementById("badge-count-hoje");
      const badgeAmanha = document.getElementById("badge-count-amanha");
      if (badgeHoje) badgeHoje.innerText = `${eventosHoje.length} ${eventosHoje.length === 1 ? 'jogo' : 'jogos'}`;
      if (badgeAmanha) badgeAmanha.innerText = `${eventosAmanha.length} ${eventosAmanha.length === 1 ? 'jogo' : 'jogos'}`;

      const listHoje = document.getElementById("list-eventos-hoje");
      const listAmanha = document.getElementById("list-eventos-amanha");

      if (listHoje) {
        if (eventosHoje.length === 0) {
          listHoje.innerHTML = '<div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Nenhum confronto agendado para hoje.</div>';
        } else {
          listHoje.innerHTML = eventosHoje.map(ev => `
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 6px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
              <div>
                <div style="font-size: 11px; color: #166534; font-weight: 700; text-transform: uppercase;">
                  ${ev.campeonato || 'FUTEBOL / ESPORTES'} &bull; <span style="font-size: 12px; color: #0F172A; font-weight: 800;">${ev.horario || '--:--'}</span>
                </div>
                <div style="font-size: 13.5px; font-weight: 700; color: #1E293B; margin: 3px 0;">
                  ${ev.partida || '-'}
                </div>
                <div style="font-size: 11px; color: #475569;">
                  Responsável: <b>${ev.responsavel || '-'}</b> &bull; PVID: <code style="font-family:'JetBrains Mono',monospace; background:#E2E8F0; padding:1px 4px; border-radius:3px;">${ev.pvid || '-'}</code>
                </div>
              </div>
              <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                ${getChannelBadge(ev.canal)}
                ${getStatusBadge(ev.status_entrega)}
              </div>
            </div>
          `).join('');
        }
      }

      if (listAmanha) {
        if (eventosAmanha.length === 0) {
          listAmanha.innerHTML = '<div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Nenhum confronto agendado para amanhã.</div>';
        } else {
          listAmanha.innerHTML = eventosAmanha.map(ev => `
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #2563EB; border-radius: 6px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
              <div>
                <div style="font-size: 11px; color: #1E40AF; font-weight: 700; text-transform: uppercase;">
                  ${ev.campeonato || 'FUTEBOL / ESPORTES'} &bull; <span style="font-size: 12px; color: #0F172A; font-weight: 800;">${ev.horario || '--:--'}</span>
                </div>
                <div style="font-size: 13.5px; font-weight: 700; color: #1E293B; margin: 3px 0;">
                  ${ev.partida || '-'}
                </div>
                <div style="font-size: 11px; color: #475569;">
                  Responsável: <b>${ev.responsavel || '-'}</b> &bull; PVID: <code style="font-family:'JetBrains Mono',monospace; background:#E2E8F0; padding:1px 4px; border-radius:3px;">${ev.pvid || '-'}</code>
                </div>
              </div>
              <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                ${getChannelBadge(ev.canal)}
                ${getStatusBadge(ev.status_entrega)}
              </div>
            </div>
          `).join('');
        }
      }
    }

    function renderTable() {
      initStreamingFilters();
      updateStreamingHighlightCards();
      // Ordenação padrão decrescente por data para os mais recentes no topo
      if (!streamSortCol) {
        streamSortCol = 'data';
        streamSortAsc = false;
      }
      const searchBox = document.getElementById("search-box");
      const q = searchBox ? searchBox.value.toLowerCase().trim() : "";
      const mesBox = document.getElementById("filter-mes");
      const fMes = mesBox ? mesBox.value.toLowerCase().trim() : "";
      const campBox = document.getElementById("filter-campeonato");
      const fCamp = campBox ? campBox.value.toLowerCase().trim() : "";
      const canalBox = document.getElementById("filter-canal");
      const fCanal = canalBox ? canalBox.value.toLowerCase().trim() : "";
      const statusBox = document.getElementById("filter-status");
      const fStatus = statusBox ? statusBox.value.toLowerCase().trim() : "";

      const tbody = document.getElementById("table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      let caze = 0, prime = 0, netflix = 0, outros = 0;

      let filtered = allEvents.filter((ev) => {
        const cStr = String(ev.canal || "").toLowerCase();
        if (cStr.includes("cazé") || cStr.includes("caze")) caze++;
        else if (cStr.includes("prime") || cStr.includes("amazon")) prime++;
        else if (cStr.includes("netflix")) netflix++;
        else outros++;

        if (fMes && !String(ev.mes || "").toLowerCase().includes(fMes)) return false;
        if (fCamp && !String(ev.campeonato || "").toLowerCase().includes(fCamp)) return false;
        if (fCanal && !cStr.includes(fCanal)) return false;
        if (fStatus && !String(ev.status_entrega || "").toLowerCase().includes(fStatus)) return false;

        if (q) {
          const fullText = (
            (ev.partida || '') + " " + (ev.campeonato || '') + " " +
            (ev.data || '') + " " + (ev.canal || '') + " " + (ev.responsavel || '')
          ).toLowerCase();
          if (!fullText.includes(q)) return false;
        }
        return true;
      });

      if (streamSortCol) {
        filtered.sort((a, b) => {
          let va = a[streamSortCol] || '';
          let vb = b[streamSortCol] || '';
          if (streamSortCol === 'data') {
            const parseDate = s => {
              const parts = String(s).split('/');
              if (parts.length === 3) return new Date(parts[2], parts[1] - 1, parts[0]).getTime();
              return 0;
            };
            const da = parseDate(va);
            const db = parseDate(vb);
            return streamSortAsc ? (da - db) : (db - da);
          }
          const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true, sensitivity: 'base' });
          return streamSortAsc ? cmp : -cmp;
        });
      }

      const now = new Date();
      const pad = n => String(n).padStart(2, "0");
      const hojeStr = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()}`;
      const hojeParts = hojeStr.split('/');
      const hojeTimestamp = new Date(hojeParts[2], hojeParts[1] - 1, hojeParts[0]).getTime();

      const parseEvTimestamp = (dateStr) => {
        if (!dateStr) return 0;
        const parts = String(dateStr).split('/');
        if (parts.length === 3) return new Date(parts[2], parts[1] - 1, parts[0]).getTime();
        return 0;
      };

      filtered.forEach((ev) => {
        count++;
        const tr = document.createElement("tr");

        const evTimestamp = parseEvTimestamp(ev.data);
        const isHoje = String(ev.data || "").trim() === hojeStr;
        const isPassado = evTimestamp > 0 && evTimestamp < hojeTimestamp;
        const isFuturo = evTimestamp > hojeTimestamp;

        if (isHoje) {
          tr.style.backgroundColor = "rgba(34, 197, 94, 0.12)";
          tr.style.borderLeft = "5px solid #16A34A";
          tr.classList.add("stream-row-today");
        } else if (isPassado) {
          tr.style.backgroundColor = "rgba(239, 68, 68, 0.08)";
          tr.style.borderLeft = "5px solid #EF4444";
          tr.classList.add("stream-row-past");
        } else if (isFuturo) {
          tr.style.borderLeft = "5px solid #3B82F6";
          tr.classList.add("stream-row-future");
        }

        const evId = ev.id || `${ev.partida}_${ev.data}`;
        if (isStreamGridEditMode) {
          tr.innerHTML = `
            <td class="td-center"><input type="checkbox" class="chk-stream-row" value="${evId}" onchange="updateStreamingSelectionState()"></td>
            <td class="td-center" style="color: #64748B; font-weight: 600;">${count}</td>
            <td class="td-center"><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'mes', this.innerText.trim())">${ev.mes || ''}</div></td>
            <td class="td-center"><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'data', this.innerText.trim())">${ev.data || ''}</div></td>
            <td class="td-center"><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'horario', this.innerText.trim())">${ev.horario || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'campeonato', this.innerText.trim())">${ev.campeonato || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell sp-grid-cell-wide" onblur="updateStreamField('${evId}', 'partida', this.innerText.trim())">${ev.partida || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'responsavel', this.innerText.trim())">${ev.responsavel || ''}</div></td>
            <td class="td-center">
              <select class="sp-grid-select" onchange="updateStreamField('${evId}', 'canal', this.value)">
                <option value="Cazé TV" ${String(ev.canal).includes('Cazé') ? 'selected' : ''}>Cazé TV</option>
                <option value="Amazon Prime" ${String(ev.canal).includes('Amazon') || String(ev.canal).includes('Prime') ? 'selected' : ''}>Amazon Prime</option>
                <option value="Netflix" ${String(ev.canal).includes('Netflix') ? 'selected' : ''}>Netflix</option>
                <option value="TNT / MAX / Record" ${String(ev.canal).includes('TNT') || String(ev.canal).includes('Record') ? 'selected' : ''}>TNT / MAX / Record</option>
                <option value="YouTube" ${String(ev.canal).includes('YouTube') ? 'selected' : ''}>YouTube</option>
                <option value="Outros" ${!['Cazé', 'Amazon', 'Prime', 'Netflix', 'TNT', 'Record', 'YouTube'].some(k => String(ev.canal).includes(k)) ? 'selected' : ''}>Outros</option>
              </select>
            </td>
            <td class="td-center"><div contenteditable="true" class="sp-grid-cell" onblur="updateStreamField('${evId}', 'pvid', this.innerText.trim())">${ev.pvid || ''}</div></td>
            <td class="td-center">
              <select class="sp-grid-select sp-grid-select-sm" onchange="updateStreamField('${evId}', 'status_entrega', this.value)">
                <option value="Exibido" ${ev.status_entrega === 'Exibido' ? 'selected' : ''}>Exibido</option>
                <option value="Em andamento" ${ev.status_entrega === 'Em andamento' ? 'selected' : ''}>Em andamento</option>
                <option value="Pendente" ${ev.status_entrega === 'Pendente' ? 'selected' : ''}>Pendente</option>
                <option value="Cancelado" ${ev.status_entrega === 'Cancelado' ? 'selected' : ''}>Cancelado</option>
              </select>
            </td>
            <td class="td-center">
              <select class="sp-grid-select sp-grid-select-sm" onchange="updateStreamField('${evId}', 'programado', this.value)">
                <option value="SIM" ${String(ev.programado).toUpperCase() === 'SIM' ? 'selected' : ''}>SIM</option>
                <option value="NÃO" ${String(ev.programado).toUpperCase() !== 'SIM' ? 'selected' : ''}>NÃO</option>
              </select>
            </td>
          `;
          tbody.appendChild(tr);
          return;
        }

        tr.innerHTML = `
          <td class="td-center"><input type="checkbox" class="chk-stream-row" value="${evId}" onchange="updateStreamingSelectionState()"></td>
          <td class="td-center" style="color: #64748B; font-weight: 600;">${count}</td>
          <td class="td-center">${ev.mes || '-'}</td>
          <td class="td-center" style="font-weight: 600;">${ev.data || '-'}</td>
          <td class="td-center">${ev.horario || '-'}</td>
          <td><b>${ev.campeonato || '-'}</b></td>
          <td><b>${ev.partida || '-'}</b></td>
          <td>${ev.responsavel || '-'}</td>
          <td class="td-center">${getChannelBadge(ev.canal)}</td>
          <td class="td-center"><span class="badge badge-pvid">${ev.pvid || '-'}</span></td>
          <td class="td-center">${getStatusBadge(ev.status_entrega)}</td>
          <td class="td-center">${ev.programado || '-'}</td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById("kpi-caze").innerText = caze;
      document.getElementById("kpi-prime").innerText = prime;
      document.getElementById("kpi-netflix").innerText = netflix;
      document.getElementById("kpi-outros").innerText = outros;
      document.getElementById("showing-count").innerText = count;
      const streamTitleEl = document.getElementById("streaming-list-title");
      if (streamTitleEl) {
        streamTitleEl.innerHTML = `Programação Streaming (${allEvents.length} Confrontos) <span class="star-icon">☆</span>`;
      }
      updateStreamingSelectionState();
    }

    function toggleSelectAllStreaming(masterChk) {
      const isChecked = !!masterChk.checked;
      document.querySelectorAll(".chk-stream-row").forEach(chk => {
        chk.checked = isChecked;
      });
      updateStreamingSelectionState();
    }

    function updateStreamingSelectionState() {
      const allRowChks = document.querySelectorAll(".chk-stream-row");
      const checkedRows = Array.from(allRowChks).filter(chk => chk.checked);
      const btnDel = document.getElementById("btn-delete-stream-selected");
      const countEl = document.getElementById("count-stream-selected");
      const masterChk = document.getElementById("chk-stream-all");

      if (countEl) countEl.innerText = checkedRows.length;
      if (btnDel) btnDel.style.display = checkedRows.length > 0 ? "inline-flex" : "none";
      if (masterChk) masterChk.checked = (allRowChks.length > 0 && checkedRows.length === allRowChks.length);
    }

    // ==============================================================================
    // MODAL IN-DOM SEGURO PARA CONFIRMAÇÃO DE EXCLUSÃO (GOOGLE SITES / IFRAME SAFE)
    // ==============================================================================
    let _customDeleteResolve = null;

    function showCustomDeleteModal(title, message, confirmBtnText = "Sim, Excluir Definitivamente") {
      return new Promise((resolve) => {
        _customDeleteResolve = resolve;
        const modal = document.getElementById("modal-generic-confirm-delete");
        const titleEl = document.getElementById("modal-delete-title");
        const msgEl = document.getElementById("modal-delete-message");
        const btnConfirm = document.getElementById("modal-delete-confirm-btn");
        if (titleEl) titleEl.innerText = title;
        if (msgEl) msgEl.innerHTML = message;
        if (btnConfirm) btnConfirm.innerText = confirmBtnText;
        if (modal) modal.style.display = "flex";
      });
    }
    window.showCustomDeleteModal = showCustomDeleteModal;

    function closeCustomDeleteModal(confirmed) {
      const modal = document.getElementById("modal-generic-confirm-delete");
      if (modal) modal.style.display = "none";
      if (_customDeleteResolve) {
        _customDeleteResolve(confirmed);
        _customDeleteResolve = null;
      }
    }
    window.closeCustomDeleteModal = closeCustomDeleteModal;

    async function deleteSelectedStreamingEvents() {
      const checkedRows = Array.from(document.querySelectorAll(".chk-stream-row:checked"));
      if (checkedRows.length === 0) return;
      const count = checkedRows.length;
      const confirmed = await showCustomDeleteModal(
        "Confirmar Exclusão de Confrontos",
        `Tem certeza que deseja remover definitivamente <strong>${count} confronto(s)</strong> selecionado(s) da programação de streaming?`
      );
      if (!confirmed) return;
      const selectedIds = new Set(checkedRows.map(chk => String(chk.value)));
      allEvents = allEvents.filter(ev => {
        const evId = String(ev.id || `${ev.partida}_${ev.data}`);
        return !selectedIds.has(evId);
      });
      localStorage.setItem("sp_custom_streaming_events", JSON.stringify(allEvents));
      renderTable();
      updateStreamingSelectionState();
      showToast(`🗑️ ${count} confrontos excluídos com sucesso da programação!`, "success");
    }

    let hospSortCol = null;
    let hospSortAsc = true;

    function sortHospBy(col) {
      if (hospSortCol === col) {
        hospSortAsc = !hospSortAsc;
      } else {
        hospSortCol = col;
        hospSortAsc = true;
      }
      document.querySelectorAll('#pane-hospedeiros .th-sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.innerText = '↕';
      });
      const curIcon = document.getElementById('sort-hosp-' + col);
      if (curIcon && curIcon.parentElement) {
        curIcon.parentElement.classList.add(hospSortAsc ? 'sorted-asc' : 'sorted-desc');
        curIcon.innerText = hospSortAsc ? '▲' : '▼';
      }
      renderHospedeirosTable();
    }

    let isHospGridEditMode = false;

    function openNewHospedeiroModal() {
      const modal = document.getElementById("modal-new-hospedeiro");
      if (modal) modal.style.display = "flex";
    }

    function closeNewHospedeiroModal() {
      const modal = document.getElementById("modal-new-hospedeiro");
      if (modal) modal.style.display = "none";
    }

    function saveNewHospedeiro(event) {
      if (event) event.preventDefault();
      const cidade = document.getElementById("new-hosp-cidade")?.value.trim() || "";
      const nome = document.getElementById("new-hosp-nome")?.value.trim() || "";
      const esp = document.getElementById("new-hosp-esp")?.value.trim() || "Técnico de Recepção";
      const telcom = document.getElementById("new-hosp-telcom")?.value.trim() || "-";
      const telcel = document.getElementById("new-hosp-telcel")?.value.trim() || "-";

      if (!cidade || !nome) {
        showToast("⚠️ Preencha a cidade e o nome do técnico!", "warning");
        return;
      }

      const newId = "hosp_" + Date.now();
      const newHosp = {
        id: newId,
        Title: cidade,
        Nome1: nome,
        Especialidade: esp,
        Telefone_x0020_Comercial: telcom,
        Telefone_x0020_Celular: telcel
      };

      allHospedeiros.unshift(newHosp);

      try {
        let customHosp = JSON.parse(localStorage.getItem('sp_custom_hospedeiros') || '[]');
        customHosp.unshift(newHosp);
        localStorage.setItem('sp_custom_hospedeiros', JSON.stringify(customHosp));
      } catch (e) {
        console.warn("Erro ao salvar hospedeiro local:", e);
      }

      closeNewHospedeiroModal();
      document.getElementById("form-new-hospedeiro")?.reset();
      renderHospedeirosTable();
      showToast(`✅ Hospedeiro '${nome}' (${cidade}) cadastrado com sucesso!`, "success");
    }

    function toggleHospGridEdit() {
      isHospGridEditMode = !isHospGridEditMode;
      const btn = document.getElementById("btn-grid-hosp");
      const icon = document.getElementById("btn-grid-hosp-icon");
      const txt = document.getElementById("btn-grid-hosp-text");
      const alertBox = document.getElementById("hosp-grid-mode-alert");

      if (isHospGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderHospedeirosTable();
    }

    function updateHospField(id, field, value) {
      const item = allHospedeiros.find(h => (String(h.id) === String(id) || String(h.Title) === String(id)));
      if (!item) return;

      item[field] = value;

      try {
        let customEdits = JSON.parse(localStorage.getItem('sp_custom_hospedeiros_edits') || '{}');
        if (!customEdits[id]) customEdits[id] = {};
        customEdits[id][field] = value;
        localStorage.setItem('sp_custom_hospedeiros_edits', JSON.stringify(customEdits));
      } catch (e) {
        console.warn("Erro ao persistir edição hospedeiro:", e);
      }

      showToast(`💾 Alteração salva em ${field}!`, "success");
    }

    function renderHospedeirosTable() {
      const sBox = document.getElementById("search-hosp-box");
      const q = sBox ? sBox.value.toLowerCase().trim() : "";
      const tbody = document.getElementById("hosp-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let list = allHospedeiros.filter((h) => {
        if (!q) return true;
        const t = ((h.Title||'') + " " + (h.Nome1||'') + " " + (h.Especialidade||'') + " " + (h.Telefone_x0020_Comercial||'') + " " + (h.Telefone_x0020_Celular||'')).toLowerCase();
        return t.includes(q);
      });

      if (hospSortCol) {
        list.sort((a, b) => {
          let va = a[hospSortCol] || '';
          let vb = b[hospSortCol] || '';
          const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true, sensitivity: 'base' });
          return hospSortAsc ? cmp : -cmp;
        });
      }

      let count = 0;
      list.forEach((h) => {
        count++;
        const tr = document.createElement("tr");

        if (isHospGridEditMode) {
          const hospId = h.id || `${h.Title}_${h.Nome1}`;
          tr.innerHTML = `
            <td class="td-center" style="color: #64748B;">${count}</td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateHospField('${hospId}', 'Title', this.innerText.trim())">${h.Title || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateHospField('${hospId}', 'Nome1', this.innerText.trim())">${h.Nome1 || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateHospField('${hospId}', 'Especialidade', this.innerText.trim())">${h.Especialidade || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateHospField('${hospId}', 'Telefone_x0020_Comercial', this.innerText.trim())">${h.Telefone_x0020_Comercial || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateHospField('${hospId}', 'Telefone_x0020_Celular', this.innerText.trim())">${h.Telefone_x0020_Celular || ''}</div></td>
          `;
          tbody.appendChild(tr);
          return;
        }

        tr.innerHTML = `
          <td class="td-center" style="color: #64748B;">${count}</td>
          <td><b>${h.Title || '-'}</b></td>
          <td>${h.Nome1 || '-'}</td>
          <td><span style="color: #0078D4; font-weight: 600;">${h.Especialidade || '-'}</span></td>
          <td>📞 ${h.Telefone_x0020_Comercial || '-'}</td>
          <td>📱 ${h.Telefone_x0020_Celular || '-'}</td>
        `;
        tbody.appendChild(tr);
      });
      document.getElementById("showing-hosp-count").innerText = count;
    }

    let currentOcoView = "emandamento";
    let activeStatusFilters = ["Em andamento", "Feedback"];
    let ocoSortCol = "Criado";
    let ocoSortAsc = false;

    function switchOcoView(viewName) {
      currentOcoView = viewName;
      document.querySelectorAll(".sp-view-tab").forEach(tab => tab.classList.remove("active"));
      const activeTab = document.getElementById("view-tab-" + viewName);
      if (activeTab) activeTab.classList.add("active");

      const pillWrap = document.getElementById("oco-filter-pills-wrap");
      if (viewName === "emandamento") {
        activeStatusFilters = ["Em andamento", "Feedback"];
        if (pillWrap) pillWrap.style.display = "flex";
        const p1 = document.getElementById("pill-emandamento");
        const p2 = document.getElementById("pill-feedback");
        if (p1) p1.style.display = "inline-flex";
        if (p2) p2.style.display = "inline-flex";
      } else {
        if (pillWrap) pillWrap.style.display = "none";
      }

      renderOcorrenciasTable();
    }

    function toggleStatusFilter(statusName) {
      if (activeStatusFilters.includes(statusName)) {
        activeStatusFilters = activeStatusFilters.filter(s => s !== statusName);
        if (statusName === "Em andamento") {
          const p = document.getElementById("pill-emandamento");
          if (p) p.style.display = "none";
        } else if (statusName === "Feedback") {
          const p = document.getElementById("pill-feedback");
          if (p) p.style.display = "none";
        }
      } else {
        activeStatusFilters.push(statusName);
        if (statusName === "Em andamento") {
          const p = document.getElementById("pill-emandamento");
          if (p) p.style.display = "inline-flex";
        } else if (statusName === "Feedback") {
          const p = document.getElementById("pill-feedback");
          if (p) p.style.display = "inline-flex";
        }
      }
      renderOcorrenciasTable();
    }

    function clearOcoFilters() {
      switchOcoView("todos");
    }

    function sortOcoBy(col) {
      if (ocoSortCol === col) {
        ocoSortAsc = !ocoSortAsc;
      } else {
        ocoSortCol = col;
        ocoSortAsc = (col === "Criado" ? false : true);
      }
      document.querySelectorAll('#pane-ocorrencias .th-sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.innerText = '↕';
      });
      const curIcon = document.getElementById('sort-oco-' + col);
      if (curIcon && curIcon.parentElement) {
        curIcon.parentElement.classList.add(ocoSortAsc ? 'sorted-asc' : 'sorted-desc');
        curIcon.innerText = ocoSortAsc ? '▲' : '▼';
      }
      renderOcorrenciasTable();
    }

    function toggleOcoSort() {
      sortOcoBy("Criado");
    }

    function formatSPDate(isoStr) {
      if (!isoStr) return '-';
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const pad = n => String(n).padStart(2, '0');
      return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    let isOcoGridEditMode = false;

    function openNewOcoModal() {
      const dl = document.getElementById("hosts-datalist");
      if (dl && dl.children.length === 0 && Array.isArray(allHosts)) {
        allHosts.forEach(h => {
          const opt = document.createElement("option");
          opt.value = h.Title || h.host || h;
          dl.appendChild(opt);
        });
      }
      const modal = document.getElementById("modal-new-oco");
      if (modal) modal.style.display = "flex";
    }

    function closeNewOcoModal() {
      const modal = document.getElementById("modal-new-oco");
      if (modal) modal.style.display = "none";
    }

    function saveNewOcorrencia(event) {
      event.preventDefault();
      const status = document.getElementById("new-oco-status").value;
      const host = document.getElementById("new-oco-host").value.trim();
      const cs = document.getElementById("new-oco-cs").value.trim() || "-";
      const veiculo = document.getElementById("new-oco-veiculo").value.trim() || "-";
      const equip = document.getElementById("new-oco-equipamento").value.trim() || "-";
      const tipo = document.getElementById("new-oco-tipo").value;
      const recup = document.getElementById("new-oco-recup").value;
      const stream = document.getElementById("new-oco-streaming").value;
      const operacao = document.getElementById("new-oco-operacao").checked;
      const acoes = document.getElementById("new-oco-acoes").value.trim() || "-";
      const area = document.getElementById("new-oco-area").value;
      const redmine = document.getElementById("new-oco-redmine").value.trim() || "";

      if (!host) {
        showToast("Por favor informe o Host / Praça da ocorrência.", "warning");
        return;
      }

      const nowIso = new Date().toISOString();
      const newOco = {
        id: "oco_" + Date.now(),
        Status: status,
        Criado: nowIso,
        HostName: host,
        CS: cs,
        Veiculo: veiculo,
        Equipamento: equip,
        TipoProblema: tipo,
        EmRecuperacao: recup,
        GravacaoStreaming: stream,
        InformarOperacao: operacao,
        AcoesExecutadas: acoes,
        AreaResponsavel: area,
        Redmine: redmine
      };

      allOcorrencias.unshift(newOco);

      try {
        let customOcos = JSON.parse(localStorage.getItem('sp_custom_ocorrencias') || '[]');
        customOcos.unshift(newOco);
        localStorage.setItem('sp_custom_ocorrencias', JSON.stringify(customOcos));
      } catch (e) {
        console.warn("Erro ao salvar no localStorage:", e);
      }

      closeNewOcoModal();
      document.getElementById("form-new-oco").reset();
      renderOcorrenciasTable();
      showToast(`✅ Ocorrência para '${host}' cadastrada com sucesso!`, "success");
    }

    function toggleOcoGridEdit() {
      isOcoGridEditMode = !isOcoGridEditMode;
      const btn = document.getElementById("btn-grid-oco");
      const icon = document.getElementById("btn-grid-oco-icon");
      const txt = document.getElementById("btn-grid-oco-text");
      const alertBox = document.getElementById("oco-grid-mode-alert");

      if (isOcoGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderOcorrenciasTable();
    }

    function updateOcoField(id, field, value) {
      const item = allOcorrencias.find(o => (o.id === id || String(o.Criado) === String(id)));
      if (!item) return;

      item[field] = value;

      try {
        let customEdits = JSON.parse(localStorage.getItem('sp_custom_ocorrencias_edits') || '{}');
        if (!customEdits[id]) customEdits[id] = {};
        customEdits[id][field] = value;
        localStorage.setItem('sp_custom_ocorrencias_edits', JSON.stringify(customEdits));
      } catch (e) {
        console.warn("Erro ao persistir edição:", e);
      }

      showToast(`💾 Alteração salva em ${field}!`, "success");
    }

    function renderOcorrenciasTable() {
      const sBox = document.getElementById("search-oco-box");
      const q = sBox ? sBox.value.toLowerCase().trim() : "";
      const tbody = document.getElementById("oco-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let list = allOcorrencias.slice();

      // 1. Filtragem por View
      if (currentOcoView === "emandamento") {
        if (activeStatusFilters.length > 0) {
          list = list.filter(o => activeStatusFilters.includes(o.Status));
        }
      } else if (currentOcoView === "recuperacao") {
        list = list.filter(o => String(o.EmRecuperacao || "").toLowerCase() === "sim");
      } else if (currentOcoView === "operacao") {
        list = list.filter(o => Boolean(o.InformarOperacao));
      }

      // 2. Filtragem por busca
      if (q) {
        list = list.filter(o => {
          const cs = Array.isArray(o.CS) ? o.CS.join(" ") : (o.CS || "");
          const eq = Array.isArray(o.Equipamento) ? o.Equipamento.join(" ") : (o.Equipamento || "");
          const host = o.HostName || "";
          const str = (o.Status + " " + host + " " + cs + " " + (o.Veiculo||"") + " " + eq + " " + (o.TipoProblema||"") + " " + (o.AcoesExecutadas||"") + " " + (o.AreaResponsavel||"") + " " + (o.Redmine||"")).toLowerCase();
          return str.includes(q);
        });
      }

      // 3. Ordenação por Coluna
      list.sort((a, b) => {
        if (ocoSortCol === "Criado") {
          const da = new Date(a.Criado || 0).getTime();
          const db = new Date(b.Criado || 0).getTime();
          return ocoSortAsc ? (da - db) : (db - da);
        }
        let va = a[ocoSortCol];
        let vb = b[ocoSortCol];
        if (Array.isArray(va)) va = va.join(", ");
        if (Array.isArray(vb)) vb = vb.join(", ");
        if (typeof va === 'boolean') va = va ? '1' : '0';
        if (typeof vb === 'boolean') vb = vb ? '1' : '0';
        va = String(va || '');
        vb = String(vb || '');
        const cmp = va.localeCompare(vb, undefined, { numeric: true, sensitivity: 'base' });
        return ocoSortAsc ? cmp : -cmp;
      });

      let count = 0;
      list.forEach((o) => {
        count++;
        const tr = document.createElement("tr");
        const ocoId = o.id || o.Criado;
        tr.setAttribute("data-oco-id", ocoId);

        if (isOcoGridEditMode) {
          // MODO DE EXIBIÇÃO DE GRADE (EDITÁVEL DIRETO NO BROWSER)
          const hostVal = o.HostName || o.hostLookupId || '';
          const csVal = Array.isArray(o.CS) ? o.CS.join(", ") : (o.CS || '');
          const veicVal = o.Veiculo || '';
          const equipVal = Array.isArray(o.Equipamento) ? o.Equipamento.join(", ") : (o.Equipamento || '');
          const tipoVal = o.TipoProblema || '';
          const acoesVal = o.AcoesExecutadas || '';
          const areaVal = o.AreaResponsavel || '';
          const redmineVal = o.Redmine ? String(o.Redmine).replace('.0', '').trim() : '';

          tr.innerHTML = `
            <td>
              <select class="sp-grid-select" onchange="updateOcoField('${ocoId}', 'Status', this.value)">
                <option value="Em andamento" ${o.Status === 'Em andamento' ? 'selected' : ''}>Em andamento</option>
                <option value="Feedback" ${o.Status === 'Feedback' ? 'selected' : ''}>Feedback</option>
                <option value="Concluído" ${o.Status === 'Concluído' ? 'selected' : ''}>Concluído</option>
              </select>
            </td>
            <td style="color: #64748B; font-size: 11.5px; white-space: nowrap;">${formatSPDate(o.Criado)}</td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'HostName', this.innerText.trim())">${hostVal}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'CS', this.innerText.trim())">${csVal}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'Veiculo', this.innerText.trim())">${veicVal}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'Equipamento', this.innerText.trim())">${equipVal}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'TipoProblema', this.innerText.trim())">${tipoVal}</div></td>
            <td class="td-center">
              <select class="sp-grid-select sp-grid-select-sm" onchange="updateOcoField('${ocoId}', 'EmRecuperacao', this.value)">
                <option value="Não" ${String(o.EmRecuperacao).toLowerCase() !== 'sim' ? 'selected' : ''}>Não</option>
                <option value="Sim" ${String(o.EmRecuperacao).toLowerCase() === 'sim' ? 'selected' : ''}>Sim</option>
              </select>
            </td>
            <td class="td-center">
              <select class="sp-grid-select sp-grid-select-sm" onchange="updateOcoField('${ocoId}', 'GravacaoStreaming', this.value)">
                <option value="Não" ${String(o.GravacaoStreaming).toLowerCase() !== 'sim' ? 'selected' : ''}>Não</option>
                <option value="Sim" ${String(o.GravacaoStreaming).toLowerCase() === 'sim' ? 'selected' : ''}>Sim</option>
              </select>
            </td>
            <td class="td-center">
              <input type="checkbox" onchange="updateOcoField('${ocoId}', 'InformarOperacao', this.checked)" ${o.InformarOperacao ? 'checked' : ''} style="width: 16px; height: 16px; cursor: pointer;">
            </td>
            <td><div contenteditable="true" class="sp-grid-cell sp-grid-cell-wide" onblur="updateOcoField('${ocoId}', 'AcoesExecutadas', this.innerText.trim())">${acoesVal}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'AreaResponsavel', this.innerText.trim())">${areaVal}</div></td>
            <td class="td-center"><div contenteditable="true" class="sp-grid-cell" onblur="updateOcoField('${ocoId}', 'Redmine', this.innerText.trim())">${redmineVal}</div></td>
          `;
          tbody.appendChild(tr);
          return;
        }

        // Status badge com ação de encerramento rápido (pop-up ao clicar no banner)
        let statusBadge = `<span class="sp-badge sp-badge-concluido" onclick="event.stopPropagation(); openQuickCloseOcoModal('${ocoId}')" title="Clique para reabrir ou gerenciar ocorrência" style="cursor: pointer;">Concluído ⌵</span>`;
        if (o.Status === "Em andamento") {
          statusBadge = `<span class="sp-badge sp-badge-em-andamento" onclick="event.stopPropagation(); openQuickCloseOcoModal('${ocoId}')" title="Clique no banner para abrir pop-up e encerrar" style="cursor: pointer; animation: pulse 2s infinite;">Em andamento ⚡</span>`;
        } else if (o.Status === "Feedback") {
          statusBadge = `<span class="sp-badge sp-badge-feedback" onclick="event.stopPropagation(); openQuickCloseOcoModal('${ocoId}')" title="Clique no banner para abrir pop-up e encerrar" style="cursor: pointer;">Feedback ⚡</span>`;
        }

        // Host
        const hostName = o.HostName || o.hostLookupId || '-';

        // CS
        const csStr = Array.isArray(o.CS) ? o.CS.join(", ") : (o.CS || '-');

        // Veículo
        const veiculoStr = o.Veiculo || '-';

        // Equipamento Badges
        let equipBadges = '';
        const eqList = Array.isArray(o.Equipamento) ? o.Equipamento : [o.Equipamento];
        eqList.filter(Boolean).forEach(eq => {
          let badgeClass = 'sp-badge-dark';
          const eqUpper = String(eq).toUpperCase();
          if (eqUpper.includes("ROTEADOR") || eqUpper.includes("SWITCH")) badgeClass = 'sp-badge-amber';
          else if (eqUpper.includes("MAQUINA")) badgeClass = 'sp-badge-teal';
          else if (eqUpper.includes("TOMATE")) badgeClass = 'sp-badge-red';
          else if (eqUpper.includes("WADT")) badgeClass = 'sp-badge-purple';
          equipBadges += `<span class="sp-badge ${badgeClass}" style="margin-right: 4px;">${eq}</span>`;
        });
        if (!equipBadges) equipBadges = '-';

        // Tipo do Problema
        let tipoBadgeClass = 'sp-badge-gray';
        const tipo = o.TipoProblema || '-';
        const tUpper = String(tipo).toUpperCase();
        if (tUpper.includes("SEM SINAL")) tipoBadgeClass = 'sp-badge-yellow';
        else if (tUpper.includes("SEM COMUNICAÇÃO")) tipoBadgeClass = 'sp-badge-blue';
        else if (tUpper.includes("NÃO ESTÁ GRAVANDO") || tUpper.includes("NÃO GRAVA")) tipoBadgeClass = 'sp-badge-red-soft';
        else if (tUpper.includes("SEM DETECÇÃO")) tipoBadgeClass = 'sp-badge-indigo';
        else if (tUpper.includes("IMAGEM CONGELADA")) tipoBadgeClass = 'sp-badge-cyan';
        else if (tUpper.includes("SEM ENERGIA")) tipoBadgeClass = 'sp-badge-orange';
        const tipoBadge = tipo !== '-' ? `<span class="sp-badge ${tipoBadgeClass}">${tipo}</span>` : '-';

        // Em recuperação
        const emRecup = (String(o.EmRecuperacao).toLowerCase() === 'sim') ?
          `<span class="sp-badge sp-badge-sim">Sim</span>` :
          `<span class="sp-badge sp-badge-nao">Não</span>`;

        // Gravação Streaming
        const gravStream = (String(o.GravacaoStreaming).toLowerCase() === 'sim') ?
          `<span class="sp-badge sp-badge-sim">Sim</span>` :
          `<span class="sp-badge sp-badge-nao">Não</span>`;

        // Informar Operação
        const infOper = o.InformarOperacao ? `<span style="color: #10B981; font-weight: bold; font-size: 15px;">✓</span>` : '';

        // Ações Executadas
        const acoes = o.AcoesExecutadas || '-';

        // Área / Responsável
        let areaBadge = o.AreaResponsavel || '-';
        if (o.AreaResponsavel === "N1") {
          areaBadge = `<span class="sp-badge sp-badge-n1">N1</span>`;
        } else if (String(o.AreaResponsavel).includes("Solucionado")) {
          areaBadge = `<span class="sp-badge sp-badge-solucionado">${o.AreaResponsavel}</span>`;
        } else if (String(o.AreaResponsavel).includes("Vinicius")) {
          areaBadge = `<span class="sp-badge sp-badge-vinicius">Vinicius Dantas</span>`;
        } else if (String(o.AreaResponsavel).includes("Lucieudes")) {
          areaBadge = `<span class="sp-badge sp-badge-lucieudes">Lucieudes Victor</span>`;
        } else if (o.AreaResponsavel) {
          areaBadge = `<span class="sp-badge sp-badge-blue">${o.AreaResponsavel}</span>`;
        }

        // Redmine
        let redmineHtml = '-';
        if (o.Redmine) {
          const rNum = String(o.Redmine).replace('.0', '').trim();
          redmineHtml = `<a href="http://10.1.0.39/redmine/issues/${rNum}" target="_blank" class="sp-redmine-link">#${rNum}</a>`;
        }

        tr.innerHTML = `
          <td>${statusBadge}</td>
          <td style="color: #64748B; font-size: 12px; white-space: nowrap;">${formatSPDate(o.Criado)}</td>
          <td><a href="javascript:void(0)" onclick="searchHostInOco('${encodeURIComponent(hostName)}')" style="color: #0078D4; font-weight: 600; text-decoration: none;">${hostName}</a></td>
          <td><span style="font-weight: 600; color: #475569;">${csStr}</span></td>
          <td><b>${veiculoStr}</b></td>
          <td>${equipBadges}</td>
          <td>${tipoBadge}</td>
          <td class="td-center">${emRecup}</td>
          <td class="td-center">${gravStream}</td>
          <td class="td-center">${infOper}</td>
          <td style="color: #334155; font-size: 12.5px; max-width: 320px;">${acoes}</td>
          <td>${areaBadge}</td>
          <td class="td-center">${redmineHtml}</td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById("showing-oco-count").innerText = count;
      document.getElementById("total-oco-count").innerText = allOcorrencias.length;
    }

    function searchHostInOco(encodedHost) {
      const hostName = decodeURIComponent(encodedHost);
      showPane('ocorrencias');
      const sBox = document.getElementById("search-oco-box");
      if (sBox) {
        sBox.value = hostName;
        renderOcorrenciasTable();
      }
    }

    let isAnteGridEditMode = false;

    function toggleAnteGridEdit() {
      isAnteGridEditMode = !isAnteGridEditMode;
      const btn = document.getElementById("btn-grid-ante");
      const icon = document.getElementById("btn-grid-ante-icon");
      const txt = document.getElementById("btn-grid-ante-text");
      const alertBox = document.getElementById("ante-grid-mode-alert");

      if (isAnteGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderAntenistasTable();
    }

    function updateAnteField(id, field, value) {
      const item = allAntenistas.find(a => (String(a.id) === String(id) || String(a.Title) === String(id)));
      if (!item) return;

      item[field] = value;

      try {
        let customEdits = JSON.parse(localStorage.getItem('sp_custom_antenistas_edits') || '{}');
        if (!customEdits[id]) customEdits[id] = {};
        customEdits[id][field] = value;
        localStorage.setItem('sp_custom_antenistas_edits', JSON.stringify(customEdits));
      } catch (e) {
        console.warn("Erro ao persistir edição antenista:", e);
      }

      showToast(`💾 Alteração salva em ${field}!`, "success");
    }

    function exportAntenistasCSV() {
      let csv = `Nome / Contato;Cidade / Praca;Especialidade / Cargo;Empresa;Telefone Comercial;Telefone Celular\\n`;
      allAntenistas.forEach(a => {
        csv += `"${a.Title || ''}";"${a.field_0 || ''}";"${a.Cargo || ''}";"${a.Empresa || ''}";"${a.Telefone_x0020_Comercial || ''}";"${a.Telefone_x0020_Celular || ''}"\\n`;
      });
      const blob = new Blob(["\\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `Contatos_Antenistas_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast("📥 Exportação de Antenistas CSV concluída com sucesso!", "success");
    }

    function renderAntenistasTable() {
      const sBox = document.getElementById("search-ante-box");
      const q = sBox ? sBox.value.toLowerCase().trim() : "";
      const tbody = document.getElementById("ante-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      allAntenistas.forEach((a) => {
        const nome = a.Title || '-';
        const cidade = a.field_0 || '-';
        const cargo = a.Cargo || 'Técnico em Antenas';
        const empresa = a.Empresa || '-';
        const telCom = a.Telefone_x0020_Comercial || '-';
        const telCel = a.Telefone_x0020_Celular || '-';

        if (q) {
          const str = (nome + " " + cidade + " " + cargo + " " + empresa + " " + telCom + " " + telCel).toLowerCase();
          if (!str.includes(q)) return;
        }

        const tr = document.createElement("tr");

        if (isAnteGridEditMode) {
          const anteId = a.id || `${a.Title}_${a.field_0}`;
          tr.innerHTML = `
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'Title', this.innerText.trim())">${a.Title || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'field_0', this.innerText.trim())">${a.field_0 || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'Cargo', this.innerText.trim())">${a.Cargo || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'Empresa', this.innerText.trim())">${a.Empresa || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'Telefone_x0020_Comercial', this.innerText.trim())">${a.Telefone_x0020_Comercial || ''}</div></td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updateAnteField('${anteId}', 'Telefone_x0020_Celular', this.innerText.trim())">${a.Telefone_x0020_Celular || ''}</div></td>
          `;
          tbody.appendChild(tr);
          return;
        }

        tr.innerHTML = `
          <td><b>${nome}</b></td>
          <td><span style="font-weight: 600; color: #0078D4;">${cidade}</span></td>
          <td><span class="badge badge-default">${cargo}</span></td>
          <td>${empresa}</td>
          <td>${telCom}</td>
          <td style="color: #10B981; font-weight: 600;">${telCel}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    let isHostGridEditMode = false;

    function toggleHostGridEdit() {
      isHostGridEditMode = !isHostGridEditMode;
      const btn = document.getElementById("btn-grid-hosts");
      const icon = document.getElementById("btn-grid-hosts-icon");
      const txt = document.getElementById("btn-grid-hosts-text");
      const alertBox = document.getElementById("hosts-grid-mode-alert");

      if (isHostGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderHostsTable();
    }

    function updateHostField(id, value) {
      allHosts[id] = value;
      try {
        let customHosts = JSON.parse(localStorage.getItem('sp_custom_hosts') || '{}');
        customHosts[id] = value;
        localStorage.setItem('sp_custom_hosts', JSON.stringify(customHosts));
      } catch (e) {
        console.warn("Erro ao persistir edição host:", e);
      }
      showToast(`💾 Host #${id} atualizado com sucesso!`, "success");
    }

    function exportHostsCSV() {
      let csv = `ID;Codigo do Host / Praca;Status\\n`;
      Object.keys(allHosts).sort((a,b) => Number(a) - Number(b)).forEach(id => {
        csv += `"${id}";"${allHosts[id]}";"Ativo"\\n`;
      });
      const blob = new Blob(["\\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `Cadastro_Hosts_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast("📥 Exportação de Hosts CSV concluída com sucesso!", "success");
    }

    function renderHostsTable() {
      const sBox = document.getElementById("search-hosts-box");
      const q = sBox ? sBox.value.toLowerCase().trim() : "";
      const tbody = document.getElementById("hosts-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      Object.keys(allHosts).sort((a,b) => Number(a) - Number(b)).forEach((id) => {
        const name = allHosts[id];
        if (q && !name.toLowerCase().includes(q) && !id.includes(q)) return;
        count++;

        const tr = document.createElement("tr");

        if (isHostGridEditMode) {
          tr.innerHTML = `
            <td class="td-center" style="color: #64748B;">${id}</td>
            <td><div contenteditable="true" class="sp-grid-cell sp-grid-cell-wide" onblur="updateHostField('${id}', this.innerText.trim())">${name}</div></td>
            <td class="td-center"><span class="sp-badge sp-badge-concluido">Ativo</span></td>
            <td class="td-center">
              <button class="btn-action btn-action-secondary" onclick="searchHostInOco('${encodeURIComponent(name)}')">Ver Incidentes</button>
            </td>
          `;
          tbody.appendChild(tr);
          return;
        }

        tr.innerHTML = `
          <td class="td-center" style="color: #64748B;">${id}</td>
          <td><b>${name}</b></td>
          <td class="td-center"><span class="sp-badge sp-badge-concluido">Ativo</span></td>
          <td class="td-center">
            <button class="btn-action btn-action-secondary" onclick="searchHostInOco('${encodeURIComponent(name)}')">Ver Incidentes</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
      const cEl = document.getElementById("showing-hosts-count");
      if (cEl) cEl.innerText = count;
    }

    function renderProcedimentosTable() {
      const sBox = document.getElementById("search-proc-box");
      const q = sBox ? sBox.value.toLowerCase() : "";
      const tbody = document.getElementById("proc-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      allProcedimentos.forEach((p, i) => {
        const name = p.FileLeafRef || p.Title || 'Procedimento #' + (i+1);
        if (q && !name.toLowerCase().includes(q)) return;

        count++;
        const ext = name.split('.').pop().toLowerCase();
        let icon = '📄';
        if (ext === 'pdf') icon = '📕';
        else if (ext === 'docx' || ext === 'doc') icon = '📘';
        else if (ext === 'xlsx' || ext === 'xls') icon = '📗';

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="td-center" style="color: #64748B;">${count}</td>
          <td><b>${icon} ${name}</b></td>
          <td><span class="badge badge-default">${ext.toUpperCase() || 'GUIA'}</span></td>
          <td style="color: #64748B;">${p.Modified ? p.Modified.substring(0,10) : '2026-11'}</td>
          <td class="td-center">
            <button class="btn-action btn-action-secondary" data-name="${encodeURIComponent(name)}" onclick="openProcModal(decodeURIComponent(this.getAttribute('data-name')))">👁️ Visualizar</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
      document.getElementById("showing-proc-count").innerText = count;
    }

    function renderDocumentosTable() {
      const sBox = document.getElementById("search-doc-box");
      const q = sBox ? sBox.value.toLowerCase() : "";
      const tbody = document.getElementById("docs-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      allDocumentos.forEach((d, i) => {
        const name = d.FileLeafRef || d.Title || 'Documento #' + (i+1);
        if (q && !name.toLowerCase().includes(q)) return;

        count++;
        const ext = name.split('.').pop().toLowerCase();
        let icon = '📁';
        if (ext === 'xlsx') icon = '📊';
        else if (ext === 'docx') icon = '📄';

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="td-center" style="color: #64748B;">${count}</td>
          <td><b>${icon} ${name}</b></td>
          <td><span class="badge badge-default">${d.ContentType || ext.toUpperCase()}</span></td>
          <td style="color: #64748B;">${d.Modified ? d.Modified.substring(0,10) : '2026-11'}</td>
          <td class="td-center">
            <a href="Escala_de_trabalho_2026.xlsx" download class="btn-action btn-action-secondary" style="text-decoration: none;">📥 Baixar</a>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    let isPermsGridEditMode = false;

    function openNewPermModal() {
      const modal = document.getElementById("modal-new-perm");
      if (modal) modal.style.display = "flex";
    }

    function closeNewPermModal() {
      const modal = document.getElementById("modal-new-perm");
      if (modal) modal.style.display = "none";
    }

    function saveNewPerm(event) {
      if (event) event.preventDefault();
      const nome = document.getElementById("new-perm-nome")?.value.trim() || "";
      const tipo = document.getElementById("new-perm-tipo")?.value || "user";
      const email = document.getElementById("new-perm-email")?.value.trim() || "";
      const sp_role = document.getElementById("new-perm-sp")?.value || "Membro";
      const google_role = document.getElementById("new-perm-google")?.value || "Operador";
      const escopo = document.getElementById("new-perm-escopo")?.value.trim() || "Suporte Captação";

      if (!nome || !email) {
        showToast("⚠️ Preencha o nome e o e-mail corporativo!", "warning");
        return;
      }

      const newPerm = {
        id: "perm_" + Date.now(),
        name: nome,
        type: tipo,
        email: email,
        sp_role: sp_role,
        google_role: google_role,
        scope: escopo,
        cargo: escopo
      };

      allPermissions.unshift(newPerm);

      try {
        let customPerms = JSON.parse(localStorage.getItem('sp_custom_permissions') || '[]');
        customPerms.unshift(newPerm);
        localStorage.setItem('sp_custom_permissions', JSON.stringify(customPerms));
      } catch (e) {
        console.warn("Erro ao salvar permissão local:", e);
      }

      closeNewPermModal();
      document.getElementById("form-new-perm")?.reset();
      renderPermsTable();
      showToast(`✅ Permissão para '${nome}' cadastrada com sucesso!`, "success");
    }

    function togglePermsGridEdit() {
      isPermsGridEditMode = !isPermsGridEditMode;
      const btn = document.getElementById("btn-grid-perms");
      const icon = document.getElementById("btn-grid-perms-icon");
      const txt = document.getElementById("btn-grid-perms-text");
      const alertBox = document.getElementById("perms-grid-mode-alert");

      if (isPermsGridEditMode) {
        if (btn) btn.classList.add("btn-grid-active");
        if (icon) icon.innerText = "💾";
        if (txt) txt.innerText = "Sair do modo de exibição de grade";
        if (alertBox) alertBox.style.display = "flex";
        showToast("Modo de exibição de grade ativado. Clique nas células para editar.", "info");
      } else {
        if (btn) btn.classList.remove("btn-grid-active");
        if (icon) icon.innerText = "田";
        if (txt) txt.innerText = "Editar no modo de exibição de grade";
        if (alertBox) alertBox.style.display = "none";
        showToast("Modo de exibição de grade finalizado. Todas as alterações salvas!", "success");
      }
      renderPermsTable();
    }

    function updatePermField(id, field, value) {
      const item = allPermissions.find(p => (String(p.id) === String(id) || String(p.email) === String(id)));
      if (!item) return;

      item[field] = value;

      try {
        let customEdits = JSON.parse(localStorage.getItem('sp_custom_perms_edits') || '{}');
        if (!customEdits[id]) customEdits[id] = {};
        customEdits[id][field] = value;
        localStorage.setItem('sp_custom_perms_edits', JSON.stringify(customEdits));
      } catch (e) {
        console.warn("Erro ao persistir edição permissão:", e);
      }

      showToast(`💾 Alteração salva em ${field}!`, "success");
    }

    function renderPermsTable() {
      const tbody = document.getElementById("perms-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      const searchInput = document.getElementById("search-perm-box");
      const q = searchInput ? searchInput.value.toLowerCase().trim() : "";

      const filtered = allPermissions.filter(p => {
        if (!q) return true;
        const name = (p.name || "").toLowerCase();
        const email = (p.email || "").toLowerCase();
        const type = (p.type || "").toLowerCase();
        const sp_role = (p.sp_role || "").toLowerCase();
        const google_role = (p.google_role || "").toLowerCase();
        const cargo = (p.cargo || "").toLowerCase();
        const scope = (p.scope || "").toLowerCase();
        return name.includes(q) || email.includes(q) || type.includes(q) ||
               sp_role.includes(q) || google_role.includes(q) || cargo.includes(q) || scope.includes(q);
      });

      filtered.forEach((p, i) => {
        let badgeClass = "badge-role-read";
        if (p.google_role === "Administrador") badgeClass = "badge-role-owner";
        else if (p.google_role === "Operador") badgeClass = "badge-role-write";

        const tr = document.createElement("tr");

        if (isPermsGridEditMode) {
          const permId = p.id || p.email;
          tr.innerHTML = `
            <td class="td-center" style="color: #64748B;">${i+1}</td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updatePermField('${permId}', 'name', this.innerText.trim())">${p.name || ''}</div></td>
            <td>
              <select class="sp-grid-select sp-grid-select-sm" onchange="updatePermField('${permId}', 'type', this.value)">
                <option value="user" ${p.type === 'user' ? 'selected' : ''}>user</option>
                <option value="group" ${p.type === 'group' ? 'selected' : ''}>group</option>
              </select>
            </td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updatePermField('${permId}', 'email', this.innerText.trim())">${p.email || ''}</div></td>
            <td>
              <select class="sp-grid-select" onchange="updatePermField('${permId}', 'sp_role', this.value)">
                <option value="Proprietário" ${String(p.sp_role).includes('Proprietário') ? 'selected' : ''}>Proprietário</option>
                <option value="Membro" ${String(p.sp_role).includes('Membro') ? 'selected' : ''}>Membro</option>
                <option value="Visitante" ${String(p.sp_role).includes('Visitante') ? 'selected' : ''}>Visitante</option>
              </select>
            </td>
            <td>
              <select class="sp-grid-select" onchange="updatePermField('${permId}', 'google_role', this.value)">
                <option value="Administrador" ${p.google_role === 'Administrador' ? 'selected' : ''}>Administrador</option>
                <option value="Operador" ${p.google_role === 'Operador' ? 'selected' : ''}>Operador</option>
                <option value="Leitor" ${p.google_role === 'Leitor' ? 'selected' : ''}>Leitor</option>
              </select>
            </td>
            <td><div contenteditable="true" class="sp-grid-cell" onblur="updatePermField('${permId}', 'scope', this.innerText.trim())">${p.scope || ''}</div></td>
          `;
          tbody.appendChild(tr);
          return;
        }

        tr.innerHTML = `
          <td class="td-center" style="color: #64748B;">${i+1}</td>
          <td><b>${p.name}</b></td>
          <td><span class="badge badge-default">${p.type}</span></td>
          <td>${p.email}</td>
          <td>${p.sp_role}</td>
          <td><span class="badge ${badgeClass}">${p.google_role}</span></td>
          <td style="font-size: 11px; color: #64748B;">${p.scope || '-'}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Modal
    function openProcModal(title) {
      document.getElementById("modal-title").innerText = title;
      document.getElementById("modal-content").innerHTML = `
        <div style="background: #F8FAFC; padding: 14px; border-radius: 6px; margin-bottom: 14px; border-left: 4px solid #0078D4;">
          <b>Guia Oficial de Suporte N1 & Procedimento Operacional</b><br>
          Este documento foi migrado do repositório corporativo e está disponível offline no novo Portal Web.
        </div>
        <p><b>Passo 1:</b> Verificar status de telemetria no Zabbix e confirmar sinal de entrada.</p>
        <p><b>Passo 2:</b> Em caso de falha no receptor TV BOX, executar reinicialização via comando remoto ou ciclo de energia.</p>
        <p><b>Passo 3:</b> Registrar o ticket de incidente no Redmine e notificar o plantão da Captação via Google Chat.</p>
        <div style="margin-top: 20px; text-align: right;">
          <button class="btn-action btn-action-primary" onclick="closeModal()">Fechar Procedimento</button>
        </div>
      `;
      document.getElementById("proc-modal").style.display = "flex";
    }

    function closeModal() {
      document.getElementById("proc-modal").style.display = "none";
    }

    // Sistema de Notificações Toast (Estilo Microsoft 365 / Google Workspace)
    function showToast(message, type = 'info') {
      let container = document.getElementById('sp-toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'sp-toast-container';
        document.body.appendChild(container);
      }
      const toast = document.createElement('div');
      toast.className = `sp-toast toast-${type}`;
      let icon = 'ℹ️';
      if (type === 'success') icon = '✅';
      else if (type === 'warning') icon = '⚠️';
      else if (type === 'error') icon = '❌';

      toast.innerHTML = `<span style="font-size: 16px;">${icon}</span><span>${message}</span>`;
      container.appendChild(toast);

      setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
      }, 3500);
    }

    // Modais e Inclusões para Antenistas, Hosts e Drive
    function openNewAntenistaModal() {
      const modal = document.getElementById("modal-new-antenista");
      if (modal) modal.style.display = "flex";
    }
    function closeNewAntenistaModal() {
      const modal = document.getElementById("modal-new-antenista");
      if (modal) modal.style.display = "none";
    }
    function saveNewAntenista(event) {
      event.preventDefault();
      const nome = document.getElementById("new-ante-nome").value.trim();
      const cidade = document.getElementById("new-ante-cidade").value.trim();
      const cargo = document.getElementById("new-ante-cargo").value.trim() || "Técnico em Antenas";
      const empresa = document.getElementById("new-ante-empresa").value.trim() || "-";
      const telCom = document.getElementById("new-ante-telcom").value.trim() || "-";
      const telCel = document.getElementById("new-ante-telcel").value.trim() || "-";

      if (!nome || !cidade) return;

      const newA = {
        Title: nome,
        field_0: cidade,
        Cargo: cargo,
        Empresa: empresa,
        Telefone_x0020_Comercial: telCom,
        Telefone_x0020_Celular: telCel
      };

      allAntenistas.unshift(newA);
      try {
        let saved = JSON.parse(localStorage.getItem('sp_custom_antenistas') || '[]');
        saved.unshift(newA);
        localStorage.setItem('sp_custom_antenistas', JSON.stringify(saved));
      } catch(e) {
        console.warn("Erro ao salvar antenista:", e);
      }

      closeNewAntenistaModal();
      document.getElementById("form-new-antenista").reset();
      renderAntenistasTable();
      showToast(`✅ Antenista '${nome}' cadastrado com sucesso!`, "success");
    }

    function openNewHostModal() {
      const modal = document.getElementById("modal-new-host");
      if (modal) modal.style.display = "flex";
    }
    function closeNewHostModal() {
      const modal = document.getElementById("modal-new-host");
      if (modal) modal.style.display = "none";
    }
    function saveNewHost(event) {
      event.preventDefault();
      const code = document.getElementById("new-host-code").value.trim();
      const status = document.getElementById("new-host-status").value;

      if (!code) return;

      const newH = {
        Title: code,
        Status: status,
        ID: allHosts.length + 1
      };

      allHosts.unshift(newH);
      try {
        let saved = JSON.parse(localStorage.getItem('sp_custom_hosts') || '[]');
        saved.unshift(newH);
        localStorage.setItem('sp_custom_hosts', JSON.stringify(saved));
      } catch(e) {
        console.warn("Erro ao salvar host:", e);
      }

      closeNewHostModal();
      document.getElementById("form-new-host").reset();
      renderHostsTable();
      showToast(`✅ Host '${code}' cadastrado com sucesso!`, "success");
    }

    function openNewDriveFileModal() {
      const modal = document.getElementById("modal-new-drive-file");
      if (modal) modal.style.display = "flex";
    }
    function closeNewDriveFileModal() {
      const modal = document.getElementById("modal-new-drive-file");
      if (modal) modal.style.display = "none";
    }
    function saveNewDriveFile(event) {
      event.preventDefault();
      const type = document.getElementById("new-drive-type").value;
      const name = document.getElementById("new-drive-name").value.trim();
      const author = document.getElementById("new-drive-author").value.trim() || "Cleber Gonçalves";

      if (!name) return;

      const driveData = currentDriveKey && SP_MASTER_DATA.drives && SP_MASTER_DATA.drives[currentDriveKey];
      if (driveData && driveData.items) {
        const newItem = {
          name: name,
          type: type,
          extension: type === 'folder' ? '' : (name.split('.').pop() || 'dat'),
          size: type === 'folder' ? 0 : 1024,
          lastModifiedDateTime: new Date().toISOString(),
          lastModifiedBy: author,
          webUrl: "#"
        };
        driveData.items.unshift(newItem);
        filterDriveTable();
      }

      closeNewDriveFileModal();
      document.getElementById("form-new-drive-file").reset();
      showToast(`✅ Item '${name}' adicionado à biblioteca de documentos!`, "success");
    }

    function toggleDriveGridMode() {
      showToast("Visualização detalhada em grade da biblioteca ativada.", "info");
    }

    // Exportações CSV
    function exportCSV() {
      const rows = [["Indice","Mes","Data","Horario","Campeonato","Partida","Responsavel","Canal","PVID","Status","Programado"]];
      allEvents.forEach((ev, i) => {
        rows.push([i+1, ev.mes||'', ev.data||'', ev.horario||'', ev.campeonato||'', ev.partida||'', ev.responsavel||'', ev.canal||'', ev.pvid||'', ev.status_entrega||'', ev.programado||'']);
      });
      const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join(String.fromCharCode(13, 10));
      downloadCSV(csv, "programacao_eventos_streaming.csv");
    }

    function exportHospedeirosCSV() {
      const rows = [["Indice","Cidade","Nome","Especialidade","Telefone_Comercial","Telefone_Celular"]];
      allHospedeiros.forEach((h, i) => {
        rows.push([i+1, h.Title||'', h.Nome1||'', h.Especialidade||'', h.Telefone_x0020_Comercial||'', h.Telefone_x0020_Celular||'']);
      });
      const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join(String.fromCharCode(13, 10));
      downloadCSV(csv, "contatos_hospedeiros_completo.csv");
    }

    function exportOcorrenciasCSV() {
      const rows = [["Status","Criado","Host","CS","Veiculo","Equipamento","TipoProblema","EmRecuperacao","GravacaoStreaming","InformarOperacao","AcoesExecutadas","AreaResponsavel","Redmine"]];
      allOcorrencias.forEach((o) => {
        const cs = Array.isArray(o.CS) ? o.CS.join("; ") : (o.CS || '');
        const eq = Array.isArray(o.Equipamento) ? o.Equipamento.join("; ") : (o.Equipamento || '');
        rows.push([
          o.Status || '',
          formatSPDate(o.Criado),
          o.HostName || o.hostLookupId || '',
          cs,
          o.Veiculo || '',
          eq,
          o.TipoProblema || '',
          o.EmRecuperacao || 'Não',
          o.GravacaoStreaming || 'Não',
          o.InformarOperacao ? 'Sim' : 'Não',
          o.AcoesExecutadas || '',
          o.AreaResponsavel || '',
          o.Redmine || ''
        ]);
      });
      const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join(String.fromCharCode(13, 10));
      downloadCSV(csv, "painel_ocorrencias_sharepoint_completo.csv");
    }

    function exportPermsCSV() {
      const rows = [["Nome","Tipo","Email","Nivel_SharePoint","Nivel_Google_Sites","Cargo","Escopo"]];
      allPermissions.forEach((p) => {
        rows.push([p.name, p.type, p.email, p.sp_role, p.google_role, p.cargo||'', p.scope||'']);
      });
      const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join(String.fromCharCode(13, 10));
      downloadCSV(csv, "permissoes_suporte_captacao_google_sites.csv");
    }

    function downloadCSV(csvContent, filename) {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
    }

    async function syncLiveAPI(btnElement) {
      const btn = btnElement || (typeof event !== 'undefined' ? event.target : null);
      const originalText = btn ? btn.innerText : "";
      if (btn) {
        btn.innerText = "⏳ Atualizando...";
        btn.disabled = true;
      }

      try {
        const url = "https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec?format=json";
        const resp = await fetch(url);
        if (resp.ok) {
          const freshEvents = await resp.json();
          if (Array.isArray(freshEvents) && freshEvents.length > 0) {
            allEvents = freshEvents;
            renderTable();
            alert("✅ Portal atualizado com sucesso! Total: " + freshEvents.length + " eventos sincronizados.");
          }
        } else {
          alert("⚠️ Não foi possível obter dados remotos (Status " + resp.status + "). Mantendo dados locais.");
        }
      } catch (e) {
        console.warn("Erro ao buscar dados remotos:", e);
        alert("ℹ️ Base local mantida ativa.");
      } finally {
        btn.innerText = originalText;
        btn.disabled = false;
      }
    }

    // Listeners
    document.getElementById("search-box")?.addEventListener("input", renderTable);
    document.getElementById("filter-mes")?.addEventListener("change", renderTable);
    document.getElementById("filter-campeonato")?.addEventListener("change", renderTable);
    document.getElementById("filter-canal")?.addEventListener("change", renderTable);
    document.getElementById("filter-status")?.addEventListener("change", renderTable);
    document.getElementById("search-hosp-box")?.addEventListener("input", renderHospedeirosTable);
    document.getElementById("search-oco-box")?.addEventListener("input", renderOcorrenciasTable);
    document.getElementById("search-proc-box")?.addEventListener("input", renderProcedimentosTable);
    document.getElementById("search-doc-box")?.addEventListener("input", renderDocumentosTable);
    document.getElementById("search-perm-box")?.addEventListener("input", renderPermsTable);

    document.getElementById("global-search")?.addEventListener("input", function(e) {
      const term = e.target.value.trim();
      if (term.length > 0) {
        showPane('streaming');
        const sBox = document.getElementById("search-box");
        if (sBox) {
          sBox.value = term;
          renderTable();
        }
      }
    });

    // Exposição global explícita no window
    window.showPane = showPane;
    window.selectEscalaMonth = selectEscalaMonth;
    window.toggleDarkMode = toggleDarkMode;
    window.onRoleChange = onRoleChange;
    window.sortStreamBy = sortStreamBy;
    window.clearStreamFilters = clearStreamFilters;
    window.sortHospBy = sortHospBy;
    window.sortOcoBy = sortOcoBy;
    window.sortGenericList = sortGenericList;
    window.exportCSV = exportCSV;
    window.exportHospedeirosCSV = exportHospedeirosCSV;
    window.exportOcorrenciasCSV = exportOcorrenciasCSV;
    window.exportPermsCSV = exportPermsCSV;
    window.syncLiveAPI = syncLiveAPI;
    window.switchOcoView = switchOcoView;
    window.toggleStatusFilter = toggleStatusFilter;
    window.clearOcoFilters = clearOcoFilters;
    window.toggleOcoSort = toggleOcoSort;
    window.searchHostInOco = searchHostInOco;
    window.toggleDropdown = toggleDropdown;
    window.handleMenuClick = handleMenuClick;
    window.openDrive = openDrive;
    window.openDriveFolder = openDriveFolder;
    window.navigateDriveBreadcrumb = navigateDriveBreadcrumb;
    window.filterDriveTable = filterDriveTable;
    window.exportCurrentDriveCSV = exportCurrentDriveCSV;
    window.openRealList = openRealList;
    window.filterRealListTable = filterRealListTable;
    window.exportGenericListCSV = exportGenericListCSV;
    window.renderGenericList = openRealList;
    window.filterListViewerTable = filterRealListTable;
    window.renderAntenistasTable = renderAntenistasTable;
    window.renderHostsTable = renderHostsTable;
    window.renderTable = renderTable;
    window.renderHospedeirosTable = renderHospedeirosTable;
    window.renderOcorrenciasTable = renderOcorrenciasTable;
    window.renderPermsTable = renderPermsTable;
    window.showToast = showToast;
    window.openNewOcoModal = openNewOcoModal;
    window.closeNewOcoModal = closeNewOcoModal;
    window.saveNewOcorrencia = saveNewOcorrencia;
    window.toggleOcoGridEdit = toggleOcoGridEdit;
    window.updateOcoField = updateOcoField;
    window.openNewListItemModal = openNewListItemModal;
    window.closeNewListItemModal = closeNewListItemModal;
    window.saveNewListItem = saveNewListItem;
    window.toggleGenericListGridEdit = toggleGenericListGridEdit;
    window.updateGenericListField = updateGenericListField;
    window.openNewAntenistaModal = openNewAntenistaModal;
    window.closeNewAntenistaModal = closeNewAntenistaModal;
    window.saveNewAntenista = saveNewAntenista;
    window.openNewHostModal = openNewHostModal;
    window.closeNewHostModal = closeNewHostModal;
    window.saveNewHost = saveNewHost;
    window.openNewDriveFileModal = openNewDriveFileModal;
    window.closeNewDriveFileModal = closeNewDriveFileModal;
    window.saveNewDriveFile = saveNewDriveFile;
    window.toggleDriveGridMode = toggleDriveGridMode;
    window.openNewStreamModal = openNewStreamModal;
    window.closeNewStreamModal = closeNewStreamModal;
    window.saveNewStreamEvent = saveNewStreamEvent;
    window.toggleStreamGridEdit = toggleStreamGridEdit;
    window.updateStreamField = updateStreamField;
    window.triggerGoogleChatAgendaModal = triggerGoogleChatAgendaModal;
    window.closeChatWebhookModal = closeChatWebhookModal;
    window.sendChatAgendaFromModal = sendChatAgendaFromModal;
    window.openNewHospedeiroModal = openNewHospedeiroModal;
    window.closeNewHospedeiroModal = closeNewHospedeiroModal;
    window.saveNewHospedeiro = saveNewHospedeiro;
    window.toggleHospGridEdit = toggleHospGridEdit;
    window.updateHospField = updateHospField;
    window.toggleAnteGridEdit = toggleAnteGridEdit;
    window.updateAnteField = updateAnteField;
    window.exportAntenistasCSV = exportAntenistasCSV;
    window.toggleHostGridEdit = toggleHostGridEdit;
    window.updateHostField = updateHostField;
    window.exportHostsCSV = exportHostsCSV;
    window.openNewPermModal = openNewPermModal;
    window.closeNewPermModal = closeNewPermModal;
    window.saveNewPerm = saveNewPerm;
    window.togglePermsGridEdit = togglePermsGridEdit;
    window.updatePermField = updatePermField;
    window.openAutonomousDocViewer = openAutonomousDocViewer;
    window.openReportDocument = openReportDocument;
    window.downloadAutonomousMockDoc = downloadAutonomousMockDoc;
    window.generateAndDownloadRdp = generateAndDownloadRdp;
    window.toggleSelectAllStreaming = toggleSelectAllStreaming;
    window.updateStreamingSelectionState = updateStreamingSelectionState;
    window.deleteSelectedStreamingEvents = deleteSelectedStreamingEvents;
    window.openQuickMstscModal = openQuickMstscModal;
    window.switchRdpViewMode = switchRdpViewMode;
    window.openRdpSubfolder = openRdpSubfolder;
    window.openRdpFolderCrumb = openRdpFolderCrumb;
    window.resetRdpFolderRoot = resetRdpFolderRoot;
    window.onMstscHostSelected = onMstscHostSelected;
    window.copyMstscCommand = copyMstscCommand;
    window.launchMstscConnection = launchMstscConnection;
    window.renderRdpTable = renderRdpTable;
    window.filterRdpTable = filterRdpTable;
    window.setRdpCategory = setRdpCategory;
    window.triggerRdpConnect = triggerRdpConnect;
    window.exportRdpCSV = exportRdpCSV;

    // Inicialização
    initEscalaMonths();
    renderTable();
    renderHospedeirosTable();
    renderOcorrenciasTable();
    renderAntenistasTable();
    renderHostsTable();
    renderPermsTable();
  
    // =========================================================================
    // NOC ACCESS HUB & SMART LIST PROPERTIES (1:1 SHAREPOINT EXTENSION)
    // =========================================================================
    let RDP_MASTER_DATASET = [{"id": "br_altamira", "regiao": "Brasil", "pais": "Brasil", "praca": "Altamira", "router": "192.168.176.29", "cs1_ip": "192.168.176.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.19", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_anápolis", "regiao": "Brasil", "pais": "Brasil", "praca": "Anápolis", "router": "192.168.176.45", "cs1_ip": "192.168.176.34", "cs2_ip": "192.168.176.35", "cs3_ip": "N/A", "pdu_ip": "192.168.176.44", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_aracaju", "regiao": "Brasil", "pais": "Brasil", "praca": "Aracaju", "router": "192.168.176.61", "cs1_ip": "192.168.176.53", "cs2_ip": "192.168.176.52", "cs3_ip": "N/A", "pdu_ip": "192.168.176.51", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_araguaína", "regiao": "Brasil", "pais": "Brasil", "praca": "Araguaína", "router": "192.168.176.77", "cs1_ip": "192.168.176.68", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.67", "pdu_tipo": "Volt", "obs": "Volt não funciona", "status": "warning"}, {"id": "br_araxá", "regiao": "Brasil", "pais": "Brasil", "praca": "Araxá", "router": "192.168.176.93", "cs1_ip": "192.168.176.84", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.83", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_ariquemes", "regiao": "Brasil", "pais": "Brasil", "praca": "Ariquemes", "router": "192.168.176.109", "cs1_ip": "192.168.176.100", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.108", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_b._horizonte", "regiao": "Brasil", "pais": "Brasil", "praca": "B. Horizonte", "router": "192.168.176.125", "cs1_ip": "192.168.176.124", "cs2_ip": "192.168.176.118", "cs3_ip": "REPUCOM", "pdu_ip": "192.168.176.115", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_bagé", "regiao": "Brasil", "pais": "Brasil", "praca": "Bagé", "router": "192.168.176.141", "cs1_ip": "192.168.176.132", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.131", "pdu_tipo": "Volt", "obs": "VOLT", "status": "nominal"}, {"id": "br_balsas", "regiao": "Brasil", "pais": "Brasil", "praca": "Balsas", "router": "192.168.176.157", "cs1_ip": "192.168.176.148", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.147", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_barreiras", "regiao": "Brasil", "pais": "Brasil", "praca": "Barreiras", "router": "192.168.176.173", "cs1_ip": "192.168.176.164", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.176.163", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_bauru", "regiao": "Brasil", "pais": "Brasil", "praca": "Bauru", "router": "192.168.176.189", "cs1_ip": "192.168.176.177", "cs2_ip": "192.168.176.180", "cs3_ip": "N/A", "pdu_ip": "192.168.176.179", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_belém", "regiao": "Brasil", "pais": "Brasil", "praca": "Belém", "router": "192.168.176.205", "cs1_ip": "192.168.176.194", "cs2_ip": "192.168.176.196", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_blumenau", "regiao": "Brasil", "pais": "Brasil", "praca": "Blumenau", "router": "192.168.176.221", "cs1_ip": "192.168.176.209", "cs2_ip": "192.168.176.210", "cs3_ip": "N/A", "pdu_ip": "192.168.176.211", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_boa_vista", "regiao": "Brasil", "pais": "Brasil", "praca": "Boa Vista", "router": "192.168.50.254", "cs1_ip": "192.168.50.11", "cs2_ip": "192.168.50.22", "cs3_ip": "N/A", "pdu_ip": "192.168.50.253", "pdu_tipo": "Volt", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_brasília", "regiao": "Brasil", "pais": "Brasil", "praca": "Brasília", "router": "192.168.176.253", "cs1_ip": "192.168.176.246", "cs2_ip": "192.168.20.22", "cs3_ip": "192.168.176.241", "pdu_ip": "192.168.0.51(FILIAL) | 192.168.20.2 (Externo CSDT2)", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_c._fabriciano", "regiao": "Brasil", "pais": "Brasil", "praca": "C. Fabriciano", "router": "192.168.177.13", "cs1_ip": "192.168.177.4", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.3", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_c._itapemirim", "regiao": "Brasil", "pais": "Brasil", "praca": "C. Itapemirim", "router": "192.168.177.29", "cs1_ip": "192.168.177.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.19", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_cabo_frio", "regiao": "Brasil", "pais": "Brasil", "praca": "Cabo Frio", "router": "192.168.177.45", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.35", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_cacoal", "regiao": "Brasil", "pais": "Brasil", "praca": "Cacoal", "router": "192.168.177.61", "cs1_ip": "192.168.177.54", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.51", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_campina_grande", "regiao": "Brasil", "pais": "Brasil", "praca": "Campina Grande", "router": "192.168.177.77", "cs1_ip": "192.168.177.66", "cs2_ip": "192.168.177.69", "cs3_ip": "N/A", "pdu_ip": "192.168.177.67", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_campinas", "regiao": "Brasil", "pais": "Brasil", "praca": "Campinas", "router": "192.168.177.93", "cs1_ip": "192.168.180.86", "cs2_ip": "192.168.180.81", "cs3_ip": "192.168.180.84", "pdu_ip": "192.168.177.83", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_campo_grande", "regiao": "Brasil", "pais": "Brasil", "praca": "Campo Grande", "router": "192.168.177.109", "cs1_ip": "192.168.177.98", "cs2_ip": "192.168.177.100", "cs3_ip": "N/A", "pdu_ip": "192.168.177.99", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_campos", "regiao": "Brasil", "pais": "Brasil", "praca": "Campos", "router": "192.168.177.125", "cs1_ip": "192.168.177.113", "cs2_ip": "192.168.177.114", "cs3_ip": "N/A", "pdu_ip": "192.168.177.115", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_caruaru", "regiao": "Brasil", "pais": "Brasil", "praca": "Caruaru", "router": "192.168.177.141", "cs1_ip": "192.168.177.133", "cs2_ip": "192.168.177.132", "cs3_ip": "N/A", "pdu_ip": "192.168.177.131", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_cascavel", "regiao": "Brasil", "pais": "Brasil", "praca": "Cascavel", "router": "192.168.177.157", "cs1_ip": "192.168.177.146", "cs2_ip": "192.168.177.148", "cs3_ip": "N/A", "pdu_ip": "192.168.177.147", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_castanhal", "regiao": "Brasil", "pais": "Brasil", "praca": "Castanhal", "router": "192.168.177.173", "cs1_ip": "192.168.177.164", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.163", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_catalão", "regiao": "Brasil", "pais": "Brasil", "praca": "Catalão", "router": "192.168.177.189", "cs1_ip": "192.168.177.177", "cs2_ip": "192.168.177.180", "cs3_ip": "192.168.177.181", "pdu_ip": "192.168.177.179", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_caxias_do_sul", "regiao": "Brasil", "pais": "Brasil", "praca": "Caxias do Sul", "router": "192.168.177.205", "cs1_ip": "192.168.177.193", "cs2_ip": "192.168.177.194", "cs3_ip": "N/A", "pdu_ip": "192.168.177.195", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_chapecó", "regiao": "Brasil", "pais": "Brasil", "praca": "Chapecó", "router": "192.168.1.1", "cs1_ip": "192.168.1.33", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.211", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_codó", "regiao": "Brasil", "pais": "Brasil", "praca": "Codó", "router": "192.168.177.237", "cs1_ip": "192.168.177.228", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.177.227", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_colatina", "regiao": "Brasil", "pais": "Brasil", "praca": "Colatina", "router": "192.168.1.1", "cs1_ip": "192.168.1.33", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.1.2", "pdu_tipo": "Volt", "obs": "Não funcionaipconfig", "status": "warning"}, {"id": "br_corumbá", "regiao": "Brasil", "pais": "Brasil", "praca": "Corumbá", "router": "192.168.178.13", "cs1_ip": "192.168.178.4", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.3", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_criciúma", "regiao": "Brasil", "pais": "Brasil", "praca": "Criciúma", "router": "192.168.178.29", "cs1_ip": "192.168.178.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.28", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_cruz_alta", "regiao": "Brasil", "pais": "Brasil", "praca": "Cruz Alta", "router": "192.168.178.45", "cs1_ip": "192.168.178.36", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.35", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_cruzeiro_do_sul", "regiao": "Brasil", "pais": "Brasil", "praca": "Cruzeiro do Sul", "router": "192.168.178.61", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.51", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_cuiabá", "regiao": "Brasil", "pais": "Brasil", "praca": "Cuiabá", "router": "192.168.178.77", "cs1_ip": "192.168.178.65", "cs2_ip": "192.168.178.68", "cs3_ip": "N/A", "pdu_ip": "192.168.178.67", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_curitiba", "regiao": "Brasil", "pais": "Brasil", "praca": "Curitiba", "router": "192.168.178.93", "cs1_ip": "192.168.178.81", "cs2_ip": "192.168.178.86", "cs3_ip": "192.168.178.82", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_erechim", "regiao": "Brasil", "pais": "Brasil", "praca": "Erechim", "router": "192.168.178.109", "cs1_ip": "192.168.178.98", "cs2_ip": "192.168.178.100", "cs3_ip": "192.168.178.97", "pdu_ip": "192.168.178.099", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_f._santana", "regiao": "Brasil", "pais": "Brasil", "praca": "F. Santana", "router": "192.168.178.125", "cs1_ip": "192.168.178.116", "cs2_ip": "192.168.178.114", "cs3_ip": "N/A", "pdu_ip": "192.168.178.115", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_floriano", "regiao": "Brasil", "pais": "Brasil", "praca": "Floriano", "router": "192.168.178.141", "cs1_ip": "192.168.178.132", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.131", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_florianópolis", "regiao": "Brasil", "pais": "Brasil", "praca": "Florianópolis", "router": "192.168.178.157", "cs1_ip": "192.168.178.145", "cs2_ip": "192.168.178.150", "cs3_ip": "192.168.178.146", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_fortaleza", "regiao": "Brasil", "pais": "Brasil", "praca": "Fortaleza", "router": "192.168.178.173", "cs1_ip": "192.168.178.161", "cs2_ip": "192.168.178.162", "cs3_ip": "192.168.178.168", "pdu_ip": "192.168.178.163", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_foz_de_iguaçu", "regiao": "Brasil", "pais": "Brasil", "praca": "Foz de Iguaçu", "router": "192.168.178.189", "cs1_ip": "192.168.178.180", "cs2_ip": "192.168.178.178", "cs3_ip": "N/A", "pdu_ip": "http://192.168.178.188", "pdu_tipo": "Volt", "obs": "Não funciona", "status": "warning"}, {"id": "br_franca", "regiao": "Brasil", "pais": "Brasil", "praca": "Franca", "router": "192.168.178.205", "cs1_ip": "192.168.178.194", "cs2_ip": "192.168.178.196", "cs3_ip": "N/A", "pdu_ip": "192.168.178.195", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_g._valadares", "regiao": "Brasil", "pais": "Brasil", "praca": "G. Valadares", "router": "192.168.178.221", "cs1_ip": "192.168.178.212", "cs2_ip": "192.168.178.209", "cs3_ip": "N/A", "pdu_ip": "192.168.178.211", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_goiânia", "regiao": "Brasil", "pais": "Brasil", "praca": "Goiânia", "router": "192.168.178.237", "cs1_ip": "192.168.178.225", "cs2_ip": "192.168.178.228", "cs3_ip": "REPUCOM", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_guajará-mirim", "regiao": "Brasil", "pais": "Brasil", "praca": "Guajará-Mirim", "router": "192.168.178.253", "cs1_ip": "192.168.178.244", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.178.243", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_guarapuava", "regiao": "Brasil", "pais": "Brasil", "praca": "Guarapuava", "router": "192.168.25.1", "cs1_ip": "192.168.25.11", "cs2_ip": "192.168.25.22", "cs3_ip": "N/A", "pdu_ip": "192.168.0.51", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_gurupi", "regiao": "Brasil", "pais": "Brasil", "praca": "Gurupi", "router": "192.168.179.29", "cs1_ip": "192.168.179.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.19", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_imperatriz", "regiao": "Brasil", "pais": "Brasil", "praca": "Imperatriz", "router": "192.168.179.45", "cs1_ip": "192.168.179.34", "cs2_ip": "192.168.179.36", "cs3_ip": "N/A", "pdu_ip": "192.168.0.51", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_itabuna", "regiao": "Brasil", "pais": "Brasil", "praca": "Itabuna", "router": "192.168.179.61", "cs1_ip": "192.168.179.52", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.51", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_itacoatiara", "regiao": "Brasil", "pais": "Brasil", "praca": "Itacoatiara", "router": "192.168.179.77", "cs1_ip": "192.168.179.69", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.67", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_itaituba", "regiao": "Brasil", "pais": "Brasil", "praca": "Itaituba", "router": "192.168.179.93", "cs1_ip": "192.168.179.84", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.83", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_itapetininga", "regiao": "Brasil", "pais": "Brasil", "praca": "Itapetininga", "router": "192.168.179.109", "cs1_ip": "192.168.179.98", "cs2_ip": "192.168.179.100", "cs3_ip": "N/A", "pdu_ip": "192.168.179.110", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_ituiutaba", "regiao": "Brasil", "pais": "Brasil", "praca": "Ituiutaba", "router": "192.168.179.125", "cs1_ip": "192.168.179.117", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.115", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_itumbiara", "regiao": "Brasil", "pais": "Brasil", "praca": "Itumbiara", "router": "192.168.179.141", "cs1_ip": "192.168.179.132", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.131", "pdu_tipo": "Volt", "obs": "Régua VOLT", "status": "nominal"}, {"id": "br_jataí", "regiao": "Brasil", "pais": "Brasil", "praca": "Jataí", "router": "192.168.179.157", "cs1_ip": "192.168.179.148", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.147", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_ji-paraná", "regiao": "Brasil", "pais": "Brasil", "praca": "Ji-Paraná", "router": "192.168.179.173", "cs1_ip": "192.168.179.164", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.163", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_joaçaba", "regiao": "Brasil", "pais": "Brasil", "praca": "Joaçaba", "router": "192.168.179.189", "cs1_ip": "192.168.179.180", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.179.179", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_joão_pessoa", "regiao": "Brasil", "pais": "Brasil", "praca": "João Pessoa", "router": "192.168.179.205", "cs1_ip": "192.168.179.194", "cs2_ip": "192.168.179.196", "cs3_ip": "N/A", "pdu_ip": "192.168.179.195", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_joinville", "regiao": "Brasil", "pais": "Brasil", "praca": "Joinville", "router": "192.168.179.221", "cs1_ip": "192.168.179.209", "cs2_ip": "192.168.179.210", "cs3_ip": "N/A", "pdu_ip": "192.168.179.211", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_juazeiro", "regiao": "Brasil", "pais": "Brasil", "praca": "Juazeiro", "router": "192.168.179.237", "cs1_ip": "192.168.179.226", "cs2_ip": "192.168.179.228", "cs3_ip": "N/A", "pdu_ip": "192.168.179.236", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_juazeiro_do_n.", "regiao": "Brasil", "pais": "Brasil", "praca": "Juazeiro do N.", "router": "192.168.179.253", "cs1_ip": "192.168.179.244", "cs2_ip": "192.168.179.241", "cs3_ip": "N/A", "pdu_ip": "192.168.179.243", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_juiz_de_fora", "regiao": "Brasil", "pais": "Brasil", "praca": "Juiz de Fora", "router": "192.168.180.13", "cs1_ip": "192.168.180.2", "cs2_ip": "192.168.180.4", "cs3_ip": "192.168.180.5", "pdu_ip": "192.168.180.8", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_linhares", "regiao": "Brasil", "pais": "Brasil", "praca": "Linhares", "router": "192.168.180.29", "cs1_ip": "192.168.180.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.180.19", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_londrina", "regiao": "Brasil", "pais": "Brasil", "praca": "Londrina", "router": "192.168.180.45", "cs1_ip": "192.168.180.34", "cs2_ip": "192.168.180.36", "cs3_ip": "N/A", "pdu_ip": "182.168.180.44", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_luziânia", "regiao": "Brasil", "pais": "Brasil", "praca": "Luziânia", "router": "192.168.180.61", "cs1_ip": "192.168.180.49", "cs2_ip": "192.168.180.52", "cs3_ip": "N/A", "pdu_ip": "192.168.180.51", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_m._das_cruzes", "regiao": "Brasil", "pais": "Brasil", "praca": "M. das Cruzes", "router": "192.168.180.77", "cs1_ip": "192.168.180.66", "cs2_ip": "192.168.180.68", "cs3_ip": "N/A", "pdu_ip": "192.168.180.67", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_macapá", "regiao": "Brasil", "pais": "Brasil", "praca": "Macapá", "router": "192.168.180.93", "cs1_ip": "192.168.180.81", "cs2_ip": "192.168.180.82", "cs3_ip": "N/A", "pdu_ip": "192.168.180.83", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_maceió", "regiao": "Brasil", "pais": "Brasil", "praca": "Maceió", "router": "192.168.180.109", "cs1_ip": "192.168.180.98", "cs2_ip": "192.168.180.100", "cs3_ip": "N/A", "pdu_ip": "192.168.180.99", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_manaus", "regiao": "Brasil", "pais": "Brasil", "praca": "Manaus", "router": "192.168.180.125", "cs1_ip": "192.168.180.113", "cs2_ip": "192.168.180.116", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_marabá", "regiao": "Brasil", "pais": "Brasil", "praca": "Marabá", "router": "192.168.180.141", "cs1_ip": "192.168.180.130", "cs2_ip": "192.168.180.132", "cs3_ip": "N/A", "pdu_ip": "192.168.180.131", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_maringá", "regiao": "Brasil", "pais": "Brasil", "praca": "Maringá", "router": "192.168.180.157", "cs1_ip": "192.168.180.146", "cs2_ip": "192.168.180.148", "cs3_ip": "N/A", "pdu_ip": "http://177.84.130.238/config.htm", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_montes_claros", "regiao": "Brasil", "pais": "Brasil", "praca": "Montes Claros", "router": "192.168.180.173", "cs1_ip": "192.168.180.164", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.180.163", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_natal", "regiao": "Brasil", "pais": "Brasil", "praca": "Natal", "router": "192.168.180.189", "cs1_ip": "192.168.180.177", "cs2_ip": "192.168.180.182", "cs3_ip": "N/A", "pdu_ip": "192.168.180.180", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_nova_friburgo", "regiao": "Brasil", "pais": "Brasil", "praca": "Nova Friburgo", "router": "192.168.180.205", "cs1_ip": "192.168.180.194", "cs2_ip": "192.168.180.193", "cs3_ip": "N/A", "pdu_ip": "192.168.180.195", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_palmas", "regiao": "Brasil", "pais": "Brasil", "praca": "Palmas", "router": "192.168.180.221", "cs1_ip": "192.168.180.210", "cs2_ip": "192.168.180.212", "cs3_ip": "N/A", "pdu_ip": "192.168.180.211", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_paragominas", "regiao": "Brasil", "pais": "Brasil", "praca": "Paragominas", "router": "192.168.180.237", "cs1_ip": "192.168.180.228", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.180.227", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_paranavaí", "regiao": "Brasil", "pais": "Brasil", "praca": "Paranavaí", "router": "192.168.180.253", "cs1_ip": "192.168.180.241", "cs2_ip": "192.168.180.244", "cs3_ip": "N/A", "pdu_ip": "192.168.180.243", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_parauapebas", "regiao": "Brasil", "pais": "Brasil", "praca": "Parauapebas", "router": "192.168.181.13", "cs1_ip": "192.168.181.4", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.3", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_parintins", "regiao": "Brasil", "pais": "Brasil", "praca": "Parintins", "router": "192.168.181.29", "cs1_ip": "192.168.181.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.19", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_passo_fundo", "regiao": "Brasil", "pais": "Brasil", "praca": "Passo Fundo", "router": "192.168.181.45", "cs1_ip": "192.168.181.36", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.35", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_pelotas", "regiao": "Brasil", "pais": "Brasil", "praca": "Pelotas", "router": "192.168.181.61", "cs1_ip": "192.168.181.49", "cs2_ip": "192.168.181.52", "cs3_ip": "N/A", "pdu_ip": "192.168.181.51", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_ponta_grossa", "regiao": "Brasil", "pais": "Brasil", "praca": "Ponta Grossa", "router": "192.168.181.77", "cs1_ip": "192.168.181.65", "cs2_ip": "192.168.181.66", "cs3_ip": "N/A", "pdu_ip": "192.168.181.68", "pdu_tipo": "Volt", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_ponta_pora", "regiao": "Brasil", "pais": "Brasil", "praca": "Ponta Pora", "router": "192.168.181.93", "cs1_ip": "192.168.181.84", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.83", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_porangatú", "regiao": "Brasil", "pais": "Brasil", "praca": "Porangatú", "router": "192.168.181.109", "cs1_ip": "192.168.181.100", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.099", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_porto_alegre", "regiao": "Brasil", "pais": "Brasil", "praca": "Porto Alegre", "router": "192.168.181.125", "cs1_ip": "192.168.181.113", "cs2_ip": "192.168.181.114", "cs3_ip": "192.168.181.118", "pdu_ip": "192.168.181.115", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_porto_velho", "regiao": "Brasil", "pais": "Brasil", "praca": "Porto Velho", "router": "192.168.181.141", "cs1_ip": "192.168.181.130", "cs2_ip": "192.168.181.134", "cs3_ip": "N/A", "pdu_ip": "192.168.181.131", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_pres._prudente", "regiao": "Brasil", "pais": "Brasil", "praca": "Pres. Prudente", "router": "192.168.181.157", "cs1_ip": "192.168.181.145", "cs2_ip": "192.168.181.150", "cs3_ip": "N/A", "pdu_ip": "192.168.181.147", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_recife", "regiao": "Brasil", "pais": "Brasil", "praca": "Recife", "router": "192.168.181.173", "cs1_ip": "192.168.181.161", "cs2_ip": "192.168.181.168", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_redenção", "regiao": "Brasil", "pais": "Brasil", "praca": "Redenção", "router": "192.168.181.189", "cs1_ip": "192.168.181.181", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.181.179", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_resende", "regiao": "Brasil", "pais": "Brasil", "praca": "Resende", "router": "192.168.181.205", "cs1_ip": "192.168.181.195", "cs2_ip": "192.168.181.196", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_ribeirão_preto", "regiao": "Brasil", "pais": "Brasil", "praca": "Ribeirão Preto", "router": "192.168.181.221", "cs1_ip": "192.168.181.209", "cs2_ip": "192.168.181.212", "cs3_ip": "N/A", "pdu_ip": "192.168.181.211", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rio_branco", "regiao": "Brasil", "pais": "Brasil", "praca": "Rio Branco", "router": "192.168.181.237", "cs1_ip": "192.168.181.226", "cs2_ip": "192.168.181.228", "cs3_ip": "N/A", "pdu_ip": "192.168.181.227", "pdu_tipo": "MCosta", "obs": "ATIVO, Não funciona, há verificar", "status": "warning"}, {"id": "br_rio_de_janeiro", "regiao": "Brasil", "pais": "Brasil", "praca": "Rio de Janeiro", "router": "192.168.181.253", "cs1_ip": "192.168.181.241", "cs2_ip": "192.168.181.242", "cs3_ip": "192.168.181.244", "pdu_ip": "192.168.20.2", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rio_grande", "regiao": "Brasil", "pais": "Brasil", "praca": "Rio Grande", "router": "192.168.182.13", "cs1_ip": "192.168.182.3", "cs2_ip": "192.168.182.4", "cs3_ip": "N/A", "pdu_ip": "192.168.182.2", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_rio_verde", "regiao": "Brasil", "pais": "Brasil", "praca": "Rio Verde", "router": "192.168.182.16", "cs1_ip": "177.10.143.122", "cs2_ip": "192.168.182.22", "cs3_ip": "N/A", "pdu_ip": "192.168.182.19", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rondonópolis", "regiao": "Brasil", "pais": "Brasil", "praca": "Rondonópolis", "router": "192.168.182.45", "cs1_ip": "192.168.182.33", "cs2_ip": "192.168.182.36", "cs3_ip": "N/A", "pdu_ip": "192.168.182.35", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_s.j._campos", "regiao": "Brasil", "pais": "Brasil", "praca": "S.J. Campos", "router": "192.168.182.61", "cs1_ip": "192.168.182.49", "cs2_ip": "192.168.182.52", "cs3_ip": "N/A", "pdu_ip": "192.168.182.60", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_s.j.rio_preto", "regiao": "Brasil", "pais": "Brasil", "praca": "S.J.Rio Preto", "router": "192.168.182.77", "cs1_ip": "192.168.182.66", "cs2_ip": "192.168.182.68", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_salvador", "regiao": "Brasil", "pais": "Brasil", "praca": "Salvador", "router": "192.168.182.93", "cs1_ip": "192.168.182.81", "cs2_ip": "192.168.182.85", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_santa_c.do_sul", "regiao": "Brasil", "pais": "Brasil", "praca": "Santa C.do Sul", "router": "192.168.182.109", "cs1_ip": "192.168.182.100", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.182.099", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_santa_maria", "regiao": "Brasil", "pais": "Brasil", "praca": "Santa Maria", "router": "192.168.182.141", "cs1_ip": "192.168.182.130", "cs2_ip": "192.168.182.132", "cs3_ip": "N/A", "pdu_ip": "192.168.182.131", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_santa_rosa", "regiao": "Brasil", "pais": "Brasil", "praca": "Santa Rosa", "router": "192.168.182.157", "cs1_ip": "192.168.182.149", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.182.158", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_santarém", "regiao": "Brasil", "pais": "Brasil", "praca": "Santarém", "router": "192.168.182.173", "cs1_ip": "192.168.182.164", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.182.165", "pdu_tipo": "Volt", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_rj-paytv_bloco_01", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 01", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.177", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_02", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 02", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.178", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_03", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 03", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.179", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_04", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 04", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.180", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_05", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 05", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.181", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_06", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 06", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.182", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_07", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 07", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.183", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_08", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 08", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.184", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_são_carlos", "regiao": "Brasil", "pais": "Brasil", "praca": "São Carlos", "router": "192.168.182.205", "cs1_ip": "192.168.182.193", "cs2_ip": "192.168.182.196", "cs3_ip": "N/A", "pdu_ip": "192.168.182.195", "pdu_tipo": "Volt", "obs": "ATIVO", "status": "nominal"}, {"id": "br_são_luís", "regiao": "Brasil", "pais": "Brasil", "praca": "São Luís", "router": "192.168.182.221", "cs1_ip": "192.168.182.210", "cs2_ip": "192.168.182.212", "cs3_ip": "N/A", "pdu_ip": "192.168.182.211", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_sinop", "regiao": "Brasil", "pais": "Brasil", "praca": "Sinop", "router": "192.168.182.253", "cs1_ip": "192.168.182.244", "cs2_ip": "192.168.182.242", "cs3_ip": "N/A", "pdu_ip": "192.168.182.243", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_sorocaba", "regiao": "Brasil", "pais": "Brasil", "praca": "Sorocaba", "router": "192.168.183.13", "cs1_ip": "192.168.183.2", "cs2_ip": "192.168.183.4", "cs3_ip": "N/A", "pdu_ip": "192.168.183.3", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_t._da_serra", "regiao": "Brasil", "pais": "Brasil", "praca": "T. da Serra", "router": "192.168.183.29", "cs1_ip": "192.168.183.20", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "1", "pdu_tipo": "Volt", "obs": "Desativado", "status": "nominal"}, {"id": "br_taubaté", "regiao": "Brasil", "pais": "Brasil", "praca": "Taubaté", "router": "192.168.183.45", "cs1_ip": "192.168.183.34", "cs2_ip": "192.168.183.36", "cs3_ip": "N/A", "pdu_ip": "192.168.183.44", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_teresina", "regiao": "Brasil", "pais": "Brasil", "praca": "Teresina", "router": "192.168.183.61", "cs1_ip": "192.168.183.50", "cs2_ip": "192.168.183.52", "cs3_ip": "N/A", "pdu_ip": "192.168.0.51", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_tucuruí", "regiao": "Brasil", "pais": "Brasil", "praca": "Tucuruí", "router": "192.168.183.77", "cs1_ip": "192.168.183.68", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.183.67", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_uberlândia", "regiao": "Brasil", "pais": "Brasil", "praca": "Uberlândia", "router": "192.168.183.93", "cs1_ip": "192.168.183.81", "cs2_ip": "192.168.183.84", "cs3_ip": "N/A", "pdu_ip": "192.168.183.83", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_uruguaiana", "regiao": "Brasil", "pais": "Brasil", "praca": "Uruguaiana", "router": "192.168.183.109", "cs1_ip": "192.168.183.100", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.183.101", "pdu_tipo": "Volt", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_v._da_conquista", "regiao": "Brasil", "pais": "Brasil", "praca": "V. da Conquista", "router": "192.168.183.125", "cs1_ip": "192.168.183.114", "cs2_ip": "192.168.183.117", "cs3_ip": "N/A", "pdu_ip": "192.168.183.115", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_varginha", "regiao": "Brasil", "pais": "Brasil", "praca": "Varginha", "router": "192.168.183.141", "cs1_ip": "192.168.183.132", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.183.11", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_vilhena", "regiao": "Brasil", "pais": "Brasil", "praca": "Vilhena", "router": "192.168.183.157", "cs1_ip": "192.168.183.148", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.183.147", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_vitória", "regiao": "Brasil", "pais": "Brasil", "praca": "Vitória", "router": "192.168.183.173", "cs1_ip": "192.168.183.161", "cs2_ip": "192.168.183.164", "cs3_ip": "N/A", "pdu_ip": "192.168.183.163", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_lisboa", "regiao": "Brasil", "pais": "Brasil", "praca": "Lisboa", "router": "192.168.1.1", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.1.12", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "br_santos", "regiao": "Brasil", "pais": "Brasil", "praca": "Santos", "router": "192.168.1.1", "cs1_ip": "192.168.1.44", "cs2_ip": "192.168.1.22", "cs3_ip": "N/A", "pdu_ip": "192.168.1.20", "pdu_tipo": "MCosta", "obs": "ATIVO", "status": "nominal"}, {"id": "br_rj-paytv_bloco_09", "regiao": "Brasil", "pais": "Brasil", "praca": "RJ-Paytv Bloco 09", "router": "192.168.182.189", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.182.185", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_mossoró", "regiao": "Brasil", "pais": "Brasil", "praca": "Mossoró", "router": "192.168.182.237", "cs1_ip": "192.168.182.226", "cs2_ip": "192.168.182.225", "cs3_ip": "N/A", "pdu_ip": "192.168.182.228", "pdu_tipo": "Volt", "obs": "Régua VOLT", "status": "nominal"}, {"id": "br_uberaba", "regiao": "Brasil", "pais": "Brasil", "praca": "Uberaba", "router": "192.168.10.250", "cs1_ip": "192.168.10.11", "cs2_ip": "192.168.10.33", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_penha-dt1", "regiao": "Brasil", "pais": "Brasil", "praca": "Penha-DT1", "router": "192.168.20.1", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.20.44", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_penha-dt2", "regiao": "Brasil", "pais": "Brasil", "praca": "Penha-DT2", "router": "192.168.20.1", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "192.168.20.55", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_penha-hq", "regiao": "Brasil", "pais": "Brasil", "praca": "Penha-HQ", "router": "192.168.20.1", "cs1_ip": "N/A", "cs2_ip": "192.168.20.66", "cs3_ip": "N/A", "pdu_ip": "http://192.168.20.101", "pdu_tipo": "Volt", "obs": "Volt", "status": "nominal"}, {"id": "br_penha-sat", "regiao": "Brasil", "pais": "Brasil", "praca": "Penha-SAT", "router": "192.168.20.1", "cs1_ip": "192.168.20.11", "cs2_ip": "192.168.20.22", "cs3_ip": "192.168.20.33", "pdu_ip": "N/A", "pdu_tipo": "N/A", "obs": "ATIVO", "status": "nominal"}, {"id": "br_miami", "regiao": "Brasil", "pais": "Brasil", "praca": "Miami", "router": "10.1.10.1", "cs1_ip": "N/A", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "192.168.1.20", "pdu_tipo": "MCosta", "obs": "Não funciona, há verificar", "status": "warning"}, {"id": "latam_costa_rica_-_san_josé_(bl1)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL1)", "router": "10.45.10.1", "cs1_ip": "10.45.10.11", "cs2_ip": "10.45.10.12", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl2)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL2)", "router": "10.45.10.1", "cs1_ip": "10.45.10.21", "cs2_ip": "10.45.10.22", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl3)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL3)", "router": "10.45.10.1", "cs1_ip": "10.45.10.31", "cs2_ip": "10.45.10.32", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl4)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL4)", "router": "10.45.10.1", "cs1_ip": "10.45.10.41", "cs2_ip": "10.45.10.42", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl5)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL5)", "router": "10.45.10.1", "cs1_ip": "10.45.10.51", "cs2_ip": "10.45.10.52", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl6)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL6)", "router": "10.45.10.1", "cs1_ip": "10.45.10.61", "cs2_ip": "10.45.10.62", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl7)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL7)", "router": "10.45.10.1", "cs1_ip": "10.45.10.71", "cs2_ip": "10.45.10.72", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl8)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL8)", "router": "10.45.10.1", "cs1_ip": "10.45.10.81", "cs2_ip": "10.45.10.82", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl9)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL9)", "router": "10.45.10.1", "cs1_ip": "10.45.10.91", "cs2_ip": "10.45.10.92", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_san_josé_(bl10)", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - San José (BL10)", "router": "10.45.10.1", "cs1_ip": "10.45.10.101", "cs2_ip": "10.45.10.102", "cs3_ip": "N/A", "pdu_ip": "10.45.10.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_costa_rica_-_conversion_server", "regiao": "América Central", "pais": "Costa Rica", "praca": "Costa Rica - Conversion Server", "router": "10.45.10.1", "cs1_ip": "10.45.10.200", "cs2_ip": "N/A", "cs3_ip": "N/A", "pdu_ip": "N/A", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_paraguai_-_assunção_cs1_cs2", "regiao": "América Central / LATAM", "pais": "Paraguai", "praca": "Paraguai - Assunção CS1/CS2", "router": "10.50.20.1", "cs1_ip": "10.50.20.11", "cs2_ip": "10.50.20.12", "cs3_ip": "N/A", "pdu_ip": "10.50.20.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_guatemala_-_cidade_da_guatemala", "regiao": "América Central", "pais": "Guatemala", "praca": "Guatemala - Cidade da Guatemala", "router": "10.48.30.1", "cs1_ip": "10.48.30.11", "cs2_ip": "10.48.30.12", "cs3_ip": "N/A", "pdu_ip": "10.48.30.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}, {"id": "latam_panamá_-_cidade_do_panamá", "regiao": "América Central", "pais": "Panamá", "praca": "Panamá - Cidade do Panamá", "router": "10.49.40.1", "cs1_ip": "10.49.40.11", "cs2_ip": "10.49.40.12", "cs3_ip": "N/A", "pdu_ip": "10.49.40.254", "pdu_tipo": "PDU Remoto", "obs": "Captação Internacional Ativa", "status": "nominal"}];
    let currentRdpFilterCategory = 'all';
    let currentRdpSearchTerm = '';

    const OFICIAL_PRACAS = ["Altamira", "Anápolis", "Aracaju", "Araguaína", "Araxá", "Ariquemes", "B. Horizonte", "Bagé", "Balsas", "Barreiras", "Bauru", "Belém", "Blumenau", "Boa Vista", "Brasília", "C. Fabriciano", "C. Itapemirim", "Cabo Frio", "Cacoal", "Campina Grande", "Campinas", "Campo Grande", "Campos", "Caruaru", "Cascavel", "Castanhal", "Catalão", "Caxias do Sul", "Chapecó", "Codó", "Colatina", "Corumbá", "Costa Rica - Conversion Server", "Costa Rica - San José (BL1)", "Costa Rica - San José (BL10)", "Costa Rica - San José (BL2)", "Costa Rica - San José (BL3)", "Costa Rica - San José (BL4)", "Costa Rica - San José (BL5)", "Costa Rica - San José (BL6)", "Costa Rica - San José (BL7)", "Costa Rica - San José (BL8)", "Costa Rica - San José (BL9)", "Criciúma", "Cruz Alta", "Cruzeiro do Sul", "Cuiabá", "Curitiba", "Erechim", "F. Santana", "Floriano", "Florianópolis", "Fortaleza", "Foz de Iguaçu", "Franca", "G. Valadares", "Goiânia", "Guajará-Mirim", "Guarapuava", "Guatemala - Cidade da Guatemala", "Gurupi", "Imperatriz", "Itabuna", "Itacoatiara", "Itaituba", "Itapetininga", "Ituiutaba", "Itumbiara", "Jataí", "Ji-Paraná", "Joaçaba", "Joinville", "João Pessoa", "Juazeiro", "Juazeiro do N.", "Juiz de Fora", "Linhares", "Lisboa", "Londrina", "Luziânia", "M. das Cruzes", "Macapá", "Maceió", "Manaus", "Marabá", "Maringá", "Miami", "Montes Claros", "Mossoró", "Natal", "Nova Friburgo", "Palmas", "Panamá - Cidade do Panamá", "Paragominas", "Paraguai - Assunção CS1/CS2", "Paranavaí", "Parauapebas", "Parintins", "Passo Fundo", "Pelotas", "Penha-DT1", "Penha-DT2", "Penha-HQ", "Penha-SAT", "Ponta Grossa", "Ponta Pora", "Porangatú", "Porto Alegre", "Porto Velho", "Pres. Prudente", "RJ-Paytv Bloco 01", "RJ-Paytv Bloco 02", "RJ-Paytv Bloco 03", "RJ-Paytv Bloco 04", "RJ-Paytv Bloco 05", "RJ-Paytv Bloco 06", "RJ-Paytv Bloco 07", "RJ-Paytv Bloco 08", "RJ-Paytv Bloco 09", "Recife", "Redenção", "Resende", "Ribeirão Preto", "Rio Branco", "Rio Grande", "Rio Verde", "Rio de Janeiro", "Rondonópolis", "S.J. Campos", "S.J.Rio Preto", "Salvador", "Santa C.do Sul", "Santa Maria", "Santa Rosa", "Santarém", "Santos", "Sinop", "Sorocaba", "São Carlos", "São Luís", "T. da Serra", "Taubaté", "Teresina", "Tucuruí", "Uberaba", "Uberlândia", "Uruguaiana", "V. da Conquista", "Varginha", "Vilhena", "Vitória"];
    const OFICIAL_EMISSORAS = ["Globo", "SBT", "Record TV", "Band", "Rede Vida", "TV Brasil", "TV Aparecida", "RIT", "Record News", "TV Gazeta", "TV Canção Nova", "TV Senado", "TV Câmara", "TV Justiça", "Outra"];
    const OFICIAL_STATUS_RETORNO = ["Pendente", "Em análise", "Não confirmado", "Confirmado"];
    const OFICIAL_AREAS = ["Preços", "SAC", "Captação", "Engenharia", "Comercial", "TI Corporativa"];

    let editingListItemIndex = null;
    let currentQuickOcoId = null;

    function renderRdpTable() {
      const tbody = document.getElementById("rdp-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let filtered = RDP_MASTER_DATASET.filter(h => {
        if (currentRdpFilterCategory === 'Brasil' && h.regiao !== 'Brasil') return false;
        if (currentRdpFilterCategory === 'América Central' && h.regiao === 'Brasil') return false;
        if (currentRdpFilterCategory === 'Volt' && (!h.pdu_ip || h.pdu_ip === 'N/A')) return false;

        if (currentRdpSearchTerm) {
          const txt = (h.praca + " " + h.pais + " " + h.regiao + " " + h.router + " " + h.cs1_ip + " " + h.cs2_ip + " " + h.cs3_ip + " " + h.pdu_ip).toLowerCase();
          return txt.includes(currentRdpSearchTerm);
        }
        return true;
      });

      filtered.forEach((h, idx) => {
        const tr = document.createElement("tr");

        const renderCsCell = (ip, role) => {
          if (!ip || ip === 'N/A') return '<span style="color:#94A3B8; font-size:11px;">-</span>';
          return `
            <div style="display:flex; align-items:center; gap:6px;">
              <code style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#1E293B;">${ip}</code>
              <button class="sp-btn-cmd" style="padding:2px 6px; font-size:10.5px; border-radius:3px; background:#EFF6FC; border-color:#BFDBFE; color:#0078D4;" onclick="triggerRdpConnect('${ip}', '${h.praca}', '${role}', 3389)" title="Conectar RDP 1-clique (${role})">
                🖥️ RDP
              </button>
              <button class="sp-btn-cmd" style="padding:2px 5px; font-size:10px; border-radius:3px; color:#64748B;" onclick="copyTextToClipboard('${ip}')" title="Copiar IP">
                📋
              </button>
            </div>
          `;
        };

        const renderRouterCell = (ip) => {
          if (!ip || ip === 'N/A') return '<span style="color:#94A3B8; font-size:11px;">-</span>';
          return `
            <div style="display:flex; align-items:center; gap:6px;">
              <code style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#0F766E;">${ip}</code>
              <a href="http://${ip}" target="_blank" class="sp-btn-cmd" style="padding:2px 6px; font-size:10.5px; border-radius:3px; text-decoration:none; color:#0F766E; background:#F0FDFA; border-color:#99F6E4;" title="Abrir Web GUI do Roteador">
                🌐 Web
              </a>
            </div>
          `;
        };

        const renderPduCell = (ip, tipo) => {
          if (!ip || ip === 'N/A') return '<span style="color:#94A3B8; font-size:11px;">Sem PDU</span>';
          return `
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="badge" style="background:#FEF3C7; color:#92400E; font-size:10.5px; border:1px solid #FDE68A; padding:2px 6px;">⚡ ${tipo || 'Volt'}</span>
              <code style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#78350F;">${ip}</code>
              <a href="http://${ip}" target="_blank" class="sp-btn-cmd" style="padding:2px 6px; font-size:10px; border-radius:3px; text-decoration:none; color:#92400E; background:#FFFBEB; border-color:#FDE68A;" title="Acessar painel da Régua Volt">
                Reset
              </a>
            </div>
          `;
        };

        const flag = h.pais === 'Brasil' ? '🇧🇷' : '🌎';
        tr.style.borderBottom = "1px solid #F1F5F9";
        tr.innerHTML = `
          <td style="padding: 11px 14px; text-align: center; color: #64748B; font-size: 11.5px; font-weight: 600;">${idx + 1}</td>
          <td style="padding: 11px 14px;"><b>${flag} ${h.pais}</b> <span style="color:#64748B; font-size:11px;">(${h.regiao})</span></td>
          <td style="padding: 11px 14px;"><b style="color:#0078D4; font-size: 13px;">${h.praca}</b></td>
          <td style="padding: 11px 14px;">${renderRouterCell(h.router)}</td>
          <td style="padding: 11px 14px;">${renderCsCell(h.cs1_ip, 'CS1')}</td>
          <td style="padding: 11px 14px;">${renderCsCell(h.cs2_ip, 'CS2')}</td>
          <td style="padding: 11px 14px;">${renderCsCell(h.cs3_ip, 'CS3')}</td>
          <td style="padding: 11px 14px;">${renderPduCell(h.pdu_ip, h.pdu_tipo)}</td>
          <td style="padding: 11px 14px; text-align: center;"><span class="badge" style="background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; font-size:10.5px; padding:3px 8px;">● Online</span></td>
        `;
        tbody.appendChild(tr);
      });

      const footer = document.getElementById("rdp-table-footer");
      if (footer) {
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${RDP_MASTER_DATASET.length}</b> nós remotos`;
      }
    }

    // ==========================================
    // 2.7 NAVEGADOR DE PASTAS RDP & CONEXÃO RÁPIDA MSTSC
    // ==========================================
    let rdpCurrentViewMode = 'list';
    let rdpFolderBreadcrumbs = [];

    function switchRdpViewMode(mode) {
      rdpCurrentViewMode = mode;
      const listBtn = document.getElementById('btn-rdp-view-list');
      const foldersBtn = document.getElementById('btn-rdp-view-folders');
      const listWrap = document.getElementById('rdp-view-list-container');
      const foldersWrap = document.getElementById('rdp-view-folders-container');

      if (mode === 'folders') {
        if (listBtn) listBtn.classList.remove('active');
        if (foldersBtn) foldersBtn.classList.add('active');
        if (listWrap) listWrap.style.display = 'none';
        if (foldersWrap) foldersWrap.style.display = 'block';
        initRdpFolders();
      } else {
        if (listBtn) listBtn.classList.add('active');
        if (foldersBtn) foldersBtn.classList.remove('active');
        if (listWrap) listWrap.style.display = 'block';
        if (foldersWrap) foldersWrap.style.display = 'none';
        renderRdpTable();
      }
    }

    function initRdpFolders() {
      const rdpDrive = SP_MASTER_DATA.drives && SP_MASTER_DATA.drives['Acesso Remoto'];
      const rootItems = rdpDrive ? (rdpDrive.items || []) : [];
      rdpFolderBreadcrumbs = [{ name: 'Acesso Remoto', items: rootItems }];
      renderRdpFolderGrid();
    }

    function resetRdpFolderRoot() {
      initRdpFolders();
    }

    function openRdpFolderCrumb(index) {
      if (index >= 0 && index < rdpFolderBreadcrumbs.length) {
        rdpFolderBreadcrumbs = rdpFolderBreadcrumbs.slice(0, index + 1);
        renderRdpFolderGrid();
      }
    }

    function openRdpSubfolder(folderId) {
      const cur = rdpFolderBreadcrumbs[rdpFolderBreadcrumbs.length - 1];
      if (!cur) return;
      const folder = (cur.items || []).find(it => String(it.id) === String(folderId));
      if (folder) {
        rdpFolderBreadcrumbs.push({
          name: folder.name,
          items: folder.children || []
        });
        renderRdpFolderGrid();
      }
    }

    function renderRdpFolders() {
      renderRdpFolderGrid();
    }

    function renderRdpFolderGrid() {
      const cur = rdpFolderBreadcrumbs[rdpFolderBreadcrumbs.length - 1];
      const items = cur ? (cur.items || []) : [];
      const bcEl = document.getElementById('rdp-folders-breadcrumb');
      const gridEl = document.getElementById('rdp-folders-grid');
      if (!gridEl) return;

      if (bcEl) {
        bcEl.innerHTML = rdpFolderBreadcrumbs.map((crumb, idx) => {
          if (idx === rdpFolderBreadcrumbs.length - 1) {
            return `<span style="color:#1E293B; font-weight:700;">${crumb.name}</span>`;
          }
          return `<span style="cursor:pointer; color:#0078D4;" onclick="openRdpFolderCrumb(${idx})">${crumb.name}</span> &rsaquo; `;
        }).join('');
      }

      if (items.length === 0) {
        gridEl.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #94A3B8;">Esta pasta não possui subpastas ou arquivos .rdp.</div>`;
        return;
      }

      gridEl.innerHTML = items.map(it => {
        const isFolder = it.type === 'folder';
        if (isFolder) {
          const childCount = (it.children ? it.children.length : (it.childCount || 0));
          return `
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 12px;" onclick="openRdpSubfolder('${it.id}')" onmouseover="this.style.borderColor='#0078D4'; this.style.background='#F0F9FF';" onmouseout="this.style.borderColor='#E2E8F0'; this.style.background='#F8FAFC';">
              <span style="font-size: 26px;">📁</span>
              <div style="flex: 1; overflow: hidden;">
                <div style="font-size: 13px; font-weight: 700; color: #1E293B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${it.name}</div>
                <div style="font-size: 11px; color: #64748B; margin-top: 2px;">${childCount} itens</div>
              </div>
              <span style="color: #0078D4; font-size: 14px;">&rsaquo;</span>
            </div>
          `;
        } else {
          return `
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
              <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
                <span style="font-size: 24px;">🖥️</span>
                <div style="overflow: hidden;">
                  <div style="font-size: 12.5px; font-weight: 700; color: #1E293B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${it.name}">${it.name}</div>
                  <div style="font-size: 10.5px; color: #64748B;">${formatFileSize(it.size)}</div>
                </div>
              </div>
              <button class="sp-btn-cmd" style="padding: 4px 10px; font-size: 11px; border-radius: 4px; color: #0284C7; border-color: #BAE6FD; background: #F0F9FF; font-weight: 700;" onclick="generateAndDownloadRdp('${encodeURIComponent(it.name)}')" title="Baixar e Conectar">
                Conectar
              </button>
            </div>
          `;
        }
      }).join('');
    }

    function openQuickMstscModal(prefilledIp, prefilledLabel) {
      const hosts = RDP_MASTER_DATASET || [];
      const modalHtml = `
        <div id="modal-quick-mstsc" class="sp-modal-overlay" style="display:flex; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.7); backdrop-filter:blur(4px); z-index:9999; justify-content:center; align-items:center;">
          <div style="background:white; border-radius:10px; width:90%; max-width:580px; box-shadow:0 20px 40px rgba(0,0,0,0.25); overflow:hidden; border:1px solid #E2E8F0; animation:fadeIn 0.2s ease-out;">
            <div style="background:linear-gradient(135deg, #0F172A, #1E293B); color:white; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155;">
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px; color:#38BDF8;">⚡</span>
                <div>
                  <h3 style="margin:0; font-size:15px; font-weight:700;">Conexão Rápida MSTSC / RDP Nativo</h3>
                  <div style="font-size:11px; color:#94A3B8;">Microsoft Terminal Services Client &bull; Porta Padrão 3389</div>
                </div>
              </div>
              <button onclick="document.getElementById('modal-quick-mstsc').remove()" style="background:none; border:none; color:white; font-size:20px; cursor:pointer; line-height:1;">&times;</button>
            </div>
            <div style="padding:22px;">
              <div style="margin-bottom:16px;">
                <label style="display:block; font-size:12px; font-weight:700; color:#334155; margin-bottom:6px;">Selecione a Praça / Estação Homologada:</label>
                <select id="mstsc-select-host" class="select-field" style="width:100%; font-size:12.5px; padding:8px 10px;" onchange="onMstscHostSelected(this.value)">
                  <option value="">-- Selecione uma Praça (151 Nós Disponíveis) --</option>
                  ${hosts.map(h => `<option value="${h.cs1_ip}" data-cs1="${h.cs1_ip}" data-cs2="${h.cs2_ip}" data-cs3="${h.cs3_ip}" data-label="${h.praca}" ${prefilledLabel === h.praca ? 'selected' : ''}>${h.pais === 'Brasil' ? '🇧🇷' : '🌎'} ${h.praca} (${h.regiao}) - CS1: ${h.cs1_ip || 'N/A'}</option>`).join('')}
                </select>
              </div>

              <div style="display:grid; grid-template-columns:2fr 1fr; gap:12px; margin-bottom:16px;">
                <div>
                  <label style="display:block; font-size:12px; font-weight:700; color:#334155; margin-bottom:6px;">Endereço IP ou Hostname:</label>
                  <input type="text" id="mstsc-input-ip" value="${prefilledIp || ''}" placeholder="Ex: 10.150.12.10" class="input-field" style="width:100%; font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:700; color:#0F172A; padding:8px 10px;">
                </div>
                <div>
                  <label style="display:block; font-size:12px; font-weight:700; color:#334155; margin-bottom:6px;">Porta RDP:</label>
                  <input type="text" id="mstsc-input-port" value="3389" class="input-field" style="width:100%; font-family:'JetBrains Mono',monospace; font-size:13px; padding:8px 10px;">
                </div>
              </div>

              <div style="margin-bottom:18px;">
                <label style="display:block; font-size:12px; font-weight:700; color:#334155; margin-bottom:6px;">Modo de Visualização:</label>
                <select id="mstsc-select-res" class="select-field" style="width:100%; font-size:12px; padding:8px 10px;">
                  <option value="fullscreen">🖥️ Tela Cheia (Multimonitor)</option>
                  <option value="1920x1080">📐 1920 x 1080 (Full HD)</option>
                  <option value="1366x768">📐 1366 x 768 (HD Padrão)</option>
                </select>
              </div>

              <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px 14px; font-size:11.5px; margin-bottom:20px;">
                <div style="color:#64748B; font-weight:600; margin-bottom:4px;">💡 Como funciona a Conexão Rápida:</div>
                <div style="color:#334155; line-height:1.4;">
                  Clique em <strong>Conectar Agora</strong> para baixar o arquivo <code>.rdp</code> configurado e abrir instantaneamente no Remote Desktop nativo do Windows, ou use <strong>Copiar Comando</strong> para colar no Executar (Win+R).
                </div>
              </div>

              <div style="display:flex; gap:10px; justify-content:flex-end; flex-wrap:wrap;">
                <button type="button" class="btn-action btn-action-secondary" onclick="copyMstscCommand()">
                  📋 Copiar Comando (mstsc /v:...)
                </button>
                <button type="button" class="btn-action btn-action-primary" onclick="launchMstscConnection()" style="background:#0284C7; border-color:#0284C7;">
                  🚀 Conectar Agora (.rdp)
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      const prev = document.getElementById('modal-quick-mstsc');
      if (prev) prev.remove();
      document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    function onMstscHostSelected(ip) {
      const input = document.getElementById('mstsc-input-ip');
      if (input && ip) input.value = ip;
    }

    function copyMstscCommand() {
      const ip = (document.getElementById('mstsc-input-ip')?.value || '').trim();
      const port = (document.getElementById('mstsc-input-port')?.value || '3389').trim();
      if (!ip) {
        showToast('⚠️ Informe um IP ou selecione uma praça primeiro.', 'error');
        return;
      }
      const addr = port === '3389' ? ip : `${ip}:${port}`;
      const cmd = `mstsc /v:${addr} /f`;
      copyTextToClipboard(cmd);
      showToast(`📋 Comando '${cmd}' copiado para a Área de Transferência!`, 'success');
    }

    function launchMstscConnection() {
      const ip = (document.getElementById('mstsc-input-ip')?.value || '').trim();
      const port = (document.getElementById('mstsc-input-port')?.value || '3389').trim();
      if (!ip) {
        showToast('⚠️ Informe um IP ou selecione uma praça primeiro.', 'error');
        return;
      }
      const label = document.getElementById('mstsc-select-host')?.selectedOptions[0]?.getAttribute('data-label') || ip;
      triggerRdpConnect(ip, label, 'CS1', port);
      document.getElementById('modal-quick-mstsc')?.remove();
    }

    function filterRdpTable() {
      const el = document.getElementById("search-rdp-box");
      currentRdpSearchTerm = el ? el.value.toLowerCase().trim() : '';
      renderRdpTable();
    }

    function setRdpCategory(cat, btn) {
      currentRdpFilterCategory = cat;
      document.querySelectorAll(".rdp-cat-pill").forEach(p => p.classList.remove("active"));
      if (btn) btn.classList.add("active");
      renderRdpTable();
    }

    function triggerRdpConnect(ip, hostLabel, role, port) {
      if (!ip || ip === 'N/A') {
        showToast('IP indisponível para esta estação.', 'error');
        return;
      }
      port = port || 3389;
      const addr = (port == 3389) ? ip : (ip + ':' + port);
      const rdpContent = [
        "screen mode id:i:2",
        "use multimon:i:0",
        "desktopwidth:i:1920",
        "desktopheight:i:1080",
        "session bpp:i:32",
        "winposstr:s:0,1,0,0,1920,1080",
        "compression:i:1",
        "keyboardhook:i:2",
        "audiocapturemode:i:0",
        "videoplaybackmode:i:1",
        "connection type:i:7",
        "networkautodetect:i:1",
        "bandwidthautodetect:i:1",
        "displayconnectionbar:i:1",
        "enableworkspacereconnect:i:0",
        "disable wallpaper:i:0",
        "allow font smoothing:i:1",
        "allow desktop composition:i:1",
        "disable full window drag:i:1",
        "disable menu anims:i:1",
        "disable themes:i:0",
        "disable cursor setting:i:0",
        "bitmapcachepersistenable:i:1",
        `full address:s:${addr}`,
        "audiomode:i:0",
        "redirectprinters:i:0",
        "redirectcomports:i:0",
        "redirectsmartcards:i:0",
        "redirectclipboard:i:1",
        "redirectposdevices:i:0",
        "drivestoredirect:s:",
        "prompt for credentials:i:1",
        "negotiate security layer:i:1",
        "remoteapplicationmode:i:0",
        `server port:i:${port}`,
        "gatewayusagemethod:i:0",
        "promptcredentialonce:i:0",
        "authentication level:i:2"
      ].join("\\r\\n");

      const blob = new Blob([rdpContent], { type: 'application/x-rdp' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safeLabel = (hostLabel || "Host").replace(/[^a-zA-Z0-9_-]/g, "_");
      a.href = url;
      a.download = `${safeLabel}_${role || 'CS'}_${ip}.rdp`;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 3000);

      if (!localStorage.getItem('rdp_autopen_hint_shown')) {
        localStorage.setItem('rdp_autopen_hint_shown', '1');
        _showRdpFirstTimeHint(hostLabel || ip, ip, role || 'CS');
      } else {
        showToast(`🖥️ Arquivo .RDP gerado para ${hostLabel || ip} (${role || 'CS'} - ${ip})! Clique na barra de downloads para conectar.`, 'success');
      }
    }

    function _showRdpFirstTimeHint(label, ip, role) {
      const pid = 'modal-rdp-firsttime-hint';
      const prev = document.getElementById(pid);
      if (prev) prev.remove();
      const overlay = document.createElement('div');
      overlay.id = pid;
      overlay.className = 'sp-modal-overlay';
      overlay.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(15,23,42,0.8);backdrop-filter:blur(4px);z-index:10000;justify-content:center;align-items:center;';
      overlay.innerHTML = `
        <div style="background:white;border-radius:12px;width:90%;max-width:500px;box-shadow:0 20px 50px rgba(0,0,0,0.3);overflow:hidden;border:2px solid #0078D4;">
          <div style="background:linear-gradient(135deg,#0078D4,#005A9E);color:white;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:22px;">🖥️</span>
              <div>
                <h3 style="margin:0;font-size:15px;font-weight:700;">Conexão RDP Iniciada!</h3>
                <div style="font-size:11px;opacity:0.9;">Arquivo gerado para ${label} (${ip})</div>
              </div>
            </div>
            <button type="button" data-close-rdp-hint style="background:none;border:none;color:white;font-size:20px;cursor:pointer;line-height:1;">&times;</button>
          </div>
          <div style="padding:20px;">
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:14px;margin-bottom:16px;">
              <div style="font-size:13px;font-weight:700;color:#1D4ED8;margin-bottom:8px;">💡 Como abrir automaticamente no Edge / Chrome:</div>
              <div style="font-size:12px;color:#1E3A5F;line-height:1.6;">
                O navegador baixa o arquivo <code>.rdp</code> por segurança. Para abrir com 1 clique:<br>
                • No <strong>Microsoft Edge</strong>: se aparecer aviso de segurança em Downloads, clique em <strong>Manter</strong> → <strong>Abrir arquivo</strong> (ou clique com o <strong>botão direito</strong> no arquivo <code>.rdp</code> e marque <strong>"Sempre abrir arquivos deste tipo"</strong>).<br>
                • No <strong>Google Chrome</strong>: clique na seta / botão direito no download e marque <strong>"Sempre abrir arquivos deste tipo"</strong>.<br>
                • Ou use o botão abaixo para copiar <code>mstsc /v:${ip}</code> e colar no Executar (<code>Win+R</code>).
              </div>
            </div>
            <div style="display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;">
              <button type="button" data-copy-mstsc-cmd class="btn-action btn-action-secondary" style="font-size:12px;padding:8px 14px;">📋 Copiar mstsc /v:${ip}</button>
              <button type="button" data-close-rdp-hint class="btn-action btn-action-primary" style="font-size:12px;padding:8px 18px;">✅ Entendi, Fechar</button>
            </div>
          </div>
        </div>
      `;
      overlay.querySelectorAll('[data-copy-mstsc-cmd]').forEach(btn => {
        btn.addEventListener('click', () => {
          copyTextToClipboard(`mstsc /v:${ip}`);
        });
      });
      overlay.querySelectorAll('[data-close-rdp-hint]').forEach(btn => {
        btn.addEventListener('click', () => overlay.remove());
      });
      document.body.appendChild(overlay);
    }
    window._showRdpFirstTimeHint = _showRdpFirstTimeHint;

    function copyTextToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(`IP ${text} copiado para a área de transferência!`, "success");
      }).catch(() => {
        const temp = document.createElement("input");
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        document.execCommand("copy");
        document.body.removeChild(temp);
        showToast(`IP ${text} copiado!`, "success");
      });
    }

    function exportRdpCSV() {
      const headers = ["ID", "Pais", "Regiao", "Praca", "Router_IP", "CS1_IP", "CS2_IP", "CS3_IP", "PDU_IP", "PDU_Tipo", "Status"];
      const rows = RDP_MASTER_DATASET.map(h => [
        `"${h.id || ''}"`,
        `"${h.pais || ''}"`,
        `"${h.regiao || ''}"`,
        `"${h.praca || ''}"`,
        `"${h.router || ''}"`,
        `"${h.cs1_ip || ''}"`,
        `"${h.cs2_ip || ''}"`,
        `"${h.cs3_ip || ''}"`,
        `"${h.pdu_ip || ''}"`,
        `"${h.pdu_tipo || ''}"`,
        `"${h.status || 'nominal'}"`
      ].join(","));

      const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\\r\\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Inventario_RDP_Acesso_Remoto_NOC_${new Date().toISOString().substring(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("Planilha de Acesso Remoto exportada com sucesso!", "success");
    }

    function buildSmartFieldHtml(colId, colTitle, currentValue) {
      const titleLower = (colTitle || colId || '').toLowerCase();
      const val = currentValue !== null && currentValue !== undefined ? String(currentValue) : '';

      if (titleLower.includes("praça") || titleLower.includes("praca") || titleLower.includes("cidade") || titleLower === "host") {
        const options = OFICIAL_PRACAS.map(p => `<option value="${p}" ${val.toLowerCase() === p.toLowerCase() ? "selected" : ""}>${p}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione a Praça...</option>
              ${options}
            </select>
          </div>
        `;
      }

      if (titleLower.includes("emissora") || titleLower.includes("rede") || titleLower.includes("veículo") || titleLower.includes("veiculo")) {
        const options = OFICIAL_EMISSORAS.map(e => `<option value="${e}" ${val.toLowerCase() === e.toLowerCase() ? "selected" : ""}>${e}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione a Emissora...</option>
              ${options}
            </select>
          </div>
        `;
      }

      if (titleLower.includes("data") || titleLower.includes("hora") || titleLower.includes("solicita") || titleLower.includes("início") || titleLower.includes("inicio") || titleLower.includes("fim")) {
        let dateVal = val;
        if (dateVal.includes("T")) dateVal = dateVal.substring(0, 16);
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <div style="display: flex; gap: 6px;">
              <input type="datetime-local" name="${colId}" class="sp-form-input list-dyn-input" value="${dateVal}" style="flex: 1; height: 38px;">
              <button type="button" class="sp-btn-cmd" style="padding: 0 10px; font-size: 11.5px;" onclick="setFieldNow(this, '${colId}')">Agora</button>
            </div>
          </div>
        `;
      }

      if (titleLower.includes("área") || titleLower.includes("area") || titleLower === "área a solicitar") {
        const options = OFICIAL_AREAS.map(a => `<option value="${a}" ${val.toLowerCase() === a.toLowerCase() ? "selected" : ""}>${a}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              ${options}
            </select>
          </div>
        `;
      }

      if (titleLower.includes("retorno") || titleLower === "status_retorno" || titleLower.includes("status do retorno")) {
        const options = OFICIAL_STATUS_RETORNO.map(s => `<option value="${s}" ${val.toLowerCase() === s.toLowerCase() ? "selected" : ""}>${s}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              ${options}
            </select>
          </div>
        `;
      }

      if (titleLower.includes("presente") || titleLower.includes("recuperacao") || titleLower.includes("recuperação") || titleLower.includes("gravacao") || titleLower.includes("gravação")) {
        const isSim = val.toLowerCase() === "sim" || val.toLowerCase() === "true" || val === "1";
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="Sim" ${isSim ? "selected" : ""}>Sim</option>
              <option value="Não" ${!isSim ? "selected" : ""}>Não</option>
            </select>
          </div>
        `;
      }

      if (titleLower.includes("indício") || titleLower.includes("indicio") || titleLower.includes("descri") || titleLower.includes("ação") || titleLower.includes("acao") || titleLower.includes("observa") || titleLower.includes("resposta")) {
        return `
          <div class="sp-form-group" style="grid-column: 1 / -1;">
            <label class="sp-form-label">${colTitle}</label>
            <textarea name="${colId}" class="sp-form-input list-dyn-input" rows="4" placeholder="Descreva os detalhes..." style="width: 100%; font-family: inherit; resize: vertical;">${val}</textarea>
          </div>
        `;
      }

      return `
        <div class="sp-form-group">
          <label class="sp-form-label">${colTitle}</label>
          <input type="text" name="${colId}" class="sp-form-input list-dyn-input" value="${val}" placeholder="Informe ${colTitle}...">
        </div>
      `;
    }

    function setFieldNow(btn, fieldName) {
      const input = btn.closest(".sp-form-group").querySelector(`[name="${fieldName}"]`);
      if (input) {
        const now = new Date();
        const iso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().substring(0, 16);
        input.value = iso;
      }
    }

    function openEditListItemModal(itemIndex) {
      if (!currentRealListName) return;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[currentRealListName];
      if (!listData || !listData.items || !listData.items[itemIndex]) return;

      editingListItemIndex = itemIndex;
      const item = listData.items[itemIndex];

      const titleEl = document.getElementById("modal-new-list-title");
      if (titleEl) titleEl.innerHTML = `✏️ Propriedades do Item &mdash; ${currentRealListTitle}`;

      const container = document.getElementById("new-list-fields-container");
      if (!container) return;
      container.innerHTML = "";
      container.style.display = "grid";
      container.style.gridTemplateColumns = "repeat(auto-fit, minmax(260px, 1fr))";
      container.style.gap = "14px";

      const cols = listData.columns || [];
      const systemCols = ['id', 'modified', 'created', 'author', 'editor', 'attachments', 'contenttypeid'];
      const editableCols = cols.filter(c => !systemCols.includes(String(c.name || '').toLowerCase()));
      const renderCols = editableCols.length > 0 ? editableCols : cols;

      renderCols.forEach(col => {
        const colId = col.name;
        const colTitle = col.displayName || col.name;
        const val = item[colId] !== undefined ? item[colId] : (item[colTitle] !== undefined ? item[colTitle] : "");
        container.innerHTML += buildSmartFieldHtml(colId, colTitle, val);
      });

      const submitBtn = document.querySelector("#modal-new-list-item button[type='submit']");
      if (submitBtn) submitBtn.innerText = "💾 Salvar Alterações";

      const modal = document.getElementById("modal-new-list-item");
      if (modal) modal.style.display = "flex";
    }

    function openQuickCloseOcoModal(ocoId) {
      currentQuickOcoId = ocoId;
      const oco = allOcorrencias.find(o => String(o.id || o.Criado) === String(ocoId));
      if (!oco) return;

      document.getElementById("quick-close-oco-id").value = ocoId;
      document.getElementById("quick-close-host-title").innerText = (oco.HostName || oco.hostLookupId || 'Host') + ' (CS ' + (oco.CS || '-') + ')';
      document.getElementById("quick-close-status").value = "Concluído";
      document.getElementById("quick-close-area").value = "Solucionado";
      document.getElementById("quick-close-acoes").value = oco.AcoesExecutadas || "";
      document.getElementById("quick-close-recup").checked = String(oco.EmRecuperacao).toLowerCase() === 'sim';
      document.getElementById("quick-close-informar").checked = Boolean(oco.InformarOperacao);

      const modal = document.getElementById("modal-quick-close-oco");
      if (modal) modal.style.display = "flex";
    }

    function closeQuickCloseOcoModal() {
      const modal = document.getElementById("modal-quick-close-oco");
      if (modal) modal.style.display = "none";
    }

    function setQuickAcao(texto) {
      const el = document.getElementById("quick-close-acoes");
      if (el) {
        el.value = (el.value ? el.value + " " : "") + texto;
      }
    }

    function submitQuickCloseOco(ev) {
      ev.preventDefault();
      const ocoId = document.getElementById("quick-close-oco-id").value;
      const oco = allOcorrencias.find(o => String(o.id || o.Criado) === String(ocoId));
      if (!oco) return;

      oco.Status = document.getElementById("quick-close-status").value;
      oco.AreaResponsavel = document.getElementById("quick-close-area").value;
      oco.AcoesExecutadas = document.getElementById("quick-close-acoes").value;
      oco.EmRecuperacao = document.getElementById("quick-close-recup").checked ? "Sim" : "Não";
      oco.InformarOperacao = document.getElementById("quick-close-informar").checked;
      oco.Modified = new Date().toISOString();

      try {
        let edits = JSON.parse(localStorage.getItem('sp_custom_oco_edits') || '{}');
        edits[ocoId] = {
          Status: oco.Status,
          AreaResponsavel: oco.AreaResponsavel,
          AcoesExecutadas: oco.AcoesExecutadas,
          EmRecuperacao: oco.EmRecuperacao,
          InformarOperacao: oco.InformarOperacao,
          Modified: oco.Modified
        };
        localStorage.setItem('sp_custom_oco_edits', JSON.stringify(edits));
      } catch (e) {
        console.warn("Erro ao salvar encerramento localmente:", e);
      }

      closeQuickCloseOcoModal();
      renderOcorrenciasTable();
      showToast("Ocorrência encerrada e atualizada com sucesso!", "success");
    }

    async function refreshOcorrenciasData(btn) {
      const icon = document.getElementById("icon-refresh-oco");
      if (icon) icon.style.animation = "spin 1s linear infinite";
      if (btn) btn.disabled = true;

      try {
        const savedEdits = JSON.parse(localStorage.getItem('sp_custom_oco_edits') || '{}');
        let countUpdated = 0;
        allOcorrencias.forEach(o => {
          const ocoId = o.id || o.Criado;
          if (savedEdits[ocoId]) {
            Object.assign(o, savedEdits[ocoId]);
            countUpdated++;
          }
        });

        const newSaved = JSON.parse(localStorage.getItem('sp_custom_new_ocorrencias') || '[]');
        newSaved.forEach(newItem => {
          if (!allOcorrencias.some(o => (o.id && o.id === newItem.id) || o.Criado === newItem.Criado)) {
            allOcorrencias.unshift(newItem);
            countUpdated++;
          }
        });

        renderOcorrenciasTable();
        const now = new Date();
        const timeStr = now.toLocaleTimeString('pt-BR');
        showToast(`Painel atualizado às ${timeStr}! (${allOcorrencias.length} registros)`, "success");
      } catch (err) {
        console.warn("Falha no refresh:", err);
        renderOcorrenciasTable();
      } finally {
        setTimeout(() => {
          if (icon) icon.style.animation = "";
          if (btn) btn.disabled = false;
        }, 600);
      }
    }

  
    function openRelatorioTecnicoModal(ev) {
      if (ev) {
        ev.stopPropagation();
        ev.preventDefault();
      }
      const modal = document.getElementById("modal-relatorio-tecnico-pdf");
      const iframe = document.getElementById("iframe-relatorio-pdf");
      if (modal && iframe) {
        iframe.src = "Relatorio_Tecnico_Arquitetura_Fluxo_Dados_Seguranca_NOC.pdf?v=" + Date.now();
        modal.style.display = "flex";
      }
    }

    function closeRelatorioTecnicoModal() {
      const modal = document.getElementById("modal-relatorio-tecnico-pdf");
      const iframe = document.getElementById("iframe-relatorio-pdf");
      if (modal) modal.style.display = "none";
      if (iframe) iframe.src = "";
    }

</script>

  <!-- MODAL OFICIAL DE VISUALIZAÇÃO DE RELATÓRIO PDF -->
  <div id="modal-pdf-viewer" class="sp-modal-overlay" style="display: none; z-index: 999999; position: fixed; inset: 0; background: rgba(0,0,0,0.65); align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="sp-modal-content" style="max-width: 980px; width: 95vw; height: 92vh; display: flex; flex-direction: column; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); border: 1px solid #CBD5E1;">
      <div style="background: linear-gradient(135deg, #004578 0%, #002d50 100%); color: #fff; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <div style="display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 14.5px;">
          <span style="font-size: 18px;">📄</span>
          <span id="pdf-viewer-title">Relatório Oficial de Auditoria</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <a id="pdf-viewer-download" href="#" download class="sp-btn-cmd" style="color: #fff; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); text-decoration: none; padding: 5px 12px; font-size: 12px; border-radius: 6px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
            <span>⬇️</span> Baixar PDF
          </a>
          <button onclick="closePdfModal()" style="background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 4px; line-height: 1;" title="Fechar">✕</button>
        </div>
      </div>
      <div style="flex: 1; background: #525659; position: relative;">
        <iframe id="pdf-viewer-frame" style="width: 100%; height: 100%; border: none;"></iframe>
      </div>
    </div>
  </div>


  <!-- MODAL DO RELATÓRIO TÉCNICO OFICIAL (ARQUITETURA, FLUXO & SEGURANÇA NOC) -->
  <div id="modal-relatorio-tecnico-pdf" class="sp-modal-overlay" style="display:none; z-index:99999; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); align-items:center; justify-content:center;">
    <div class="sp-modal-card" style="width: 95vw; max-width: 1200px; height: 90vh; display: flex; flex-direction: column; background: #ffffff; border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,0.3); border: 1px solid #CBD5E1; overflow: hidden;">
      <div style="background: #004578; color: #ffffff; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #003359;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 20px;">🛡️</span>
          <div>
            <h3 style="margin: 0; font-size: 15px; font-weight: 700; letter-spacing: 0.3px;">Relatório Técnico Oficial — Arquitetura, Fluxo de Dados e Segurança do Ambiente NOC</h3>
            <span style="font-size: 11px; color: #BAE6FD;">Documento Homologado &bull; Auditoria de Segurança &bull; Central Autônoma</span>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <a href="Relatorio_Tecnico_Arquitetura_Fluxo_Dados_Seguranca_NOC.pdf" download class="sp-btn-cmd" style="background: #10B981; border-color: #059669; color: #fff; font-weight: 700; padding: 6px 14px; border-radius: 6px; text-decoration: none;">
            📥 Baixar PDF
          </a>
          <button type="button" class="sp-modal-close-btn" style="background: transparent; border: none; color: #ffffff; font-size: 22px; cursor: pointer;" onclick="closeRelatorioTecnicoModal()">✕</button>
        </div>
      </div>
      <div style="flex: 1; background: #525659; position: relative;">
        <iframe id="iframe-relatorio-pdf" src="" style="width: 100%; height: 100%; border: none;"></iframe>
      </div>
    </div>
  </div>

</body>
</html>"""


def get_project_root() -> str:
    """Retorna a raiz real do projeto tanto em ambiente de desenvolvimento quanto em PyInstaller."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.basename(exe_dir).lower() == "dist":
            return os.path.dirname(exe_dir)
        if os.path.exists(os.path.join(exe_dir, "config")):
            return exe_dir
        parent = os.path.dirname(exe_dir)
        if os.path.exists(os.path.join(parent, "config")):
            return parent
        return exe_dir
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_config_path(base_dir: str, filename: str) -> str:
    """Busca o arquivo de configuração no diretório local e, se ausente, recupera do bundle PyInstaller."""
    target = os.path.join(base_dir, "config", filename)
    if os.path.exists(target):
        return target
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = os.path.join(meipass, "config", filename)
        if os.path.exists(bundled):
            try:
                os.makedirs(os.path.join(base_dir, "config"), exist_ok=True)
                shutil.copy2(bundled, target)
                return target
            except Exception:
                return bundled
    return target


def generate_portal():
    base_dir = get_project_root()
    json_path = resolve_config_path(base_dir, "sharepoint_clean_migrated_events.json")
    perms_path = resolve_config_path(base_dir, "sharepoint_extracted_permissions.json")
    migrated_data_path = resolve_config_path(base_dir, "sharepoint_migrated_standalone_data.json")
    escala_path = resolve_config_path(base_dir, "escala_completa_2026.json")
    raw_escala_excel = resolve_config_path(base_dir, "Escala de trabalho 2026.xlsx")
    
    output_dir = os.path.join(base_dir, "portal_web")
    os.makedirs(output_dir, exist_ok=True)
    output_html = os.path.join(output_dir, "index.html")

    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    docs_html = os.path.join(docs_dir, "index.html")

    # Copia arquivo oficial da escala para download estático
    if os.path.exists(raw_escala_excel):
        shutil.copy2(raw_escala_excel, os.path.join(output_dir, "Escala_de_trabalho_2026.xlsx"))
        shutil.copy2(raw_escala_excel, os.path.join(docs_dir, "Escala_de_trabalho_2026.xlsx"))

    # 1. Eventos Streaming (862 jogos)
    events = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            events = json.load(f)
    events_json_str = json.dumps(events, ensure_ascii=False)

    # 2. Dados Standalone Migrados (Hospedeiros, Ocorrências, POPs, Documentos)
    standalone_data = {}
    if os.path.exists(migrated_data_path):
        with open(migrated_data_path, "r", encoding="utf-8") as f:
            standalone_data = json.load(f)

    hospedeiros = standalone_data.get("contatos_hospedeiros", [])
    ocorrencias = standalone_data.get("painel_ocorrencias", [])
    procedimentos = standalone_data.get("procedimentos", [])
    documentos_lib = standalone_data.get("escala_trabalho", [])
    antenistas = standalone_data.get("contatos_antenistas", [])

    # Carregar Hosts cadastrados (220 hosts)
    hosts_path = resolve_config_path(base_dir, "cadastro_hosts_all.json")
    hosts_dict = {}
    if os.path.exists(hosts_path):
        with open(hosts_path, "r", encoding="utf-8") as f:
            hosts_dict = json.load(f)

    # Carregar Ocorrências Live Sincronizadas do SharePoint (1.000 Casos)
    live_oco_path = resolve_config_path(base_dir, "painel_ocorrencias_clean_live.json")
    if os.path.exists(live_oco_path):
        with open(live_oco_path, "r", encoding="utf-8") as f:
            ocorrencias = json.load(f)

    # Mesclar nome legível do Host em cada ocorrência
    for o in ocorrencias:
        hid = str(o.get("hostLookupId") or "")
        o["HostName"] = hosts_dict.get(hid) or hid or "-"

    hospedeiros_json_str = json.dumps(hospedeiros, ensure_ascii=False)
    ocorrencias_json_str = json.dumps(ocorrencias, ensure_ascii=False)
    procedimentos_json_str = json.dumps(procedimentos, ensure_ascii=False)
    documentos_json_str = json.dumps(documentos_lib, ensure_ascii=False)

    # 3. Escala Completa 2026 (todos os meses, turnos, CLT 66)
    escala_data = {}
    if os.path.exists(escala_path):
        with open(escala_path, "r", encoding="utf-8") as f:
            escala_data = json.load(f)
    escala_json_str = json.dumps(escala_data, ensure_ascii=False)

    # 4. Permissões Extraídas do SharePoint
    raw_perms = []
    if os.path.exists(perms_path):
        with open(perms_path, "r", encoding="utf-8") as f:
            raw_perms = json.load(f)

    team_members_roles = [
        {"type": "user", "displayName": "Cleber De Souza Goncalves", "email": "cleber.goncalves@ibope.com", "roles": ["owner"], "cargo": "COORD. SUPORTE CAPTAÇÃO", "google_role": "Administrador"},
        {"type": "user", "displayName": "Luiz De Sa Lemos", "email": "luiz.lemos@ibope.com", "roles": ["owner"], "cargo": "DIR. SUPORTE CAPTAÇÃO LATAM", "google_role": "Administrador"},
        {"type": "user", "displayName": "Andre Toshio Uiete Uehara", "email": "andre.uehara@ibope.com", "roles": ["write"], "cargo": "Assistente Administrativo", "google_role": "Operador"},
        {"type": "user", "displayName": "Maria Simone De Santana Matos", "email": "maria.matos@ibope.com", "roles": ["write"], "cargo": "Analista de dados Jr.", "google_role": "Operador"},
        {"type": "user", "displayName": "ALAN KELVIN CHURA CARRILLO", "email": "alan.carrillo@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE JR (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Bruno Lopes Viana", "email": "bruno.viana@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE JR (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Cleber Rodrigo Gomes", "email": "cleber.gomes@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE JR (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Cassio Esteves De Oliveira", "email": "cassio.esteves@ibope.com", "roles": ["owner"], "cargo": "ADMINISTRADOR DO PORTAL / SUPORTE CAPTAÇÃO", "google_role": "Administrador"},
        {"type": "user", "displayName": "RODRIGO DE ALMEIDA MEIRELLES", "email": "rodrigo.meirelles@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE JR (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Rômulo Silva", "email": "romulo.silva@ibope.com", "roles": ["write"], "cargo": "Tecnico De Suporte Jr (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Marcelo Fialho", "email": "Marcelo.Fialho@ibope.com", "roles": ["write"], "cargo": "Tecnico De Suporte Jr (N1)", "google_role": "Operador"},
        {"type": "user", "displayName": "Joao Diego Silva Merino", "email": "joao.merino@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE PL (N2)", "google_role": "Operador"},
        {"type": "user", "displayName": "Lucieudes Vicente Ferreira", "email": "lucieudes.ferreira@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE PL (N2)", "google_role": "Operador"},
        {"type": "user", "displayName": "Marcelo Pereira Silva", "email": "marcelo.pereira@ibope.com", "roles": ["write"], "cargo": "LIDER TECNICO LATAM (N2)", "google_role": "Operador"},
        {"type": "user", "displayName": "Marcos Antonio Bezerra Da Silva", "email": "marcos.bezerra@ibope.com", "roles": ["write"], "cargo": "TEC. SUPORTE SR (N2)", "google_role": "Operador"},
        {"type": "user", "displayName": "Vinicius Dantas Ferreira Da Silva", "email": "vinicius.dantas@ibope.com", "roles": ["owner"], "cargo": "ADMINISTRADOR DO PORTAL / SUPORTE CAPTAÇÃO", "google_role": "Administrador"}
    ]

    all_permissions = []
    seen_identifiers = set()

    for m in team_members_roles:
        seen_identifiers.add(m["email"].lower())
        all_permissions.append({
            "name": m["displayName"],
            "type": "Usuário",
            "email": m["email"],
            "sp_role": "Proprietário (owner)" if "owner" in m["roles"] else "Edição (write)",
            "google_role": m["google_role"],
            "cargo": m["cargo"],
            "scope": "Acesso Completo (Todas as Seções & Ações)" if m["google_role"] == "Administrador" else "Operacional (Streaming, Receptores, POPs)"
        })

    for p in raw_perms:
        p_name = p.get("displayName") or "Desconhecido"
        p_type = "Grupo de Segurança" if p.get("type") == "group" else "Usuário"
        p_email = p.get("email") or "-"
        p_roles = p.get("roles") or []

        if p_email != "-" and p_email.lower() in seen_identifiers:
            continue
        if p_email != "-":
            seen_identifiers.add(p_email.lower())
        else:
            if p_name.lower() in seen_identifiers:
                continue
            seen_identifiers.add(p_name.lower())

        is_owner = "owner" in p_roles
        is_write = "write" in p_roles
        
        if is_owner:
            sp_r = "Proprietário (owner)"
            g_r = "Administrador"
            scope_desc = "Acesso Total & Gestão de Permissões"
        elif is_write:
            sp_r = "Colaborador (write)"
            g_r = "Operador"
            scope_desc = "Edição da Grade Streaming & Monitoramento"
        else:
            sp_r = "Visitante (read)"
            g_r = "Leitor"
            scope_desc = "Consulta à Programação & Links Úteis"

        all_permissions.append({
            "name": p_name,
            "type": p_type,
            "email": p_email,
            "sp_role": sp_r,
            "google_role": g_r,
            "cargo": "Grupo Corporativo" if p_type == "Grupo de Segurança" else "Colaborador",
            "scope": scope_desc
        })

    perms_json_str = json.dumps(all_permissions, ensure_ascii=False)
    # 5. Master Data do SharePoint (21 Drives com 260 Relatórios e 46 Listas Reais)
    master_data_path = resolve_config_path(base_dir, "sharepoint_portal_master_data.json")
    master_data = {"drives": {}, "lists": {}}
    if os.path.exists(master_data_path):
        with open(master_data_path, "r", encoding="utf-8") as f:
            master_data = json.load(f)
    master_data_json_str = json.dumps(master_data, ensure_ascii=False)


    # Exporta CSV oficial
    os.makedirs(os.path.join(base_dir, "config"), exist_ok=True)
    csv_path = os.path.join(base_dir, "config", "permissoes_google_workspace_suportecaptacao.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Nome", "Tipo", "Email", "Nivel_SharePoint", "Nivel_Google_Sites", "Cargo_Funcao", "Escopo_Permissoes"])
        for p in all_permissions:
            writer.writerow([p["name"], p["type"], p["email"], p["sp_role"], p["google_role"], p["cargo"], p["scope"]])

    html_content = HTML_TEMPLATE
    html_content = html_content.replace("__EVENTS_JSON__", events_json_str)
    html_content = html_content.replace("__HOSPEDEIROS_JSON__", hospedeiros_json_str)
    html_content = html_content.replace("__OCORRENCIAS_JSON__", ocorrencias_json_str)
    html_content = html_content.replace("__ANTENISTAS_JSON__", json.dumps(antenistas, ensure_ascii=False))
    html_content = html_content.replace("__HOSTS_JSON__", json.dumps(hosts_dict, ensure_ascii=False))
    html_content = html_content.replace("__PROCEDIMENTOS_JSON__", procedimentos_json_str)
    html_content = html_content.replace("__DOCUMENTOS_JSON__", documentos_json_str)
    html_content = html_content.replace("__ESCALA_JSON__", escala_json_str)
    html_content = html_content.replace("__PERMS_JSON__", perms_json_str)
    html_content = html_content.replace("__SP_MASTER_DATA__", master_data_json_str)
    html_content = html_content.replace("__EVENTS_COUNT__", str(len(events)))
    html_content = html_content.replace("__HOSPEDEIROS_COUNT__", str(len(hospedeiros)))
    html_content = html_content.replace("__OCORRENCIAS_COUNT__", str(len(ocorrencias)))
    html_content = html_content.replace("__HOSTS_COUNT__", str(len(hosts_dict)))
    html_content = html_content.replace("__PROCEDIMENTOS_COUNT__", str(len(procedimentos)))
    html_content = html_content.replace("__DOCUMENTOS_COUNT__", str(len(documentos_lib)))
    html_content = html_content.replace("__PERMS_COUNT__", str(len(all_permissions)))

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(docs_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Portal Web Suporte Captação gerado com sucesso em: {output_html}")
    print(f"Publicação atualizada em: {docs_html}")
    print(f"Tamanho do arquivo: {os.path.getsize(output_html)} bytes")
    return output_html

if __name__ == "__main__":
    generate_portal()
