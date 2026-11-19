# -*- coding: utf-8 -*-
"""
Gerador do Portal Web Oficial do Suporte Captação (Kantar IBOPE Media).
Gera um portal intranet moderno, responsivo, profissional e autônomo em 'portal_web/index.html'.
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

    # Injeta os eventos formatados no script
    events_json_str = json.dumps(events, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Suporte Captação | Central de Operações & Streaming</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0B0F19;
      --bg-secondary: #111827;
      --bg-card: #1E293B;
      --bg-card-hover: #243247;
      --border-color: #334155;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --accent-blue: #2563EB;
      --accent-blue-hover: #1D4ED8;
      --accent-green: #10B981;
      --accent-amber: #F59E0B;
      --accent-purple: #8B5CF6;
      --accent-red: #EF4444;

      /* Badges Oficiais */
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
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    body {{
      background: var(--bg-primary);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Topbar Corporativa */
    .topbar {{
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 0 24px;
    }}

    .topbar-container {{
      max-width: 1600px;
      margin: 0 auto;
      height: 70px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}

    .brand-area {{
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }}

    .brand-logo-badge {{
      width: 42px;
      height: 42px;
      border-radius: 10px;
      background: linear-gradient(135deg, #2563EB, #1D4ED8);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
      color: #FFF;
      font-weight: 800;
      font-size: 20px;
    }}

    .brand-text h1 {{
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #FFF;
    }}

    .brand-text p {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .status-area {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .status-pulse-pill {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      color: #34D399;
    }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10B981;
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
      animation: pulse-green 2s infinite;
    }}

    @keyframes pulse-green {{
      0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
      70% {{ box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }}
      100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
    }}

    .clock-pill {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: var(--text-muted);
      background: var(--bg-card);
      padding: 6px 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }}

    /* Navegação por Abas */
    .nav-tabs {{
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      padding: 0 24px;
    }}

    .tabs-container {{
      max-width: 1600px;
      margin: 0 auto;
      display: flex;
      gap: 8px;
      overflow-x: auto;
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 14px 18px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }}

    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.03);
    }}

    .tab-btn.active {{
      color: #60A5FA;
      border-bottom-color: #3B82F6;
      background: rgba(59, 130, 246, 0.08);
    }}

    /* Conteúdo Principal */
    .main-content {{
      flex: 1;
      max-width: 1600px;
      width: 100%;
      margin: 0 auto;
      padding: 24px;
    }}

    .tab-pane {{
      display: none;
    }}

    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Cards de Métricas (KPIs) */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 18px 20px;
      transition: transform 0.2s, border-color 0.2s;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      border-color: #475569;
    }}

    .kpi-label {{
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .kpi-val {{
      font-size: 26px;
      font-weight: 800;
      color: #FFF;
      margin-top: 6px;
      display: flex;
      align-items: baseline;
      gap: 6px;
    }}

    .kpi-sub {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* Barra de Ações e Filtros */
    .filter-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}

    .filter-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      flex: 1;
    }}

    .search-input {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 13px;
      min-width: 280px;
      flex: 1;
      outline: none;
      transition: border-color 0.2s;
    }}

    .search-input:focus {{
      border-color: var(--accent-blue);
    }}

    .select-filter {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      cursor: pointer;
    }}

    .btn {{
      padding: 9px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
      text-decoration: none;
    }}

    .btn-primary {{
      background: var(--accent-blue);
      color: #FFF;
    }}

    .btn-primary:hover {{
      background: var(--accent-blue-hover);
    }}

    .btn-secondary {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
    }}

    .btn-secondary:hover {{
      background: #1F2937;
      border-color: #475569;
    }}

    /* Tabela de Dados Oficial */
    .table-container {{
      background: #FFFFFF;
      border-radius: 12px;
      border: 1px solid #CBD5E1;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }}

    .table-scroll {{
      max-height: 65vh;
      overflow-y: auto;
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
      color: #0F172A;
    }}

    thead th {{
      background: #F8FAFC;
      color: #475569;
      font-weight: 700;
      padding: 12px 14px;
      border-bottom: 2px solid #CBD5E1;
      border-right: 1px solid #E2E8F0;
      position: sticky;
      top: 0;
      z-index: 10;
      white-space: nowrap;
    }}

    tbody tr {{
      background: #FFFBEB;
      border-bottom: 1px solid #E2E8F0;
      transition: background 0.15s;
    }}

    tbody tr:hover {{
      background: #FEF3C7;
    }}

    tbody td {{
      padding: 10px 14px;
      border-right: 1px solid #E2E8F0;
      vertical-align: middle;
      white-space: nowrap;
    }}

    .td-center {{ text-align: center; }}
    
    .partida-name {{
      font-weight: 700;
      color: #166534;
      white-space: normal;
      min-width: 220px;
    }}

    /* Badges Idênticos ao SharePoint */
    .badge {{
      display: inline-block;
      padding: 4px 10px;
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
    .badge-default {{ background: #334155; color: #FFF; }}

    .badge-pvid {{
      background: var(--badge-pvid-bg);
      color: var(--badge-pvid-txt);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }}

    .badge-pendente {{ background: var(--badge-pend-bg); color: var(--badge-pend-txt); }}
    .badge-exibido {{ background: var(--badge-exib-bg); color: var(--badge-exib-txt); }}
    .badge-nao-exibido {{ background: var(--badge-nao-bg); color: var(--badge-nao-txt); }}

    /* Cards Informativos (TV BOX & Equipe) */
    .info-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
    }}

    .box-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 22px;
      transition: all 0.2s;
    }}

    .box-card:hover {{
      border-color: #60A5FA;
      transform: translateY(-2px);
    }}

    .box-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }}

    .box-title {{
      font-size: 16px;
      font-weight: 700;
      color: #FFF;
    }}

    .box-detail-row {{
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }}

    .box-detail-row:last-child {{
      border-bottom: none;
    }}

    .box-label {{
      color: var(--text-muted);
    }}

    .box-val {{
      font-weight: 600;
      color: #E2E8F0;
    }}

    /* Rodapé */
    .footer {{
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-color);
      padding: 20px 24px;
      margin-top: auto;
    }}

    .footer-container {{
      max-width: 1600px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      font-size: 12px;
      color: var(--text-muted);
    }}

    @media (max-width: 900px) {{
      .topbar-container {{ height: auto; padding: 14px 0; flex-direction: column; align-items: flex-start; }}
      .status-area {{ width: 100%; justify-content: space-between; }}
      .filter-card {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>

  <!-- TOPBAR -->
  <header class="topbar">
    <div class="topbar-container">
      <div class="brand-area">
        <div class="brand-logo-badge">K</div>
        <div class="brand-text">
          <h1>Suporte Captação | Streaming Operations Hub</h1>
          <p>Kantar IBOPE Media — Central de Monitoramento & Ingest de Transmissões</p>
        </div>
      </div>
      <div class="status-area">
        <div class="status-pulse-pill">
          <div class="pulse-dot"></div>
          <span>SISTEMA ATIVO & CONECTADO</span>
        </div>
        <div class="clock-pill" id="live-clock">--:--:--</div>
      </div>
    </div>
  </header>

  <!-- ABAS DE NAVEGAÇÃO -->
  <nav class="nav-tabs">
    <div class="tabs-container">
      <button class="tab-btn active" onclick="switchTab('streaming')">⚽ Programação Streaming</button>
      <button class="tab-btn" onclick="switchTab('receptores')">📡 Receptores & TV BOX</button>
      <button class="tab-btn" onclick="switchTab('equipe')">👥 Equipe & Escala de Plantão</button>
      <button class="tab-btn" onclick="switchTab('atalhos')">📂 Links & Sistemas Oficiais</button>
      <button class="tab-btn" onclick="switchTab('metricas')">📊 Métricas & Auditorias</button>
    </div>
  </nav>

  <!-- CONTEÚDO PRINCIPAL -->
  <main class="main-content">

    <!-- ABA 1: PROGRAMAÇÃO STREAMING -->
    <section id="pane-streaming" class="tab-pane active">
      
      <!-- KPIs -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Total de Confrontos</div>
          <div class="kpi-val" id="kpi-total">862</div>
          <div class="kpi-sub">Base Oficial Sincronizada</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #10B981;">
          <div class="kpi-label">Cazé TV</div>
          <div class="kpi-val" id="kpi-caze">0</div>
          <div class="kpi-sub">YouTube Live & PPV</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #00509E;">
          <div class="kpi-label">Amazon Prime</div>
          <div class="kpi-val" id="kpi-prime">0</div>
          <div class="kpi-sub">Prime Video Sports</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #7F4F24;">
          <div class="kpi-label">Netflix</div>
          <div class="kpi-val" id="kpi-netflix">0</div>
          <div class="kpi-sub">NFL & Eventos Especiais</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #8B5CF6;">
          <div class="kpi-label">TNT / Max / Record</div>
          <div class="kpi-val" id="kpi-outros">0</div>
          <div class="kpi-sub">Paulistão & HBO Max</div>
        </div>
      </div>

      <!-- Filtros e Busca -->
      <div class="filter-card">
        <div class="filter-group">
          <input type="text" id="search-box" class="search-input" placeholder="🔍 Buscar por partida, campeonato, responsável ou data...">
          <select id="filter-canal" class="select-filter">
            <option value="">Todos os Canais</option>
            <option value="cazé">Cazé TV</option>
            <option value="prime">Amazon Prime Video</option>
            <option value="netflix">Netflix</option>
            <option value="tnt">TNT / Max</option>
            <option value="record">Record</option>
            <option value="dazn">DAZN</option>
          </select>
          <select id="filter-status" class="select-filter">
            <option value="">Todos os Status</option>
            <option value="pendente">Pendente</option>
            <option value="exibido">Exibido</option>
            <option value="não exibido">Não Exibido</option>
          </select>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" onclick="syncLiveAPI()">🔄 Atualizar em Tempo Real</button>
          <button class="btn btn-primary" onclick="exportCSV()">📥 Exportar CSV</button>
        </div>
      </div>

      <!-- Tabela Oficial de Eventos -->
      <div class="table-container">
        <div class="table-scroll">
          <table>
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
      <div style="margin-top: 10px; font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between;">
        <div>Mostrando <b id="showing-count" style="color: #FFF;">0</b> eventos filtrados</div>
        <div>Padrão de Cores Oficial SharePoint Modern Lists</div>
      </div>

    </section>

    <!-- ABA 2: RECEPTORES & TV BOX -->
    <section id="pane-receptores" class="tab-pane">
      <h2 style="font-size: 18px; margin-bottom: 16px; color: #FFF;">📡 Mapa de Receptores & Dispositivos de Captura (PVID TV BOX)</h2>
      <div class="info-grid">
        <div class="box-card">
          <div class="box-header">
            <span class="box-title">CAZETV - PV3623</span>
            <span class="badge badge-caze">ATIVO</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Plataforma</span><span class="box-val">YouTube / CazéTV Live</span></div>
          <div class="box-detail-row"><span class="box-label">PVID Oficial</span><span class="box-val">PV3623</span></div>
          <div class="box-detail-row"><span class="box-label">Resolução / FPS</span><span class="box-val">1080p @ 60fps</span></div>
          <div class="box-detail-row"><span class="box-label">Responsável Backup</span><span class="box-val">Cleber / Marcelo</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Prime Video - PV3687</span>
            <span class="badge badge-prime">ATIVO</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Plataforma</span><span class="box-val">Amazon Prime Video Sports</span></div>
          <div class="box-detail-row"><span class="box-label">PVID Oficial</span><span class="box-val">PV3687</span></div>
          <div class="box-detail-row"><span class="box-label">Resolução / FPS</span><span class="box-val">1080p @ 60fps</span></div>
          <div class="box-detail-row"><span class="box-label">Responsável Backup</span><span class="box-val">Lucieudes / Cleber</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Netflix - PV3679</span>
            <span class="badge badge-netflix">ATIVO</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Plataforma</span><span class="box-val">Netflix Live Eventos (NFL)</span></div>
          <div class="box-detail-row"><span class="box-label">PVID Oficial</span><span class="box-val">PV3679</span></div>
          <div class="box-detail-row"><span class="box-label">Resolução / FPS</span><span class="box-val">4K UHD / 1080p</span></div>
          <div class="box-detail-row"><span class="box-label">Responsável Backup</span><span class="box-val">Cleber BL01</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">TNT - PV316</span>
            <span class="badge badge-tnt">ATIVO</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Plataforma</span><span class="box-val">TNT Sports / Max (Paulistão)</span></div>
          <div class="box-detail-row"><span class="box-label">PVID Oficial</span><span class="box-val">PV316</span></div>
          <div class="box-detail-row"><span class="box-label">Resolução / FPS</span><span class="box-val">1080i HD</span></div>
          <div class="box-detail-row"><span class="box-label">Responsável Backup</span><span class="box-val">Lucieudes BL01</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Record - PV58</span>
            <span class="badge badge-record">ATIVO</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Plataforma</span><span class="box-val">Record Aberta / PlayPlus</span></div>
          <div class="box-detail-row"><span class="box-label">PVID Oficial</span><span class="box-val">PV58</span></div>
          <div class="box-detail-row"><span class="box-label">Resolução / FPS</span><span class="box-val">1080i ISDB-T</span></div>
          <div class="box-detail-row"><span class="box-label">Responsável Backup</span><span class="box-val">Marcelo BL01</span></div>
        </div>
      </div>
    </section>

    <!-- ABA 3: EQUIPE & PLANTÃO -->
    <section id="pane-equipe" class="tab-pane">
      <h2 style="font-size: 18px; margin-bottom: 16px; color: #FFF;">👥 Operadores & Estrutura de Plantão da Captação</h2>
      <div class="info-grid">
        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Cleber</span>
            <span class="badge badge-caze">OPERADOR TITULAR</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Perfil</span><span class="box-val">Cleber BL01 e Backup</span></div>
          <div class="box-detail-row"><span class="box-label">Foco Operacional</span><span class="box-val">Cazé TV, Prime Video, Netflix</span></div>
          <div class="box-detail-row"><span class="box-label">Status</span><span class="box-val" style="color:#10B981;">Disponível</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Lucieudes</span>
            <span class="badge badge-prime">OPERADOR TITULAR</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Perfil</span><span class="box-val">Lucieudes BL01 e Backup</span></div>
          <div class="box-detail-row"><span class="box-label">Foco Operacional</span><span class="box-val">Prime Video, Brasileirão Série A, Copa do Brasil</span></div>
          <div class="box-detail-row"><span class="box-label">Status</span><span class="box-val" style="color:#10B981;">Disponível</span></div>
        </div>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Marcelo</span>
            <span class="badge badge-tnt">OPERADOR TITULAR</span>
          </div>
          <div class="box-detail-row"><span class="box-label">Perfil</span><span class="box-val">Marcelo BL01 e Backup</span></div>
          <div class="box-detail-row"><span class="box-label">Foco Operacional</span><span class="box-val">Cazé TV, Paulistão, Transmissões Noturnas</span></div>
          <div class="box-detail-row"><span class="box-label">Status</span><span class="box-val" style="color:#10B981;">Disponível</span></div>
        </div>
      </div>
    </section>

    <!-- ABA 4: ATALHOS & SISTEMAS OFICIAIS -->
    <section id="pane-atalhos" class="tab-pane">
      <h2 style="font-size: 18px; margin-bottom: 16px; color: #FFF;">📂 Ecossistema de Ferramentas & Links Oficiais</h2>
      <div class="info-grid">
        <a href="https://adgbl.sharepoint.com/sites/suportecaptacao/Lists/Programao%20de%20eventos%20%20Streaming/AllItems.aspx" target="_blank" class="box-card" style="text-decoration: none;">
          <div class="box-header">
            <span class="box-title">SharePoint Oficial</span>
            <span class="badge badge-prime">MICROSOFT 365</span>
          </div>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">Lista corporativa oficial 'Programação de eventos - Streaming' no SharePoint da Kantar IBOPE Media.</p>
          <span style="color: #60A5FA; font-size: 12px; font-weight: 600;">Acessar SharePoint ↗</span>
        </a>

        <a href="https://docs.google.com/spreadsheets/d/1nRfUjyOH-nwskR1pmKtdbMIHTtxcvLeV5dzZUuYh5rE/edit" target="_blank" class="box-card" style="text-decoration: none;">
          <div class="box-header">
            <span class="box-title">Google Sheets Espelho</span>
            <span class="badge badge-caze">GOOGLE WORKSPACE</span>
          </div>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">Planilha na nuvem sincronizada em paralelo pelo Monitor de Esportes com todas as 862 linhas coloridas.</p>
          <span style="color: #60A5FA; font-size: 12px; font-weight: 600;">Abrir Planilha no Google ↗</span>
        </a>

        <div class="box-card">
          <div class="box-header">
            <span class="box-title">Monitor de Esportes (v2.5.17)</span>
            <span class="badge badge-caze">ONLINE</span>
          </div>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">Aplicação desktop de monitoramento, OCR em tempo real, varredura de CBF e captura oficial.</p>
          <span style="color: #34D399; font-size: 12px; font-weight: 600;">Executável Local Ativo</span>
        </div>
      </div>
    </section>

    <!-- ABA 5: MÉTRICAS -->
    <section id="pane-metricas" class="tab-pane">
      <h2 style="font-size: 18px; margin-bottom: 16px; color: #FFF;">📊 Volume Histórico de Eventos por Canal</h2>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Cazé TV (Todas)</div>
          <div class="kpi-val" style="color: #34D399;">468</div>
          <div class="kpi-sub">54.3% do Volume Total</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Amazon Prime</div>
          <div class="kpi-val" style="color: #60A5FA;">183</div>
          <div class="kpi-sub">21.2% do Volume Total</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">TNT Sports / Max</div>
          <div class="kpi-val" style="color: #C084FC;">113</div>
          <div class="kpi-sub">13.1% do Volume Total</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Record / DAZN / Outros</div>
          <div class="kpi-val" style="color: #FBBF24;">98</div>
          <div class="kpi-sub">11.4% do Volume Total</div>
        </div>
      </div>
    </section>

  </main>

  <!-- RODAPÉ CORPORATIVO -->
  <footer class="footer">
    <div class="footer-container">
      <div><b>Kantar IBOPE Media</b> — Central de Operações & Suporte Captação © 2026</div>
      <div>Sincronizado automaticamente via <b>Monitor de Esportes v2.5.17</b> & Google Workspace</div>
    </div>
  </footer>

  <script>
    // Dataset inicial seguro
    let allEvents = {events_json_str};

    // Relógio ao Vivo
    function updateClock() {{
      const now = new Date();
      document.getElementById("live-clock").innerText = now.toLocaleTimeString('pt-BR');
    }}
    setInterval(updateClock, 1000);
    updateClock();

    // Navegação de Abas
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      const pane = document.getElementById('pane-' + tabId);
      if (pane) pane.classList.add('active');

      const btns = document.querySelectorAll('.tab-btn');
      btns.forEach(b => {{
        if (b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabId)) {{
          b.classList.add('active');
        }}
      }});
    }}

    // Badges
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

    function getStatusBadge(status) {{
      const s = String(status || "").toLowerCase();
      if (s.includes("exibido") && !s.includes("não") && !s.includes("nao")) return '<span class="badge badge-exibido">' + status + '</span>';
      if (s.includes("não") || s.includes("nao") || s.includes("cancelado")) return '<span class="badge badge-nao-exibido">' + status + '</span>';
      return '<span class="badge badge-pendente">' + (status || "Pendente") + '</span>';
    }}

    // Renderizar Tabela
    function renderTable() {{
      const q = document.getElementById("search-box").value.toLowerCase();
      const fCanal = document.getElementById("filter-canal").value.toLowerCase();
      const fStatus = document.getElementById("filter-status").value.toLowerCase();
      
      const tbody = document.getElementById("table-body");
      tbody.innerHTML = "";

      let count = 0;
      let caze = 0, prime = 0, netflix = 0, outros = 0;

      allEvents.forEach((ev, idx) => {{
        const cStr = String(ev.canal || "").toLowerCase();
        if (cStr.includes("cazé") || cStr.includes("caze")) caze++;
        else if (cStr.includes("prime") || cStr.includes("amazon")) prime++;
        else if (cStr.includes("netflix")) netflix++;
        else outros++;

        // Filtros
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
          <td class="partida-name">${{ev.partida || '-'}}</td>
          <td>${{ev.responsavel || '-'}}</td>
          <td class="td-center">${{getChannelBadge(ev.canal)}}</td>
          <td class="td-center"><span class="badge badge-pvid">${{ev.pvid || '-'}}</span></td>
          <td class="td-center">${{getStatusBadge(ev.status_entrega)}}</td>
          <td class="td-center" style="font-weight: 600;">${{ev.programado || 'NÃO'}}</td>
        `;
        tbody.appendChild(tr);
      }});

      document.getElementById("kpi-total").innerText = allEvents.length;
      document.getElementById("kpi-caze").innerText = caze;
      document.getElementById("kpi-prime").innerText = prime;
      document.getElementById("kpi-netflix").innerText = netflix;
      document.getElementById("kpi-outros").innerText = outros;
      document.getElementById("showing-count").innerText = count;
    }}

    document.getElementById("search-box").addEventListener("input", renderTable);
    document.getElementById("filter-canal").addEventListener("change", renderTable);
    document.getElementById("filter-status").addEventListener("change", renderTable);

    // Consulta em tempo real na nuvem do Google Sheets
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
          alert("⚠️ Não foi possível obter dados frescos da API (Status " + resp.status + "). Usando dados locais.");
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

    print(f"Portal Web Suporte Captação gerado com sucesso em: {output_html}")
    print(f"Tamanho do arquivo: {os.path.getsize(output_html)} bytes")
    return output_html

if __name__ == "__main__":
    generate_portal()
