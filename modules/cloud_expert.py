from google import genai
from google.genai import types
import json
import base64
import os
import cv2
import numpy as np
import time
from typing import List, Optional

class CloudExpert:
    """
    Serviço de análise visual em nuvem usando o SDK google-genai.
    Suporta análise de frames individuais ou em LOTE (Batching) para maior contexto.
    """
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("API Key do Gemini é obrigatória.")
        # Configura httpx para ignorar verificação de certificado SSL se necessário (casos de proxy/corporativo)
        http_options = types.HttpOptions(client_args={"verify": False})
        self.client = genai.Client(api_key=api_key, http_options=http_options)
        self.model_id = model_id
        self._last_call_t = 0
        self._min_gap_s = 6.0  # Safe rate limit for free tier

    def analyze_batch(self, frames: List[np.ndarray], info_text: str = "") -> dict:
        """
        Envia uma sequência de frames para análise cronológica.
        """
        now = time.time()
        if (now - self._last_call_t) < self._min_gap_s:
             # Pequena espera forçada para evitar 429 excessivo
             time.sleep(self._min_gap_s - (now - self._last_call_t))
        
        self._last_call_t = time.time()

        parts = []
        if info_text:
            parts.append(f"Contexto Adicional: {info_text}\n")
        
        parts.append("Analise esta sequência de frames de uma transmissão esportiva (ordenados no tempo).")

        for i, frame in enumerate(frames):
            # Redimensionar para economizar tokens e banda (640p é suficiente para contexto)
            h, w = frame.shape[:2]
            if h > 480:
                scale = 480 / h
                frame = cv2.resize(frame, (int(w * scale), 480), interpolation=cv2.INTER_AREA)
            
            success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if success:
                parts.append(types.Part.from_bytes(data=buffer.tobytes(), mime_type='image/jpeg'))

        prompt = """
        Determine the current state of the match based on this sequence.
        Return ONLY a JSON object:
        {
          "current_phase": "pre_game" | "first_half" | "half_time" | "second_half" | "post_game" | "unknown",
          "current_score": "e.g. 2x1 or null",
          "current_clock": "e.g. 35:10 or null",
          "is_replay_now": boolean (is the LAST frame a replay?),
          "banners": {
             "active": boolean,
             "headline": "text or null",
             "subheadline": "text or null"
          },
          "summary": "short description of what happened in this batch",
          "events_detected": ["GOAL", "CARD", "etc"],
          "hud_calibration": {
             "visible": boolean,
             "bbox_score_normalized": [ymin, xmin, ymax, xmax] (0-1000)
          }
        }
        Be extremely accurate. If the sequence shows a transition (e.g. goal scored), reflect it in the summary.
        IMPORTANT: Use PORTUGUESE for the 'summary' field.
        """
        parts.append(prompt)

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            if not response.text:
                return {"error": "IA retornou resposta vazia."}
            
            text = response.text.strip()
            
            def _robust_json_cleaner(raw: str) -> dict:
                import re
                # 1. Remover markdown wrappers
                if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw: raw = raw.split("```")[1].split("```")[0].strip()
                
                # 2. Encontrar o objeto principal
                s = raw.find('{')
                e = raw.rfind('}')
                if s == -1 or e == -1: 
                    if not raw: return {}
                    # Se houver texto mas sem chaves, pode ser uma recusa
                    return {"error": f"IA não retornou JSON. Resposta: {raw[:100]}..."}
                
                raw = raw[s:e+1]
                
                # 3. Limpeza de caracteres de controle ilegais
                raw = re.sub(r'[\x00-\x1F]+', ' ', raw)
                
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as err:
                    # Se falhar, mostramos o erro com o início do texto
                    raise ValueError(f"JSON Syntax Error (IA): {str(err)} | Texto: {raw[:100]}")

            return _robust_json_cleaner(text)
        except Exception as e:
            raise RuntimeError(f"Falha na consulta Expert: {e}")

if __name__ == "__main__":
    # Teste rápido de lote
    print("Testando CloudExpert Batch (Gemini 2.0)...")
    import sys
    from pathlib import Path
    if getattr(sys, "frozen", False):
        proj_root = Path(sys.executable).parent
    else:
        proj_root = Path(__file__).resolve().parents[1]
    config_path = os.path.join(proj_root, "config", "google_ai.json")
    with open(config_path, "r") as f:
        key = json.load(f)["api_key"]
    
    expert = CloudExpert(key)
    # Criar 3 frames fake
    batch = [np.zeros((480, 854, 3), dtype=np.uint8) for _ in range(3)]
    try:
        res = expert.analyze_batch(batch, "Teste de bateria de frames vazios")
        print("Resultado Batch:", json.dumps(res, indent=2))
    except Exception as e:
        print(f"Erro: {e}")
