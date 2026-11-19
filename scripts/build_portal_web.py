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
import json
import csv
import shutil

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Suporte e Captação | Portal Oficial & Central Autônoma</title>
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
        Google Sites <span>| Suporte e Captação</span>
      </div>
    </div>

    <div class="suite-nav-center">
      <input type="text" class="suite-search-box" id="global-search" placeholder="Pesquisar partidas, contatos, ocorrências, procedimentos...">
    </div>

    <div class="suite-nav-right">
      <select id="user-role-select" class="role-switcher-select" onchange="onRoleChange()" title="Simulador de Perfil de Acesso">
        <option value="admin">👤 Cleber Gonçalves (Gestor/Admin)</option>
        <option value="admin_cassio">👤 Cássio Esteves (Administrador)</option>
        <option value="admin_vinicius">👤 Vinícius Dantas (Administrador)</option>
        <option value="operador">🛠️ Operador Suporte N1/N2</option>
        <option value="leitor">👁️ Visitante (NOC / SAC / Consulta)</option>
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
          <h2>Suporte e Captação</h2>
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
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('escala', '💼 Escala de Trabalho 2026', event)">💼 Escala de Trabalho 2026</a>
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
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('metas', '🎯 Metas & OKRs da Equipe', event)">🎯 Metas & OKRs da Equipe <span class="item-count-badge">8</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('contratos', '📝 Controle de Contratos Parceiros', event)">📝 Controle de Contratos Parceiros <span class="item-count-badge">114</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('fornecedores', '🏢 Avaliação Técnica de Fornecedores', event)">🏢 Avaliação Técnica de Fornecedores</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('solicitacoes', '🔑 Solicitações de Acesso', event)">🔑 Solicitações de Acesso</a>
          </div>
        </div>

        <!-- Qualidade ⌵ -->
        <div class="sp-menu-item">
          <button type="button" class="sp-menu-btn" onclick="toggleDropdown(this, event)">Qualidade <span class="sp-caret">⌵</span></button>
          <div class="sp-dropdown-menu">
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('sla', '⏱️ SLA de Atendimento', event)">⏱️ SLA de Atendimento</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('dashboard', '📊 Dashboard & Indicadores', event)">📊 Dashboard & Indicadores</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('notificacoes', '🔔 Análise de Notificações', event)">🔔 Análise de Notificações</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('backup', '💾 Validação de Backup', event)">💾 Validação de Backup</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('analisedados', '📈 Análise de Dados', event)">📈 Análise de Dados</a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('falhas', '⚠️ Confirmação de Falhas', event)">⚠️ Confirmação de Falhas</a>
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
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('remoto', '🎮 Acesso Remoto & América Central', event)">🎮 Acesso Remoto & América Central <span class="item-count-badge">19</span></a>
            <a href="javascript:void(0)" class="sp-dropdown-link" onclick="handleMenuClick('relatoriosjogos', '🏀 Relatórios de Jogos (YouTube & NBA)', event)">🏀 Relatórios de Jogos (YouTube & NBA) <span class="item-count-badge">260</span></a>
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
            <h1 class="hero-main-title">Suporte e Captação</h1>
            <p class="hero-description">
              Bem vindo(a) ao site da equipe de Suporte e Captação! Aqui você pode encontrar informações sobre problemas técnicos, verificar o status das ocorrências, localizar documentos e dados referentes à área e muito mais.
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

        <!-- Grade 3x3 de Botões Brancos Idênticos ao SharePoint -->
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
        </div>
      </section>

      <!-- ÁREA INFERIOR DA PÁGINA (CHAMADA E LINKS EXTERNOS) -->
      <section class="home-lower-body">
        <div class="contact-callout-box">
          <div class="contact-callout-header">Entre em contato com a nossa equipe</div>
          <div class="contact-callout-body">
            <p>Precisa de suporte imediato ou alinhamento técnico com o plantão da Captação? Chame diretamente no Teams.</p>
            <a href="https://teams.microsoft.com/l/team/19:DbmEit-Jw5Egnzv9KJysAxgT20jeLg_9HvF-OtRncrE1@thread.tacv2/conversations?groupId=b85ee2f2-68d9-461a-8ba8-d4eecbf19d94&tenantId=1e355c04-e0a4-42ed-8e2d-7351591f0ef1" target="_blank" class="btn-contact-action">
              Enviar uma mensagem
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
        <div>
          <a href="Escala_de_trabalho_2026.xlsx" download class="btn-action btn-action-primary" title="Baixar arquivo oficial da escala">
            📥 Baixar Planilha Oficial (.xlsx)
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

      <div class="filter-bar">
        <div class="filter-inputs">
          <input type="text" id="search-box" class="search-field" placeholder="🔍 Buscar partida, campeonato, responsável ou data...">
          <select id="filter-canal" class="select-field">
            <option value="">Todos os Canais</option>
            <option value="cazé">Cazé TV</option>
            <option value="prime">Amazon Prime Video</option>
            <option value="netflix">Netflix</option>
            <option value="tnt">TNT / Max</option>
            <option value="record">Record</option>
            <option value="dazn">DAZN</option>
          </select>
          <select id="filter-status" class="select-field">
            <option value="">Todos os Status</option>
            <option value="pendente">Pendente</option>
            <option value="exibido">Exibido</option>
            <option value="não exibido">Não Exibido</option>
          </select>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-action btn-action-secondary action-admin-only" onclick="syncLiveAPI(this)">🔄 Sincronizar em Tempo Real</button>
          <button class="btn-action btn-action-primary" onclick="exportCSV()">📥 Exportar CSV</button>
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="td-center">#</th>
                <th class="td-center">Mês</th>
                <th class="td-center">Data</th>
                <th class="td-center">Horário</th>
                <th>Campeonato</th>
                <th>Partida</th>
                <th>Responsável Gravação</th>
                <th class="td-center">Canal de Transmissão</th>
                <th class="td-center">PVID TV BOX</th>
                <th class="td-center">Status de Entrega</th>
                <th class="td-center">Programado</th>
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
      <div class="section-title-wrap">
        <h2 class="section-title">📞 Contatos Técnicos de Hospedeiros (__HOSPEDEIROS_COUNT__ Registros)</h2>
        <p class="section-desc">Diretório completo de centrais e técnicos de recepção e captação em todas as praças.</p>
      </div>

      <div class="filter-bar">
        <div class="filter-inputs">
          <input type="text" id="search-hosp-box" class="search-field" placeholder="🔍 Buscar por cidade, técnico, especialidade ou telefone...">
        </div>
        <div>
          <button class="btn-action btn-action-primary" onclick="exportHospedeirosCSV()">📥 Exportar Hospedeiros CSV</button>
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="td-center">#</th>
                <th>Cidade / Praça</th>
                <th>Nome do Técnico / Central</th>
                <th>Especialidade</th>
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
    <div id="pane-ocorrencias" class="pane-container">
      
      <!-- BARRA DE COMANDOS DO SHAREPOINT -->
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new action-admin-only" onclick="alert('Formulário de Nova Ocorrência conectado ao SharePoint')">
            <span>+</span> Novo
          </button>
          <button class="sp-btn-cmd" onclick="toggleOcoCompact()">
            <span>田</span> Editar no modo de exibição de grade
          </button>
          <button class="sp-btn-cmd" onclick="renderOcorrenciasTable()">
            <span>↺</span> Atualizar
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

      <!-- TABELA DO SHAREPOINT (13 COLUNAS OFICIAIS) -->
      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th style="min-width: 120px;">Status</th>
                <th style="min-width: 130px; cursor: pointer;" onclick="toggleOcoSort()">Criado ↓</th>
                <th style="min-width: 190px;">Host</th>
                <th style="min-width: 70px;">CS</th>
                <th style="min-width: 110px;">Veículo</th>
                <th style="min-width: 140px;">Equipamento</th>
                <th style="min-width: 140px;">Tipo do Problema</th>
                <th style="min-width: 110px;" class="td-center">Em recuperação</th>
                <th style="min-width: 120px;" class="td-center">GravaçãoStreaming</th>
                <th style="min-width: 120px;" class="td-center">Informar Operação</th>
                <th style="min-width: 250px;">Ações executadas</th>
                <th style="min-width: 130px;">Area/Responsável</th>
                <th style="min-width: 80px;" class="td-center">Redmine</th>
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
          <button class="sp-btn-new action-admin-only" onclick="alert('Formulário de Novo Contato')"><span>+</span> Novo</button>
          <button class="sp-btn-cmd" onclick="renderAntenistasTable()"><span>↺</span> Atualizar</button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-ante-box" placeholder="Pesquisar antenistas..." oninput="renderAntenistasTable()">
        </div>
      </div>
      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">Contatos de Antenistas <span class="star-icon">☆</span></h2>
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
          <button class="sp-btn-new action-admin-only" onclick="alert('Novo Host')"><span>+</span> Novo Host</button>
          <button class="sp-btn-cmd" onclick="renderHostsTable()"><span>↺</span> Atualizar</button>
        </div>
        <div class="sp-command-search">
          <input type="text" id="search-hosts-box" placeholder="Pesquisar hosts ou cidades..." oninput="renderHostsTable()">
        </div>
      </div>
      <div class="sp-list-header-row">
        <h2 class="sp-list-main-title">Cadastro - Hosts (220 Praças Ativas) <span class="star-icon">☆</span></h2>
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
          <button class="sp-btn-new action-admin-only" onclick="alert('Inclusão de arquivos restrita a administradores no SharePoint Online')"><span>+</span> Novo</button>
          <button class="sp-btn-cmd" onclick="alert('Modo de exibição de grade do SharePoint ativado')"><span>田</span> Modo Grade</button>
          <button class="sp-btn-cmd" onclick="exportCurrentDriveCSV()"><span>📥</span> Exportar CSV</button>
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
        Biblioteca oficial sincronizada 1:1 com o Microsoft SharePoint Online da Central de Suporte e Captação.
      </p>

      <div class="filter-bar">
        <div class="filter-inputs" style="width: 100%;">
          <input type="text" id="drive-viewer-search" class="search-field" oninput="filterDriveTable()" placeholder="🔍 Buscar por nome do arquivo, pasta ou responsável...">
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
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

    <!-- SUBMENU 2: RELATÓRIOS OFICIAIS DE AUDITORIA DE JOGOS (NBA, YOUTUBE & FUTEBOL - 260 CASOS) -->
    <div id="pane-relatoriosjogos" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-cmd" onclick="exportRelatoriosCSV()"><span>📥</span> Exportar CSV</button>
          <button class="sp-btn-cmd" onclick="handleMenuClick('home', 'Página Inicial')"><span>🏠</span> Voltar ao Início</button>
        </div>
      </div>

      <div class="sp-list-header-row">
        <div>
          <div style="font-size: 12px; color: #64748B; margin-bottom: 4px;">Suporte Captação &rsaquo; Relatórios de Auditoria</div>
          <h2 class="sp-list-main-title">Relatórios de Jogos & Auditoria de Transmissão <span class="star-icon">☆</span></h2>
        </div>
        <div class="sp-views-bar">
          <span class="sp-view-tab active">260 Relatórios Oficiais</span>
        </div>
      </div>

      <p style="color: #64748B; font-size: 13px; margin: 4px 0 14px 0; line-height: 1.5;">
        Repositório oficial de relatórios de auditoria com parecer técnico e comprovação de horários CBF, CazéTV e NBA. Todos os 260 relatórios oficiais do SharePoint disponíveis para download direto.
      </p>

      <!-- Pílulas de Seleção de Categoria (Tabs) -->
      <div style="display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap;">
        <button class="sp-tab-pill active" id="pill-relatorios-nba" onclick="switchRelatoriosTab('nba')">
          🏀 NBA (<span id="count-rel-nba">168</span> Relatórios)
        </button>
        <button class="sp-tab-pill" id="pill-relatorios-yt" onclick="switchRelatoriosTab('yt')">
          📺 YouTube & CazéTV (<span id="count-rel-yt">51</span> Relatórios)
        </button>
        <button class="sp-tab-pill" id="pill-relatorios-fut" onclick="switchRelatoriosTab('fut')">
          ⚽ Auditoria Futebol (<span id="count-rel-fut">41</span> Relatórios)
        </button>
      </div>

      <div class="filter-bar">
        <div class="filter-inputs" style="width: 100%;">
          <input type="text" id="search-relatorios-box" class="search-field" oninput="filterRelatoriosTable()" placeholder="🔍 Buscar relatório por partida, time, data ou responsável...">
        </div>
      </div>

      <div class="sp-table-wrap">
        <div class="sp-table-scroll">
          <table class="sp-list-table">
            <thead>
              <tr>
                <th class="td-center" style="width: 45px;">#</th>
                <th>Nome do Relatório / Partida</th>
                <th>Tipo / Formato</th>
                <th>Tamanho</th>
                <th>Data de Auditoria</th>
                <th>Auditor Responsável</th>
                <th class="td-center" style="width: 140px;">Relatório PDF</th>
              </tr>
            </thead>
            <tbody id="relatorios-table-body">
              <!-- Renderizado via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary);" id="relatorios-footer-count">
        Mostrando relatórios sincronizados com SharePoint Online
      </div>
    </div>

    <!-- SUBMENU 3: VISUALIZADOR DINÂMICO DE LISTAS NATIVAS DO SHAREPOINT (46 LISTAS REAIS) -->
    <div id="pane-list-viewer" class="pane-container">
      <div class="sp-command-bar">
        <div class="sp-command-left">
          <button class="sp-btn-new action-admin-only" onclick="alert('Formulário de inclusão conectado ao SharePoint Online')"><span>+</span> Novo</button>
          <button class="sp-btn-cmd" onclick="alert('Modo de exibição de grade do SharePoint ativado')"><span>田</span> Editar no modo de exibição de grade</button>
          <button class="sp-btn-cmd" onclick="exportGenericListCSV()"><span>📥</span> Exportar CSV</button>
          <button class="sp-btn-cmd" onclick="handleMenuClick('home', 'Página Inicial')"><span>🏠</span> Voltar ao Início</button>
        </div>
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
        Esta lista está sincronizada 1:1 com a esteira oficial do SharePoint Online da Central de Suporte e Captação.
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


    <!-- ABA 8: DASHBOARD & INDICADORES -->
    <div id="pane-dashboard" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">📊 Dashboard Operacional & Indicadores de Transmissão</h2>
        <p class="section-desc">Telemetria de ingest de sinais esportivos, uptime de streaming e prontidão de equipe.</p>
      </div>

      <div class="kpi-row">
        <div class="kpi-box" style="border-left: 4px solid #10B981;">
          <div class="kpi-box-label">Disponibilidade Operacional (SLA)</div>
          <div class="kpi-box-val">99.85%</div>
          <div class="kpi-box-sub">Meta Corporativa: &gt; 99.50%</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #0078D4;">
          <div class="kpi-box-label">Eventos Monitorados 2026</div>
          <div class="kpi-box-val">__EVENTS_COUNT__</div>
          <div class="kpi-box-sub">CazéTV, Prime, Netflix, TNT, Record</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #D97706;">
          <div class="kpi-box-label">Conformidade CLT Art. 66</div>
          <div class="kpi-box-val">100.0%</div>
          <div class="kpi-box-sub">11h de Descanso entre Jornadas</div>
        </div>
        <div class="kpi-box" style="border-left: 4px solid #8B5CF6;">
          <div class="kpi-box-label">Tempo Médio de Reparo (MTTR)</div>
          <div class="kpi-box-val">2.8 min</div>
          <div class="kpi-box-sub">Restabelecimento de Transmissão</div>
        </div>
      </div>

      <div class="escala-footer-grid">
        <div class="escala-info-card">
          <h4>🛰️ Status dos Canais de Ingest</h4>
          <ul class="sobreaviso-schedule-list">
            <li>🟢 <b>YouTube Live (CazéTV):</b> 100% Operacional &bull; Latência 1.1s</li>
            <li>🟢 <b>Amazon Prime Video Sports:</b> 100% Operacional &bull; PVID PV3623</li>
            <li>🟢 <b>Netflix Live (NFL):</b> 100% Operacional &bull; PVID PV3687</li>
            <li>🟢 <b>Max / TNT Sports:</b> 100% Operacional &bull; PVID PV3679</li>
            <li>🟢 <b>Record / PlayPlus:</b> 100% Operacional &bull; Sinais Regionais OK</li>
          </ul>
        </div>
        <div class="escala-info-card">
          <h4>📡 PVIDs de Hardware TV BOX</h4>
          <ul class="sobreaviso-schedule-list">
            <li>📶 <b>PV3623:</b> Central Principal Barra Funda &bull; Primário</li>
            <li>📶 <b>PV3687:</b> Ingest Secundário Fibra Óptica &bull; Ativo</li>
            <li>📶 <b>PV3679:</b> Contingência TV BOX Backup &bull; Standby Quente</li>
          </ul>
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
        <h2 class="section-title">👥 Equipe de Suporte e Captação</h2>
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
      <div class="section-title-wrap">
        <h2 class="section-title">🔐 Controle de Acessos & Mapeamento RBAC (__PERMS_COUNT__ Registros)</h2>
        <p class="section-desc">Matriz de permissões migrada do SharePoint para perfis corporativos Google Workspace.</p>
      </div>
      <div class="filter-bar">
        <div class="filter-inputs">
          <input type="text" id="search-perm-box" class="search-field" placeholder="🔍 Buscar usuário ou grupo...">
        </div>
        <div>
          <button class="btn-action btn-action-primary" onclick="exportPermsCSV()">📥 Exportar Permissões CSV</button>
        </div>
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

    let currentRole = "admin";
    let currentMonth = "Novembro";

    function onRoleChange() {
      const sel = document.getElementById("user-role-select");
      currentRole = sel.value;
      const avatar = document.getElementById("top-user-avatar");

      if (currentRole.startsWith("admin")) {
        if (currentRole === "admin_cassio") avatar.innerText = "CE";
        else if (currentRole === "admin_vinicius") avatar.innerText = "VD";
        else avatar.innerText = "CG";
        avatar.style.background = "#004578";
        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "";
      } else if (currentRole === "operador") {
        avatar.innerText = "OP";
        avatar.style.background = "#059669";
        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "";
      } else {
        avatar.innerText = "LE";
        avatar.style.background = "#64748B";
        document.querySelectorAll(".action-admin-only").forEach(el => el.style.display = "none");
        const permTab = document.getElementById("nav-tab-permissoes");
        if (permTab) permTab.style.display = "none";
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
      'procedimentos': { type: 'drive', name: 'Procedimentos', title: 'Procedimentos Operacionais Padrão (POPs N1)' },
      'documentos': { type: 'drive', name: 'Documentos', title: 'Documentos Compartilhados da Equipe' },
      'capacitacao': { type: 'drive', name: 'Ficha de Capacitação', title: 'Ficha de Capacitação' },
      'tratativa': { type: 'drive', name: 'Tratativa de Problemas de captação', title: 'Tratativa de Problemas de Captação' },
      'doctecnicos': { type: 'drive', name: 'Documentos Técnicos', title: 'Documentos Técnicos (PayTV)' },
      'metas': { type: 'drive', name: 'Metas', title: 'Metas & Acompanhamento da Equipe' },
      'contratos': { type: 'drive', name: 'Controle de contratos parceiros', title: 'Controle de Contratos Parceiros' },
      'automacoes': { type: 'drive', name: 'Repositorio_Automacoes', title: 'Repositório de Automações' },

      // Relatórios Dedicados (NBA, YouTube & Futebol - 260 Casos)
      'relatoriosjogos': { type: 'relatorios', title: 'Relatórios de Jogos (YouTube & NBA)' },

      // Listas Oficiais do SharePoint
      'fornecedores': { type: 'list', name: 'Avaliação Técnica de Fornecedores', title: 'Avaliação Técnica de Fornecedores' },
      'solicitacoes': { type: 'list', name: 'Solicitações de Acesso', title: 'Solicitações de Acesso' },
      'sla': { type: 'list', name: 'SLA', title: 'SLA de Atendimento' },
      'notificacoes': { type: 'list', name: 'Análise de Notificações', title: 'Análise de Notificações' },
      'backup': { type: 'list', name: 'Validação de Backup', title: 'Validação de Backup' },
      'analisedados': { type: 'list', name: 'Analise de Dados', title: 'Análise de Dados' },
      'falhas': { type: 'list', name: 'Confirmação de Falhas Suporte Captação', title: 'Confirmação de Falhas' },
      'antenistas': { type: 'list', name: 'Contatos de Antenistas', title: 'Contatos de Antenistas' },
      'redmine': { type: 'list', name: 'Redmine', title: 'Redmine (Demandas & Chamados)' },
      'hosts': { type: 'list', name: 'Cadastro - Hosts', title: 'Cadastro de Hosts' },
      'cidades': { type: 'list', name: 'Cidades', title: 'Mapeamento de Cidades e Emissoras' },
      'gestaoservicos': { type: 'list', name: 'Painel de gestão de serviços dos CS', title: 'Painel de Gestão de Serviços dos CS' },
      'monitoramentocanais': { type: 'list', name: 'Monitoramento de Canais CS', title: 'Monitoramento de Canais CS' },
      'redescs': { type: 'list', name: 'Configurações de Rede do CS', title: 'Configurações de Rede do CS' },
      'redepcd': { type: 'list', name: 'Mapeamento de Rede do CPD', title: 'Mapeamento de Rede do CPD' },
      'remoto': { type: 'list', name: 'Acesso Remote Control - America Central', title: 'Acesso Remoto & América Central' },
      'links': { type: 'list', name: 'Links de Internet dos Parceiros', title: 'Links de Internet dos Parceiros' },
      'projetos': { type: 'list', name: 'Projetos', title: 'Projetos & Iniciativas' }
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
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(s)) {
        return formatDate(s);
      }
      if (['Ativo', 'Online', 'Concluído', 'Resolvido', 'Vigente', 'Operacional', 'Sim'].includes(s)) {
        return `<span class="badge badge-exibido">${s}</span>`;
      }
      if (s.includes('SLA Estourado')) {
        return `<span class="badge" style="background:#FEE2E2;color:#991B1B;border:1px solid #FECACA;">${s}</span>`;
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
      
      const tEl = document.getElementById('drive-viewer-title');
      const dEl = document.getElementById('drive-viewer-desc');
      const sBox = document.getElementById('drive-viewer-search');
      if (tEl) tEl.innerHTML = currentDriveTitle + ' <span class="star-icon">☆</span>';
      if (dEl) dEl.innerText = `Biblioteca oficial sincronizada 1:1 com o Microsoft SharePoint Online (${drive ? drive.items_count : 0} itens mapeados).`;
      if (sBox) sBox.value = '';
      
      renderCurrentDriveLevel();
    }

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
        return it.name.toLowerCase().includes(q) || (it.lastModifiedBy && it.lastModifiedBy.toLowerCase().includes(q));
      });

      const tbody = document.getElementById('drive-viewer-tbody');
      const footer = document.getElementById('drive-viewer-footer');
      if (!tbody) return;

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 30px; color: #94A3B8;">${q ? 'Nenhum item encontrado para esta busca.' : 'Esta pasta está vazia no SharePoint.'}</td></tr>`;
      } else {
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
            const link = it.webUrl || '#';
            nameHtml = `<span>${icon} ${it.name}</span>`;
            actionHtml = `<a href="${link}" target="_blank" class="btn-doc-download">Abrir ↗</a>`;
          }

          return `
            <tr class="${isFolder ? 'sp-folder-row' : ''}">
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
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${rawItems.length}</b> itens nesta pasta &bull; Sincronizado com Microsoft SharePoint Online`;
      }
    }

    function exportCurrentDriveCSV() {
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      if (!currentLevel || !currentLevel.items) return;
      const items = currentLevel.items;
      let csv = "ID,Nome,Tipo,Extensao,Tamanho_Bytes,Modificado_Em,Modificado_Por,WebUrl" + String.fromCharCode(10);
      items.forEach(it => {
        csv += `"${it.id || ''}","${(it.name || '').replace(/"/g, '""')}","${it.type || ''}","${it.extension || ''}","${it.size || 0}","${it.lastModifiedDateTime || ''}","${it.lastModifiedBy || ''}","${it.webUrl || ''}"` + String.fromCharCode(10);
      });
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
              <td><b>📕 ${it.name}</b></td>
              <td><span class="badge badge-exibido">PDF AUDITORIA OFICIAL (2 PÁG)</span></td>
              <td style="color: #475569;">${sizeStr}</td>
              <td style="color: #64748B;">${modStr}</td>
              <td style="color: #475569;">${authorStr}</td>
              <td class="td-center">
                <a href="${link}" target="_blank" class="btn-doc-download">Baixar PDF ↗</a>
              </td>
            </tr>
          `;
        }).join('');
      }

      if (footer) {
        const catName = currentRelatoriosTab === 'nba' ? 'NBA' : (currentRelatoriosTab === 'yt' ? 'YouTube & CazéTV' : 'Auditoria Futebol');
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${raw.length}</b> relatórios oficiais de ${catName} &bull; Sincronizado com SharePoint Online (Total Geral: 260 relatórios)`;
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
    // 3. CONTROLADOR DE LISTAS NATIVAS REAIS DO SHAREPOINT (46 LISTAS)
    // ==========================================
    let currentRealListName = null;
    let currentRealListTitle = '';

    function openRealList(listName, title) {
      currentRealListName = listName;
      currentRealListTitle = title || listName;
      const listData = SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[listName];

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
          thead.innerHTML = '<tr><th class="td-center" style="width: 45px;">#</th>' + listData.columns.map(col => `<th>${col.displayName || col.name}</th>`).join('') + '</tr>';
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
      const filtered = items.filter(it => {
        if (!q) return true;
        return Object.values(it).some(val => String(val || '').toLowerCase().includes(q));
      });

      if (tbody) {
        if (filtered.length === 0) {
          tbody.innerHTML = `<tr><td colspan="${cols.length + 1}" style="text-align:center; padding: 26px; color: #94A3B8;">Nenhum registro encontrado nesta lista.</td></tr>`;
        } else {
          tbody.innerHTML = filtered.map((it, idx) => {
            const cells = cols.map(c => {
              const val = it[c.name] !== undefined ? it[c.name] : (it[c.displayName] !== undefined ? it[c.displayName] : '');
              return `<td>${formatCellContent(val, c.name)}</td>`;
            }).join('');
            return `<tr><td class="td-center" style="color: #64748B;">${idx + 1}</td>${cells}</tr>`;
          }).join('');
        }
      }

      if (footer) {
        footer.innerHTML = `Mostrando <b>${filtered.length}</b> de <b>${items.length}</b> registros &bull; Sincronizado com Microsoft SharePoint Online`;
      }
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
      document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.pane-container').forEach(pane => pane.classList.remove('active'));

      const res = SP_RESOURCE_MAP[paneId];
      let targetPane = null;

      if (paneId === 'relatoriosjogos' || (res && res.type === 'relatorios')) {
        targetPane = document.getElementById('pane-relatoriosjogos');
        if (targetPane) {
          targetPane.classList.add('active');
          initRelatoriosJogos();
        }
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
        targetPane = document.getElementById('pane-' + paneId);
        if (!targetPane) {
          // Fallback para list-viewer se for uma lista por nome direto
          if (SP_MASTER_DATA.lists && SP_MASTER_DATA.lists[paneId]) {
            targetPane = document.getElementById('pane-list-viewer');
            if (targetPane) {
              targetPane.classList.add('active');
              openRealList(paneId, title);
            }
          } else if (SP_MASTER_DATA.drives && SP_MASTER_DATA.drives[paneId]) {
            targetPane = document.getElementById('pane-drive-viewer');
            if (targetPane) {
              targetPane.classList.add('active');
              openDrive(paneId, title);
            }
          }
        } else {
          targetPane.classList.add('active');
        }
      }

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
        <th class="th-sticky-left" style="min-width: 130px;">Nome Operador</th>
        <th style="min-width: 80px;">Matrícula</th>
        <th style="min-width: 100px;">Horário</th>
        <th style="min-width: 120px;">Equipe</th>`;

      for (let d = 1; d <= numDays; d++) {
        hHtml += `<th style="min-width: 38px;">${d}</th>`;
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
          <td class="td-sticky-left"><b>${op.nome}</b></td>
          <td style="color: #64748B;">${op.matricula || '-'}</td>
          <td style="font-size: 11px;">${op.horario}</td>
          <td><span style="font-size: 11px; color: #0078D4; font-weight: 600;">${op.equipe}</span></td>`;

        for (let d = 1; d <= numDays; d++) {
          const val = (op.dias && op.dias[d]) ? op.dias[d] : "";
          if (val) {
            rHtml += `<td><span class="${getBadgeClass(val)}">${val}</span></td>`;
          } else {
            rHtml += `<td style="color: #CBD5E1;">-</td>`;
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

    function renderTable() {
      const searchBox = document.getElementById("search-box");
      const q = searchBox ? searchBox.value.toLowerCase() : "";
      const canalBox = document.getElementById("filter-canal");
      const fCanal = canalBox ? canalBox.value.toLowerCase() : "";
      const statusBox = document.getElementById("filter-status");
      const fStatus = statusBox ? statusBox.value.toLowerCase() : "";

      const tbody = document.getElementById("table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      let caze = 0, prime = 0, netflix = 0, outros = 0;

      allEvents.forEach((ev) => {
        const cStr = String(ev.canal || "").toLowerCase();
        if (cStr.includes("cazé") || cStr.includes("caze")) caze++;
        else if (cStr.includes("prime") || cStr.includes("amazon")) prime++;
        else if (cStr.includes("netflix")) netflix++;
        else outros++;

        if (fCanal && !cStr.includes(fCanal)) return;
        if (fStatus && !String(ev.status_entrega || "").toLowerCase().includes(fStatus)) return;

        if (q) {
          const fullText = (
            (ev.partida || '') + " " + (ev.campeonato || '') + " " +
            (ev.data || '') + " " + (ev.canal || '') + " " + (ev.responsavel || '')
          ).toLowerCase();
          if (!fullText.includes(q)) return;
        }

        count++;
        const tr = document.createElement("tr");
        tr.innerHTML = `
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
    }

    function renderHospedeirosTable() {
      const sBox = document.getElementById("search-hosp-box");
      const q = sBox ? sBox.value.toLowerCase() : "";
      const tbody = document.getElementById("hosp-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      let count = 0;
      allHospedeiros.forEach((h, i) => {
        if (q) {
          const t = ((h.Title||'') + " " + (h.Nome1||'') + " " + (h.Especialidade||'') + " " + (h.Telefone_x0020_Comercial||'') + " " + (h.Telefone_x0020_Celular||'')).toLowerCase();
          if (!t.includes(q)) return;
        }
        count++;
        const tr = document.createElement("tr");
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

    function toggleOcoSort() {
      ocoSortAsc = !ocoSortAsc;
      renderOcorrenciasTable();
    }

    function formatSPDate(isoStr) {
      if (!isoStr) return '-';
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const pad = n => String(n).padStart(2, '0');
      return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
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

      // 3. Ordenação
      list.sort((a, b) => {
        const da = new Date(a.Criado || 0).getTime();
        const db = new Date(b.Criado || 0).getTime();
        return ocoSortAsc ? (da - db) : (db - da);
      });

      let count = 0;
      list.forEach((o) => {
        count++;
        const tr = document.createElement("tr");

        // Status badge
        let statusBadge = `<span class="sp-badge sp-badge-concluido">Concluído</span>`;
        if (o.Status === "Em andamento") {
          statusBadge = `<span class="sp-badge sp-badge-em-andamento">Em andamento</span>`;
        } else if (o.Status === "Feedback") {
          statusBadge = `<span class="sp-badge sp-badge-feedback">Feedback</span>`;
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

    function renderPermsTable() {
      const tbody = document.getElementById("perms-table-body");
      if (!tbody) return;
      tbody.innerHTML = "";

      allPermissions.forEach((p, i) => {
        let badgeClass = "badge-role-read";
        if (p.google_role === "Administrador") badgeClass = "badge-role-owner";
        else if (p.google_role === "Operador") badgeClass = "badge-role-write";

        const tr = document.createElement("tr");
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
        <p><b>Passo 3:</b> Registrar o ticket de incidente no Redmine e notificar o plantão da Captação via Teams.</p>
        <div style="margin-top: 20px; text-align: right;">
          <button class="btn-action btn-action-primary" onclick="closeModal()">Fechar Procedimento</button>
        </div>
      `;
      document.getElementById("proc-modal").style.display = "flex";
    }

    function closeModal() {
      document.getElementById("proc-modal").style.display = "none";
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
    window.openProcModal = openProcModal;
    window.closeModal = closeModal;
    window.toggleDarkMode = toggleDarkMode;
    window.onRoleChange = onRoleChange;
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
    window.filterListViewerTable = filterListViewerTable;
    window.exportGenericListCSV = exportGenericListCSV;
    window.renderGenericList = renderGenericList;
    window.renderAntenistasTable = renderAntenistasTable;
    window.renderHostsTable = renderHostsTable;

    // Inicialização
    initEscalaMonths();
    renderTable();
    renderHospedeirosTable();
    renderOcorrenciasTable();
    renderAntenistasTable();
    renderHostsTable();
    renderPermsTable();
  </script>
</body>
</html>"""


def generate_portal():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "config", "sharepoint_clean_migrated_events.json")
    perms_path = os.path.join(base_dir, "config", "sharepoint_extracted_permissions.json")
    migrated_data_path = os.path.join(base_dir, "config", "sharepoint_migrated_standalone_data.json")
    escala_path = os.path.join(base_dir, "config", "escala_completa_2026.json")
    raw_escala_excel = os.path.join(base_dir, "config", "Escala de trabalho 2026.xlsx")
    
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
    hosts_path = os.path.join(base_dir, "config", "cadastro_hosts_all.json")
    hosts_dict = {}
    if os.path.exists(hosts_path):
        with open(hosts_path, "r", encoding="utf-8") as f:
            hosts_dict = json.load(f)

    # Carregar Ocorrências Live Sincronizadas do SharePoint (1.000 Casos)
    live_oco_path = os.path.join(base_dir, "config", "painel_ocorrencias_clean_live.json")
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
    master_data_path = os.path.join(base_dir, "config", "sharepoint_portal_master_data.json")
    master_data = {"drives": {}, "lists": {}}
    if os.path.exists(master_data_path):
        with open(master_data_path, "r", encoding="utf-8") as f:
            master_data = json.load(f)
    master_data_json_str = json.dumps(master_data, ensure_ascii=False)


    # Exporta CSV oficial
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
