from google import genai
from google.genai import types
import json
import os
import time
import threading
from typing import List, Dict, Any, Callable, Optional

class AdAnalyzer:
    """
    Analisa arquivos de vídeo (.mp4) para detectar comerciais, anúncios e merchandising
    usando o modelo Gemini.
    """
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("API Key do Gemini é obrigatória para AdAnalyzer.")
        # Configuração de httpx otimizada para redes corporativas e proxies:
        # 1. verify=False (ignora erro de certificado SSL autoassinado)
        # 2. http2=False (força HTTP/1.1 pra evitar que proxies corporativos cortem streams HTTP/2)
        # 3. max_keepalive_connections=0 (desativa pooling de conexões persistentes que proxies derrubam)
        # 4. timeout=300.0s (tempo maior para uploads de vídeos no Gemini)
        import httpx
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=10)
        timeout = httpx.Timeout(300.0, connect=30.0)
        self.http_options = types.HttpOptions(
            client_args={
                "verify": False,
                "timeout": timeout,
                "http2": False,
                "limits": limits
            }
        )
        self.api_keys = [k.strip() for k in api_key.split(",") if k.strip()]
        self.exhausted_keys = set()
        self.current_key_idx = 0
        self.model_id = model_id
        self._init_client()

    def _init_client(self):
        healthy_indices = [i for i, k in enumerate(self.api_keys) if k not in self.exhausted_keys]
        if healthy_indices:
            if self.current_key_idx not in healthy_indices:
                self.current_key_idx = healthy_indices[0]
        else:
            print("[ADS WARN] Todas as chaves foram marcadas como esgotadas. Reiniciando ciclo de chaves...")
            self.exhausted_keys.clear()
            self.current_key_idx = 0

        key = self.api_keys[self.current_key_idx]
        self.client = genai.Client(api_key=key, http_options=self.http_options)
        print(f"[ADS] Cliente do SDK inicializado com a chave índice {self.current_key_idx} (final: ...{key[-6:]})")

    def rotate_key(self, mark_exhausted: bool = True) -> bool:
        if len(self.api_keys) <= 1:
            return False
        if mark_exhausted:
            bad_key = self.api_keys[self.current_key_idx]
            self.exhausted_keys.add(bad_key)
            print(f"[ADS WARN] Chave índice {self.current_key_idx} (final ...{bad_key[-6:]}) marcada como ESGOTADA (429/cota).")
        
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        self._init_client()
        return True

    def get_video_duration(self, path: str) -> float:
        import subprocess
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', path
            ]
            res = subprocess.check_output(cmd).decode('utf-8').strip()
            return float(res)
        except Exception:
            return 0.0

    def _split_video(self, input_path: str, start_sec: int, duration_sec: int, output_path: str) -> bool:
        import subprocess
        try:
            # -ss antes do -i para busca rápida, -t para duração, -c copy para não reencodar
            cmd = [
                'ffmpeg', '-y', '-ss', str(start_sec), '-i', input_path,
                '-t', str(duration_sec), '-c', 'copy', output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception:
            return False

    def analyze_video(self, video_path: str, progress_callback: Optional[Callable[[str], None]] = None, extra_offset_sec: int = 0, result_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None, stop_flag: Optional[threading.Event] = None) -> List[Dict[str, Any]]:
        """
        Analisa o vídeo completo dividindo em partes de 10 minutos para máxima confiabilidade.
        Possui suporte a offset extra para processamento em lote (Batch) e callback de resultados em tempo real.
        """
        import os, json, time, tempfile

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

        total_duration = self.get_video_duration(video_path)
        chunk_size = 600 # Reduzido para 10 min para garantir estabilidade
        all_results = []

        if total_duration <= 0:
            if progress_callback: progress_callback("Erro: Duração do vídeo não detectada.")
            return []

        # Se for até 11 min, analisa direto sem fatiar
        if total_duration <= 660:
            res = self._analyze_chunk(video_path, extra_offset_sec, progress_callback)
            if result_callback: result_callback(res)
            return res

        num_chunks = int((total_duration + chunk_size - 1) // chunk_size)
        if progress_callback:
            progress_callback(f"Análise profunda ({int(total_duration//60)}min). Processando em {num_chunks} blocos de 10min...")

        for i in range(num_chunks):
            if stop_flag and stop_flag.is_set():
                if progress_callback: progress_callback("Análise interrompida pelo usuário.")
                break

            start_sec = i * chunk_size
            if start_sec >= total_duration: break
            
            # Calcular duração real deste bloco
            current_chunk_duration = min(chunk_size, int(total_duration - start_sec))
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                if progress_callback:
                    progress_callback(f"Processando bloco {i+1}/{num_chunks} ({start_sec//60}min até {(start_sec+current_chunk_duration)//60}min)...")
                
                # Fatiamento cirúrgico
                if self._split_video(video_path, start_sec, current_chunk_duration, tmp_path):
                    chunk_results = self._analyze_chunk(tmp_path, start_sec + extra_offset_sec, progress_callback)
                    all_results.extend(chunk_results)
                    if result_callback:
                        result_callback(chunk_results)
                    if progress_callback:
                        progress_callback(f"Bloco {i+1} finalizado. {len(chunk_results)} ads encontrados.")
                else:
                    if progress_callback: progress_callback(f"Erro técnico ao fatiar bloco {i+1}")
            finally:
                if os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except: pass

        return all_results

    def _analyze_chunk(self, chunk_path: str, offset_sec: int, progress_callback: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
        """Lógica interna de análise de um arquivo (original ou fatia)."""
        import time, json
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            uploaded_file = None
            try:
                if progress_callback:
                    progress_callback(f"Fazendo upload do bloco para o Gemini (Tentativa {attempt+1}/{max_retries})...")

                uploaded_file = self.client.files.upload(file=chunk_path)

                # Polling
                while True:
                    time.sleep(3)
                    uploaded_file = self.client.files.get(name=uploaded_file.name)
                    state = getattr(uploaded_file, 'state', None)
                    state_name = getattr(state, 'name', str(state)) if state else "UNKNOWN"
                    
                    if state_name == "ACTIVE" or state_name == "SUCCEEDED":
                        break
                    if state_name == "FAILED":
                        raise RuntimeError("Falha no processamento do vídeo pelo Gemini.")
                    if state_name != "PROCESSING":
                        # Alguns modelos usando states diferentes dependendo da versão
                        break

                prompt = """
                Sua missão é realizar uma auditoria COMERCIAL E DE MERCHANDISING. 
                Você deve ser EXTREMAMENTE RÍGIDO. Na dúvida, NÃO detecte.
                
                ⚠️ REGRAS DE EXCLUSÃO ABSOLUTA (NÃO DETECTAR DE JEITO NENHUM):
                - JORNALISMO/NOTÍCIAS: Ignore notícias sobre política, tribunais (TSE, TRE), meteorologia, crimes ou economia.
                - BRANDING DA CASA: Ignore logos da Globo, GloboNews, G1, hashtags de programas (#SP1, #JN) ou IDs de canal.
                - BANNERS INFORMATIVOS: Ignore o header/footer técnico da transmissão (Ex: SP1 - GLO(DT) - Data/Hora).
                - CONTEÚDOS SEM MARCA EXTERNA: Se não houver uma marca comercial clara (ex: Samsung, Shell, Betano, Coca-Cola), IGNORE.
                - PERSONAGENS/ATORES: Entrevistas com atores ou famosos sobre carreira NÃO são Merchan, a menos que promovam explicitamente um produto pago.
                
                ✅ O QUE DETECTAR (SOMENTE MARCAS COMERCIAIS EXTERNAS):
                - COMERCIAIS DE TV: Intervalos comerciais clássicos de marcas externas.
                - MERCHANDISING: O apresentador segurando um produto ou falando explicitamente de uma marca paga.
                - BANNERS COMERCIAIS: Placas de publicidade de campo (LED ou Estáticas) de marcas externas claras.
                - PATROCÍNIO: Vinhetas de "Oferecimento" de marcas externas.
                
                ⚠️ CONFIANÇA: Só retorne o item se você tiver mais de 70% de certeza que é publicidade paga.
                
                Campos JSON:
                - "inicio": "MM:SS", "fim": "MM:SS", "timestamp": "MM:SS"
                - "tipo": "Comercial | Merchan | Banner | Patrocínio"
                - "marca": "Nome da MARCA EXTERNA (ex: Samsung, Shell, Betano)"
                - "metodo": "Visual | Auditivo | Híbrido"
                - "posicao": "Local na tela"
                - "descricao": "Breve descrição foca no PRODUTO/MARCA"
                - "confianca": 0.0 a 1.0 (Retorne apenas itens > 0.70)

                Responda APENAS o array JSON:
                """

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )

                text = response.text.strip()
                
                # Limpeza defensiva de JSON
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                def _smart_json_repair(raw_text: str) -> List[Dict[str, Any]]:
                    # 1. Tenta direto
                    try: return json.loads(raw_text)
                    except: pass

                    # 2. Se falhar, tenta encontrar o último objeto completo '}' antes do fim
                    import re
                    try:
                        matches = list(re.finditer(r'\}\s*,?\s*$', raw_text))
                        if not matches:
                            matches = list(re.finditer(r'\}', raw_text))
                        
                        if matches:
                            last_valid_pos = matches[-1].end()
                            repaired = raw_text[:last_valid_pos].strip()
                            if repaired.endswith(','):
                                repaired = repaired[:-1]
                            if not repaired.endswith(']'):
                                repaired += ']'
                            return json.loads(repaired)
                    except:
                        pass
                    
                    if raw_text.startswith('[') and not raw_text.endswith(']'):
                        try: return json.loads(raw_text + ']')
                        except: pass
                    
                    return []

                data = _smart_json_repair(text)
                
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except: pass

                if not isinstance(data, list):
                    return []

                # Função auxiliar para ajustar tempo com offset
                def adjust_ts(ts_str, offset):
                    if not ts_str: return ts_str
                    try:
                        parts = ts_str.split(':')
                        if len(parts) == 2:
                            m, s = map(int, parts)
                            total_s = m * 60 + s + offset
                            return f"{total_s // 60:02d}:{total_s % 60:02d}"
                        elif len(parts) == 3:
                            h, m, s = map(int, parts)
                            total_s = h * 3600 + m * 60 + s + offset
                            return f"{total_s // 3600:02d}:{(total_s % 3600) // 60:02d}:{total_s % 60:02d}"
                    except: pass
                    return ts_str

                # Ajustar timestamps e filtrar por confiança
                filtered_data = []
                for item in data:
                    conf = 0.0
                    try: conf = float(item.get("confianca", 0))
                    except: pass
                    
                    if conf >= 0.5: # Hard limit para evitar ruído extremo
                        # Ajustar tempos se houver offset
                        if offset_sec > 0:
                            item["timestamp"] = adjust_ts(item.get("timestamp"), offset_sec)
                            item["inicio"] = adjust_ts(item.get("inicio"), offset_sec)
                            item["fim"] = adjust_ts(item.get("fim"), offset_sec)
                        filtered_data.append(item)

                return filtered_data

            except Exception as e:
                last_error = e
                err_msg = str(e)
                print(f"[ADS WARN] Falha na tentativa {attempt+1} de análise do bloco: {err_msg}")
                
                # Excluir arquivo temporário do Gemini se foi criado antes da falha
                if uploaded_file:
                    try: self.client.files.delete(name=uploaded_file.name)
                    except: pass
                
                # Se for erro de quota/spend cap, rotaciona a chave de API
                if "429" in err_msg or "spend cap" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower():
                    if self.rotate_key():
                        print("[ADS] Rotação de chave ativada devido a limite/quota na aba Ads. Nova chave carregada.")
                        continue
                
                # Para erros recuperáveis de conexão ou 503, espera e tenta de novo
                is_recoverable = (
                    "503" in err_msg or
                    "429" in err_msg or
                    "server disconnected" in err_msg.lower() or
                    "disconnected without sending" in err_msg.lower() or
                    "connection reset" in err_msg.lower() or
                    "remote end closed" in err_msg.lower() or
                    "timed out" in err_msg.lower() or
                    "timeout" in err_msg.lower()
                )
                if is_recoverable:
                    time.sleep(10 * (attempt + 1))
                    continue
                else:
                    raise e
        
        if last_error:
            raise last_error
