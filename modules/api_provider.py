from flask import Flask, jsonify, Response, request, send_from_directory
from flask_cors import CORS
import threading
import logging
import cv2
import numpy as np
import time
import os
import json
from typing import Dict, Any, List

from modules.youtube_events import get_channel_events
from modules.youtube_api_v3 import get_official_events

# Desativa logs poluentes do Flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

_monitor_app = None
_last_expert_results = None
_last_ad_results = None

# --- API Endpoints ---

@app.route('/api/status', methods=['GET'])
def get_status():
    global _monitor_app
    if not _monitor_app:
        return jsonify({"status": "inactive", "error": "App não vinculado"}), 200
    
    app_inst = _monitor_app
    
    detector_data = {
        "phase": "IDLE",
        "confirmed_score": "0x0",
        "clock": "--:--",
        "is_live": False
    }

    try:
        if hasattr(app_inst, 'detector') and app_inst.detector:
            st = getattr(app_inst.detector, '_state', None)
            if st:
                detector_data = {
                    "phase": str(getattr(st, 'phase', 'ocioso')),
                    "confirmed_score": str(getattr(st, 'confirmed_score', '0x0')),
                    "clock": str(getattr(st, 'last_clock_text', '--:--')),
                    "is_live": bool(getattr(st, 'is_live', False)),
                    "visual_confidence": float(getattr(app_inst.runtime, 'last_visual_confidence', 0.0)),
                    "detector_stage": str(getattr(app_inst.detector_stage_var, 'get', lambda: 'Ocioso')()),
                    "frames_seen": int(getattr(app_inst.runtime, 'frames_seen', 0)),
                    "current_match": str(getattr(app_inst.runtime, 'current_match_display', '—')),
                    "current_competition": str(getattr(app_inst.runtime, 'current_competition', '—')),
                    "banner_text": str(getattr(st, 'last_banner_text', '—'))
                }
    except Exception as e:
        print(f"[API ERROR] Detector state: {e}")

    ia_stats = {"last_analysis_t": 0, "next_analysis_countdown": 0, "analysis_active": False}
    ia_logs = []
    try:
        ia_logs = getattr(app_inst, '_ia_logs', [])[-40:] 
        st = getattr(app_inst.detector, '_state', None)
        if st:
            ia_stats = {
                "last_analysis_t": float(getattr(st, "last_cloud_analysis_t", 0)),
                "next_analysis_countdown": int(max(0, getattr(st, "_cloud_countdown", 0))),
                "analysis_active": bool(getattr(st, "_cloud_busy", False)),
                "ia_status": str(getattr(st, "_ia_status_msg", "Aguardando gatilho...")),
                "last_analysis_raw": str(getattr(st, "_last_cloud_raw_response", "Nenhuma análise realizada ainda."))
            }
    except Exception:
        pass

    events = []
    try:
        if hasattr(app_inst.detector, 'event_history'):
            events = app_inst.detector.event_history
        elif hasattr(app_inst, '_events'):
            events = app_inst._events
    except Exception: pass

    perf = {
        "fps": getattr(app_inst.runtime, 'detector_fps', 0.0) if hasattr(app_inst, 'runtime') else 0.0,
        "latency_ms": getattr(app_inst.runtime, 'detector_latency_ms', 0.0) if hasattr(app_inst, 'runtime') else 0.0
    }

    return jsonify({
        "status": "active" if getattr(app_inst, 'isRunning', False) or getattr(app_inst.runtime, 'is_running', False) else "idle",
        "detector": detector_data,
        "events": events,
        "ia_stats": ia_stats,
        "ia_logs": ia_logs,
        "perf": perf,
        "current_url": str(getattr(app_inst.channel_url_var, 'get', lambda: '')()),
        "settings": {
            "cloud_enabled": bool(getattr(app_inst.cloud_enabled_var, 'get', lambda: False)()),
            "cloud_interval": int(getattr(app_inst.cloud_interval_var, 'get', lambda: 5)()),
            "banner_ocr_interval": float(getattr(app_inst.banner_ocr_interval_var, 'get', lambda: 1.2)()),
            "email_enabled": bool(getattr(app_inst.send_report_email_var, 'get', lambda: False)()),
            "recipients": str(getattr(app_inst.email_recipients_var, 'get', lambda: '')()),
            "cleanup_days": int(getattr(app_inst.cleanup_days_var, 'get', lambda: 7)())
        }
    })

@app.route('/api/command', methods=['POST'])
def send_command():
    global _monitor_app
    if not _monitor_app: return jsonify({"status": "error"}), 400
    
    data = request.json
    cmd = data.get('command')
    params = data.get('params', {})
    
    print(f"[API] Comando recebido: {cmd} | Params: {params}")
    
    if cmd == 'start':
        url = params.get('url')
        if url: _monitor_app.channel_url_var.set(url)
        _monitor_app._on_start_stop()
    elif cmd == 'stop':
        _monitor_app._on_start_stop()
    elif cmd == 'cleanup':
        days = params.get('days', 7)
        _monitor_app.cleanup_days_var.set(days)
        _monitor_app._run_cleanup_now()
    elif cmd == 'start_ads':
        files = params.get('files', [])
        _monitor_app._run_ad_analysis(files)
    elif cmd == 'expert_batch':
        events = params.get('events', [])
        _monitor_app._run_expert_batch_analysis(events)
    elif cmd == 'export_expert_pdf':
        _monitor_app._log("[API] Exportando PDF Expert...")
        _monitor_app._generate_report(finalize=False, reason='manual_export_expert')
    elif cmd == 'export_monitor_pdf':
        _monitor_app._log("[API] Exportando PDF Monitoramento...")
        _monitor_app._generate_report(finalize=False, reason='manual_export_monitor')
        
    return jsonify({"status": "ok"})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    global _monitor_app
    if not _monitor_app: return jsonify({"status": "error"}), 400
    data = request.json
    if 'cloud_enabled' in data: _monitor_app.cloud_enabled_var.set(data['cloud_enabled'])
    if 'cloud_interval' in data: _monitor_app.cloud_interval_var.set(data['cloud_interval'])
    if 'banner_ocr_interval' in data: _monitor_app.banner_ocr_interval_var.set(data['banner_ocr_interval'])
    return jsonify({"status": "ok"})

@app.route('/api/scan_youtube', methods=['POST'])
def scan_youtube():
    data = request.json
    url = data.get('url')
    date_after = data.get('date_after')
    date_before = data.get('date_before')
    
    if not url: return jsonify({"status": "error"}), 400
    events = get_channel_events(url, date_after=date_after, date_before=date_before)
    return jsonify({"status": "ok", "events": events})

@app.route('/api/browse_files', methods=['POST'])
def browse_files():
    # Em modo headless, podemos usar um dialog se rodando local, ou apenas listar uma pasta
    # Por agora, vamos simular ou retornar lista de data/temp se existir
    import tkinter.filedialog as fd
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    files = fd.askopenfilenames(title="Selecionar Vídeos para Análise de Ads", filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
    root.destroy()
    return jsonify({"status": "ok", "files": list(files)})

@app.route('/api/system_logs', methods=['GET'])
def get_system_logs():
    # Retorna as últimas linhas do log do console se capturado, ou apenas info
    return jsonify({"logs": ["Sistema operacional", "Aguardando eventos..."]})

@app.route('/api/system_errors', methods=['GET'])
def get_system_errors():
    return jsonify({"errors": []})

@app.route('/api/frame')
def get_frame():
    global _monitor_app
    if not _monitor_app or not hasattr(_monitor_app, '_latest_raw_frame'):
        return Response(status=404)
    
    frame = _monitor_app._latest_raw_frame
    if frame is None: return Response(status=404)
    
    _, buffer = cv2.imencode('.jpg', frame)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/api/roi/<type>')
def get_roi(type):
    global _monitor_app
    if not _monitor_app: return Response(status=404)
    
    st = getattr(_monitor_app.detector, '_state', None)
    if not st: return Response(status=404)
    
    img = None
    if type == 'score': img = getattr(st, 'last_score_crop', None)
    elif type == 'clock': img = getattr(st, 'last_clock_crop', None)
    elif type == 'banner': img = getattr(st, 'last_banner_crop', None)
    
    if img is None: return Response(status=404)
    _, buffer = cv2.imencode('.jpg', img)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/api/expert_batch', methods=['POST'])
def expert_batch():
    global _monitor_app, _last_expert_results
    data = request.json
    events = data.get('events', [])
    _monitor_app._run_expert_batch_analysis(events)
    return jsonify({"status": "ok"})

@app.route('/api/expert_manual', methods=['POST'])
def expert_manual():
    global _monitor_app, _last_expert_results
    data = request.json
    _monitor_app._run_expert_analysis(data)
    return jsonify({"status": "ok"})

@app.route('/api/expert_results', methods=['GET'])
def get_expert_results():
    global _last_expert_results
    # Precisamos capturar os resultados do HeadlessApp. 
    # Vou modificar o HeadlessApp para guardar isso.
    res = getattr(_monitor_app, '_last_expert_results', [])
    return jsonify({"results": res})

@app.route('/api/export_ad_pdf', methods=['POST'])
def export_ad_pdf():
    global _monitor_app
    # O HeadlessApp já gera o PDF ao final da análise de Ads. 
    # Mas podemos forçar ou retornar o último.
    return jsonify({"status": "ok", "msg": "PDF gerado automaticamente na pasta data/reports"})

@app.route('/api/export_monitor_pdf', methods=['POST'])
def export_monitor_pdf():
    global _monitor_app
    if not _monitor_app: return jsonify({"status": "error"}), 400
    
    try:
        # Pega dados atuais do monitor para gerar um PDF parcial/final
        event_meta = {
            "title": _monitor_app.channel_var.get(),
            "channel": _monitor_app.channel_var.get(),
            "match_display": _monitor_app.match_var.get(),
            "competition": _monitor_app.comp_var.get()
        }
        timeline = getattr(_monitor_app.detector, 'event_history', [])
        notes = {
            "current_score": _monitor_app.runtime.last_score_text,
            "current_clock": _monitor_app.runtime.last_clock_text,
            "report_kind": "manual_export"
        }
        paths = _monitor_app.reporter.write_live_report(event_meta, timeline, notes, generate_pdf=True)
        return jsonify({"status": "ok", "pdf": os.path.basename(paths.pdf_path)})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/api/reports/list', methods=['GET'])
def list_reports():
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
    if not os.path.exists(reports_dir): return jsonify({"reports": []})
    
    files = []
    for f in os.listdir(reports_dir):
        if f.endswith('.pdf') or f.endswith('.json'):
            p = os.path.join(reports_dir, f)
            files.append({
                "name": f,
                "size": os.path.getsize(p),
                "date": os.path.getmtime(p),
                "type": "pdf" if f.endswith('.pdf') else "json"
            })
    # Ordena por data (mais recentes primeiro)
    files.sort(key=lambda x: x['date'], reverse=True)
    return jsonify({"reports": files})

@app.route('/api/reports/download/<filename>')
def download_report(filename):
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
    return send_from_directory(reports_dir, filename, as_attachment=True)

def _start_flask(inst, port):
    global _monitor_app
    _monitor_app = inst
    current_port = port
    for attempt in range(5):
        try:
            print(f"\n==================================================\n  API MDNA INICIADA: http://127.0.0.1:{current_port}\n==================================================\n")
            app.run(host='0.0.0.0', port=current_port, debug=False, use_reloader=False)
            break
        except (OSError, SystemExit):
            current_port += 1
        except Exception: break

def start_api_thread(app_instance, port=5000):
    t = threading.Thread(target=_start_flask, args=(app_instance, port), daemon=True)
    t.start()
    return t

# --- Frontend Routing (Deve ficar por ultimo) ---
FRONTEND_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "monitor-frontend", "dist"))

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    # Ignora rotas que comecam com api/
    if path.startswith("api/"):
        return jsonify({"error": "Not Found"}), 404

    full_path = os.path.join(FRONTEND_PATH, path)
    if path != "" and os.path.exists(full_path):
        return send_from_directory(FRONTEND_PATH, path)
    else:
        index_html = os.path.join(FRONTEND_PATH, "index.html")
        if not os.path.exists(index_html):
            return f"[ERRO] Frontend 'dist' nao encontrado em: {FRONTEND_PATH}. Execute 'npm run build' primeiro.", 404
        return send_from_directory(FRONTEND_PATH, "index.html")
