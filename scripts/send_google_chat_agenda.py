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

def montar_payload_google_chat(data_hoje_str: str, jogos_hoje: list, data_amanha_str: str, jogos_amanha: list) -> dict:
    """
    Constrói o payload JSON no padrão Google Chat Cards v2 idêntico ao modelo
    que a equipe recebia anteriormente no Teams via Power Automate.
    """
    sections = []
    
    # Seção 1: Hoje
    widgets_hoje = []
    if not jogos_hoje:
        widgets_hoje.append({
            "decoratedText": {
                "text": "<i>Nenhuma transmissão programada para hoje.</i>"
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
        "header": f"Hoje - {data_hoje_str}",
        "widgets": widgets_hoje
    })
    
    # Seção 2: Amanhã
    widgets_amanha = []
    if not jogos_amanha:
        widgets_amanha.append({
            "decoratedText": {
                "text": "<i>Nenhuma transmissão programada para amanhã.</i>"
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
        "header": f"Amanhã - {data_amanha_str}",
        "widgets": widgets_amanha
    })
    
    # Fallback texto simples
    linhas_texto = [
        "⚽ *Agenda de Transmissões*",
        "Programação de jogos de hoje e amanhã",
        "",
        f"*Hoje - {data_hoje_str}*:"
    ]
    if jogos_hoje:
        for j in jogos_hoje:
            linhas_texto.append(f"• {j['partida']} ({j['horario']}) - {j['responsavel']} [{j['pvid']}]")
    else:
        linhas_texto.append("• Nenhuma transmissão.")
        
    linhas_texto.append("")
    linhas_texto.append(f"*Amanhã - {data_amanha_str}*:")
    if jogos_amanha:
        for j in jogos_amanha:
            linhas_texto.append(f"• {j['partida']} ({j['horario']}) - {j['responsavel']} [{j['pvid']}]")
    else:
        linhas_texto.append("• Nenhuma transmissão.")
        
    payload = {
        "text": "\n".join(linhas_texto),
        "cardsV2": [
            {
                "cardId": f"agenda-streaming-{data_hoje_str.replace('/', '-')}",
                "card": {
                    "header": {
                        "title": "Agenda de Transmissões",
                        "subtitle": "Programação de jogos de hoje e amanhã",
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
    
    if args.dry_run or not args.webhook:
        print("\n--- PAYLOAD GOOGLE CHAT (Cards v2) ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        if not args.webhook:
            print("\n[Aviso] Nenhum webhook fornecido. Use --webhook <URL> para efetuar o envio real.")
        return 0
        
    print(f"\nDisparando para o Webhook do Google Chat...")
    resultado = disparar_webhook_google_chat(args.webhook, payload)
    print(f"Resultado do envio: {resultado}")
    return 0 if resultado.get("status") == "success" else 1

if __name__ == "__main__":
    sys.exit(main())
