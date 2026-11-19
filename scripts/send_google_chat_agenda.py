#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Envio da Agenda de Transmissões (Hoje e Amanhã) para o Google Chat
Grupo: 'Streaming - Gravações' (Suporte Captação LATAM)

Substitui o antigo fluxo do Power Automate (Teams) por integração 100% nativa com o Google Chat.
Pode ser executado via CLI, agendado no Task Scheduler do Windows, ou chamado programaticamente.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import urllib.request
import urllib.error

def formatar_data_br(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")

def carregar_eventos_streaming(caminho_arquivo: str = None) -> list:
    """Carrega eventos de streaming do arquivo local limpo ou da base master."""
    if not caminho_arquivo:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_arquivo = os.path.join(base_dir, "config", "sharepoint_clean_migrated_events.json")
    
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo de eventos não encontrado: {caminho_arquivo}")
    
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        events = json.load(f)
    return events

def filtrar_eventos_por_datas(eventos: list, data_hoje_str: str, data_amanha_str: str) -> tuple:
    """Filtra eventos programados para hoje e amanhã."""
    jogos_hoje = []
    jogos_amanha = []
    
    for ev in eventos:
        d = str(ev.get("data", "")).strip()
        # Normalizar para DD/MM/YYYY
        if "/" in d:
            partes = d.split("/")
            if len(partes) == 3 and len(partes[2]) == 4:
                d_norm = f"{int(partes[0]):02d}/{int(partes[1]):02d}/{partes[2]}"
            else:
                d_norm = d
        else:
            d_norm = d
            
        partida = ev.get("partida") or ev.get("Title") or ""
        horario = ev.get("horario") or ev.get("Hor_x00e1_rio") or ev.get("hora") or "--:--"
        responsavel = ev.get("responsavel") or "Marcos BL01 e Backup"
        canal = ev.get("canal") or ev.get("Transmiss_x00e3_o") or "Transmissão Oficial"
        pvid = ev.get("pvid") or ev.get("PVID") or f"{canal} - TV BOX"
        
        item = {
            "partida": partida,
            "horario": horario,
            "responsavel": responsavel,
            "canal": canal,
            "pvid": pvid,
            "campeonato": ev.get("campeonato") or ev.get("Title") or ""
        }
        
        if d_norm == data_hoje_str:
            jogos_hoje.append(item)
        elif d_norm == data_amanha_str:
            jogos_amanha.append(item)
            
    # Ordenar por horário
    jogos_hoje.sort(key=lambda x: x["horario"])
    jogos_amanha.sort(key=lambda x: x["horario"])
    return jogos_hoje, jogos_amanha

def obter_webhook_url(webhook_cli: str = None) -> str:
    """Busca a URL do Webhook do Google Chat em argumentos, ambiente ou arquivo de config."""
    if webhook_cli and webhook_cli.strip():
        url = webhook_cli.strip()
        salvar_webhook_config(url)
        return url
        
    # 1. Variável de ambiente
    env_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL") or os.environ.get("GOOGLE_CHAT_STREAMING_WEBHOOK")
    if env_url and env_url.strip():
        return env_url.strip()
        
    # 2. config/google_chat_webhook.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, "config", "google_chat_webhook.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                c = json.load(f)
                url = c.get("streaming_webhook_url") or c.get("webhook_url")
                if url and url.strip():
                    return url.strip()
        except Exception:
            pass
            
    # 3. config/google_ai.json
    gai_path = os.path.join(base_dir, "config", "google_ai.json")
    if os.path.exists(gai_path):
        try:
            with open(gai_path, "r", encoding="utf-8") as f:
                c = json.load(f)
                url = c.get("chat_webhook_url") or c.get("streaming_webhook_url")
                if url and url.strip():
                    return url.strip()
        except Exception:
            pass
            
    return ""

def salvar_webhook_config(url: str):
    """Persiste a URL do Webhook em arquivo de configuração local."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base_dir, "config", "google_chat_webhook.json")
    dados = {
        "streaming_webhook_url": url,
        "agendamento_diario": "09:00",
        "descricao": "Webhook oficial do espaço 'Streaming - Gravações' no Google Chat (Suporte Captação LATAM)"
    }
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def montar_payload_google_chat(data_hoje_str: str, jogos_hoje: list, data_amanha_str: str, jogos_amanha: list) -> dict:
    """
    Constrói o payload JSON no padrão Google Chat Cards v2 idêntico ao modelo
    que a equipe recebia anteriormente no Teams via Power Automate.
    Avisa explicitamente quando NÃO houver transmissões hoje e/ou amanhã.
    """
    sections = []
    
    # Subtítulo inteligente
    if not jogos_hoje and not jogos_amanha:
        subtitulo = "Grade Livre • Sem transmissões agendadas para hoje e amanhã"
    elif not jogos_hoje:
        subtitulo = f"Grade de hoje livre • {len(jogos_amanha)} transmissão(ões) amanhã"
    elif not jogos_amanha:
        subtitulo = f"{len(jogos_hoje)} transmissão(ões) hoje • Grade de amanhã livre"
    else:
        subtitulo = f"{len(jogos_hoje)} transmissão(ões) hoje • {len(jogos_amanha)} amanhã"
    
    # Seção 1: Hoje
    widgets_hoje = []
    if not jogos_hoje:
        widgets_hoje.append({
            "decoratedText": {
                "topLabel": "Status da Grade de Hoje",
                "text": "<b>Nenhuma transmissão programada para hoje.</b>",
                "bottomLabel": "✅ Grade 100% livre • Operação normal sem eventos de streaming escalados.",
                "wrapText": True
            }
        })
    else:
        for j in jogos_hoje:
            widgets_hoje.append({
                "decoratedText": {
                    "topLabel": f"{j['horario']} • {j['responsavel']}",
                    "text": f"<b>{j['partida']}</b>",
                    "bottomLabel": f"📺 {j['pvid']}",
                    "wrapText": True
                }
            })
            
    sections.append({
        "header": f"Hoje - {data_hoje_str}" if jogos_hoje else f"Hoje - {data_hoje_str} (Grade Livre)",
        "widgets": widgets_hoje
    })
    
    # Seção 2: Amanhã
    widgets_amanha = []
    if not jogos_amanha:
        widgets_amanha.append({
            "decoratedText": {
                "topLabel": "Previsão para Amanhã",
                "text": "<b>Nenhuma transmissão programada para amanhã.</b>",
                "bottomLabel": "ℹ️ Grade 100% livre • Sem eventos de streaming previstos.",
                "wrapText": True
            }
        })
    else:
        for j in jogos_amanha:
            widgets_amanha.append({
                "decoratedText": {
                    "topLabel": f"{j['horario']} • {j['responsavel']}",
                    "text": f"<b>{j['partida']}</b>",
                    "bottomLabel": f"📺 {j['pvid']}",
                    "wrapText": True
                }
            })
            
    sections.append({
        "header": f"Amanhã - {data_amanha_str}" if jogos_amanha else f"Amanhã - {data_amanha_str} (Grade Livre)",
        "widgets": widgets_amanha
    })
    
    # Fallback texto simples
    linhas_texto = [
        "⚽ *Agenda de Transmissões | Suporte Captação*",
        subtitulo,
        "",
        f"*Hoje - {data_hoje_str}*:"
    ]
    if jogos_hoje:
        for j in jogos_hoje:
            linhas_texto.append(f"• {j['partida']} ({j['horario']}) - {j['responsavel']} [{j['pvid']}]")
    else:
        linhas_texto.append("• ✅ Nenhuma transmissão programada para hoje.")
        
    linhas_texto.append("")
    linhas_texto.append(f"*Amanhã - {data_amanha_str}*:")
    if jogos_amanha:
        for j in jogos_amanha:
            linhas_texto.append(f"• {j['partida']} ({j['horario']}) - {j['responsavel']} [{j['pvid']}]")
    else:
        linhas_texto.append("• ℹ️ Nenhuma transmissão programada para amanhã.")
        
    if not jogos_hoje and not jogos_amanha:
        linhas_texto.append("\n_Grade de eventos 100% liberada. Operação regular._")
        
    payload = {
        "text": "\n".join(linhas_texto),
        "cardsV2": [
            {
                "cardId": f"agenda-streaming-{data_hoje_str.replace('/', '-')}",
                "card": {
                    "header": {
                        "title": "Agenda de Transmissões",
                        "subtitle": subtitulo,
                        "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlestyles/sports_soccer/default/48px.png",
                        "imageType": "CIRCLE"
                    },
                    "sections": sections
                }
            }
        ]
    }
    return payload

def disparar_webhook_google_chat(webhook_url: str, payload: dict) -> dict:
    """Envia o payload JSON para o Webhook do Google Chat."""
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data_bytes,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return {"status": "success", "code": resp.status, "response": resp_body}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        return {"status": "error", "code": e.code, "message": str(e), "body": err_body}
    except Exception as e:
        return {"status": "error", "code": 0, "message": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Envio da Agenda de Streaming para o Google Chat")
    parser.add_argument("--webhook", "-w", help="URL do Webhook do Google Chat (Espaço Streaming - Gravações)")
    parser.add_argument("--date", "-d", help="Data base (DD/MM/YYYY). Se omitido, usa a data atual.")
    parser.add_argument("--dry-run", action="store_true", help="Gera o payload e imprime sem enviar.")
    args = parser.parse_args()
    
    if args.date:
        dt_hoje = datetime.strptime(args.date, "%d/%m/%Y")
    else:
        dt_hoje = datetime.now()
        
    dt_amanha = dt_hoje + timedelta(days=1)
    
    hoje_str = formatar_data_br(dt_hoje)
    amanha_str = formatar_data_br(dt_amanha)
    
    print(f"=== AGENDA DE TRANSMISSÕES GOOGLE CHAT ===")
    print(f"Data Base (Hoje):   {hoje_str}")
    print(f"Data Base (Amanhã): {amanha_str}")
    
    eventos = carregar_eventos_streaming()
    jogos_hoje, jogos_amanha = filtrar_eventos_por_datas(eventos, hoje_str, amanha_str)
    
    print(f"Jogos Hoje ({hoje_str}):   {len(jogos_hoje)}")
    for j in jogos_hoje:
        print(f"  - {j['horario']} | {j['partida']} | {j['responsavel']} | {j['pvid']}")
        
    print(f"Jogos Amanhã ({amanha_str}): {len(jogos_amanha)}")
    for j in jogos_amanha:
        print(f"  - {j['horario']} | {j['partida']} | {j['responsavel']} | {j['pvid']}")
        
    payload = montar_payload_google_chat(hoje_str, jogos_hoje, amanha_str, jogos_amanha)
    
    webhook_url = obter_webhook_url(args.webhook)
    
    if args.dry_run:
        print("\n--- PAYLOAD GOOGLE CHAT (Cards v2) [MODO SIMULAÇÃO] ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
        
    if not webhook_url:
        print("\n[Aviso] Nenhum webhook fornecido nem configurado em config/google_chat_webhook.json.")
        print("--- PAYLOAD GERADO ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("\nPara enviar de verdade, execute com --webhook <URL> ou configure config/google_chat_webhook.json")
        return 0
        
    print(f"\nDisparando para o Webhook do Google Chat...")
    resultado = disparar_webhook_google_chat(webhook_url, payload)
    print(f"Resultado do envio: {resultado}")
    return 0 if resultado.get("status") == "success" else 1

if __name__ == "__main__":
    sys.exit(main())
