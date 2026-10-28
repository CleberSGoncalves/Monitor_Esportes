"""
Mixin de Interface Gráfica para Monitoramento e Auditoria de Eventos da NBA.
Implementa a aba '🏀 Eventos NBA' com navegação de jogos, visualização de Game Books,
geração de relatórios em 1 clique e sincronização com SharePoint e E-mail.
"""

import os
import sys
import threading
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.email_service import EmailService

class NBAEventsMixin:
    """Mixin integrado à classe principal da GUI para a aba NBA."""

    def _init_nba_state(self) -> None:
        self.nba_service = NBAService()
        self.nba_reporter = NBAReportGenerator()
        self.nba_current_date = datetime.now().strftime("%Y-%m-%d")
        self.nba_games = []
        self._nba_loading = False
        self._nba_reports = {}  # game_id -> pdf_path

    def _build_tab_nba(self) -> None:
        """Constrói a interface completa da aba '🏀 Eventos NBA'."""
        self._init_nba_state()

        parent = getattr(self, "tab_nba", None)
        if not parent:
            return

        # Frame Principal
        main_frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. BARRA SUPERIOR DE CONTROLE E DATA
        top_bar = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("#F1F5F9", "#1E293B"), height=55)
        top_bar.pack(fill="x", padx=4, pady=(0, 8))
        top_bar.pack_propagate(False)

        # Título
        lbl_title = ctk.CTkLabel(
            top_bar,
            text="🏀 Monitor de Eventos NBA — Temporada 2026-27",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC")
        )
        lbl_title.pack(side="left", padx=14, pady=10)

        # Seletor de Data
        date_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        date_frame.pack(side="left", padx=15)

        btn_prev = ctk.CTkButton(
            date_frame, text="◀ Ontem", width=70, height=28,
            fg_color=("#CBD5E1", "#334155"), text_color=("#0F172A", "#F8FAFC"),
            command=self._nba_prev_day
        )
        btn_prev.pack(side="left", padx=2)

        self.lbl_nba_date = ctk.CTkLabel(
            date_frame,
            text=f"📅 {self.nba_current_date}",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=110
        )
        self.lbl_nba_date.pack(side="left", padx=6)

        btn_next = ctk.CTkButton(
            date_frame, text="Amanhã ▶", width=70, height=28,
            fg_color=("#CBD5E1", "#334155"), text_color=("#0F172A", "#F8FAFC"),
            command=self._nba_next_day
        )
        btn_next.pack(side="left", padx=2)

        btn_today = ctk.CTkButton(
            date_frame, text="Hoje", width=55, height=28,
            fg_color=("#3B82F6", "#2563EB"),
            command=self._nba_today
        )
        btn_today.pack(side="left", padx=4)

        # Ações Globais
        btn_refresh = ctk.CTkButton(
            top_bar, text="🔄 Atualizar Jogos", width=120, height=32,
            fg_color=("#0284C7", "#0369A1"),
            command=self._nba_load_games_async
        )
        btn_refresh.pack(side="right", padx=10)

        btn_audit_all = ctk.CTkButton(
            top_bar, text="🚀 Auditar & Sincronizar Todos", width=190, height=32,
            fg_color=("#16A34A", "#15803D"),
            command=self._nba_audit_all_games
        )
        btn_audit_all.pack(side="right", padx=4)

        # 2. STATUS / RESUMO DO DIA
        self.lbl_nba_status = ctk.CTkLabel(
            main_frame,
            text="Carregando jogos da NBA...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.lbl_nba_status.pack(anchor="w", padx=8, pady=(0, 4))

        # 3. LISTA ROLÁVEL DE JOGOS
        self.scroll_nba_games = ctk.CTkScrollableFrame(
            main_frame,
            corner_radius=8,
            fg_color=("#FFFFFF", "#0F172A")
        )
        self.scroll_nba_games.pack(fill="both", expand=True, padx=4, pady=4)

        # Carregar jogos iniciais
        self._nba_load_games_async()

    def _nba_prev_day(self) -> None:
        try:
            dt = datetime.strptime(self.nba_current_date, "%Y-%m-%d") - timedelta(days=1)
            self.nba_current_date = dt.strftime("%Y-%m-%d")
            self.lbl_nba_date.configure(text=f"📅 {self.nba_current_date}")
            self._nba_load_games_async()
        except Exception:
            pass

    def _nba_next_day(self) -> None:
        try:
            dt = datetime.strptime(self.nba_current_date, "%Y-%m-%d") + timedelta(days=1)
            self.nba_current_date = dt.strftime("%Y-%m-%d")
            self.lbl_nba_date.configure(text=f"📅 {self.nba_current_date}")
            self._nba_load_games_async()
        except Exception:
            pass

    def _nba_today(self) -> None:
        self.nba_current_date = datetime.now().strftime("%Y-%m-%d")
        self.lbl_nba_date.configure(text=f"📅 {self.nba_current_date}")
        self._nba_load_games_async()

    def _nba_load_games_async(self) -> None:
        if self._nba_loading:
            return
        self._nba_loading = True
        self.lbl_nba_status.configure(text=f"Buscando jogos da NBA para {self.nba_current_date}...")

        def _worker():
            try:
                games = self.nba_service.fetch_games_for_date(self.nba_current_date)
                self.after(0, lambda: self._on_nba_games_loaded(games))
            except Exception as e:
                self.after(0, lambda: self.lbl_nba_status.configure(text=f"Erro ao buscar jogos: {e}"))
            finally:
                self._nba_loading = False

        threading.Thread(target=_worker, daemon=True).start()

    def _on_nba_games_loaded(self, games: list) -> None:
        self.nba_games = games
        count = len(games)
        fin = sum(1 for g in games if g.get("is_finished"))
        self.lbl_nba_status.configure(
            text=f"Total de {count} jogo(s) encontrado(s) em {self.nba_current_date} ({fin} finalizado(s))."
        )
        self._render_nba_cards()

    def _render_nba_cards(self) -> None:
        for w in self.scroll_nba_games.winfo_children():
            w.destroy()

        if not self.nba_games:
            empty_lbl = ctk.CTkLabel(
                self.scroll_nba_games,
                text=f"Nenhum jogo programado para {self.nba_current_date}.",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            return

        for game in self.nba_games:
            self._create_nba_game_card(self.scroll_nba_games, game)

    def _create_nba_game_card(self, parent, game: dict) -> None:
        gid = game.get("id")
        card = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#F8FAFC", "#1E293B"), border_width=1, border_color=("#E2E8F0", "#334155"))
        card.pack(fill="x", padx=6, pady=4)

        # Linha 1: Confronto, Placar, Status e Plataforma
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(8, 4))

        # Nome do Jogo
        match_title = f"{game.get('away_team')} @ {game.get('home_team')}"
        lbl_match = ctk.CTkLabel(
            row1,
            text=match_title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0F172A", "#F8FAFC")
        )
        lbl_match.pack(side="left")

        # Badge de Status
        status_text = game.get("status", "Agendado")
        is_fin = game.get("is_finished")
        is_live = game.get("is_live")
        
        status_color = "#16A34A" if is_fin else ("#EF4444" if is_live else "#64748B")
        badge_status = ctk.CTkLabel(
            row1,
            text=f" {status_text.upper()} ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=status_color,
            corner_radius=4
        )
        badge_status.pack(side="left", padx=10)

        # Placar
        score_text = game.get("score_display", "—")
        if is_fin or is_live:
            lbl_score = ctk.CTkLabel(
                row1,
                text=f"🏀 {score_text}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#0284C7", "#38BDF8")
            )
            lbl_score.pack(side="left", padx=8)

        # Plataforma Seletor Interativo
        plat_options = ["Disney", "Amazon Prime", "ESPN", "Disney + ESPN", "NBA League Pass"]
        current_plat = game.get("platform") or "NBA League Pass"
        if current_plat not in plat_options:
            p_chk = current_plat.upper()
            if "DISNEY" in p_chk: current_plat = "Disney"
            elif "AMAZON" in p_chk or "PRIME" in p_chk: current_plat = "Amazon Prime"
            elif "ESPN" in p_chk: current_plat = "ESPN"
            else: current_plat = "NBA League Pass"

        btn_bg = "#1E3A8A" if "AMAZON" in current_plat.upper() or "PRIME" in current_plat.upper() else ("#B91C1C" if "DISNEY" in current_plat.upper() else ("#C2410C" if "ESPN" in current_plat.upper() else "#334155"))
        btn_hover = "#1D4ED8" if "AMAZON" in current_plat.upper() or "PRIME" in current_plat.upper() else ("#991B1B" if "DISNEY" in current_plat.upper() else ("#9A3412" if "ESPN" in current_plat.upper() else "#1E293B"))

        opt_plat = ctk.CTkOptionMenu(
            row1,
            values=plat_options,
            width=135,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=btn_bg,
            button_color=btn_hover,
            button_hover_color=btn_bg,
            command=lambda val, g=game: self._on_nba_platform_changed(g, val)
        )
        opt_plat.set(current_plat)
        opt_plat.pack(side="right")
        game["_opt_widget"] = opt_plat

        # Linha 2: Detalhes e Botões de Ação
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(2, 8))

        lbl_time = ctk.CTkLabel(
            row2,
            text=f"⏰ {game.get('time_brt')} BRT | 📄 Game Book: {game.get('gamebook_filename')}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        lbl_time.pack(side="left")

        btn_box = ctk.CTkFrame(row2, fg_color="transparent")
        btn_box.pack(side="right")

        # Botão 1: Baixar/Abrir Game Book
        btn_gb = ctk.CTkButton(
            btn_box,
            text="📥 Game Book (PDF NBA)",
            width=140,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("#475569", "#334155"),
            command=lambda g=game: self._on_nba_open_gamebook(g)
        )
        btn_gb.pack(side="left", padx=4)

        # Botão 2: Gerar Relatório NBA
        btn_gen = ctk.CTkButton(
            btn_box,
            text="⚡ Gerar Relatório",
            width=120,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#D97706", "#B45309"),
            command=lambda g=game: self._on_nba_generate_report(g)
        )
        btn_gen.pack(side="left", padx=4)

        # Botão 3: Sincronizar SharePoint
        btn_sp = ctk.CTkButton(
            btn_box,
            text="☁️ SharePoint",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("#0284C7", "#0369A1"),
            command=lambda g=game: self._on_nba_sync_sharepoint(g)
        )
        btn_sp.pack(side="left", padx=4)

        # Botão 4: E-mail
        btn_mail = ctk.CTkButton(
            btn_box,
            text="✉️ E-mail",
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("#16A34A", "#15803D"),
            command=lambda g=game: self._on_nba_send_email(g)
        )
        btn_mail.pack(side="left", padx=4)

    def _on_nba_platform_changed(self, game: dict, val: str) -> None:
        """Manipula a alteração manual da plataforma de transmissão pelo usuário."""
        self.nba_service.set_game_platform(game, val)
        # Limpa cache do relatório anterior para forçar regeneração com a nova plataforma
        self._nba_reports.pop(game.get("id"), None)

        widget = game.get("_opt_widget")
        if widget:
            val_up = val.upper()
            if "AMAZON" in val_up or "PRIME" in val_up:
                widget.configure(fg_color="#1E3A8A", button_color="#1D4ED8")
            elif "DISNEY" in val_up:
                widget.configure(fg_color="#B91C1C", button_color="#991B1B")
            elif "ESPN" in val_up:
                widget.configure(fg_color="#C2410C", button_color="#9A3412")
            else:
                widget.configure(fg_color="#334155", button_color="#1E293B")
        self.lbl_nba_status.configure(text=f"Plataforma de {game.get('match_display')} definida como: {val}")

    def _on_nba_open_gamebook(self, game: dict) -> None:
        """Baixa e abre o Game Book oficial da NBA no leitor de PDF do sistema."""
        def _worker():
            self.lbl_nba_status.configure(text=f"Baixando Game Book de {game.get('match_display')}...")
            pdf = self.nba_service.download_gamebook(game)
            if pdf and os.path.exists(pdf):
                self.lbl_nba_status.configure(text=f"✅ Game Book baixado com sucesso: {os.path.basename(pdf)}")
                os.startfile(pdf)
            else:
                self.after(0, lambda: messagebox.showwarning(
                    "Game Book NBA",
                    f"O Game Book oficial ainda não foi publicado pela NBA para esta partida ou o jogo ainda não terminou.\n\nURL: {game.get('gamebook_url')}"
                ))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_nba_generate_report(self, game: dict) -> None:
        """Gera o relatório oficial de auditoria em PDF da NBA em segundo plano."""
        def _worker():
            self.lbl_nba_status.configure(text=f"Gerando relatório oficial de {game.get('match_display')}...")
            gb_path = self.nba_service.download_gamebook(game)
            parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
            pdf = self.nba_reporter.generate_report(game, parsed)
            if pdf and os.path.exists(pdf):
                self._nba_reports[game.get("id")] = pdf
                self.lbl_nba_status.configure(text=f"✅ Relatório NBA gerado: {os.path.basename(pdf)}")
                os.startfile(pdf)
            else:
                self.after(0, lambda: messagebox.showerror("Erro", "Falha ao gerar o relatório PDF da NBA."))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_nba_sync_sharepoint(self, game: dict) -> None:
        """Sincroniza o relatório do jogo diretamente com o SharePoint."""
        def _worker():
            self.lbl_nba_status.configure(text=f"Preparando relatório oficial de {game.get('match_display')}...")
            gb_path = self.nba_service.download_gamebook(game)
            parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
            pdf = self.nba_reporter.generate_report(game, parsed)
            self._nba_reports[game.get("id")] = pdf

            self.lbl_nba_status.configure(text=f"Sincronizando {game.get('match_display')} com SharePoint ({game.get('platform')})...")
            ok = SharePointNBAReporter.sync_nba_report(pdf, game)
            if ok:
                self.lbl_nba_status.configure(text=f"🎉 Sincronizado no SharePoint com sucesso: {game.get('match_display')}")
                self.after(0, lambda: messagebox.showinfo("SharePoint NBA", f"Relatório de {game.get('match_display')} sincronizado com sucesso!\nPlataforma: {game.get('platform')}"))
            else:
                self.lbl_nba_status.configure(text=f"⚠️ Falha ao sincronizar {game.get('match_display')} no SharePoint.")
        threading.Thread(target=_worker, daemon=True).start()

    def _on_nba_send_email(self, game: dict) -> None:
        """Envia o relatório oficial do jogo da NBA por e-mail para Arthur e Cleber."""
        pdf = self._nba_reports.get(game.get("id"))
        if not pdf or not os.path.exists(pdf):
            gb_path = self.nba_service.download_gamebook(game)
            parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
            pdf = self.nba_reporter.generate_report(game, parsed)
            self._nba_reports[game.get("id")] = pdf

        def _worker():
            try:
                import json
                with open("config/saved_emails.json", "r", encoding="utf-8") as f:
                    recipients = json.load(f)
                with open("config/google_ai.json", "r", encoding="utf-8") as f:
                    ai_cfg = json.load(f)

                svc = EmailService("smtp.gmail.com", 587, ai_cfg.get("email"), ai_cfg.get("senha"))
                subj = f"🏀 Relatório de Auditoria NBA — {game.get('match_display')} ({game.get('platform')})"
                body = (
                    f"Olá,\n\n"
                    f"Segue em anexo o relatório oficial de auditoria técnica da NBA:\n"
                    f"• Partida: {game.get('match_display')}\n"
                    f"• Data: {game.get('date_display')} às {game.get('time_brt')} BRT\n"
                    f"• Placar Final: {game.get('score_display')}\n"
                    f"• Plataforma: {game.get('platform')}\n\n"
                    f"Relatório homologado com o NBA Game Book oficial e sincronizado com o SharePoint.\n\n"
                    f"— Monitor de Esportes / Auditoria NBA"
                )
                ok = svc.send_report(recipients, subj, body, pdf_path=pdf)
                if ok:
                    self.lbl_nba_status.configure(text=f"✉️ E-mail enviado com sucesso para {', '.join(recipients)}")
                    self.after(0, lambda: messagebox.showinfo("E-mail Enviado", f"Relatório enviado com sucesso para:\n{', '.join(recipients)}"))
                else:
                    self.lbl_nba_status.configure(text="❌ Falha no envio do e-mail.")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro E-mail", str(e)))
        threading.Thread(target=_worker, daemon=True).start()

    def _nba_audit_all_games(self) -> None:
        """Audita, gera relatórios e sincroniza no SharePoint todos os jogos finalizados do dia em lote."""
        finished = [g for g in self.nba_games if g.get("is_finished")]
        if not finished:
            messagebox.showinfo("Auditoria NBA", "Nenhum jogo finalizado encontrado para auditar nesta data.")
            return

        def _worker():
            total = len(finished)
            self.lbl_nba_status.configure(text=f"Iniciando auditoria em lote de {total} jogos da NBA...")
            success = 0
            for i, g in enumerate(finished, 1):
                self.lbl_nba_status.configure(text=f"[{i}/{total}] Auditando {g.get('match_display')}...")
                gb_path = self.nba_service.download_gamebook(g)
                parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
                pdf = self.nba_reporter.generate_report(g, parsed)
                self._nba_reports[g.get("id")] = pdf
                ok = SharePointNBAReporter.sync_nba_report(pdf, g)
                if ok: success += 1

            self.lbl_nba_status.configure(text=f"🎉 Auditoria em lote concluída: {success}/{total} jogos sincronizados no SharePoint!")
            self.after(0, lambda: messagebox.showinfo("Lote Concluído", f"{success} de {total} jogos foram auditados e sincronizados no SharePoint!"))

        threading.Thread(target=_worker, daemon=True).start()
