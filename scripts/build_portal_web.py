# -*- coding: utf-8 -*-
"""
Gerador do Portal Web Oficial do Suporte Captação (Kantar IBOPE Media).
Gera um portal intranet moderno, responsivo, profissional e 100% fiel à HomePage
original do SharePoint (https://adgbl.sharepoint.com/sites/suportecaptacao/SitePages/HomePage.aspx),
integrado com a Programação Oficial de Eventos Streaming (Google Sheets & SharePoint).
"""

import os
import json

def generate_portal():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "config", "sharepoint_clean_migrated_events.json")
    output_dir = os.path.join(base_dir, "portal_web")
    os.makedirs(output_dir, exist_ok=True)
    output_html = os.path.join(output_dir, "index.html")

    events = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            events = json.load(f)

    events_json_str = json.dumps(events, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Suporte e Captação | Portal Corporativo & Streaming Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      /* Microsoft SharePoint Modern Theme (Fluent UI) */
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
      --sp-hero-bg: linear-gradient(135deg, #004B50 0%, #0F3854 50%, #164E63 100%);

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

      --shadow-card: 0 1.6px 3.6px 0 rgba(0,0,0,0.132), 0 0.3px 0.9px 0 rgba(0,0,0,0.108);
      --shadow-hover: 0 6.4px 14.4px 0 rgba(0,0,0,0.132), 0 1.2px 3.6px 0 rgba(0,0,0,0.108);
    }}

    /* Modo Noturno Operacional (Opcional) */
    body.dark-mode {{
      --sp-body-bg: #0B0F19;
      --sp-card-bg: #1E293B;
      --sp-text-main: #F8FAFC;
      --sp-text-secondary: #94A3B8;
      --sp-text-muted: #64748B;
      --sp-border: #334155;
      --sp-border-hover: #475569;
      --sp-nav-bg: #0F172A;
      --sp-hero-bg: linear-gradient(135deg, #091E28 0%, #0F2D3E 50%, #153E54 100%);
      --shadow-card: 0 4px 12px rgba(0,0,0,0.3);
      --shadow-hover: 0 8px 24px rgba(0,0,0,0.5);
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }}

    body {{
      background: var(--sp-body-bg);
      color: var(--sp-text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      transition: background 0.3s, color 0.3s;
    }}

    /* Barra Superior Microsoft 365 (Suite Nav) */
    .suite-nav {{
      background: var(--sp-nav-bg);
      color: #FFFFFF;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 4px rgba(0,0,0,0.14);
    }}

    .suite-nav-left {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .waffle-icon {{
      width: 32px;
      height: 32px;
      display: grid;
      grid-template-columns: repeat(3, 4px);
      gap: 3px;
      place-content: center;
      cursor: pointer;
      border-radius: 4px;
      transition: background 0.2s;
    }}

    .waffle-icon:hover {{
      background: rgba(255,255,255,0.15);
    }}

    .waffle-dot {{
      width: 4px;
      height: 4px;
      background: #FFFFFF;
      border-radius: 1px;
    }}

    .suite-title {{
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.01em;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .suite-title span {{
      font-weight: 400;
      opacity: 0.9;
    }}

    .suite-nav-center {{
      flex: 1;
      max-width: 520px;
      margin: 0 20px;
    }}

    .suite-search-box {{
      width: 100%;
      background: rgba(255,255,255,0.2);
      border: 1px solid transparent;
      border-radius: 4px;
      padding: 6px 14px;
      color: #FFF;
      font-size: 13px;
      outline: none;
      transition: background 0.2s, border 0.2s;
    }}

    .suite-search-box::placeholder {{
      color: rgba(255,255,255,0.8);
    }}

    .suite-search-box:focus {{
      background: #FFFFFF;
      color: #323130;
      border-color: #EDEBE9;
    }}

    .suite-nav-right {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .nav-pill-btn {{
      background: rgba(255,255,255,0.15);
      border: none;
      color: #FFFFFF;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }}

    .nav-pill-btn:hover {{
      background: rgba(255,255,255,0.25);
    }}

    .user-avatar {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #004578;
      border: 2px solid rgba(255,255,255,0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      color: #FFFFFF;
    }}

    /* Menu de Navegação do Site (SharePoint Quick Launch / Hub Nav) */
    .site-nav-bar {{
      background: var(--sp-card-bg);
      border-bottom: 1px solid var(--sp-border);
      padding: 0 24px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

    .site-nav-container {{
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      overflow-x: auto;
    }}

    .site-brand-row {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 12px 0;
    }}

    .site-brand-icon {{
      width: 38px;
      height: 38px;
      border-radius: 6px;
      background: #0078D4;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #FFFFFF;
      font-weight: 800;
      font-size: 18px;
    }}

    .site-brand-info h2 {{
      font-size: 16px;
      font-weight: 700;
      color: var(--sp-text-main);
      line-height: 1.2;
    }}

    .site-brand-info p {{
      font-size: 12px;
      color: var(--sp-text-secondary);
    }}

    .nav-menu-tabs {{
      display: flex;
      gap: 4px;
      align-items: center;
    }}

    .tab-link {{
      background: transparent;
      border: none;
      color: var(--sp-text-secondary);
      padding: 14px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      border-bottom: 3px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }}

    .tab-link:hover {{
      color: var(--sp-theme-primary);
      background: rgba(0, 120, 212, 0.04);
    }}

    .tab-link.active {{
      color: var(--sp-theme-primary);
      border-bottom-color: var(--sp-theme-primary);
      font-weight: 700;
    }}

    /* Conteúdo Principal */
    .main-body {{
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px;
      flex: 1;
    }}

    /* HERO BANNER 1:1 SHAREPOINT HOMEPAGE */
    .hero-banner {{
      background: var(--sp-hero-bg);
      border-radius: 8px;
      color: #FFFFFF;
      padding: 36px 40px;
      margin-bottom: 28px;
      display: grid;
      grid-template-columns: 1fr 280px;
      gap: 32px;
      align-items: center;
      box-shadow: 0 4px 16px rgba(0,0,0,0.18);
      position: relative;
      overflow: hidden;
    }}

    .hero-banner::after {{
      content: "";
      position: absolute;
      right: -60px;
      bottom: -60px;
      width: 240px;
      height: 240px;
      background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
      border-radius: 50%;
      pointer-events: none;
    }}

    .hero-content h1 {{
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 12px;
      letter-spacing: -0.02em;
      color: #FFFFFF;
    }}

    .hero-content p {{
      font-size: 15px;
      line-height: 1.5;
      color: #E2E8F0;
      max-width: 780px;
    }}

    .weather-widget {{
      background: rgba(255, 255, 255, 0.12);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      padding: 16px 20px;
      text-align: right;
    }}

    .weather-location {{
      font-size: 13px;
      font-weight: 600;
      color: #E2E8F0;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
    }}

    .weather-temp {{
      font-size: 30px;
      font-weight: 700;
      color: #FFFFFF;
      margin: 4px 0;
    }}

    .weather-status {{
      font-size: 12px;
      color: #CBD5E1;
    }}

    /* SEÇÃO 1: LINKS ÚTEIS (QUICK LINKS - BUTTON LAYOUT SHAREPOINT) */
    .section-title-wrap {{
      margin-bottom: 16px;
    }}

    .section-title {{
      font-size: 20px;
      font-weight: 700;
      color: var(--sp-text-main);
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .section-desc {{
      font-size: 13px;
      color: var(--sp-text-secondary);
      margin-top: 4px;
    }}

    .quick-links-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }}

    .quick-link-btn {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
      color: var(--sp-text-main);
      box-shadow: var(--shadow-card);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
    }}

    .quick-link-btn:hover {{
      border-color: var(--sp-theme-primary);
      transform: translateY(-2px);
      box-shadow: var(--shadow-hover);
    }}

    .quick-link-icon-box {{
      width: 40px;
      height: 40px;
      border-radius: 6px;
      background: var(--sp-theme-lighter);
      color: var(--sp-theme-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      flex-shrink: 0;
    }}

    .quick-link-text {{
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .quick-link-title {{
      font-size: 14px;
      font-weight: 600;
      color: var(--sp-text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .quick-link-sub {{
      font-size: 11px;
      color: var(--sp-text-muted);
      margin-top: 2px;
    }}

    /* SEÇÃO 2: CHAMADA PARA AÇÃO (CTA & BOTÕES) */
    .cta-container {{
      display: grid;
      grid-template-columns: 2fr 1.2fr;
      gap: 20px;
      margin-bottom: 28px;
    }}

    .cta-banner-card {{
      background: linear-gradient(135deg, #106EBE 0%, #0078D4 100%);
      color: #FFFFFF;
      border-radius: 8px;
      padding: 24px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: var(--shadow-card);
      gap: 20px;
    }}

    .cta-banner-card h3 {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 6px;
    }}

    .cta-banner-card p {{
      font-size: 13px;
      color: #E2E8F0;
    }}

    .btn-sp-white {{
      background: #FFFFFF;
      color: #0078D4;
      font-size: 13px;
      font-weight: 700;
      padding: 10px 20px;
      border-radius: 4px;
      text-decoration: none;
      border: none;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.2s, transform 0.15s;
      box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }}

    .btn-sp-white:hover {{
      background: #F3F2F1;
      transform: translateY(-1px);
    }}

    .cta-redmine-card {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 8px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      box-shadow: var(--shadow-card);
    }}

    .cta-redmine-card h4 {{
      font-size: 14px;
      font-weight: 700;
      color: var(--sp-text-main);
      margin-bottom: 6px;
    }}

    .cta-redmine-card p {{
      font-size: 12px;
      color: var(--sp-text-secondary);
      margin-bottom: 12px;
    }}

    .btn-sp-primary {{
      background: var(--sp-theme-primary);
      color: #FFFFFF;
      font-size: 13px;
      font-weight: 600;
      padding: 9px 18px;
      border-radius: 4px;
      text-decoration: none;
      border: none;
      cursor: pointer;
      transition: background 0.2s;
    }}

    .btn-sp-primary:hover {{
      background: var(--sp-theme-dark-alt);
    }}

    /* SEÇÃO 3: LINKS EXTERNOS (WAFFLE / TILES LAYOUT) */
    .waffle-links-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
      gap: 12px;
      margin-bottom: 28px;
    }}

    .waffle-link-card {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 16px 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      text-decoration: none;
      color: var(--sp-text-main);
      box-shadow: var(--shadow-card);
      transition: all 0.2s;
    }}

    .waffle-link-card:hover {{
      border-color: var(--sp-theme-primary);
      transform: translateY(-2px);
      box-shadow: var(--shadow-hover);
    }}

    .waffle-link-icon {{
      font-size: 24px;
      margin-bottom: 8px;
    }}

    .waffle-link-title {{
      font-size: 12px;
      font-weight: 600;
      line-height: 1.3;
    }}

    /* SEÇÃO 4: CONHEÇA NOSSA EQUIPE (PEOPLE WEB PART SHAREPOINT) */
    .team-section-card {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 28px;
      box-shadow: var(--shadow-card);
    }}

    .team-group {{
      margin-bottom: 24px;
    }}

    .team-group:last-child {{
      margin-bottom: 0;
    }}

    .team-group-title {{
      font-size: 15px;
      font-weight: 700;
      color: var(--sp-theme-primary);
      border-bottom: 2px solid var(--sp-theme-light);
      padding-bottom: 6px;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .team-members-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}

    .person-card {{
      background: var(--sp-body-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 12px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      transition: border-color 0.2s;
    }}

    .person-card:hover {{
      border-color: var(--sp-theme-primary);
    }}

    .person-avatar {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0078D4, #004578);
      color: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 700;
      flex-shrink: 0;
    }}

    .person-info {{
      overflow: hidden;
      flex: 1;
    }}

    .person-name {{
      font-size: 13px;
      font-weight: 700;
      color: var(--sp-text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .person-role {{
      font-size: 11px;
      font-weight: 600;
      color: var(--sp-theme-primary);
      margin: 1px 0;
    }}

    .person-dept {{
      font-size: 10px;
      color: var(--sp-text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .person-email-link {{
      font-size: 11px;
      color: var(--sp-text-secondary);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-top: 3px;
    }}

    .person-email-link:hover {{
      color: var(--sp-theme-primary);
      text-decoration: underline;
    }}

    /* SEÇÃO 5: PROGRAMAÇÃO STREAMING & TABELAS */
    .pane-container {{
      display: none;
    }}

    .pane-container.active {{
      display: block;
      animation: fadeIn 0.2s ease-in;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}

    .kpi-box {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 14px 16px;
      box-shadow: var(--shadow-card);
    }}

    .kpi-box-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--sp-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}

    .kpi-box-val {{
      font-size: 24px;
      font-weight: 700;
      color: var(--sp-text-main);
      margin-top: 4px;
    }}

    .kpi-box-sub {{
      font-size: 11px;
      color: var(--sp-text-muted);
      margin-top: 2px;
    }}

    .filter-bar {{
      background: var(--sp-card-bg);
      border: 1px solid var(--sp-border);
      border-radius: 6px;
      padding: 12px 16px;
      margin-bottom: 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      box-shadow: var(--shadow-card);
    }}

    .filter-inputs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      flex: 1;
    }}

    .search-field {{
      background: var(--sp-body-bg);
      border: 1px solid var(--sp-border);
      color: var(--sp-text-main);
      padding: 7px 12px;
      border-radius: 4px;
      font-size: 13px;
      min-width: 260px;
      flex: 1;
      outline: none;
    }}

    .search-field:focus {{
      border-color: var(--sp-theme-primary);
    }}

    .select-field {{
      background: var(--sp-body-bg);
      border: 1px solid var(--sp-border);
      color: var(--sp-text-main);
      padding: 7px 12px;
      border-radius: 4px;
      font-size: 13px;
      outline: none;
      cursor: pointer;
    }}

    .btn-action {{
      padding: 7px 14px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: none;
      transition: all 0.2s;
    }}

    .btn-action-primary {{
      background: var(--sp-theme-primary);
      color: #FFF;
    }}

    .btn-action-primary:hover {{
      background: var(--sp-theme-dark-alt);
    }}

    .btn-action-secondary {{
      background: var(--sp-body-bg);
      border: 1px solid var(--sp-border);
      color: var(--sp-text-main);
    }}

    .btn-action-secondary:hover {{
      border-color: var(--sp-theme-primary);
    }}

    /* Tabela Idêntica às SharePoint Modern Lists */
    .sp-table-wrap {{
      background: #FFFFFF;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      overflow: hidden;
      box-shadow: var(--shadow-card);
    }}

    .sp-table-scroll {{
      max-height: 600px;
      overflow-y: auto;
      overflow-x: auto;
    }}

    table.sp-list-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
      color: #24292F;
    }}

    table.sp-list-table thead th {{
      background: #F8FAFC;
      color: #475569;
      font-weight: 700;
      padding: 10px 12px;
      border-bottom: 2px solid #CBD5E1;
      border-right: 1px solid #E2E8F0;
      position: sticky;
      top: 0;
      z-index: 10;
      white-space: nowrap;
    }}

    table.sp-list-table tbody tr {{
      background: #FFFBEB;
      border-bottom: 1px solid #E2E8F0;
      transition: background 0.15s;
    }}

    table.sp-list-table tbody tr:hover {{
      background: #FEF3C7;
    }}

    table.sp-list-table tbody td {{
      padding: 8px 12px;
      border-right: 1px solid #E2E8F0;
      vertical-align: middle;
      white-space: nowrap;
    }}

    .td-center {{ text-align: center; }}

    .partida-title {{
      font-weight: 700;
      color: #166534;
      white-space: normal;
      min-width: 220px;
    }}

    /* Badges de Cores Oficiais */
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-align: center;
    }}

    .badge-caze {{ background: var(--badge-caze-bg); color: var(--badge-caze-txt); }}
    .badge-prime {{ background: var(--badge-prime-bg); color: var(--badge-prime-txt); }}
    .badge-netflix {{ background: var(--badge-netflix-bg); color: var(--badge-netflix-txt); }}
    .badge-tnt {{ background: var(--badge-tnt-bg); color: var(--badge-tnt-txt); }}
    .badge-record {{ background: var(--badge-record-bg); color: var(--badge-record-txt); }}
    .badge-dazn {{ background: var(--badge-dazn-bg); color: var(--badge-dazn-txt); }}
    .badge-default {{ background: #E2E8F0; color: #334155; }}

    .badge-pvid {{
      background: var(--badge-pvid-bg);
      color: var(--badge-pvid-txt);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }}

    .badge-pendente {{ background: var(--badge-pend-bg); color: var(--badge-pend-txt); }}
    .badge-exibido {{ background: var(--badge-exib-bg); color: var(--badge-exib-txt); }}
    .badge-nao-exibido {{ background: var(--badge-nao-bg); color: var(--badge-nao-txt); }}

    /* Rodapé Corporativo */
    .site-footer {{
      background: var(--sp-card-bg);
      border-top: 1px solid var(--sp-border);
      padding: 20px 24px;
      margin-top: 32px;
    }}

    .site-footer-container {{
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      font-size: 12px;
      color: var(--sp-text-secondary);
    }}

    @media (max-width: 900px) {{
      .hero-banner {{ grid-template-columns: 1fr; padding: 24px; }}
      .cta-container {{ grid-template-columns: 1fr; }}
      .suite-nav-center {{ display: none; }}
      .suite-nav {{ padding: 0 12px; }}
    }}
  </style>
</head>
<body>

  <!-- 1. SUITE NAV (MICROSOFT 365 TOPBAR) -->
  <header class="suite-nav">
    <div class="suite-nav-left">
      <div class="waffle-icon" title="Inicializador de Aplicativos Microsoft 365">
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
        <div class="waffle-dot"></div><div class="waffle-dot"></div><div class="waffle-dot"></div>
      </div>
      <div class="suite-title">
        SharePoint <span>| Suporte e Captação</span>
      </div>
    </div>

    <div class="suite-nav-center">
      <input type="text" class="suite-search-box" id="global-search" placeholder="Pesquisar neste site, documentos, equipe ou partidas...">
    </div>

    <div class="suite-nav-right">
      <button class="nav-pill-btn" onclick="toggleDarkMode()" title="Alternar Modo Escuro / Claro">
        <span id="dark-mode-icon">🌙</span> Modo Operacional
      </button>
      <div class="user-avatar" title="Kantar IBOPE Media — Suporte Captação">SC</div>
    </div>
  </header>

  <!-- 2. SITE NAVIGATION & HUB TITLE -->
  <nav class="site-nav-bar">
    <div class="site-nav-container">
      <div class="site-brand-row">
        <div class="site-brand-icon">SC</div>
        <div class="site-brand-info">
          <h2>Suporte e Captação</h2>
          <p>Kantar IBOPE Media — Operations Hub, LATAM Advertising Intelligence</p>
        </div>
      </div>

      <div class="nav-menu-tabs">
        <button class="tab-link active" onclick="showPane('home')">🏠 Página Inicial</button>
        <button class="tab-link" onclick="showPane('streaming')">⚽ Programação Streaming (862)</button>
        <button class="tab-link" onclick="showPane('receptores')">📡 Receptores & TV BOX</button>
        <button class="tab-link" onclick="showPane('equipe')">👥 Equipe & Contatos</button>
        <button class="tab-link" onclick="showPane('links')">🔗 Links Úteis & Externos</button>
      </div>
    </div>
  </nav>

  <!-- 3. CONTEÚDO PRINCIPAL -->
  <main class="main-body">

    <!-- ABA 1: HOME PAGE 1:1 RÉPLICA SHAREPOINT -->
    <div id="pane-home" class="pane-container active">

      <!-- HERO BANNER -->
      <section class="hero-banner">
        <div class="hero-content">
          <h1>Suporte e Captação</h1>
          <p>
            Bem vindo(a) ao site da equipe de Suporte e Captação! Aqui você pode encontrar informações sobre problemas técnicos, verificar o status das ocorrências, localizar documentos e dados referentes à área e muito mais.
          </p>
        </div>
        <div class="weather-widget">
          <div class="weather-location">📍 São Paulo, Brasil</div>
          <div class="weather-temp">24°C</div>
          <div class="weather-status">⛅ Parcialmente nublado • Sensação 25°C</div>
        </div>
      </section>

      <!-- SEÇÃO LINKS ÚTEIS (9 CARDS DO SHAREPOINT ORIGINAL) -->
      <section>
        <div class="section-title-wrap">
          <h2 class="section-title">📌 Links úteis</h2>
          <p class="section-desc">Repositório central para todos os documentos relacionados às metas e objetivos da equipe.</p>
        </div>

        <div class="quick-links-grid">
          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Lists/Contato%20Tcnico%20de%20Hospedeiros/Teste.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">📞</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Contatos Hospedeiros</span>
              <span class="quick-link-sub">Contatos técnicos e centrais</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Documentos%20Compartilhados/Forms/AllItems.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">📁</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Documentos</span>
              <span class="quick-link-sub">Arquivos e compartilhamentos</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/SitePages/Escala.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">📅</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Escala de Trabalho</span>
              <span class="quick-link-sub">Turnos e escalas de plantão</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/SitePages/Dashboard.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">📊</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Dashboard & Indicadores</span>
              <span class="quick-link-sub">Métricas operacionais de captação</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Metas" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">🎯</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Metas</span>
              <span class="quick-link-sub">Metas e objetivos da equipe</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Lists/Painel%20de%20Ocorrncias/AllItems.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">🚨</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Painel de Ocorrências</span>
              <span class="quick-link-sub">Status e registro de incidentes</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Procedimentos/Forms/AllItems.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">📖</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Procedimentos N1</span>
              <span class="quick-link-sub">Manuais e POPs operacionais</span>
            </div>
          </a>

          <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/SitePages/HomePage.aspx" target="_blank" class="quick-link-btn">
            <div class="quick-link-icon-box">🚀</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Projetos</span>
              <span class="quick-link-sub">Iniciativas e melhorias da área</span>
            </div>
          </a>

          <div onclick="showPane('streaming')" class="quick-link-btn" style="border-left: 4px solid #10B981;">
            <div class="quick-link-icon-box" style="background: #DCFCE7; color: #166534;">⚽</div>
            <div class="quick-link-text">
              <span class="quick-link-title">Programação de Eventos Streaming</span>
              <span class="quick-link-sub" style="color: #166534; font-weight: 600;">862 Jogos Sincronizados ↗</span>
            </div>
          </div>
        </div>
      </section>

      <!-- SEÇÃO CHAMADA PARA AÇÃO & SUGESTÕES (CTAS DO SHAREPOINT ORIGINAL) -->
      <section class="cta-container">
        <div class="cta-banner-card">
          <div>
            <h3>Entre em contato com a nossa equipe</h3>
            <p>Precisa de suporte imediato ou alinhamento técnico com o plantão da Captação? Chame diretamente no Teams.</p>
          </div>
          <a href="https://teams.microsoft.com/l/team/19:DbmEit-Jw5Egnzv9KJysAxgT20jeLg_9HvF-OtRncrE1@thread.tacv2/conversations?groupId=b85ee2f2-68d9-461a-8ba8-d4eecbf19d94&tenantId=1e355c04-e0a4-42ed-8e2d-7351591f0ef1" target="_blank" class="btn-sp-white">
            💬 Enviar uma mensagem
          </a>
        </div>

        <div class="cta-redmine-card">
          <h4>Sugestões e Demandas</h4>
          <p>Sugestões e Melhorias para o Portal e SharePoint de Captação.</p>
          <a href="http://10.1.0.39/redmine/projects/suporte-captacao-demandas-sharepoint/issues?set_filter=1&tracker_id=3" target="_blank" class="btn-sp-primary">
            📝 Abrir no Redmine
          </a>
        </div>
      </section>

      <!-- SEÇÃO LINKS EXTERNOS (WAFFLE DO SHAREPOINT ORIGINAL) -->
      <section>
        <div class="section-title-wrap">
          <h2 class="section-title">🌐 Links Externos</h2>
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
      </section>

      <!-- SEÇÃO CONHEÇA NOSSA EQUIPE (PEOPLE DO SHAREPOINT ORIGINAL) -->
      <section class="team-section-card">
        <div class="section-title-wrap" style="margin-bottom: 20px;">
          <h2 class="section-title">👥 CONHEÇA NOSSA EQUIPE</h2>
          <p class="section-desc">Estrutura organizacional da equipe de Suporte e Captação da Kantar IBOPE Media.</p>
        </div>

        <!-- Grupo: Administração -->
        <div class="team-group">
          <div class="team-group-title">🏢 Administração</div>
          <div class="team-members-grid">
            <div class="person-card">
              <div class="person-avatar">AU</div>
              <div class="person-info">
                <div class="person-name">Andre Toshio Uiete Uehara</div>
                <div class="person-role">Assistente Administrativo</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:andre.uehara@ibope.com" class="person-email-link">✉️ andre.uehara@ibope.com</a>
              </div>
            </div>
          </div>
        </div>

        <!-- Grupo: Gestores -->
        <div class="team-group">
          <div class="team-group-title">👔 Gestores</div>
          <div class="team-members-grid">
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #10B981, #047857);">CG</div>
              <div class="person-info">
                <div class="person-name">Cleber De Souza Goncalves</div>
                <div class="person-role">COORD. SUPORTE CAPTAÇÃO</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:cleber.goncalves@ibope.com" class="person-email-link">✉️ cleber.goncalves@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #10B981, #047857);">LL</div>
              <div class="person-info">
                <div class="person-name">Luiz De Sa Lemos</div>
                <div class="person-role">DIR. SUPORTE CAPTAÇÃO LATAM</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:luiz.lemos@ibope.com" class="person-email-link">✉️ luiz.lemos@ibope.com</a>
              </div>
            </div>
          </div>
        </div>

        <!-- Grupo: Análise de Dados -->
        <div class="team-group">
          <div class="team-group-title">📊 Análise de Dados</div>
          <div class="team-members-grid">
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #8B5CF6, #6D28D9);">MM</div>
              <div class="person-info">
                <div class="person-name">Maria Simone De Santana Matos</div>
                <div class="person-role">Analista de dados Jr.</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:maria.matos@ibope.com" class="person-email-link">✉️ maria.matos@ibope.com</a>
              </div>
            </div>
          </div>
        </div>

        <!-- Grupo: Suporte N1 -->
        <div class="team-group">
          <div class="team-group-title">🛠️ Suporte N1</div>
          <div class="team-members-grid">
            <div class="person-card">
              <div class="person-avatar">AC</div>
              <div class="person-info">
                <div class="person-name">ALAN KELVIN CHURA CARRILLO</div>
                <div class="person-role">TEC. SUPORTE JR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:alan.carrillo@ibope.com" class="person-email-link">✉️ alan.carrillo@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">BV</div>
              <div class="person-info">
                <div class="person-name">Bruno Lopes Viana</div>
                <div class="person-role">TEC. SUPORTE JR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:bruno.viana@ibope.com" class="person-email-link">✉️ bruno.viana@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">CG</div>
              <div class="person-info">
                <div class="person-name">Cleber Rodrigo Gomes</div>
                <div class="person-role">TEC. SUPORTE JR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:cleber.gomes@ibope.com" class="person-email-link">✉️ cleber.gomes@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">CO</div>
              <div class="person-info">
                <div class="person-name">Cassio Esteves De Oliveira</div>
                <div class="person-role">TEC. SUPORTE JR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:cassio.oliveira@ibope.com" class="person-email-link">✉️ cassio.oliveira@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">RM</div>
              <div class="person-info">
                <div class="person-name">RODRIGO DE ALMEIDA MEIRELLES</div>
                <div class="person-role">TEC. SUPORTE JR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:rodrigo.meirelles@ibope.com" class="person-email-link">✉️ rodrigo.meirelles@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">RS</div>
              <div class="person-info">
                <div class="person-name">Rômulo Silva</div>
                <div class="person-role">Tecnico De Suporte Jr</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:romulo.silva@ibope.com" class="person-email-link">✉️ romulo.silva@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar">MF</div>
              <div class="person-info">
                <div class="person-name">Marcelo Fialho</div>
                <div class="person-role">Tecnico De Suporte Jr</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:marcelo.fialho@ibope.com" class="person-email-link">✉️ marcelo.fialho@ibope.com</a>
              </div>
            </div>
          </div>
        </div>

        <!-- Grupo: Suporte N2 -->
        <div class="team-group">
          <div class="team-group-title">⚡ Suporte N2</div>
          <div class="team-members-grid">
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #00509E, #002855);">JM</div>
              <div class="person-info">
                <div class="person-name">Joao Diego Silva Merino</div>
                <div class="person-role">TEC. SUPORTE PL</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:joao.merino@ibope.com" class="person-email-link">✉️ joao.merino@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #00509E, #002855);">LF</div>
              <div class="person-info">
                <div class="person-name">Lucieudes Vicente Ferreira</div>
                <div class="person-role">TEC. SUPORTE PL</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:lucieudes.ferreira@ibope.com" class="person-email-link">✉️ lucieudes.ferreira@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #00509E, #002855);">MP</div>
              <div class="person-info">
                <div class="person-name">Marcelo Pereira Silva</div>
                <div class="person-role">LIDER TECNICO LATAM</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:marcelo.pereira@ibope.com" class="person-email-link">✉️ marcelo.pereira@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #00509E, #002855);">MB</div>
              <div class="person-info">
                <div class="person-name">Marcos Antonio Bezerra Da Silva</div>
                <div class="person-role">TEC. SUPORTE SR</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:marcos.bezerra@ibope.com" class="person-email-link">✉️ marcos.bezerra@ibope.com</a>
              </div>
            </div>
            <div class="person-card">
              <div class="person-avatar" style="background: linear-gradient(135deg, #00509E, #002855);">VD</div>
              <div class="person-info">
                <div class="person-name">Vinicius Dantas Ferreira Da Silva</div>
                <div class="person-role">Tec. Suporte Pl</div>
                <div class="person-dept">Operations Hub, LATAM Advertising Intelligence</div>
                <a href="mailto:vinicius.dantas@ibope.com" class="person-email-link">✉️ vinicius.dantas@ibope.com</a>
              </div>
            </div>
          </div>
        </div>

      </section>

    </div>

    <!-- ABA 2: PROGRAMAÇÃO STREAMING COMPLETA (862 JOGOS) -->
    <div id="pane-streaming" class="pane-container">

      <!-- Métricas / KPIs -->
      <div class="kpi-row">
        <div class="kpi-box">
          <div class="kpi-box-label">Total de Confrontos</div>
          <div class="kpi-box-val" id="kpi-total">862</div>
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

      <!-- Barra de Filtros e Busca -->
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
          <button class="btn-action btn-action-secondary" onclick="syncLiveAPI()">🔄 Sincronizar em Tempo Real</button>
          <button class="btn-action btn-action-primary" onclick="exportCSV()">📥 Exportar CSV</button>
        </div>
      </div>

      <!-- Tabela Oficial de Eventos -->
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
              <!-- Linhas geradas via JavaScript -->
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top: 10px; font-size: 12px; color: var(--sp-text-secondary); display: flex; justify-content: space-between;">
        <div>Mostrando <b id="showing-count" style="color: var(--sp-theme-primary);">0</b> eventos filtrados</div>
        <div>Padrão de Cores Oficial SharePoint Modern Lists</div>
      </div>

    </div>

    <!-- ABA 3: RECEPTORES & TV BOX -->
    <div id="pane-receptores" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">📡 Mapa de Receptores & Dispositivos de Captura (PVID TV BOX)</h2>
        <p class="section-desc">Configurações de sinal, hardware de captura e redundância dos decodificadores.</p>
      </div>

      <div class="quick-links-grid" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));">
        <div class="quick-link-btn" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 700; font-size: 15px;">CAZETV - PV3623</span>
            <span class="badge badge-caze">ATIVO</span>
          </div>
          <div style="font-size: 12px; color: var(--sp-text-secondary); line-height: 1.6; width: 100%;">
            <div><b>Plataforma:</b> YouTube Live & CazéTV PPV</div>
            <div><b>PVID Oficial:</b> PV3623</div>
            <div><b>Resolução / Taxa:</b> 1080p @ 60fps</div>
            <div><b>Responsável Backup:</b> Cleber / Marcelo</div>
          </div>
        </div>

        <div class="quick-link-btn" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 700; font-size: 15px;">Prime Video - PV3687</span>
            <span class="badge badge-prime">ATIVO</span>
          </div>
          <div style="font-size: 12px; color: var(--sp-text-secondary); line-height: 1.6; width: 100%;">
            <div><b>Plataforma:</b> Amazon Prime Video Sports</div>
            <div><b>PVID Oficial:</b> PV3687</div>
            <div><b>Resolução / Taxa:</b> 1080p @ 60fps</div>
            <div><b>Responsável Backup:</b> Lucieudes / Cleber</div>
          </div>
        </div>

        <div class="quick-link-btn" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 700; font-size: 15px;">Netflix - PV3679</span>
            <span class="badge badge-netflix">ATIVO</span>
          </div>
          <div style="font-size: 12px; color: var(--sp-text-secondary); line-height: 1.6; width: 100%;">
            <div><b>Plataforma:</b> Netflix Live Events (NFL)</div>
            <div><b>PVID Oficial:</b> PV3679</div>
            <div><b>Resolução / Taxa:</b> 4K UHD / 1080p</div>
            <div><b>Responsável Backup:</b> Cleber BL01</div>
          </div>
        </div>

        <div class="quick-link-btn" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 700; font-size: 15px;">TNT - PV316</span>
            <span class="badge badge-tnt">ATIVO</span>
          </div>
          <div style="font-size: 12px; color: var(--sp-text-secondary); line-height: 1.6; width: 100%;">
            <div><b>Plataforma:</b> TNT Sports / Max (Paulistão)</div>
            <div><b>PVID Oficial:</b> PV316</div>
            <div><b>Resolução / Taxa:</b> 1080i HD</div>
            <div><b>Responsável Backup:</b> Lucieudes BL01</div>
          </div>
        </div>

        <div class="quick-link-btn" style="flex-direction: column; align-items: flex-start;">
          <div style="display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 10px;">
            <span style="font-weight: 700; font-size: 15px;">Record - PV58</span>
            <span class="badge badge-record">ATIVO</span>
          </div>
          <div style="font-size: 12px; color: var(--sp-text-secondary); line-height: 1.6; width: 100%;">
            <div><b>Plataforma:</b> Record TV / PlayPlus</div>
            <div><b>PVID Oficial:</b> PV58</div>
            <div><b>Resolução / Taxa:</b> 1080i ISDB-T</div>
            <div><b>Responsável Backup:</b> Marcelo BL01</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ABA 4: EQUIPE (ESPELHO DEDICADO) -->
    <div id="pane-equipe" class="pane-container">
      <div class="team-section-card">
        <div class="section-title-wrap" style="margin-bottom: 20px;">
          <h2 class="section-title">👥 Equipe & Escala de Plantão</h2>
          <p class="section-desc">Contatos, cargos e divisões de plantão da equipe de Suporte Captação.</p>
        </div>
        <p style="font-size: 13px; color: var(--sp-text-secondary); margin-bottom: 16px;">
          Todos os membros da equipe contam com perfis integrados ao Microsoft 365. Clique no e-mail para abrir mensagem direta no Outlook ou Teams.
        </p>
      </div>
    </div>

    <!-- ABA 5: LINKS & SISTEMAS -->
    <div id="pane-links" class="pane-container">
      <div class="section-title-wrap">
        <h2 class="section-title">🔗 Diretório de Links & Sistemas Oficiais</h2>
        <p class="section-desc">Acesso a todos os portais corporativos e ferramentas de telemetria.</p>
      </div>
    </div>

  </main>

  <!-- RODAPÉ CORPORATIVO -->
  <footer class="site-footer">
    <div class="site-footer-container">
      <div><b>Kantar IBOPE Media</b> — Central de Operações & Suporte Captação © 2026</div>
      <div>Sincronizado automaticamente via <b>Monitor de Esportes v2.5.17</b> & Google Workspace</div>
    </div>
  </footer>

  <script>
    // Dataset inicial seguro
    let allEvents = {events_json_str};

    // Navegação de Abas
    function showPane(paneId) {{
      document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.pane-container').forEach(pane => pane.classList.remove('active'));

      const targetPane = document.getElementById('pane-' + paneId);
      if (targetPane) targetPane.classList.add('active');

      document.querySelectorAll('.tab-link').forEach(btn => {{
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(paneId)) {{
          btn.classList.add('active');
        }}
      }});

      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // Modo Escuro Operacional
    function toggleDarkMode() {{
      document.body.classList.toggle('dark-mode');
      const isDark = document.body.classList.contains('dark-mode');
      document.getElementById('dark-mode-icon').innerText = isDark ? '☀️' : '🌙';
    }}

    // Badges de Canal
    function getChannelBadge(canal) {{
      const c = String(canal || "").toLowerCase();
      if (c.includes("cazé") || c.includes("caze")) return '<span class="badge badge-caze">' + canal + '</span>';
      if (c.includes("prime") || c.includes("amazon")) return '<span class="badge badge-prime">' + canal + '</span>';
      if (c.includes("netflix")) return '<span class="badge badge-netflix">' + canal + '</span>';
      if (c.includes("tnt") || c.includes("max") || c.includes("hbo")) return '<span class="badge badge-tnt">' + canal + '</span>';
      if (c.includes("record")) return '<span class="badge badge-record">' + canal + '</span>';
      if (c.includes("dazn")) return '<span class="badge badge-dazn">' + canal + '</span>';
      return '<span class="badge badge-default">' + (canal || "-") + '</span>';
    }}

    // Badges de Status
    function getStatusBadge(status) {{
      const s = String(status || "").toLowerCase();
      if (s.includes("exibido") && !s.includes("não") && !s.includes("nao")) return '<span class="badge badge-exibido">' + status + '</span>';
      if (s.includes("não") || s.includes("nao") || s.includes("cancelado")) return '<span class="badge badge-nao-exibido">' + status + '</span>';
      return '<span class="badge badge-pendente">' + (status || "Pendente") + '</span>';
    }}

    // Renderizar Tabela
    function renderTable() {{
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

      allEvents.forEach((ev, idx) => {{
        const cStr = String(ev.canal || "").toLowerCase();
        if (cStr.includes("cazé") || cStr.includes("caze")) caze++;
        else if (cStr.includes("prime") || cStr.includes("amazon")) prime++;
        else if (cStr.includes("netflix")) netflix++;
        else outros++;

        if (fCanal && !cStr.includes(fCanal)) return;
        if (fStatus && !String(ev.status_entrega || "").toLowerCase().includes(fStatus)) return;

        if (q) {{
          const fullText = (
            (ev.partida || '') + " " + (ev.campeonato || '') + " " +
            (ev.data || '') + " " + (ev.canal || '') + " " + (ev.responsavel || '')
          ).toLowerCase();
          if (!fullText.includes(q)) return;
        }}

        count++;
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="td-center" style="color: #64748B; font-weight: 600;">${{count}}</td>
          <td class="td-center">${{ev.mes || '-'}}</td>
          <td class="td-center" style="font-weight: 600;">${{ev.data || '-'}}</td>
          <td class="td-center">${{ev.horario || '-'}}</td>
          <td>${{ev.campeonato || '-'}}</td>
          <td class="partida-title">${{ev.partida || '-'}}</td>
          <td>${{ev.responsavel || '-'}}</td>
          <td class="td-center">${{getChannelBadge(ev.canal)}}</td>
          <td class="td-center"><span class="badge badge-pvid">${{ev.pvid || '-'}}</span></td>
          <td class="td-center">${{getStatusBadge(ev.status_entrega)}}</td>
          <td class="td-center" style="font-weight: 600;">${{ev.programado || 'NÃO'}}</td>
        `;
        tbody.appendChild(tr);
      }});

      const elTotal = document.getElementById("kpi-total");
      if (elTotal) elTotal.innerText = allEvents.length;
      const elCaze = document.getElementById("kpi-caze");
      if (elCaze) elCaze.innerText = caze;
      const elPrime = document.getElementById("kpi-prime");
      if (elPrime) elPrime.innerText = prime;
      const elNetflix = document.getElementById("kpi-netflix");
      if (elNetflix) elNetflix.innerText = netflix;
      const elOutros = document.getElementById("kpi-outros");
      if (elOutros) elOutros.innerText = outros;
      const elShowing = document.getElementById("showing-count");
      if (elShowing) elShowing.innerText = count;
    }}

    const sBox = document.getElementById("search-box");
    if (sBox) sBox.addEventListener("input", renderTable);
    const fCanalEl = document.getElementById("filter-canal");
    if (fCanalEl) fCanalEl.addEventListener("change", renderTable);
    const fStatusEl = document.getElementById("filter-status");
    if (fStatusEl) fStatusEl.addEventListener("change", renderTable);

    // Global Search na Suite Nav
    const gSearch = document.getElementById("global-search");
    if (gSearch) {{
      gSearch.addEventListener("input", function(e) {{
        const term = e.target.value;
        if (term.trim().length > 0) {{
          showPane('streaming');
          if (sBox) {{
            sBox.value = term;
            renderTable();
          }}
        }}
      }});
    }}

    // Sincronização em tempo real com Google Sheets
    async function syncLiveAPI() {{
      const btn = event.target;
      const originalText = btn.innerText;
      btn.innerText = "⏳ Atualizando...";
      btn.disabled = true;

      try {{
        const url = "https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec?format=json";
        const resp = await fetch(url);
        if (resp.ok) {{
          const freshEvents = await resp.json();
          if (Array.isArray(freshEvents) && freshEvents.length > 0) {{
            allEvents = freshEvents;
            renderTable();
            alert("✅ Portal atualizado com sucesso! Total: " + freshEvents.length + " eventos sincronizados.");
          }}
        }} else {{
          alert("⚠️ Não foi possível obter dados remotos frescos (Status " + resp.status + "). Mantendo dados locais.");
        }}
      }} catch (e) {{
        console.warn("Erro ao buscar dados remotos:", e);
        alert("ℹ️ Base sincronizada localmente mantida ativa.");
      }} finally {{
        btn.innerText = originalText;
        btn.disabled = false;
      }}
    }}

    // Exportar CSV
    function exportCSV() {{
      let csv = "Indice,Mes,Data,Horario,Campeonato,Partida,Responsavel,Canal,PVID,Status,Programado\\n";
      allEvents.forEach((ev, i) => {{
        csv += `"${{i+1}}","${{ev.mes||''}}","${{ev.data||''}}","${{ev.horario||''}}","${{ev.campeonato||''}}","${{ev.partida||''}}","${{ev.responsavel||''}}","${{ev.canal||''}}","${{ev.pvid||''}}","${{ev.status_entrega||''}}","${{ev.programado||''}}"\\n`;
      }});
      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "programacao_eventos_streaming.csv";
      a.click();
    }}

    // Render Inicial
    renderTable();
  </script>
</body>
</html>"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    docs_html = os.path.join(docs_dir, "index.html")
    with open(docs_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Portal Web Suporte Captação gerado com sucesso em: {output_html}")
    print(f"Publicação atualizada em: {docs_html}")
    print(f"Tamanho do arquivo: {os.path.getsize(output_html)} bytes")
    return output_html

if __name__ == "__main__":
    generate_portal()
