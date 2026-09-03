from google import genai
from google.genai import types
import json
import os
from typing import List, Dict, Any, Optional, Callable

class ExpertAssistant:
    """
    Assistente Especialista que utiliza Gemini com Search Grounding para extrair
    metadados técnicos e cronologia de eventos esportivos sem necessidade de vídeo.
    """
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash", yt_api_key: Optional[str] = None):
        if not api_key:
            raise ValueError("API Key do Gemini é obrigatória para ExpertAssistant.")
        # Aceita lista de chaves separadas por vírgula para rotação/failover
        self.api_keys = [k.strip() for k in api_key.split(",") if k.strip()]
        self.exhausted_keys = set() # Chaves que retornaram 429 / spend cap
        self.current_key_idx = 0
        self.model_id = model_id
        self.yt_api_key = yt_api_key or self.api_keys[0]
        self._init_client()

    def _init_client(self):
        # Seleciona a primeira chave saudável (que não esteja esgotada)
        healthy_indices = [i for i, k in enumerate(self.api_keys) if k not in self.exhausted_keys]
        if healthy_indices:
            if self.current_key_idx not in healthy_indices:
                self.current_key_idx = healthy_indices[0]
        else:
            # Se todas foram marcadas como esgotadas, limpa o conjunto e reinicia o ciclo
            print("[EXPERT WARN] Todas as chaves foram marcadas como esgotadas. Reiniciando ciclo de chaves...")
            self.exhausted_keys.clear()
            self.current_key_idx = 0

        key = self.api_keys[self.current_key_idx]
        import httpx
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
        timeout = httpx.Timeout(45.0, connect=10.0, read=45.0)
        h_client = httpx.Client(
            verify=False,
            http2=False,
            timeout=timeout,
            limits=limits,
            headers=browser_headers
        )
        http_options = types.HttpOptions(
            headers=browser_headers,
            httpx_client=h_client
        )
        self.client = genai.Client(api_key=key, http_options=http_options)
        print(f"[EXPERT] Cliente do SDK inicializado com User-Agent de navegador e chave índice {self.current_key_idx} (final: ...{key[-6:]})")

    def rotate_key(self, mark_exhausted: bool = True) -> bool:
        if len(self.api_keys) <= 1:
            return False
        if mark_exhausted:
            bad_key = self.api_keys[self.current_key_idx]
            self.exhausted_keys.add(bad_key)
            print(f"[EXPERT WARN] Chave índice {self.current_key_idx} (final ...{bad_key[-6:]}) marcada como ESGOTADA (429/cota).")
        
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        self._init_client()
        return True

    def get_match_chronology(self, team1: str, team2: str, competition: str, platform: str, date: str, start_timestamp: Optional[int] = None, duration: Optional[int] = None, video_url: Optional[str] = None, transcript_text: Optional[str] = None, status_callback: Optional[Callable[[str], None]] = None, sumula_raw_text: Optional[str] = None, live_start_time: Optional[str] = None, live_end_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Método público principal de auditoria de cronologia. Possui lógica de caching
        e loop auto-corretivo de validação contra a súmula oficial e portais.
        
        sumula_raw_text: Texto completo extraído diretamente do PDF oficial da súmula CBF.
                         Se fornecido, desativa o Google Search e usa o documento como fonte canônica.
        """
        from datetime import datetime, timedelta, timezone
        import hashlib
        
        # Sanitizar a competição logo no início
        comp_clean = str(competition or "").strip()
        if not comp_clean or comp_clean in ("—", "-", "None"):
            comp_clean = "Brasileirão / Copa do Brasil"
        competition = comp_clean

        # Caching de resultados do Expert
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "expert_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_key_raw = f"v3_{str(team1).strip()}_{str(team2).strip()}_{str(competition).strip()}_{str(date).strip()}".lower()
        cache_key = hashlib.md5(cache_key_raw.encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as fcache:
                    cached_res = json.load(fcache)
                if cached_res and "error" not in cached_res:
                    print(f"[EXPERT CACHE] Reaproveitando resultado cacheado para {team1} x {team2} ({date})")
                    if status_callback:
                        status_callback("Carregando resultado validado do cache...")
                    return cached_res
            except Exception as e_cache:
                print(f"[EXPERT CACHE WARN] Erro ao ler cache: {e_cache}")

        # Tentativa de buscar e decodificar a súmula em PDF automaticamente antes do loop
        if sumula_raw_text is None or not str(sumula_raw_text).strip():
            try:
                msg = "Buscando súmula oficial da CBF..."
                print(f"[EXPERT PIPELINE] {msg}")
                if status_callback:
                    status_callback(msg)
                
                from modules.cbf_schedule_fetcher import CBFScheduleFetcher

                # 1ª tentativa: PDF direto
                pdf_url = self.find_sumula_url_via_gemini(team1, team2, date, competition)
                if pdf_url:
                    msg = "Baixando e decodificando PDF da súmula..."
                    print(f"[EXPERT PIPELINE] {msg}")
                    if status_callback:
                        status_callback(msg)
                        
                    pdf_text = CBFScheduleFetcher.fetch_sumula_text(team1, team2, date, sumula_url=pdf_url)
                    if pdf_text and pdf_text.strip():
                        sumula_raw_text = pdf_text
                        print(f"[EXPERT PIPELINE] Súmula PDF obtida automaticamente! O pipeline rodará em modo canônico determinístico.")

                # 2ª tentativa: Extrair dados diretamente do HTML da página do jogo (fallback para SSL bloqueado)
                if not sumula_raw_text or not str(sumula_raw_text).strip():
                    print(f"[EXPERT PIPELINE] PDF bloqueado ou indisponível. Tentando extração via HTML da página CBF...")
                    if status_callback:
                        status_callback("PDF inacessível. Extraindo dados da página oficial CBF...")
                    
                    # Derivar URL da página do jogo a partir da URL do PDF ou buscar diretamente
                    game_page_url = None
                    if pdf_url:
                        # Converter URL do PDF em URL da página do jogo
                        import re as _re
                        # Tenta extrair o slug e ID do jogo do pdf_url se o mesmo foi encontrado via tabela
                        page_url_from_finder = getattr(self, '_last_game_page_url', None)
                        if page_url_from_finder:
                            game_page_url = page_url_from_finder
                    
                    if not game_page_url:
                        # Buscar a URL da página do jogo diretamente via scraping da tabela CBF
                        game_page_url = CBFScheduleFetcher.find_game_page_url(team1, team2, date, competition)
                    
                    if game_page_url:
                        html_text = CBFScheduleFetcher.fetch_sumula_from_cbf_html(game_page_url)
                        if html_text and html_text.strip():
                            sumula_raw_text = html_text
                            print(f"[EXPERT PIPELINE] Dados extraídos com sucesso do HTML da CBF! Pipeline rodará em modo canônico via página oficial.")
                    
                    if not sumula_raw_text or not str(sumula_raw_text).strip():
                        print(f"[EXPERT PIPELINE WARN] Falha em ambas as tentativas (PDF e HTML) de obter a súmula.")

            except Exception as e_pdf:
                print(f"[EXPERT PIPELINE WARN] Falha na rotina de busca de súmula automática: {e_pdf}")

        # TRAVA ESTRITA OBRIGATÓRIA: Relatórios Expert NÃO PODEM sair sem a súmula oficial baixada da CBF!
        if not sumula_raw_text or not str(sumula_raw_text).strip():
            msg_err = (
                f"❌ [AUDITORIA BLOQUEADA] Súmula oficial da CBF não encontrada ou pendente de publicação para {team1} x {team2} ({date}).\n"
                f"A auditoria no modo Expert exige obrigatoriamente o download da súmula oficial para garantir 100% de conformidade."
            )
            print(f"[EXPERT PIPELINE STRICT GUARD] {msg_err}")
            if status_callback:
                status_callback("❌ Auditoria cancelada: Súmula CBF pendente de publicação.")
            return {
                "error": msg_err,
                "status": "blocked_missing_sumula",
                "team1": team1,
                "team2": team2,
                "date": date
            }

        # Loop de Auditoria e Validação com Auto-Correção
        directive_correction = ""
        max_validation_attempts = 3
        res = None
        is_final_valid = False

        for val_attempt in range(max_validation_attempts):
            if sumula_raw_text:
                msg = f"Tentativa {val_attempt+1}/{max_validation_attempts}: Gerando relatório via leitura direta da súmula PDF..."
            else:
                msg = f"Tentativa {val_attempt+1}/{max_validation_attempts}: Gerando relatório com busca ativa..."
            print(f"[EXPERT PIPELINE] {msg}")
            if status_callback:
                status_callback(msg)
            
            # 1. Executa o fluxo de geração (IA com Busca Ativa ou Leitura Direta)
            try:
                res = self._execute_generation_flow(
                    team1=team1, team2=team2, competition=competition, platform=platform, date=date,
                    start_timestamp=start_timestamp, duration=duration, video_url=video_url,
                    transcript_text=transcript_text, directive_correction=directive_correction,
                    sumula_raw_text=sumula_raw_text
                )
            except Exception as ex_gen:
                print(f"[EXPERT PIPELINE WARN] Erro crítico no fluxo de geração: {ex_gen}")
                if val_attempt == max_validation_attempts - 1:
                    raise ex_gen
                continue
            
            if not res or "error" in res:
                if val_attempt == max_validation_attempts - 1:
                    return res or {"error": "IA não retornou um relatório válido."}
                continue

            # 2. Executa a validação cruzada independente contra a súmula
            msg = f"Tentativa {val_attempt+1}/{max_validation_attempts}: Validando com súmula oficial..."
            print(f"[EXPERT PIPELINE] {msg}")
            if status_callback:
                status_callback(msg)
                
            validation = self.validate_chronology(team1, team2, date, competition, res)
            
            is_valid = validation.get("is_valid") is True
            inconsistencies_list = []
            
            if validation.get("inconsistencies"):
                inconsistencies_list.append(validation.get("inconsistencies"))
            
            # Validação A: Limite de Confiança (Confidence Score) >= 90% (0.90)
            confidence_score = res.get("confidence_score", 0.0)
            if isinstance(confidence_score, (int, float)):
                if confidence_score > 1.0:
                    confidence_score = confidence_score / 100.0
            else:
                try:
                    confidence_score = float(str(confidence_score).replace("%", "").strip())
                    if confidence_score > 1.0:
                        confidence_score = confidence_score / 100.0
                except:
                    confidence_score = 0.0
            
            if confidence_score < 0.90:
                is_valid = False
                inconsistencies_list.append(
                    f"[CONFIANÇA BAIXA]: A confiança de geração reportada foi de {res.get('confidence_score') or 0.0}, que é menor que o limite aceitável de 90% (0.90). Garanta que a busca ativa no Google Search encontre dados precisos na súmula oficial e minuto a minuto da partida para elevar o nível de fidelidade."
                )
            
            # Validação B: Checagem estrita de placar contra marcos técnicos (Gols)
            official_score = str(validation.get("official_score") or "").strip()
            if official_score:
                import re
                score_nums = [int(n) for n in re.findall(r'\d+', official_score)]
                if len(score_nums) == 2:
                    expected_goals = sum(score_nums)
                    actual_goals = sum(
                        1 for m in res.get("technical_milestones", [])
                        if str(m.get("type", "")).strip().lower() == "gol"
                    )
                    if expected_goals != actual_goals:
                        is_valid = False
                        inconsistencies_list.append(
                            f"[DIVERGÊNCIA DE PLACAR]: O placar oficial real pesquisado é '{official_score}', que totaliza {expected_goals} gol(s). Porém, a lista de eventos 'technical_milestones' possui {actual_goals} gol(s). Você DEVE adicionar todos os gols corretos com seus respectivos autores e minutos exatos oficiais da partida, ou remover gols duplicados/incorretos para que o total de gols em 'technical_milestones' bata com o placar de {official_score}."
                        )
            
            if is_valid:
                msg = f"Sucesso! Relatório validado na tentativa {val_attempt+1}."
                print(f"[EXPERT PIPELINE] {msg}")
                if status_callback:
                    status_callback(msg)
                is_final_valid = True
                break
            else:
                directive_correction = " | ".join(inconsistencies_list)
                msg = f"Ajustando relatório (tentativa {val_attempt+1} recusada pelo validador)..."
                print(f"[EXPERT PIPELINE] Discrepâncias identificadas na tentativa {val_attempt+1}: {directive_correction}")
                if status_callback:
                    status_callback(msg)
                import time
                time.sleep(3)
                # Na próxima tentativa, a diretriz de correção guiará o modelo a corrigir os desvios.

        # 3. Salvar no cache (apenas se for um resultado sem erro e totalmente validado)
        if res and "error" not in res:
            if sumula_raw_text:
                import re as _re
                m_time = _re.search(r'hor[áa]rio(?:\s+de\s+in[íi]cio)?\s*:?\s*(\d{2}:\d{2})', str(sumula_raw_text), _re.IGNORECASE)
                if not m_time:
                    m_time = _re.search(r'1º\s*Tempo\s*:?\s*(\d{2}:\d{2})', str(sumula_raw_text), _re.IGNORECASE)
                if m_time:
                    ext_time = m_time.group(1).strip()
                    res["time"] = ext_time
                    res["event_time"] = ext_time
                    print(f"[EXPERT PIPELINE] Horário oficial da partida extraído da Súmula: {ext_time}")

            if live_start_time and str(live_start_time).strip():
                res["live_start_time"] = str(live_start_time).strip()
            if live_end_time and str(live_end_time).strip():
                res["live_end_time"] = str(live_end_time).strip()

            if not res.get("live_start_time"):
                plat_u = str(platform or "").upper()
                if "CAZE" in plat_u or "CAZÉ" in plat_u or "YOUTUBE" in plat_u or video_url:
                    try:
                        from modules.youtube_metadata import fetch_youtube_live_details, search_youtube_live_url
                        target_url = video_url
                        if not target_url:
                            target_url = search_youtube_live_url(f"CazéTV {team1} x {team2}")
                        if target_url:
                            live_info = fetch_youtube_live_details(target_url)
                            if live_info and live_info.get("live_start_time"):
                                res["live_start_time"] = live_info["live_start_time"]
                                if live_info.get("live_end_time"):
                                    res["live_end_time"] = live_info["live_end_time"]
                                print(f"[EXPERT YOUTUBE LIVE] Extraído automaticamente do YouTube ({target_url}): Início {live_info['live_start_time']} | Fim {live_info.get('live_end_time')}")
                    except Exception as e_yt:
                        print(f"[EXPERT YOUTUBE LIVE WARN] Falha na busca automática do YouTube: {e_yt}")

            if is_final_valid:
                try:
                    with open(cache_file, "w", encoding="utf-8") as fcache:
                        json.dump(res, fcache, indent=2, ensure_ascii=False)
                    print(f"[EXPERT CACHE] Resultado validado salvo com sucesso no cache para {team1} x {team2} ({date})")
                except Exception as e_save:
                    print(f"[EXPERT CACHE WARN] Falha ao salvar no cache: {e_save}")
        
        return res

    def _execute_generation_flow(self, team1: str, team2: str, competition: str, platform: str, date: str, start_timestamp: Optional[int] = None, duration: Optional[int] = None, video_url: Optional[str] = None, transcript_text: Optional[str] = None, directive_correction: str = "", sumula_raw_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Executa a geração do prompt de auditoria e a consulta à IA.
        Se sumula_raw_text for fornecido: usa leitura direta do PDF (sem Google Search).
        Caso contrário: mantém a busca ativa via Google Search Grounding.
        """
        from datetime import datetime, timedelta, timezone
        import hashlib

        # Caching de resultados do Expert (interno para fluxo)
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "expert_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_key_raw = f"v3_{str(team1).strip()}_{str(team2).strip()}_{str(competition).strip()}_{str(date).strip()}".lower()
        cache_key = hashlib.md5(cache_key_raw.encode("utf-8")).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")

        # Fuso horário de Brasília para a âncora do relatório
        br_tz = timezone(timedelta(hours=-3))
        
        start_time_str = "Não informado"
        duration_str = "Não informada"
        end_time_str = "Não calculado"
        
        if start_timestamp:
            try:
                dt_start = None
                if isinstance(start_timestamp, (int, float)):
                    dt_start = datetime.fromtimestamp(int(start_timestamp), tz=br_tz)
                elif isinstance(start_timestamp, str):
                    s_str = start_timestamp.strip()
                    if s_str.isdigit():
                        dt_start = datetime.fromtimestamp(int(s_str), tz=br_tz)
                    else:
                        s_iso = s_str.replace("Z", "+00:00")
                        try:
                            dt_start = datetime.fromisoformat(s_iso).astimezone(br_tz)
                        except Exception:
                            dt_start = datetime.strptime(s_iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(br_tz)
                
                if dt_start:
                    start_time_str = dt_start.strftime("%H:%M:%S")
                    start_timestamp = int(dt_start.timestamp())
                    if duration:
                        dt_end = dt_start + timedelta(seconds=int(float(duration)))
                        end_time_str = dt_end.strftime("%H:%M:%S")
            except Exception as e_ts:
                print(f"[EXPERT WARN] Falha ao processar start_timestamp ({start_timestamp}): {e_ts}")
                
        if duration:
            try:
                dur_f = float(duration)
                h = int(dur_f // 3600)
                m = int((dur_f % 3600) // 60)
                s = int(dur_f % 60)
                duration_str = f"{h:02d}:{m:02d}:{s:02d}"
            except:
                pass

        if video_url and start_time_str == "Não informado":
            import re
            vid_match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", video_url)
            if vid_match:
                vid_id = vid_match.group(1)
                meta = self.get_youtube_live_metadata(vid_id)
                if meta.get("actual_start_time"):
                    try:
                        dt = datetime.strptime(meta["actual_start_time"].replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                        dt = dt.astimezone(br_tz)
                        start_time_str = dt.strftime("%H:%M:%S")
                        start_timestamp = int(dt.timestamp())
                    except: pass
                if meta.get("duration") and duration_str == "Não informada":
                    try:
                        dur_sec = meta["duration"]
                        duration = dur_sec
                        h, m, s = dur_sec // 3600, (dur_sec % 3600) // 60, dur_sec % 60
                        duration_str = f"{h:02d}:{m:02d}:{s:02d}"
                    except: pass

        match_id_val = f"{team1}_{team2}_{date}"
        team1_safe = (team1 or "Time 1").replace('"', "'")
        team2_safe = (team2 or "Time 2").replace('"', "'")
        comp_clean = str(competition or "").strip()
        if not comp_clean or comp_clean in ("—", "-", "None"):
            comp_clean = "Brasileirão / Copa do Brasil"
        competition_safe = comp_clean.replace('"', "'")
        
        transcript_block = ""
        if transcript_text:
            transcript_block = f"""
        [TRANSCRIÇÃO DE ÁUDIO DO NARRADOR - TIMESTAMPS DO VÍDEO]:
        Esta é a transcrição fiel da narração de áudio do vídeo, dividida por janelas de tempo [MM:SS] (minutos e segundos do vídeo). Use-a como fonte prioritária de verdade para alinhar os lances e apitos:
        {transcript_text}
        """

        # Classificação de Mídia (Highlights/Short Video ou Sem Âncora)
        use_grounding_clock = False
        duration_sec = None
        if duration:
            try: duration_sec = float(duration)
            except: pass
            
        if not start_timestamp or (duration_sec is not None and duration_sec < 5400):
            use_grounding_clock = True

        if use_grounding_clock:
            rule_7_prompt = f"""7. BUSCA FOCADA NA SÚMULA ELETRÔNICA CBF E COBERTURA MINUTO A MINUTO (CRÍTICO):
           Para garantir que a cronologia reflita os horários reais e a súmula exata da partida "{team1_safe}" x "{team2_safe}" na data {date}:
           
           VOCÊ DEVE PESQUISAR EXPLICITAMENTE NO GOOGLE SEARCH PELOS SEGUINTES TERMOS E FONTES:
           1. "site:cbf.com.br" "Súmula" "{team1_safe}" "{team2_safe}"
           2. "Súmula Eletrônica CBF" "{team1_safe} x {team2_safe}" "{date}"
           3. "Tempo Real" "{team1_safe} x {team2_safe}" "{date}" site:ge.globo.com OR site:uol.com.br OR site:lance.com.br OR site:flashscore.com.br
           
           A Súmula Eletrônica Oficial da CBF e os relatos oficiais registram obrigatoriamente em relógio real os 4 carimbos de hora (timestamps) vitais da partida:
            - Início do 1º Tempo (first_half_start)
            - Término do 1º Tempo (half_time_start)
            - Início do 2º Tempo (second_half_start / half_time_end)
            - Término do 2º Tempo / Apito Final (match_end)

            REGRA DE ANCORAGEM RÍGIDA (DERIVA ZERO):
            1. EXTRAIA OS 4 CARIMBOS DE HORA REAIS DA SÚMULA/FICHA TÉCNICA. NUNCA faça cálculos sintéticos de soma ou inferências lineares para esses 4 marcos.
            2. O Apito Final ('match_end') DEVE obrigatoriamente receber o horário oficial de encerramento registrado na súmula/transmissão (ex: 23:24:03 ou 23:25:00). NUNCA calcule o apito final por soma sintética.
            3. O reinício do 2º tempo ('second_half_start') DEVE ser lido diretamente da súmula (ex: 22:35:00 ou 22:38:00) e servirá de base rígida para calcular a hora dos gols/cartões do 2º tempo.
            4. Preserve segundos exatos sempre que disponíveis na súmula ou na transmissão (ex: 23:24:03). NUNCA pode ser anterior ao último gol ou cartão ocorrido nos acréscimos!"""
            
            anchor_start_line = ""
            anchor_directive = "Busque o horário oficial da partida de Brasília (UTC-3) na internet e utilize-o como base absoluta para todos os campos do relatório."
            if start_time_str != "Não informado":
                anchor_start_line = f"\n          - Início Real/VOD da Transmissão (Informado): {start_time_str} (Brasília - UTC-3)."
                anchor_directive = f"Ignore horários de upload e buscas genéricas de início de relógio na internet. O 'Início Real/VOD da Transmissão (Informado)' ({start_time_str}) é a hora EXATA do apito inicial do primeiro tempo (first_half_start / match_start) e NÃO o início do pré-jogo. A bola deve começar a rolar exatamente neste segundo/minuto informado (ex: se informado {start_time_str}, preencha first_half_start = '{start_time_str}'). Utilize-o como base rígida e construa a linha do tempo a partir dele."

            context_anchor_prompt = f"""CONTEXTO DA TRANSMISSÃO (ÂNCORA):
          - Tipo de Mídia: MELHORES MOMENTOS / BUSCA DE IMAGEM / MANUAL (Sem fluxo contínuo de transmissão).{anchor_start_line}
          - Duração Total da Mídia: {duration_str}.
          - Diretriz: {anchor_directive}
          {transcript_block}"""
        else:
            rule_7_prompt = f"""7. ENCERRAMENTO OBRIGATÓRIO:
           O campo 'post_game_end' DEVE obrigatoriamente ser EXATAMENTE igual ao 'Encerramento OBRIGATÓRIO' ({end_time_str}) informado no Contexto da Transmissão abaixo! NENHUM segundo de diferença."""
            
            context_anchor_prompt = f"""CONTEXTO DA TRANSMISSÃO (ÂNCORA):
         - Início Real da Transmissão (VOD/Live): {start_time_str} (Brasília - UTC-3).
         - Duração Total da Mídia: {duration_str}.
         - Encerramento OBRIGATÓRIO: {end_time_str}.
         {transcript_block}"""

        # Bloco de súmula PDF injetado como fonte canônica (quando disponível)
        sumula_block = ""
        grounding_directive_4 = f"""4. GROUNDING DE PESQUISA REAL (BUSCA DA SÚMULA E COBERTURA MINUTO A MINUTO):
            Você DEVE pesquisar ativamente no Google Search pela SÚMULA OFICIAL DA CBF / FEDERAÇÃO ou coberturas minuto a minuto (Globo Esporte, UOL, Lance, Flashscore, ESPN) da partida "{team1_safe}" x "{team2_safe}" na data {date} "{competition_safe}".
            * RESTRIÇÃO FACTUAL CRÍTICA: É terminantemente proibido utilizar escalações, atletas ou eventos de confrontos históricos de outras temporadas/anos. Se a partida informada ocorreu na data {date}, todos os eventos (gols, cartões, substituições) devem pertencer estritamente a este jogo específico.
            Extraia as informações REAIS pesquisadas na internet:
            - Minutos exatos em que cada gol, cartão ou substituição ocorreu (ex: 45+3' ou 90+8').
            - Os acréscimos oficiais exatos: stoppage_time_1t = half_time_start − first_half_start − 45 min. stoppage_time_2t = match_end − second_half_start − 45 min. NUNCA invente acréscimos genéricos nem infle com estimativas opinativas.
            - O apito final da partida ('match_end') DEVE obrigatoriamente acontecer APÓS o último gol/evento ocorrido nos acréscimos."""

        if sumula_raw_text:
            sumula_block = f"""
        [DOCUMENTO OFICIAL - SÚMULA ELETRÔNICA CBF (FONTE CANÔNICA ABSOLUTA - PESO 1.0)]:
        O texto abaixo foi extraído diretamente do PDF oficial da Súmula Eletrônica da CBF para esta partida.
        Este documento tem AUTORIDADE MÁXIMA e SOBREPOSIÇÃO TOTAL sobre qualquer outra fonte.
        Você NÃO deve fazer buscas no Google Search — use EXCLUSIVAMENTE este documento para extrair:
        - Placar final e gols (autor, minuto, time)
        - Substituições realizadas (jogador que entrou, jogador que saiu, time, minuto)
        - Cartões amarelos e vermelhos (jogador, time, minuto)
        - Horários oficiais de início/fim de cada tempo (first_half_start, half_time_start, second_half_start, match_end)
        - Acréscimos reais concedidos pela arbitragem
        
        TEXTO DA SÚMULA:
        ---
        {sumula_raw_text[:8000]}
        ---
        """
            grounding_directive_4 = f"""4. FONTE CANÔNICA ABSOLUTA (SÚMULA PDF):
            O texto da súmula oficial foi injetado acima. Use EXCLUSIVAMENTE este documento.
            NÃO faça buscas adicionais no Google. NÃO complete com dados externos.
            - stoppage_time_1t = half_time_start − first_half_start − 45 min (calcule dos horários da súmula)
            - stoppage_time_2t = match_end − second_half_start − 45 min (calcule dos horários da súmula)"""

        prompt = f"""
        Você é o Motor de Reconstrução de Linha Temporal Canônica (Auditor Sênior V2.1).
        Hoje é dia {datetime.now(br_tz).strftime('%d/%m/%Y')}. A partida ocorreu no passado. O ano atual de relógio real é {datetime.now(br_tz).strftime('%Y')}.
        Sua missão é criar uma cronologia técnica EXAUSTIVA, LIVRE DE DERIVAS e EXTREMAMENTE PRECISA da partida: "{team1_safe}" x "{team2_safe}" pela competição "{competition_safe}" na data {date} (ou na data real do jogo, caso a transmissão/upload tenha ocorrido após a meia-noite ou no dia seguinte).

        DIRETRIZES DA ARQUITETURA TEMPORAL (BLUEPRINT V2):
        1. RELAÇÃO DE CONFIANÇA E DERIVA ZERO: 
           Não confie cegamente na soma linear 'início + offsets do vídeo' se houver indícios de cortes, retransmissões ou VODs editados. Crie uma "Linha Temporal Canônica" cruzando todas as evidências.
           A hierarquia de confiança absoluta é: Súmula PDF Oficial CBF (Peso 1.0) > OCR/Relógio Físico de Transmissão (Peso 0.95) > OCR do Scoreboard de Jogo (Peso 0.90) > Transcrição do Narrador (Peso 0.75) > Grounding Histórico do Gemini (Peso 0.55).
           Se houver conflito de horários entre o que o narrador diz e o relógio visual exibido na tela, o OCR visual VENCE sempre!

        2. REVERSE TIMELINE SOLVER (CRÍTICO):
           Use a técnica de cálculo reverso (back-solving) para alinhamento temporal quando aplicável (ou seja, quando tiver uma âncora de encerramento real e confiável da transmissão completa).
           
        3. CLOCK DO FUTEBOL vs RELÓGIO REAL E INTERVALO:
            - Separe explicitamente o tempo absoluto (Relógio real de Brasília) do tempo futebolístico oficial (ex: 45+3' ou 90+6' do 2T).
            - O intervalo do jogo NÃO conta como tempo de partida jogado, mas consome tempo real de relógio de transmissão (média de 21 minutos no Brasil).
            - REGRA MATEMÁTICA RÍGIDA DE CÁLCULO DE TIMESTAMPS:
              - O fim do 1º Tempo ('half_time_start') DEVE ser igual a: 'first_half_start' + 45 minutos + 'stoppage_time_1t' minutos.
              - O reinício do 2º Tempo ('second_half_start') DEVE ser igual a: 'half_time_start' + Tempo de Intervalo (exato ou estimado de 21 minutos).
              - O fim do jogo ('match_end') DEVE ser igual a: 'second_half_start' + 45 minutos + 'stoppage_time_2t' minutos.
              - Se um evento ocorre nos acréscimos do 1T (ex: 45+X minutos), seu horário real DEVE ser: 'first_half_start' + 45 minutos + X minutos.
              - Se um evento ocorre nos acréscimos do 2T (ex: 90+Y minutos), seu horário real DEVE ser: 'second_half_start' + 45 minutos + Y minutos.
              - CÁLCULO OBRIGATÓRIO DOS ACRÉSCIMOS: stoppage_time_1t = half_time_start − first_half_start − 45. stoppage_time_2t = match_end − second_half_start − 45. NUNCA infle com estimativas opinativas de transmissão.
              Qualquer desvio destas fórmulas causará rejeição pelo validador.

        {grounding_directive_4}

        5. FIDELIDADE E EXAUSTIVIDADE DE EVENTOS (NUNCA SUPRIMA MARCOS):
           Não adicione conversas, explicações longas ou rodeios fora do formato JSON. Mantenha os campos "analysis" and "event" curtos, mas garanta que TODOS os eventos cruciais de súmula estejam presentes na lista sem omitir nenhum gol, cartão ou substituição. É terminantemente proibido supor acréscimos como 0 minutos se houver acréscimos informados na súmula oficial.

        6. ITENS E FORMATO (EXAUSTIVIDADE DOS EVENTOS):
           - A lista 'technical_milestones' DEVE conter todos os marcos técnicos importantes da partida: todos os gols (placar completo e sem omissões), cartões amarelos, cartões vermelhos, substituições realizadas por ambos os times, além do início/fim de cada tempo. Ordene cronologicamente e limite a no máximo 45 itens para cobrir todos os eventos oficiais da súmula.
           - PROIBIÇÃO DE NOMES SINTÉTICOS: Se uma substituição, cartão ou gol específico não constar expressamente na súmula ou ficha técnica oficial pesquisada, NÃO invente atletas, nem complete a lista com jogadores de outros clubes ou edições de anos anteriores para atingir qualquer teto de eventos. Insira ESTRITAMENTE as substituições, cartões e gols declarados no documento oficial. Qualquer nome de atleta inventado causará rejeição pelo validador.
           - Se a mídia não possui vídeo ou transcrição de vídeo (use_grounding_clock é True), a lista 'transcript_events' DEVE obrigatoriamente vir vazia: [].
           - Se houver vídeo, a lista 'transcript_events' deve conter no máximo 15 eventos narrativos importantes e bem distribuídos ao longo do jogo. Filtre rigidamente apenas o que for relevante.

        {rule_7_prompt}
        {sumula_block}
        {context_anchor_prompt}

        FORMATO DE RESPOSTA (JSON ABSOLUTAMENTE SEVERO, RETORNE APENAS O OBJETO):
        {{
            "match_id": "{match_id_val}",
            "date": "{date}",
            "match_display": "{team1_safe} x {team2_safe}",
            "competition": "{competition_safe}",
            "confidence_score": 0.99,
            "pre_game_start": "HH:MM:SS",
            "match_start": "HH:MM:SS",
            "first_half_start": "HH:MM:SS",
            "half_time_start": "HH:MM:SS",
            "half_time_end": "HH:MM:SS",
            "second_half_start": "HH:MM:SS",
            "match_end": "HH:MM:SS",
            "post_game_end": "HH:MM:SS",
            "stoppage_time_1t": 0,
            "stoppage_time_2t": 0,
            "technical_milestones": [
                {{
                    "time": "HH:MM:SS", 
                    "minute": 19,
                    "event": "Descrição curta e clara do evento, ex: GOL de John Kennedy (Fluminense).", 
                    "type": "Gol",
                    "confidence": 0.99
                }}
            ],
            "transcript_events": [
                {{
                    "video_time": "MM:SS",
                    "real_time": "HH:MM:SS",
                    "narration": "Narração ou evento detectado na transcrição de áudio.",
                    "analysis": "Cálculo matemático detalhado (ex: Back-solving ou soma ao início)."
                }}
            ]
        }}
        """
        if directive_correction:
            prompt += f"\n\n[ATENÇÃO - DIRETRIZ DE AUTO-CORREÇÃO OBRIGATÓRIA (TENTATIVA ADICIONAL)]:\nO seu relatório gerado anteriormente continha as seguintes inconsistências em relação aos dados oficiais de súmula e minuto a minuto. Você DEVE corrigir estas discrepâncias e preencher o que estiver faltando de forma rigorosa no JSON final:\n{directive_correction}\n"
            
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
                max_output_tokens=16384,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE")
                ]
            )

            config_no_grounding = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=16384,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE")
                ]
            )

            # Mecanismo de Retry Otimizado (3 tentativas por modelo: 1ª e 2ª com Grounding, 3ª sem Grounding)
            max_retries = 3
            fallbacks = [
                "gemini-2.5-flash",
                "gemini-3.5-flash",
                "gemini-1.5-flash",
                "gemini-3.1-pro-preview"
            ]
            models_to_try = [self.model_id]
            for m in fallbacks:
                if m not in models_to_try:
                    models_to_try.append(m)

            last_error = None
            force_no_grounding = False
            for current_model in models_to_try:
                for attempt in range(max_retries):
                    # Modo PDF ou Fallback de Rede: sem grounding (ultra rápido e imune a timeout de proxy)
                    if force_no_grounding or sumula_raw_text or attempt >= 1:
                        use_cfg = config_no_grounding
                        mode_label = f"Modo Direto sem WebSearch (Tentativa {attempt+1})"
                    else:
                        use_cfg = config
                        mode_label = f"Com Grounding (Tentativa {attempt+1})"
                    try:
                        print(f"[EXPERT] Tentativa {attempt+1} com modelo {current_model} ({mode_label})...")
                        response = self.client.models.generate_content(
                            model=current_model,
                            contents=prompt,
                            config=use_cfg
                        )
                        
                        self._last_raw_response = response
                        # Debug de resposta
                        c = response.candidates[0] if response.candidates else None
                        print(f"[EXPERT] Resposta recebida. Candidatos: {len(response.candidates or [])} | Finish Reason: {c.finish_reason if c else 'N/A'}")
                        
                        if not response or not response.candidates or not response.candidates[0].content:
                             raise ValueError(f"Modelo {current_model} retornou resposta totalmente vazia.")
                              
                        # Aviso tolerante de truncamento sem derrubar a extração
                        if c and c.finish_reason and "MAX_TOKENS" in str(c.finish_reason):
                             print("[EXPERT WARN] Resposta atingiu MAX_TOKENS, tentando extrair conteúdo gerado...")

                        # Extração manual de texto das partes
                        txt = ""
                        if c.content and c.content.parts:
                            # Se o modelo retornou a resposta em partes idênticas devido a bug do SDK, removemos a duplicata
                            seen_parts = set()
                            for idx_p, p in enumerate(c.content.parts):
                                p_text = getattr(p, 'text', None)
                                if p_text:
                                    print(f"[DEBUG] Part {idx_p}: text_type={type(p_text)} | len={len(p_text)}")
                                    p_text_str = str(p_text)
                                    # Se a mesma string exata de texto for repetida sequencialmente, ignora para evitar duplicação do JSON
                                    if p_text_str not in seen_parts:
                                        txt += p_text_str
                                        seen_parts.add(p_text_str)

                        if not txt.strip():
                             raise ValueError("Falha ao extrair texto (vazio) das partes da resposta.")

                        # Extração de fontes (Search Grounding com Links Oficiais da CBF e Portais)
                        sources = []
                        try:
                            # 1. Adicionar Links Oficiais de Auditoria da CBF e Cobertura Esportiva
                            cbf_search_url = f"https://www.cbf.com.br/futebol-brasileiro/jogos?q={team1_safe}+{team2_safe}"
                            ge_search_url = f"https://ge.globo.com/busca/?q=Sumula+{team1_safe}+{team2_safe}+{date}"
                            
                            sources.append({
                                "uri": cbf_search_url,
                                "title": "Súmula Eletrônica Oficial - Confederação Brasileira de Futebol (cbf.com.br)"
                            })
                            sources.append({
                                "uri": ge_search_url,
                                "title": "Cobertura Minuto a Minuto - Globo Esporte (ge.globo.com)"
                            })

                            if response.candidates and response.candidates[0].grounding_metadata:
                                metadata = response.candidates[0].grounding_metadata
                                
                                # 2. Extrair das grounding_chunks (Evidências de busca do Gemini)
                                chunks = getattr(metadata, "grounding_chunks", [])
                                if chunks:
                                    for chunk in chunks:
                                        if hasattr(chunk, "web") and chunk.web:
                                            raw_uri = str(chunk.web.uri or "")
                                            raw_title = str(chunk.web.title or "Fonte de Pesquisa").strip()
                                            
                                            # Formatar nome amigável do portal
                                            display_title = raw_title
                                            if "cbf" in raw_title.lower() or "cbf" in raw_uri.lower():
                                                display_title = "cbf.com.br - Súmula Oficial CBF"
                                            elif "lance" in raw_title.lower():
                                                display_title = "lance.com.br - Cobertura da Partida"
                                            elif "abril" in raw_title.lower() or "placar" in raw_title.lower():
                                                display_title = "placar.abril.com.br - Ficha Técnica"
                                            elif "flashscore" in raw_title.lower() or "flashscore" in raw_uri.lower():
                                                display_title = "flashscore.com.br - Cronologia Oficial"
                                            elif "uol" in raw_title.lower():
                                                display_title = "uol.com.br/esporte - Tempo Real"

                                            sources.append({
                                                "uri": raw_uri,
                                                "title": display_title
                                            })

                                # 3. Limpar duplicatas de URLs
                                unique_sources = []
                                seen_urls = set()
                                for s in sources:
                                    u = s.get("uri")
                                    if u and u not in seen_urls:
                                        unique_sources.append(s)
                                        seen_urls.add(u)
                                sources = unique_sources
                                print(f"[EXPERT] Sucesso: {len(sources)} fontes de grounding formatadas com CBF e portais.")
                        except Exception as e_sources:
                            print(f"[EXPERT] Erro ao processar fontes de grounding: {e_sources}")
                            pass

                        # --- PROCESSAMENTO DO JSON ---
                        raw_text = txt.strip()
                        clean_text = raw_text
                        if clean_text.lower().startswith("```json"):
                            clean_text = clean_text[7:]
                        elif clean_text.startswith("```"):
                            clean_text = clean_text[3:]
                            
                        if clean_text.endswith("```"):
                            clean_text = clean_text[:-3]
                            
                        clean_text = clean_text.strip()

                        # Tenta extrair o bloco JSON usando regex
                        import re
                        json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
                        if json_match:
                            clean_text = json_match.group(1).strip()
                        else:
                            snippet = clean_text[:150].replace('\n', ' ')
                            raise ValueError(f"IA não retornou objeto JSON válido no texto. Resposta: {snippet}...")

                        # Limpeza de wrappers Markdown residuais
                        clean_text = clean_text.replace("```json", "").replace("```", "").strip()

                        # Limpeza de caracteres de controle invisíveis
                        clean_text = "".join(ch for ch in clean_text if ord(ch) >= 32 or ch in '\n\r\t')

                        if not clean_text:
                            raise ValueError("Bloco de texto limpo para JSON está vazio.")

                        # Reparo de aspas não escapadas e novas linhas
                        import json
                        def fix_json_values(text):
                            def replacer(match):
                                prefix = match.group(1) # ": "
                                content = match.group(2) # value
                                content = re.sub(r'(?<!\\)"', r'\"', content)
                                content = content.replace('\n', '\\n').replace('\r', '\\r')
                                return prefix + content + '"'
                            
                            fixed = re.sub(r'(":\s*")(.+?)("(?=\s*[,}\]]))', replacer, text, flags=re.DOTALL)
                            fixed = re.sub(r'}\s*{', '}, {', fixed)
                            fixed = re.sub(r']\s*\[', '], [', fixed)
                            fixed = re.sub(r',\s*}', '}', fixed)
                            fixed = re.sub(r',\s*]', ']', fixed)
                            return fixed

                        # Função de alinhamento temporal (Time Shift) com recálculo matemático de desvio zero
                        def align_result(res):
                            if "error" not in res:
                                try:
                                    import re
                                    def parse_int_safe(val):
                                         if val is None: return 0
                                         if isinstance(val, int): return val
                                         val_str = str(val).strip()
                                         if "+" in val_str:
                                             parts = val_str.split("+")
                                             try:
                                                 return sum(int(re.sub(r'\D', '', p)) for p in parts if re.sub(r'\D', '', p))
                                             except:
                                                 pass
                                         try:
                                             digits = re.findall(r'\d+', val_str)
                                             if digits:
                                                 return int(digits[0])
                                         except:
                                             pass
                                         return 0
                                    
                                    # 1. Determinar o horário base (kickoff)
                                    if start_timestamp:
                                        res["first_half_start"] = start_time_str
                                        res["match_start"] = start_time_str
                                    
                                    ia_start_str = res.get("first_half_start") or res.get("match_start")
                                    if not ia_start_str or ia_start_str == "HH:MM:SS":
                                        return res
                                    
                                    # Caso o modelo tenha retornado em formato parcial (ex: sem segundos), completa
                                    if len(ia_start_str) == 5:
                                        ia_start_str += ":00"
                                    
                                    # Formatar para HH:MM:SS
                                    def format_time_str(ts_str):
                                        if not ts_str or ts_str == "HH:MM:SS":
                                            return None
                                        ts_str = ts_str.strip()
                                        if len(ts_str) == 5:
                                            return ts_str + ":00"
                                        return ts_str[:8]
                                        
                                    orig_fh_start = res.get("first_half_start") or res.get("match_start")
                                    orig_ht_start = res.get("half_time_start")
                                    orig_sh_start = res.get("second_half_start") or res.get("half_time_end")
                                    orig_match_end = res.get("match_end")
                                    
                                    fh_start_s = format_time_str(orig_fh_start) or ia_start_str
                                    ht_start_s = format_time_str(orig_ht_start)
                                    sh_start_s = format_time_str(orig_sh_start)
                                    match_end_s = format_time_str(orig_match_end)
                                    
                                    t_start = datetime.strptime(fh_start_s, "%H:%M:%S")
                                    t_half_start = datetime.strptime(ht_start_s, "%H:%M:%S") if ht_start_s else None
                                    t_half_end = datetime.strptime(sh_start_s, "%H:%M:%S") if sh_start_s else None
                                    t_match_end = datetime.strptime(match_end_s, "%H:%M:%S") if match_end_s else None
                                    
                                    # Obter acréscimos informados pela IA
                                    stop1 = parse_int_safe(res.get("stoppage_time_1t"))
                                    stop2 = parse_int_safe(res.get("stoppage_time_2t"))
                                    
                                    # Deduzir stoppage_time_1t se os timestamps da súmula estiverem presentes
                                    if t_half_start:
                                        diff_1t = int((t_half_start - t_start).total_seconds() / 60)
                                        if 45 <= diff_1t <= 65:
                                            stop1 = diff_1t - 45
                                            res["stoppage_time_1t"] = stop1
                                            
                                    # Deduzir stoppage_time_2t se os timestamps da súmula estiverem presentes
                                    if t_half_end and t_match_end:
                                        diff_2t = int((t_match_end - t_half_end).total_seconds() / 60)
                                        if 45 <= diff_2t <= 65:
                                            stop2 = diff_2t - 45
                                            res["stoppage_time_2t"] = stop2
                                            
                                    # Se algum timestamp estiver ausente, calcular via acréscimos (fallback canônico)
                                    if not t_half_start:
                                        t_half_start = t_start + timedelta(minutes=45 + stop1)
                                        
                                    if not t_half_end:
                                        t_half_end = t_half_start + timedelta(minutes=21) # Intervalo comercial padrão
                                        
                                    if not t_match_end:
                                        t_match_end = t_half_end + timedelta(minutes=45 + stop2)
                                        
                                    # Salvar no JSON final alinhado
                                    res["first_half_start"] = t_start.strftime("%H:%M:%S")
                                    res["half_time_start"] = t_half_start.strftime("%H:%M:%S")
                                    res["half_time_end"] = t_half_end.strftime("%H:%M:%S")
                                    res["second_half_start"] = t_half_end.strftime("%H:%M:%S")
                                    res["match_end"] = t_match_end.strftime("%H:%M:%S")
                                    
                                    # Ajustar tempos de captação (pre e post game)
                                    res["pre_game_start"] = (t_start - timedelta(minutes=5)).strftime("%H:%M:%S")
                                    res["post_game_end"] = (t_match_end + timedelta(minutes=5)).strftime("%H:%M:%S")
                                    
                                    # 3. Alinhamento cirúrgico dos marcos técnicos
                                    milestones = res.get("technical_milestones", [])
                                    for m in milestones:
                                        min_val = m.get("minute")
                                        if min_val is not None:
                                            try:
                                                min_val = parse_int_safe(min_val)
                                                m_str = str(m.get("event", "")).upper() + " " + str(m.get("type", "")).upper() + " " + str(min_val)
                                                is_explicit_1t = ("1T" in m_str or "45+" in m_str or "PRIMEIRO" in m_str)
                                                
                                                if is_explicit_1t or min_val <= 45:
                                                    # Limitar a minuto 45+acréscimos
                                                    cap_min = min(min_val, 45 + stop1)
                                                    t_event = t_start + timedelta(minutes=cap_min)
                                                    if t_event > t_half_start:
                                                        t_event = t_half_start
                                                else:
                                                    # Segundo tempo: min_val > 45
                                                    min_2t = min_val - 45
                                                    cap_min_2t = min(min_2t, 45 + stop2)
                                                    t_event = t_half_end + timedelta(minutes=cap_min_2t)
                                                    if t_event > t_match_end:
                                                        t_event = t_match_end
                                                        
                                                m["time"] = t_event.strftime("%H:%M:%S")
                                            except Exception as e_m:
                                                print(f"[EXPERT WARN] Falha ao alinhar marco técnico: {e_m}")
                                                
                                    print(f"[EXPERT] Ancoragem rígida de Súmula travada. 1T: {res['first_half_start']}->{res['half_time_start']} | 2T: {res['second_half_start']}->{res['match_end']}")
                                except Exception as e_shift:
                                    print(f"[EXPERT WARN] Falha ao aplicar alinhamento temporal dinâmico: {e_shift}")
                            
                            return res

                        # Tenta decodificar o JSON
                        try:
                            result = json.loads(clean_text)
                            result["sources"] = sources if sources else []
                            if duration: result["duration"] = duration
                            
                            if not result.get("sources"):
                                result["sources"] = [{
                                    "uri": f"https://www.google.com/search?q={team1}+x={team2}+{date}",
                                    "title": "Link de Auditoria (Pesquisa Web)"
                                }]
                            return align_result(result)
                        except json.JSONDecodeError as je:
                            # Tenta reparar aspas e vírgulas usando a função fix_json_values
                            try:
                                fixed_text = fix_json_values(clean_text)
                                result = json.loads(fixed_text)
                                result["sources"] = sources if sources else []
                                if duration: result["duration"] = duration
                                
                                if not result.get("sources"):
                                    result["sources"] = [{
                                        "uri": f"https://www.google.com/search?q={team1}+x={team2}+{date}",
                                        "title": "Link de Auditoria (Pesquisa Web)"
                                    }]
                                return align_result(result)
                            except json.JSONDecodeError as je2:
                                with open("scratch/debug_raw_response.txt", "w", encoding="utf-8") as debug_f:
                                    debug_f.write(clean_text)
                                raise ValueError(f"JSON Decode Error: {je2} | Início: {clean_text[:150]}")

                    except Exception as e:
                        last_error = e
                        err_msg = str(e)
                        print(f"[EXPERT WARN] Falha na tentativa {attempt+1} com modelo {current_model}: {err_msg}")
                        
                        # Se for erro de quota (429) ou spend cap excedido, tenta rotacionar a chave de API e re-executar
                        if "429" in err_msg or "spend cap" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower():
                            if self.rotate_key():
                                print(f"[EXPERT] Rotação de chave ativada devido a limite/quota! Nova chave carregada. Repetindo a tentativa...")
                                continue

                        # Se for erro de desconexão de rede ou timeout (Proxy/Firewall corporativo)
                        is_disconnect = (
                            "server disconnected" in err_msg.lower() or
                            "disconnected without sending" in err_msg.lower() or
                            "connection reset" in err_msg.lower() or
                            "remote end closed" in err_msg.lower() or
                            "timed out" in err_msg.lower() or
                            "timeout" in err_msg.lower()
                        )
                        if is_disconnect:
                            force_no_grounding = True
                            try:
                                self._init_client()
                            except: pass
                            import time
                            print(f"[EXPERT AVISO] Conexão interrompida pelo firewall/proxy da rede. Sessão HTTP reinicializada e modo rápido sem WebSearch acionado...")
                            time.sleep(2)
                            continue

                        # Se for erro de quota (429) ou indisponibilidade (503)
                        is_recoverable = (
                            "503" in err_msg or
                            "429" in err_msg
                        )
                        if is_recoverable:
                            import time
                            wait_sec = 4 * (attempt + 1)
                            print(f"[EXPERT] Modelo {current_model} com limite de requisição. Aguardando {wait_sec}s...")
                            time.sleep(wait_sec)
                            continue

            # Se saiu de todos os loops e não conseguiu resposta
            if last_error:
                raise last_error
            else:
                raise RuntimeError("Falha desconhecida na consulta IA (Grounding Inacessível).")
            
            return {"error": "IA não retornou texto (Response.text vazio)."}
            
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            return {
                "error": f"Falha na consulta Expert: {str(e)}",
                "error_details": tb_str
            }

    def get_youtube_live_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Integração com YouTube Data API v3 para pegar o actualStartTime e actualEndTime precisos.
        v10.8: Adicionado Fallback via yt-dlp caso a API Key não tenha a cota de YouTube habilitada.
        """
        import requests
        import re
        import json
        import subprocess
        import sys

        out_meta = {}

        # 1. Tentativa via API Oficial (Mais rápido)
        try:
            url = f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails,contentDetails&id={video_id}&key={self.yt_api_key}"
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items")
                if items:
                    item = items[0]
                    live_dets = item.get("liveStreamingDetails") or {}
                    dur_iso = (item.get("contentDetails") or {}).get("duration")
                    actual_start = live_dets.get("actualStartTime")
                    scheduled = live_dets.get("scheduledStartTime")
                    
                    secs = None
                    if dur_iso:
                        m = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', dur_iso)
                        if m:
                            secs = int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)
                    
                    out_meta = {
                        "actual_start_time": actual_start or scheduled,
                        "duration": secs
                    }
        except Exception:
            pass

        # 2. Fallback via yt-dlp (Independente de API Key, busca direto no VOD/Live)
        if not out_meta.get("actual_start_time"):
            try:
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                    'skip_download': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    data = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    if data:
                        actual_start = data.get("actual_start_time")
                        # No yt-dlp, actual_start_time costuma vir em segundos (timestamp) ou string ISO
                        if actual_start:
                            if isinstance(actual_start, (int, float)):
                                from datetime import datetime, timezone
                                out_meta["actual_start_time"] = datetime.fromtimestamp(int(actual_start), tz=timezone.utc).isoformat()
                            else:
                                out_meta["actual_start_time"] = str(actual_start)
                        
                        if not out_meta.get("duration") and data.get("duration"):
                            out_meta["duration"] = int(data["duration"])
            except Exception:
                pass
                
        return out_meta

    def is_cbf_sumula_available(self, team1: str, team2: str, date: str, comp: str = "Brasileiro Serie A") -> bool:
        """
        Verifica se a súmula oficial (PDF ou HTML) da partida já está publicada no site da CBF.
        """
        print(f"[EXPERT SCHEDULER] Checando disponibilidade real no site da CBF para {team1} x {team2} ({date})...")
        try:
            from modules.cbf_schedule_fetcher import CBFScheduleFetcher
            import requests
            import re
            
            # 1. Busca direta ultrarrápida da página oficial do jogo na CBF
            game_url = CBFScheduleFetcher.find_game_page_url(team1, team2, date, comp)
            if game_url:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                for target_url in [game_url, game_url + "?view=documentos"]:
                    try:
                        resp = requests.get(target_url, headers=headers, verify=False, timeout=6)
                        if resp.status_code == 200:
                            pdf_matches = re.findall(r'https?://conteudo\.cbf\.com\.br/sumulas/\d{4}/[^\s"\'<>]+\.pdf', resp.text, re.IGNORECASE)
                            if pdf_matches:
                                print(f"[EXPERT SCHEDULER] ✅ Súmula em PDF confirmada no HTML da CBF: {pdf_matches[0]}")
                                return True
                    except Exception:
                        pass
                
                # Checar se há dados completos no HTML
                sumula_text = CBFScheduleFetcher.fetch_sumula_from_cbf_html(game_url)
                if sumula_text and len(sumula_text.strip()) > 100:
                    print(f"[EXPERT SCHEDULER] ✅ Súmula em HTML confirmada na CBF para {team1} x {team2}!")
                    return True

            # 2. Fallback: Busca via Gemini Grounding
            pdf_url = self.find_sumula_url_via_gemini(team1, team2, date, comp)
            if pdf_url and "sumulas" in pdf_url:
                print(f"[EXPERT SCHEDULER] ✅ Súmula em PDF confirmada via Gemini: {pdf_url}")
                return True

            print(f"[EXPERT SCHEDULER] Súmula oficial da CBF ainda NÃO publicada no site para {team1} x {team2}.")
            return False
        except Exception as e:
            print(f"[EXPERT SCHEDULER WARN] Erro ao checar súmula no site da CBF: {e}")
            return False

    def validate_chronology(self, team1: str, team2: str, date: str, competition: str, chronology_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza uma verificação independente via IA com Busca Ativa para validar se a cronologia gerada
        está completa e condizente com a súmula oficial da CBF e notícias minuto a minuto.
        Retorna {"is_valid": True} ou {"is_valid": False, "inconsistencies": "detalhes..."}
        """
        print(f"[EXPERT VALIDATOR] Iniciando verificação cruzada para {team1} x {team2} ({date})...")
        
        # prompt para o validador
        prompt = f"""
        Você é o Auditor Sênior de Integridade de Dados Esportivos (Validador Canônico V1.0).
        Sua tarefa é cruzar a cronologia de eventos de futebol gerada abaixo com a realidade oficial pesquisada na internet
        (súmula da CBF/Federação e coberturas minuto a minuto do Globo Esporte, UOL, Lance, Flashscore).
        
        Partida: {team1} x {team2}
        Competição: {competition}
        Data: {date}
        
        Cronologia gerada para validação:
        {json.dumps(chronology_json, indent=2, ensure_ascii=False)}
        
        INSTRUÇÕES DE VALIDAÇÃO CRÍTICAS E OBRIGATÓRIAS (FIDELIDADE ESTRITA À CBF):
        1. Faça uma busca ativa e minuciosa no Google pela súmula oficial da CBF/Federação e coberturas minuto-a-minuto da partida.
        2. EXIJA conformidade absoluta nos seguintes pontos (se houver divergência ou omissão, is_valid DEVE ser false):
           - PLACAR E GOLS: Compare a quantidade de gols no JSON com o placar final oficial. Todos os gols do placar devem estar listados em technical_milestones com autor e minuto exato da súmula. Se houver divergência, is_valid = false.
           - ACRESCIMOS (stoppage_time_1t e stoppage_time_2t): Compare com a súmula real. Se a súmula oficial indicar acréscimos (ex: +3' no 1T e +6' no 2T) e no JSON testado constar 0 (acréscimo zerado), ou se os acréscimos divergirem da súmula, marque como INVÁLIDO (is_valid = false). É proibido supor acréscimo zerado se a súmula tem acréscimos.
           - MARCOS DO JOGO (technical_milestones):
             - CARTÕES: Verifique e liste TODOS os cartões amarelos e vermelhos aplicados na partida (ex: Carlos Vinícius, Matheus Bahia, Alexandro Bernabei, Walter Kannemann). Se qualquer cartão da súmula oficial estiver ausente do JSON, marque como INVÁLIDO (is_valid = false).
             - SUBSTITUIÇÕES: Ambas as equipes devem ter suas substituições devidamente registradas. Se faltar qualquer substituição oficial no JSON, marque como INVÁLIDO (is_valid = false).
           - OS 4 TIMESTAMPS CANÔNICOS DA SÚMULA:
             - O JSON deve conter os horários oficiais exatos de início e término de cada tempo (first_half_start, half_time_start, second_half_start, match_end) conforme registrados no documento de súmula oficial da CBF. Se os horários divergirem da súmula oficial ou se o jogo foi cravado artificialmente em 90 minutos regulamentares teóricos ignorando os acréscimos reais da súmula, marque como INVÁLIDO (is_valid = false).
        3. O retorno DEVE ser um objeto JSON estrito com esta estrutura:
           {{
             "is_valid": true ou false,
             "official_score": "X x Y" (placar oficial pesquisado na internet, ex: "3x0" ou "2x1"),
             "inconsistencies": "Descreva com detalhes cirúrgicos tudo o que está errado, ausente ou divergente (ex: 'Falta cartão amarelo para Carlos Vinícius aos 41 e Matheus Bahia aos 42 do 1T; Acréscimos do 2T devem ser +6 em vez de +0, ajustando o fim do jogo para 22:06:58'). Se is_valid for true, deixe este campo vazio."
           }}
        
        Retorne APENAS o JSON estruturado acima. Sem texto explicativo.
        """
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=config
            )
            txt = response.text.strip()
            # Extrair JSON do bloco
            import re
            json_match = re.search(r'(\{.*\})', txt, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1).strip())
                # Garantir formato correto
                if "is_valid" in result:
                    result["is_valid"] = bool(result["is_valid"])
                    result.setdefault("inconsistencies", "")
                    result.setdefault("official_score", "")
                    return result
        except Exception as e:
            print(f"[EXPERT VALIDATOR WARN] Falha na validação do relatório: {e}")
            
        # Fallback se falhar (Não aprovar silenciosamente sem validar)
        return {"is_valid": False, "inconsistencies": "Erro técnico no validador. Por favor, pesquise na web pela súmula oficial e reinsira todos os gols, cartões e substituições reais da partida.", "official_score": ""}

    def find_sumula_url_via_gemini(self, team1: str, team2: str, date: str, competition: str) -> Optional[str]:
        """
        Localiza a URL do PDF da súmula oficial da CBF via:
        1. Raspagem ativa das tabelas da CBF e histórico de partidas dos times
        2. Google Search (Gemini Grounding) + extração da página de documentos
        """
        import re
        import requests
        import unicodedata
        import urllib3
        urllib3.disable_warnings()

        print(f"[EXPERT PDF FINDER] Buscando súmula oficial CBF para {team1} x {team2} em {date}...")

        # Extrair ano da data
        date_str = str(date).replace("-", "/")
        parts = date_str.split("/")
        year = parts[2] if len(parts) >= 3 and len(parts[2]) == 4 else parts[0]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        def _norm_clean(s):
            s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
            return re.sub(r"[^a-z0-9]+", "", s.lower())

        t1_key = _norm_clean(team1)[:4]
        t2_key = _norm_clean(team2)[:4]

        candidate_pages = set()

        # --- ETAPA 1: Raspagem direta das Tabelas e Histórico de Times da CBF ---
        table_urls = [
            f"https://www.cbf.com.br/futebol-brasileiro/tabelas/copa-do-brasil/masculino/{year}",
            f"https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/{year}",
            f"https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/{year}",
        ]

        for t_url in table_urls:
            try:
                r_tab = requests.get(t_url, headers=headers, verify=False, timeout=8)
                if r_tab.status_code == 200:
                    # 1a. Buscar links de jogos nas tabelas
                    g_links = re.findall(r'href=["\'](/futebol-brasileiro/jogos/[^"\']+)["\']', r_tab.text)
                    for gl in g_links:
                        gl_norm = _norm_clean(gl)
                        if t1_key in gl_norm and t2_key in gl_norm:
                            candidate_pages.add("https://www.cbf.com.br" + gl)

                    # 1b. Buscar links de times nas tabelas para varrer o histórico
                    team_links = re.findall(r'href=["\'](/futebol-brasileiro/times/[^"\']+)["\']', r_tab.text)
                    for tl in list(set(team_links)):
                        t_hist_url = "https://www.cbf.com.br" + tl
                        if "?tab=" not in t_hist_url:
                            t_hist_url += "?tab=historico-de-partidas"
                        try:
                            r_t = requests.get(t_hist_url, headers=headers, verify=False, timeout=6)
                            if r_t.status_code == 200:
                                t_games = re.findall(r'href=["\'](/futebol-brasileiro/jogos/[^"\']+)["\']', r_t.text)
                                for tg in t_games:
                                    tg_norm = _norm_clean(tg)
                                    if t1_key in tg_norm and t2_key in tg_norm:
                                        candidate_pages.add("https://www.cbf.com.br" + tg)
                        except Exception:
                            continue
            except Exception as e_tab:
                print(f"[EXPERT PDF FINDER WARN] Falha na raspagem de {t_url}: {e_tab}")

        # --- ETAPA 2: Google Search via Gemini Grounding ---
        prompt = f"""
Pesquise no Google Search pela Súmula Eletrônica Oficial da CBF da partida de futebol entre "{team1}" e "{team2}" realizada na data {date}.
Busque por links no site cbf.com.br ou conteudo.cbf.com.br.

Procure por:
1. Link direto do PDF da súmula em conteudo.cbf.com.br/sumulas/{year}/
2. Link da página da partida no portal da CBF (ex: cbf.com.br/futebol-brasileiro/jogos/.../{year}/...)

Retorne TODAS as URLs do site da CBF que você encontrar no resultado da busca.
"""
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=config
            )
            raw_text = str(response.text).strip()
            # 2a. Tentar extrair link direto de PDF da resposta do Gemini
            pdf_matches = re.findall(r'https://conteudo\.cbf\.com\.br/sumulas/\d{4}/[^\s"\'<>\)\],]+\.pdf', raw_text, re.IGNORECASE)
            if pdf_matches:
                print(f"[EXPERT PDF FINDER] PDF direto encontrado via resposta do Gemini: {pdf_matches[0]}")
                return pdf_matches[0]

            # 2b. Extrair das grounding_chunks se disponível
            if response.candidates and response.candidates[0].grounding_metadata:
                g_meta = response.candidates[0].grounding_metadata
                chunks = getattr(g_meta, "grounding_chunks", None) or []
                for chunk in chunks:
                    if hasattr(chunk, "web") and chunk.web and getattr(chunk.web, "uri", None):
                        uri = str(chunk.web.uri)
                        if "cbf.com.br" in uri.lower():
                            candidate_pages.add(uri)

            # 2c. Extrair URLs do texto
            urls_in_text = re.findall(r'https?://[^\s"\'<>\)\],]+', raw_text)
            for u in urls_in_text:
                if "cbf.com.br" in u.lower():
                    candidate_pages.add(u)
        except Exception as e_gem:
            print(f"[EXPERT PDF FINDER WARN] Gemini search erro: {e_gem}")

        # ETAPA 3: Testar todas as páginas candidatas e extrair o PDF de súmula
        target_d, target_m = None, None
        try:
            d_p = date.split("/")
            if len(d_p) >= 2:
                target_d = d_p[0].lstrip("0")
                target_m = d_p[1].lstrip("0")
        except Exception:
            pass

        for page_url in list(candidate_pages):
            # Se a página já é o PDF direto
            if "conteudo.cbf.com.br/sumulas" in page_url.lower() and page_url.lower().endswith(".pdf"):
                print(f"[EXPERT PDF FINDER] PDF direto encontrado: {page_url}")
                return page_url

            urls_to_fetch = [page_url]
            if "?view=documentos" not in page_url:
                urls_to_fetch.append(page_url + "?view=documentos")

            for target_url in urls_to_fetch:
                try:
                    r_game = requests.get(target_url, headers=headers, verify=False, timeout=8)
                    if r_game.status_code == 200:
                        # Verificar se o HTML da partida bate com a data solicitada
                        if target_d and target_m:
                            has_date = (
                                f"{target_d.zfill(2)}/{target_m.zfill(2)}" in r_game.text or
                                f"{target_d}/{target_m}" in r_game.text
                            )
                            if not has_date:
                                # Partida de outra rodada / data antiga
                                continue

                        base_page = page_url.split("?")[0]
                        self._last_game_page_url = base_page

                        pdfs = re.findall(r'https?://conteudo\.cbf\.com\.br/sumulas/\d{4}/[^\s"\'<>]+\.pdf', r_game.text, re.IGNORECASE)
                        if pdfs:
                            se_pdf = [p for p in pdfs if "se.pdf" in p.lower() or "su.pdf" in p.lower()]
                            final_pdf = se_pdf[0] if se_pdf else pdfs[0]
                            print(f"[EXPERT PDF FINDER] PDF de súmula capturado da página CBF ({target_url}): {final_pdf}")
                            return final_pdf
                except Exception:
                    continue

        print("[EXPERT PDF FINDER] Nenhuma súmula em PDF encontrada para a data solicitada.")
        return None





