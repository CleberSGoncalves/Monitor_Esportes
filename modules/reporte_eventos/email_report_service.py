# -*- coding: utf-8 -*-
"""
Serviço de geração de relatórios em HTML estilizado e disparo de e-mails corporativos (SMTP).
Inclui:
- Bloqueio automático de envio na madrugada (22:00 às 07:00) exceto forçado
- Idempotência de envio diário por hash
- Layout responsivo profissional com cabeçalho corporativo e links diretos
"""

import smtplib
import hashlib
import logging
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Any, Tuple

from .crypto_utils import get_auth_value

logger = logging.getLogger(__name__)

_ULTIMO_HASH_ENVIADO = ""

def _hash_corpo(corpo: str) -> str:
    """Calcula hash SHA256 do corpo do e-mail para garantia de idempotência diária."""
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()

def extrair_dados_html(rows: List[List[Any]]) -> str:
    """Gera layout HTML corporativo elegante da tabela de eventos."""
    if not rows:
        return "<p>Nenhum evento registrado para o período.</p>"

    html = """
    <html>
    <head>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; color: #333333; }
        h2 { color: #1e3a5f; margin-bottom: 5px; }
        p.subtitle { color: #666666; font-size: 13px; margin-top: 0; margin-bottom: 20px; }
        table { border-collapse: collapse; width: 100%; font-size: 12px; }
        th { background-color: #22405a; color: #ffffff; padding: 10px 8px; text-align: center; border: 1px solid #1a3247; }
        td { padding: 8px; border: 1px solid #e0e0e0; text-align: center; }
        tr:nth-child(even) { background-color: #f8fafc; }
        tr:hover { background-color: #e2e8f0; }
        .match { font-weight: bold; color: #0f172a; text-align: left; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
        .caze { background-color: #fff3cd; color: #856404; }
        .prime { background-color: #cce5ff; color: #004085; }
        .yt { background-color: #f8d7da; color: #721c24; }
        .link-btn { color: #0284c7; text-decoration: none; font-weight: bold; }
        .link-btn:hover { text-decoration: underline; }
        .footer { margin-top: 25px; font-size: 11px; color: #888888; border-top: 1px solid #eee; padding-top: 10px; }
    </style>
    </head>
    <body>
        <h2>📅 Reporte de Eventos Esportivos & Transmissões</h2>
        <p class="subtitle">Gerado automaticamente por Monitor Esportes — Central Unificada de Transmissões</p>
        <table>
            <thead>
                <tr>
                    <th>Campeonato</th>
                    <th style="text-align: left;">Confronto</th>
                    <th>Data</th>
                    <th>Horário</th>
                    <th>Canal / Plataforma</th>
                    <th>Link Transmissão</th>
                </tr>
            </thead>
            <tbody>
    """

    for r in rows:
        if len(r) < 8:
            continue
        camp = r[0]
        partida = r[1]
        data = r[2]
        hora = r[3]
        canal = r[6]
        url = r[7]

        link_html = f'<a href="{url}" class="link-btn" target="_blank">Acessar</a>' if url and str(url).startswith("http") else "-"

        html += f"""
            <tr>
                <td>{camp}</td>
                <td class="match">{partida}</td>
                <td>{data}</td>
                <td><b>{hora}</b></td>
                <td><span class="badge prime">{canal}</span></td>
                <td>{link_html}</td>
            </tr>
        """

    html += f"""
            </tbody>
        </table>
        <div class="footer">
            Sincronizado e auditado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} • Kantar IBOPE Media / Suporte Captação
        </div>
    </body>
    </html>
    """
    return html

def enviar_email_relatorio(
    rows: List[List[Any]],
    destinatarios: str,
    forcar: bool = False
) -> Tuple[bool, str]:
    """
    Dispara e-mail com a tabela de eventos para os destinatários indicados.
    Respeita a trava de segurança na madrugada (22:00 às 07:00) a menos que forcar=True.
    Garante idempotência por hash diário.
    """
    global _ULTIMO_HASH_ENVIADO

    if not destinatarios or not destinatarios.strip():
        return False, "Nenhum destinatário informado."

    # Trava de madrugada
    hora_atual = datetime.now().hour
    if (hora_atual < 7 or hora_atual >= 22) and not forcar:
        msg = f"Envio ignorado: bloqueio de segurança noturno ativo ({hora_atual:02d}h). Permitido apenas das 07:00 às 22:00."
        logger.info(f"[Email] {msg}")
        return False, msg

    corpo_html = extrair_dados_html(rows)
    hash_hoje = _hash_corpo(f"{date.today().isoformat()}|{corpo_html}")

    if hash_hoje == _ULTIMO_HASH_ENVIADO and not forcar:
        msg = "Envio ignorado: este exato relatório já foi disparado hoje (idempotência)."
        logger.info(f"[Email] {msg}")
        return True, msg

    remetente = get_auth_value("email")
    senha = get_auth_value("senha")

    if not remetente or not senha:
        return False, "Credenciais de e-mail (remetente/senha) não configuradas na aba Acessos."

    # Parse de destinatários (vírgula ou ponto e vírgula)
    dests = [d.strip() for d in destinatarios.replace(";", ",").split(",") if d.strip()]
    if not dests:
        return False, "Lista de destinatários inválida."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Programação de Eventos — {datetime.now().strftime('%d/%m/%Y')}"
        msg["From"] = remetente
        msg["To"] = ", ".join(dests)

        part_html = MIMEText(corpo_html, "html", "utf-8")
        msg.attach(part_html)

        import ssl
        import time

        estrategias = [
            {"nome": "Port 587 (STARTTLS)", "use_ssl": False, "port": 587},
            {"nome": "Port 465 (SSL Direto)", "use_ssl": True, "port": 465},
        ]
        ultimo_erro = None
        enviado = False

        for tentativa in range(1, 4):
            for est in estrategias:
                try:
                    logger.info(f"[SMTP] Tentando envio de e-mail (tentativa {tentativa}/3) via {est['nome']}...")
                    ctx = ssl.create_default_context()
                    if est["use_ssl"]:
                        with smtplib.SMTP_SSL("smtp.gmail.com", est["port"], timeout=30, context=ctx) as server:
                            server.ehlo()
                            server.login(remetente, senha)
                            refusals = server.sendmail(remetente, dests, msg.as_string())
                            if refusals:
                                logger.warning(f"[SMTP] Destinatários com recusa parcial: {refusals}")
                            enviado = True
                            break
                    else:
                        with smtplib.SMTP("smtp.gmail.com", est["port"], timeout=30) as server:
                            server.ehlo()
                            server.starttls(context=ctx)
                            server.ehlo()
                            server.login(remetente, senha)
                            refusals = server.sendmail(remetente, dests, msg.as_string())
                            if refusals:
                                logger.warning(f"[SMTP] Destinatários com recusa parcial: {refusals}")
                            enviado = True
                            break
                except Exception as e_tent:
                    ultimo_erro = e_tent
                    logger.warning(f"[SMTP] Falha via {est['nome']} na tentativa {tentativa}/3: {e_tent}")
                    time.sleep(1.5)
            if enviado:
                break

        if not enviado:
            raise ultimo_erro or Exception("Não foi possível conectar ao servidor SMTP após todas as tentativas.")

        _ULTIMO_HASH_ENVIADO = hash_hoje
        logger.info(f"[Email] Relatório enviado com sucesso para {len(dests)} destinatários!")
        return True, f"E-mail enviado com sucesso para {len(dests)} destinatários."
    except Exception as e:
        logger.error(f"[Email] Falha no envio SMTP: {e}")
        return False, f"Falha no envio de e-mail: {e}"
