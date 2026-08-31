# modules/youtube_transcript_service.py
import re
from typing import List, Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeTranscriptService:
    """
    Serviço robusto para extração de legendas/transcrições do YouTube sem uso de quota da API oficial.
    """
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extrai o ID de 11 caracteres de qualquer URL válida do YouTube.
        """
        if not url:
            return None
        
        # Regex padrão para cobrir youtu.be, youtube.com/watch, youtube.com/embed, etc.
        patterns = [
            r"(?:v=|/)([0-9A-Za-z_-]{11})",
            r"youtu\.be/([0-9A-Za-z_-]{11})",
            r"embed/([0-9A-Za-z_-]{11})",
            r"shorts/([0-9A-Za-z_-]{11})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @classmethod
    def get_transcript(cls, video_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Puxa a transcrição do vídeo, tentando português e caindo para inglês se necessário.
        """
        video_id = cls.extract_video_id(video_url)
        if not video_id:
            print("[TRANSCRIPT] URL de vídeo inválida ou ID não encontrado.")
            return None

        try:
            # Instancia o serviço da API
            api = YouTubeTranscriptApi()
            
            # Lista todas as transcrições disponíveis para o vídeo
            transcript_list = api.list(video_id)
            
            # Prioridade de idiomas:
            # 1. Português criado manualmente (pt, pt-BR)
            # 2. Português auto-gerado
            # 3. Inglês criado manualmente (en, en-US)
            # 4. Inglês auto-gerado
            # 5. Qualquer outra transcrição traduzida para português se possível
            
            best_transcript = None
            try:
                best_transcript = transcript_list.find_manually_created_transcript(['pt', 'pt-BR'])
            except:
                try:
                    best_transcript = transcript_list.find_generated_transcript(['pt', 'pt-BR'])
                except:
                    try:
                        best_transcript = transcript_list.find_manually_created_transcript(['en', 'en-US'])
                    except:
                        try:
                            best_transcript = transcript_list.find_generated_transcript(['en', 'en-US'])
                        except:
                            # Tenta traduzir a primeira transcrição disponível para português
                            for t in transcript_list:
                                if t.is_translatable:
                                    best_transcript = t.translate('pt')
                                    break
            
            if not best_transcript:
                # Tenta puxar de forma genérica
                return api.fetch(video_id, languages=['pt', 'pt-BR', 'en'])

            print(f"[TRANSCRIPT] Baixando legenda no idioma: {best_transcript.language_code} (Gerada: {best_transcript.is_generated})")
            return best_transcript.fetch()

        except Exception as e:
            print(f"[TRANSCRIPT] Erro ao baixar legenda para o vídeo {video_id}: {e}")
            return None

    @classmethod
    def get_compacted_text(cls, video_url: str, chunk_size_seconds: int = 15) -> Optional[str]:
        """
        Gera uma versão compactada do texto da narração agrupada por janelas temporais.
        Isso reduz drasticamente a quantidade de tokens enviados ao Gemini, mantendo o contexto temporal.
        
        Exemplo de saída compactada:
        [00:00 - 00:15]: olha o cruzamento na area chuta pra fora
        [00:15 - 00:30]: germán cano chuta e é gol do fluminense
        """
        transcript = cls.get_transcript(video_url)
        if not transcript:
            return None

        chunks = {}
        for entry in transcript:
            try:
                if hasattr(entry, 'start'):
                    start_time = float(entry.start)
                    text = str(entry.text).strip().replace('\n', ' ')
                elif isinstance(entry, dict):
                    start_time = float(entry.get('start', 0))
                    text = str(entry.get('text', '')).strip().replace('\n', ' ')
                else:
                    start_time = float(entry['start'])
                    text = str(entry['text']).strip().replace('\n', ' ')
            except Exception:
                continue
            
            # Determina qual fatia de tempo este trecho pertence
            chunk_idx = int(start_time // chunk_size_seconds)
            if chunk_idx not in chunks:
                chunks[chunk_idx] = []
            chunks[chunk_idx].append(text)

        lines = []
        # Ordenar os chunks no tempo
        for idx in sorted(chunks.keys()):
            t_start = idx * chunk_size_seconds
            t_end = t_start + chunk_size_seconds
            
            # Formata em MM:SS para fácil leitura pela IA
            def fmt_time(seconds):
                m = int(seconds // 60)
                s = int(seconds % 60)
                return f"{m:02d}:{s:02d}"

            chunk_text = " ".join(chunks[idx])
            lines.append(f"[{fmt_time(t_start)} - {fmt_time(t_end)}]: {chunk_text}")

        return "\n".join(lines)
