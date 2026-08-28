import cv2
import time
import json
import numpy as np
import os
import sys

# Adiciona o diretório raiz ao path para encontrar os módulos
sys.path.append(os.getcwd())

from modules.cloud_expert import CloudExpert

def test_cloud_flow():
    # Parâmetros de hardware sincronizados com MonitorCore.py
    cam_idx = 5
    width = 1920
    height = 1080
    backend = cv2.CAP_DSHOW

    # 1. Carrega API Key
    config_path = r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json"
    if not os.path.exists(config_path):
        print(f"[ERRO] Arquivo de configuração não encontrado: {config_path}")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
        api_key = config.get("api_key")
        model_id = config.get("model", "gemini-flash-latest")

    if not api_key:
        print("[ERRO] api_key não encontrada no JSON.")
        return

    print(f"[IA] Inicializando CloudExpert com modelo: {model_id}")
    expert = CloudExpert(api_key, model_id=model_id)

    # 2. Conecta na Câmera (Seguindo a lógica do StreamAnalyzer)
    print(f"[STREAM] Abrindo câmera idx={cam_idx} backend=CAP_DSHOW requested={width}x{height}")
    cap = cv2.VideoCapture(cam_idx, backend)
    
    if not cap.isOpened():
        print(f"[ERRO] Falha ao abrir a câmera no índice {cam_idx}. Verifique se a OBS Virtual Camera está ligada.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    
    print("[COLETA] Iniciando captura de 4 frames (interv. 30s, total 2min)...")
    batch = []
    for i in range(4):
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"  -> Frame {i+1}/4 capturado às {time.strftime('%H:%M:%S')} (Res actual: {w}x{h})")
            batch.append(frame)
        if i < 3: # Não espera depois do último
            time.sleep(30.0)
    
    cap.release()

    if len(batch) < 4:
        print("[ERRO] Falha ao coletar os 4 frames necessários.")
        return

    # 3. Analisa com a IA
    print(f"[NUVEM] Enviando lote para {model_id}...")
    try:
        start_t = time.perf_counter()
        result = expert.analyze_batch(batch, "Teste rápido via script autônomo")
        duration = time.perf_counter() - start_t
        
        print(f"\n[SUCESSO] Resposta recebida em {duration:.2f}s:")
        print("====================================================")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("====================================================")
        
    except Exception as e:
        print(f"\n[FALHA] Erro na comunicação com a IA: {e}")

if __name__ == "__main__":
    test_cloud_flow()
