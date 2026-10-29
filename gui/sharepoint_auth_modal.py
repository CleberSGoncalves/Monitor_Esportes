"""
Modal de Autenticação Interativa do SharePoint via Microsoft Device Code Flow.
Permite autenticar de forma amigável com 1 clique diretamente na interface gráfica.
"""

import os
import sys
import time
import threading
import webbrowser
import logging
import customtkinter as ctk
from tkinter import messagebox

logger = logging.getLogger(__name__)

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

def open_sharepoint_device_auth_modal(parent, on_success=None):
    """
    Abre o modal de autenticação via Device Code do Microsoft Graph.
    Ao concluir com sucesso, atualiza o sp_token_cache.json e executa on_success.
    """
    try:
        dev_data = SharePointReporter.request_device_code()
    except Exception as e:
        logger.error(f"[SharePoint Auth Modal] Falha ao solicitar device code: {e}")
        messagebox.showerror(
            "Erro de Conexão",
            f"Não foi possível iniciar o login da Microsoft:\n\n{e}\n\nVerifique sua conexão com a internet."
        )
        return None

    user_code = dev_data.get("user_code", "")
    device_code = dev_data.get("device_code", "")
    verification_uri = dev_data.get("verification_uri", "https://login.microsoft.com/device")
    interval = dev_data.get("interval", 5)
    expires_in = dev_data.get("expires_in", 900)

    # Copiar para a área de transferência do Windows nativamente
    try:
        parent.clipboard_clear()
        parent.clipboard_append(user_code)
    except Exception:
        pass

    # Abrir navegador automaticamente
    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass

    modal = ctk.CTkToplevel(parent)
    modal.title("🔑 Autenticação SharePoint — Microsoft 365")
    modal.geometry("540x480")
    modal.resizable(False, False)
    modal.transient(parent)
    modal.grab_set()

    # Centralizar
    try:
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 270
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 240
        modal.geometry(f"540x480+{x}+{y}")
    except Exception:
        pass

    # Cabeçalho
    header = ctk.CTkFrame(modal, fg_color=("#0F172A", "#1E293B"), corner_radius=0, height=65)
    header.pack(fill="x")
    header.pack_propagate(False)

    ctk.CTkLabel(
        header,
        text="🔑 Autenticação SharePoint MediaDNA",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#F8FAFC"
    ).pack(anchor="w", padx=16, pady=(10, 2))

    ctk.CTkLabel(
        header,
        text="Conecte sua conta corporativa para envio de relatórios e agendas ao SharePoint",
        font=ctk.CTkFont(size=11),
        text_color="#94A3B8"
    ).pack(anchor="w", padx=16)

    # Box do Código
    body_frame = ctk.CTkFrame(modal, fg_color="transparent")
    body_frame.pack(fill="both", expand=True, padx=20, pady=16)

    ctk.CTkLabel(
        body_frame,
        text="CÓDIGO DE DISPOSITIVO DA MICROSOFT:",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=("#475569", "#94A3B8")
    ).pack(anchor="center", pady=(0, 4))

    code_card = ctk.CTkFrame(body_frame, fg_color=("#F1F5F9", "#0F172A"), corner_radius=8, border_width=2, border_color="#0284C7")
    code_card.pack(fill="x", pady=(0, 10))

    lbl_code = ctk.CTkLabel(
        code_card,
        text=user_code,
        font=ctk.CTkFont(size=26, weight="bold"),
        text_color="#0284C7"
    )
    lbl_code.pack(pady=10)

    # Botão de copiar e abrir
    def _copy_and_open():
        try:
            parent.clipboard_clear()
            parent.clipboard_append(user_code)
            webbrowser.open(verification_uri)
            lbl_feedback.configure(text="📋 Código copiado! Cole no navegador aberto (Ctrl+V).", text_color="#16A34A")
        except Exception as ex:
            lbl_feedback.configure(text=f"Erro ao abrir navegador: {ex}", text_color="#EF4444")

    btn_copy = ctk.CTkButton(
        body_frame,
        text="📋 Copiar Código & Abrir Navegador Novamente",
        font=ctk.CTkFont(size=12, weight="bold"),
        height=34,
        fg_color=("#0284C7", "#0369A1"),
        hover_color=("#0369A1", "#075985"),
        command=_copy_and_open
    )
    btn_copy.pack(fill="x", pady=(0, 6))

    lbl_feedback = ctk.CTkLabel(
        body_frame,
        text="✅ Código já copiado para a Área de Transferência!",
        font=ctk.CTkFont(size=11),
        text_color="#16A34A"
    )
    lbl_feedback.pack(pady=(0, 12))

    # Instruções
    inst_card = ctk.CTkFrame(body_frame, fg_color=("#F8FAFC", "#1E293B"), corner_radius=6, border_width=1, border_color=("#E2E8F0", "#334155"))
    inst_card.pack(fill="x", pady=(0, 12), ipady=6)

    inst_text = (
        f"1. A página da Microsoft foi aberta em seu navegador:\n"
        f"   {verification_uri}\n"
        f"2. Cole o código {user_code} e clique em 'Avançar'.\n"
        f"3. Faça login com a conta de serviço:\n"
        f"   👉 {SP_CONFIG['username']}\n"
        f"4. Confirme as permissões. Esta janela fechará automaticamente!"
    )
    ctk.CTkLabel(
        inst_card,
        text=inst_text,
        justify="left",
        font=ctk.CTkFont(size=11),
        text_color=("#334155", "#CBD5E1")
    ).pack(padx=12, pady=6, anchor="w")

    # Status / Spinner
    lbl_poll_status = ctk.CTkLabel(
        body_frame,
        text="⏳ Aguardando confirmação no navegador...",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="#D97706"
    )
    lbl_poll_status.pack(pady=(4, 0))

    # Thread de monitoramento do Device Code
    is_active = {"running": True}

    def _on_close():
        is_active["running"] = False
        modal.destroy()

    modal.protocol("WM_DELETE_WINDOW", _on_close)

    def _poll_thread():
        start_t = time.time()
        while is_active["running"] and (time.time() - start_t < expires_in):
            time.sleep(interval)
            if not is_active["running"]:
                break

            try:
                poll_res = SharePointReporter.poll_device_code(device_code)
                if "access_token" in poll_res:
                    acc = poll_res.get("access_token")
                    rf = poll_res.get("refresh_token", "")
                    SharePointReporter.save_tokens(acc, rf)
                    logger.info("🎉 [SharePoint Auth] Token renovado com sucesso via Device Code!")

                    def _complete():
                        if is_active["running"]:
                            is_active["running"] = False
                            modal.destroy()
                            messagebox.showinfo(
                                "SharePoint Conectado",
                                "🎉 Autenticação realizada com sucesso!\n\n"
                                "A sessão corporativa do SharePoint está ativa.\n"
                                "Seus relatórios e agendas serão sincronizados normalmente."
                            )
                            if on_success:
                                try:
                                    on_success()
                                except Exception as cb_ex:
                                    logger.error(f"[SharePoint Auth Modal] Erro no callback on_success: {cb_ex}")

                    parent.after(0, _complete)
                    break
                else:
                    err = poll_res.get("error", "")
                    if err in ("authorization_pending", "slow_down"):
                        continue
                    else:
                        err_desc = poll_res.get("error_description", err)
                        logger.warning(f"[SharePoint Auth Modal] Polling retornou erro: {err_desc}")
                        if "expired_token" in err:
                            parent.after(0, lambda: lbl_poll_status.configure(
                                text="❌ O código expirou. Feche e abra o modal novamente.",
                                text_color="#EF4444"
                            ))
                            break
            except Exception as poll_ex:
                logger.warning(f"[SharePoint Auth Modal] Exceção no polling: {poll_ex}")

    threading.Thread(target=_poll_thread, daemon=True).start()
    return modal
