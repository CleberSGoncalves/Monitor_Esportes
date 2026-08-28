import React, { useState, useEffect } from 'react';
import { 
  Monitor, 
  Cpu, 
  Layers, 
  FileText, 
  Terminal, 
  Settings, 
  Shield, 
  RefreshCcw,
  CheckCircle2,
  Trophy,
  History,
  Youtube,
  Play,
  Square,
  Download,
  AlertTriangle,
  Clock,
  Activity,
  Check
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('mesa');
  const [data, setData] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [ytUrl, setYtUrl] = useState('https://www.youtube.com/@CazeTV/streams');
  const [scannedEvents, setScannedEvents] = useState<any[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [isExpertProcessing, setIsExpertProcessing] = useState(false);
  const [batchSelection, setBatchSelection] = useState<Set<string>>(new Set());
  const [reports, setReports] = useState<any[]>([]);
  const [expertResults, setExpertResults] = useState<any[]>([]);
  const [tick, setTick] = useState(0);
  const [expertFilter, setExpertFilter] = useState('todos'); // todos, live, ended, upcoming

  const fetchData = async () => {
    try {
      const resp = await fetch('http://127.0.0.1:5000/api/status');
      const res = await resp.json();
      setData(res);
      if (res.status === 'active') setIsRunning(true);
      // Sincroniza o estado de processamento com o backend
      if (res.ia_stats?.analysis_active) {
        setIsExpertProcessing(true);
      } else if (isExpertProcessing && !res.ia_stats?.analysis_active) {
        // Se estava processando e o backend parou, atualiza resultados e fecha overlay
        setIsExpertProcessing(false);
        fetchExpertResults();
      }
      setTick(t => t + 1);
    } catch (e) { console.error(e); }
  };

  const fetchReports = async () => {
    try {
      const resp = await fetch('http://127.0.0.1:5000/api/reports/list');
      const res = await resp.json();
      if (res.reports) setReports(res.reports);
    } catch (e) { console.error(e); }
  };

  const fetchExpertResults = async () => {
    try {
      const resp = await fetch('http://127.0.0.1:5000/api/expert_results');
      const res = await resp.json();
      if (res.results) setExpertResults(res.results);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchData();
    fetchReports();
    fetchExpertResults();
    const inv = setInterval(() => {
      fetchData();
      if (tick % 5 === 0) fetchReports();
      if (tick % 3 === 0) fetchExpertResults();
    }, 2000);
    return () => clearInterval(inv);
  }, [tick]);

  const sendCommand = async (cmd: string, params: any = {}) => {
    try {
      await fetch('http://127.0.0.1:5000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, params })
      });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleScanYoutube = async () => {
    setIsScanning(true);
    try {
      const resp = await fetch('http://127.0.0.1:5000/api/scan_youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: ytUrl })
      });
      const res = await resp.json();
      if (res.status === 'ok') setScannedEvents(res.events);
    } catch (e) { console.error(e); }
    finally { setIsScanning(false); }
  };

  const handleExpertBatchAnalysis = async () => {
    if (batchSelection.size === 0) return;
    setIsExpertProcessing(true);
    const selected = scannedEvents.filter(ev => batchSelection.has(ev.url));
    sendCommand('expert_batch', { events: selected });
  };


  const filteredEvents = scannedEvents.filter(ev => {
    if (expertFilter === 'todos') return true;
    if (expertFilter === 'live') return ev.is_live;
    if (expertFilter === 'ended') return !ev.is_live && !ev.scheduled_start;
    if (expertFilter === 'upcoming') return !!ev.scheduled_start;
    return true;
  });

  if (!data) return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center font-black text-sky-500 uppercase tracking-widest animate-pulse">
      Connecting to Station...
    </div>
  );

  const det = data.detector || {};

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 flex overflow-hidden font-sans selection:bg-sky-500/30">
      
      {/* OVERLAY DE PROCESSAMENTO - PREMIUM */}
      {isExpertProcessing && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-500">
          <div className="bg-slate-900 border border-white/10 p-16 rounded-[4rem] shadow-2xl flex flex-col items-center max-w-lg w-full mx-4">
            <div className="relative w-32 h-32 mb-10">
               <div className="absolute inset-0 border-4 border-emerald-500/10 rounded-full"></div>
               <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
               <Cpu className="absolute inset-0 m-auto text-emerald-500 animate-pulse" size={48} />
            </div>
            <h3 className="text-2xl font-black italic uppercase tracking-tighter mb-4 text-white">Analisando Inteligencia</h3>
            <div className="text-xs text-slate-400 font-bold uppercase tracking-widest text-center mb-10 h-10 px-6">
               {data?.ia_stats?.ia_status || 'Consultando Gemini & Grounding...'}
            </div>
            
            <div className="w-full space-y-2">
               <div className="flex justify-between text-[10px] font-black text-slate-500 uppercase tracking-widest">
                  <span>Progresso da Auditoria</span>
                  <span className="text-emerald-500">Ativo</span>
               </div>
               <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                  <div className="h-full bg-emerald-500 animate-pulse-fast shadow-[0_0_15px_rgba(16,185,129,0.5)]" style={{width: '100%'}}></div>
               </div>
            </div>

            <button 
              onClick={() => setIsExpertProcessing(false)} 
              className="mt-12 text-[10px] font-black uppercase tracking-widest text-slate-600 hover:text-white transition-colors border-b border-transparent hover:border-white/20 pb-1"
            >
              Fechar Visualizacao (Background)
            </button>
          </div>
        </div>
      )}

      {/* SIDEBAR */}
      <div className="w-24 bg-black/40 border-r border-white/5 flex flex-col items-center py-10 gap-10 backdrop-blur-xl z-50">
        <div className="w-12 h-12 bg-gradient-to-br from-sky-500 to-sky-700 rounded-2xl flex items-center justify-center shadow-lg shadow-sky-500/20">
          <Shield size={24} className="text-white" />
        </div>
        
        <nav className="flex flex-col gap-6">
          {[
            { id: 'mesa', icon: <Monitor size={20} />, label: 'Mesa' },
            { id: 'expert', icon: <Cpu size={20} />, label: 'Expert' },
            { id: 'ads', icon: <Layers size={20} />, label: 'Ads' },
            { id: 'reports', icon: <FileText size={20} />, label: 'Relatorios' },
            { id: 'logs', icon: <Terminal size={20} />, label: 'Logs' },
            { id: 'config', icon: <Settings size={20} />, label: 'Config' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-300 group relative ${
                activeTab === tab.id ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/30' : 'text-slate-600 hover:bg-white/5 hover:text-slate-300'
              }`}
            >
              {tab.icon}
            </button>
          ))}
        </nav>
      </div>

      <main className="flex-1 relative flex flex-col">
        
        {/* TOPBAR */}
        <header className="h-24 border-b border-white/5 flex items-center justify-between px-10 bg-black/20 backdrop-blur-md shrink-0 z-40">
          <div className="flex items-center gap-3">
             <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.5)] animate-pulse' : 'bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.5)]'}`}></div>
             <h1 className="text-sm font-black tracking-widest uppercase italic">Station <span className={isRunning ? 'text-emerald-500' : 'text-red-500'}>{isRunning ? 'Live' : 'Stopped'}</span></h1>
          </div>

          <div className="flex items-center gap-8">
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1">Local Time</span>
              <span className="text-xl font-mono font-black text-white tracking-tighter leading-none">
                {new Date().toLocaleTimeString('pt-BR')}
              </span>
            </div>
            <button 
              onClick={() => sendCommand(isRunning ? 'stop' : 'start')}
              className={`h-12 px-10 rounded-xl font-black uppercase text-xs tracking-widest transition-all shadow-xl flex items-center gap-3 ${
                isRunning ? 'bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white border border-red-500/20' : 'bg-sky-600 text-white hover:bg-sky-500'
              }`}
            >
              {isRunning ? <Square size={16} fill="currentColor"/> : <Play size={16} fill="currentColor"/>}
              {isRunning ? 'Parar Monitor' : 'Iniciar Monitor'}
            </button>
          </div>
        </header>

        {/* CONTENT */}
        <div className="flex-1 overflow-hidden relative">
          
          {/* MESA DE CONTROLE */}
          {activeTab === 'mesa' && (
            <div className="h-full flex flex-col p-10 space-y-10 animate-in fade-in duration-500 overflow-y-auto custom-scroll">
               <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                  <div className="lg:col-span-8 space-y-8">
                     <div className="aspect-video bg-black rounded-[3rem] border border-white/10 overflow-hidden shadow-2xl relative ring-1 ring-white/5">
                        <img src={`http://127.0.0.1:5000/api/frame?t=${tick}`} className="w-full h-full object-cover opacity-80" alt="Main" />
                        <div className="absolute bottom-10 left-10 flex items-center gap-6">
                           <div className="px-6 py-3 bg-black/60 backdrop-blur-md rounded-2xl border border-white/10 flex items-center gap-3">
                              <Activity size={18} className="text-sky-500 animate-pulse" />
                              <span className="text-lg font-black italic text-white uppercase">{det.phase || 'Waiting'}</span>
                           </div>
                           <div className="px-6 py-3 bg-black/60 backdrop-blur-md rounded-2xl border border-white/10 flex items-center gap-3">
                              <Clock size={18} className="text-sky-500" />
                              <span className="text-lg font-black italic text-white font-mono">{det.clock || '00:00'}</span>
                           </div>
                        </div>
                     </div>

                     <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatCard label="Score" value={det.confirmed_score} icon={<Trophy size={16}/>} />
                        <StatCard label="Competition" value={det.current_competition} icon={<Monitor size={16}/>} />
                        <StatCard label="Match" value={det.current_match} icon={<Activity size={16}/>} />
                     </div>
                  </div>

                  <div className="lg:col-span-4 h-full">
                     <div className="bg-[#0f172a] rounded-[3rem] border border-white/10 p-10 shadow-2xl h-full flex flex-col ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-10">
                           <div className="flex items-center gap-3">
                              <FileText size={20} className="text-sky-500" />
                              <h3 className="text-sm font-black uppercase italic tracking-widest text-slate-400">Live Audit Flow</h3>
                           </div>
                        </div>
                        <div className="flex-1 space-y-4 overflow-y-auto pr-4 custom-scroll">
                           {(data.events || []).slice().reverse().slice(0, 15).map((ev:any, i:number) => (
                              <div key={i} className="bg-black/40 border border-white/5 rounded-[1.5rem] p-5 flex flex-col gap-3 hover:border-sky-500/30 transition-all group">
                                 <div className="flex justify-between items-start">
                                    <span className="text-[10px] font-black text-sky-400 italic uppercase tracking-tighter">{ev.label}</span>
                                    <span className="text-[9px] font-mono text-slate-600">{ev.time_text}</span>
                                 </div>
                                 <p className="text-xs font-bold text-slate-300 leading-tight italic">"{ev.description}"</p>
                                 <div className="flex items-center gap-2">
                                    <CheckCircle2 size={12} className="text-emerald-500" />
                                    <span className="text-[9px] font-black text-emerald-500 uppercase">Validado {(ev.confidence * 100).toFixed(0)}%</span>
                                 </div>
                              </div>
                           ))}
                        </div>
                     </div>
                  </div>
               </div>
            </div>
          )}

          {/* GEMINI EXPERT - LAYOUT RICO E AMPLO */}
          {activeTab === 'expert' && (
            <div className="h-full flex flex-col p-10 space-y-10 animate-in fade-in duration-500 overflow-y-auto custom-scroll w-full">
               <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6">
                     <div className="w-20 h-20 bg-sky-600 rounded-[2rem] flex items-center justify-center shadow-2xl shadow-sky-600/20"><Cpu size={36} className="text-white"/></div>
                     <div>
                        <h2 className="text-5xl font-black uppercase italic tracking-tighter text-white leading-none">Gemini <span className="text-sky-500">Expert Agent</span></h2>
                        <p className="text-sm text-slate-500 font-bold uppercase tracking-widest mt-3 italic">Auditoria Tecnica com Search Grounding e IA Multimodal</p>
                     </div>
                  </div>
                  <button 
                    onClick={handleExpertBatchAnalysis} 
                    disabled={batchSelection.size === 0 || isExpertProcessing} 
                    className="h-16 px-12 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-20 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all flex items-center gap-4 shadow-2xl shadow-emerald-600/20"
                  >
                     <RefreshCcw size={20} className={isExpertProcessing ? 'animate-spin' : ''} />
                     Analisar Selecionados ({batchSelection.size})
                  </button>
               </div>

               <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 flex-1 min-h-0">
                  {/* ESQUERDA: BUSCA YOUTUBE COM FILTROS */}
                  <div className="lg:col-span-4 flex flex-col space-y-6 min-h-0">
                     <div className="bg-[#0f172a] rounded-[3rem] border border-white/10 p-8 shadow-2xl flex flex-col flex-1 ring-1 ring-white/5">
                        <div className="flex items-center gap-3 mb-8">
                           <Youtube className="text-red-500" size={24} />
                           <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 italic">Pesquisar Transmissoes</h3>
                        </div>

                        <div className="flex gap-2 p-2 bg-black/40 rounded-2xl border border-white/5 mb-8 shadow-inner">
                           <input 
                              type="text" 
                              value={ytUrl}
                              onChange={(e) => setYtUrl(e.target.value)}
                              className="flex-1 bg-transparent px-6 text-sm font-bold text-white focus:outline-none"
                              placeholder="URL do Canal..."
                           />
                           <button onClick={handleScanYoutube} disabled={isScanning} className="h-12 px-8 bg-sky-600 hover:bg-sky-500 text-white rounded-xl font-black uppercase text-[10px] tracking-widest transition-all">
                              {isScanning ? <RefreshCcw size={18} className="animate-spin" /> : 'Buscar'}
                           </button>
                        </div>

                        {/* FILTROS INTEGRADOS */}
                        <div className="flex flex-wrap gap-2 mb-8">
                           {[
                              { id: 'todos', label: 'Todos' },
                              { id: 'live', label: 'Ao Vivo' },
                              { id: 'ended', label: 'Encerrados' },
                              { id: 'upcoming', label: 'Proximos' }
                           ].map(f => (
                              <button 
                                 key={f.id}
                                 onClick={() => setExpertFilter(f.id)}
                                 className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${expertFilter === f.id ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/20' : 'bg-white/5 text-slate-500 hover:bg-white/10'}`}
                              >
                                 {f.label}
                              </button>
                           ))}
                        </div>

                        <div className="flex-1 space-y-4 overflow-y-auto pr-4 custom-scroll">
                           {filteredEvents.map((ev, i) => (
                              <div 
                                 key={i} 
                                 onClick={() => {
                                    const next = new Set(batchSelection);
                                    if (next.has(ev.url)) next.delete(ev.url); else next.add(ev.url);
                                    setBatchSelection(next);
                                 }}
                                 className={`p-4 rounded-3xl border transition-all cursor-pointer group flex items-center gap-5 relative overflow-hidden ${batchSelection.has(ev.url) ? 'bg-sky-600/10 border-sky-500 shadow-lg' : 'bg-black/20 border-white/5 hover:border-white/20'}`}
                              >
                                 <div className="w-32 aspect-video bg-slate-900 rounded-2xl overflow-hidden shrink-0 relative shadow-xl">
                                    <img src={ev.thumbnail} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" alt="T" />
                                    {ev.is_live && <div className="absolute top-2 right-2 px-2 py-0.5 bg-red-600 text-white text-[8px] font-black uppercase rounded shadow-lg animate-pulse">LIVE</div>}
                                 </div>
                                 <div className="flex-1 min-w-0">
                                    <h4 className="text-[11px] font-black text-white leading-tight mb-2 line-clamp-2 uppercase italic">{ev.title}</h4>
                                    <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">{ev.scheduled_start || 'Completo'}</span>
                                 </div>
                                 <div className={`absolute top-4 right-4 w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all ${batchSelection.has(ev.url) ? 'bg-sky-500 border-sky-500 shadow-lg' : 'border-white/10'}`}>
                                    {batchSelection.has(ev.url) && <Check size={12} className="text-white" />}
                                 </div>
                              </div>
                           ))}
                           {filteredEvents.length === 0 && (
                              <div className="py-20 flex flex-col items-center justify-center opacity-10">
                                 <Youtube size={64} className="mb-4" />
                                 <span className="text-xs font-black uppercase tracking-[0.4em]">Nenhuma Transmissao</span>
                              </div>
                           )}
                        </div>
                     </div>
                  </div>

                  {/* DIREITA: GRID DE RESULTADOS AMPLO */}
                  <div className="lg:col-span-8 flex flex-col space-y-6 min-h-0">
                     <div className="bg-[#0f172a] rounded-[3rem] border border-white/10 p-10 shadow-2xl flex flex-col flex-1 ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-10">
                           <div className="flex items-center gap-4">
                              <Trophy size={24} className="text-emerald-500" />
                              <h3 className="text-lg font-black uppercase italic tracking-tighter text-white">Grid de Resultados Expert</h3>
                           </div>
                           <button onClick={() => sendCommand('export_expert_pdf')} className="h-12 px-8 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-3 transition-all border border-white/5">
                              <Download size={18}/> Exportar Relatorio PDF
                           </button>
                        </div>
                        
                        <div className="overflow-x-auto flex-1 custom-scroll bg-black/20 rounded-[2rem] border border-white/5">
                           <table className="w-full text-left">
                              <thead className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-500 border-b border-white/5">
                                 <tr>
                                    <th className="px-8 py-6">Timestamp</th>
                                    <th className="px-8 py-6">Minuto</th>
                                    <th className="px-8 py-6">Evento / Insight de Auditoria</th>
                                    <th className="px-8 py-6 text-center">Validacao</th>
                                 </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5">
                                 {expertResults.flatMap(batch => Array.isArray(batch) ? batch : [batch]).flatMap((res:any) => res.technical_milestones || []).reverse().map((m:any, idx:number) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-all group">
                                       <td className="px-8 py-6 font-mono text-xs text-emerald-500 font-bold">{m.time}</td>
                                       <td className="px-8 py-6 font-black text-lg text-white italic">{m.minute}'</td>
                                       <td className="px-8 py-6">
                                          <div className="text-sm font-bold text-slate-200 leading-relaxed mb-1 italic">
                                             "{m.event}"
                                          </div>
                                          <div className="flex items-center gap-3">
                                             <span className="px-2 py-0.5 bg-slate-800 text-slate-500 rounded text-[9px] font-black uppercase tracking-tighter border border-white/5">{m.type}</span>
                                             {m.confidence < 0.9 && (
                                                <div className="flex items-center gap-1.5">
                                                   <AlertTriangle size={12} className="text-amber-500" />
                                                   <span className="text-[9px] font-black text-amber-500 uppercase">Validacao Grounding Requerida</span>
                                                </div>
                                             )}
                                          </div>
                                       </td>
                                       <td className="px-8 py-6 text-center">
                                          <div className={`w-12 h-12 rounded-2xl mx-auto flex items-center justify-center border ${m.confidence > 0.9 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500' : 'bg-amber-500/10 border-amber-500/30 text-amber-500'}`}>
                                             {m.confidence > 0.9 ? <CheckCircle2 size={24}/> : <AlertTriangle size={24}/>}
                                          </div>
                                       </td>
                                    </tr>
                                 ))}
                                 {expertResults.length === 0 && (
                                    <tr>
                                       <td colSpan={4} className="py-60 text-center opacity-10 flex flex-col items-center justify-center">
                                          <History size={80} className="mb-6" />
                                          <span className="text-xl font-black uppercase tracking-[0.6em]">Historico Vazio</span>
                                       </td>
                                    </tr>
                                 )}
                              </tbody>
                           </table>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
          )}

          {/* RELATORIOS */}
          {activeTab === 'reports' && (
            <div className="h-full p-12 max-w-6xl mx-auto space-y-12 animate-in fade-in duration-500 overflow-y-auto custom-scroll">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-4xl font-black uppercase italic tracking-tighter text-white leading-none">Arquivo <span className="text-slate-500">de Auditoria</span></h2>
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-4 italic">Gerencie e exporte documentos oficiais das sessoes monitoradas</p>
                </div>
                <button onClick={fetchReports} className="h-16 px-10 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all flex items-center gap-4">
                  <RefreshCcw size={20} /> Sincronizar Arquivos
                </button>
              </div>

              <div className="bg-[#0f172a] rounded-[3rem] border border-white/10 overflow-hidden shadow-2xl ring-1 ring-white/5">
                <table className="w-full text-left">
                  <thead className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-white/5">
                    <tr>
                      <th className="px-10 py-8">Documento / Sessao</th>
                      <th className="px-10 py-8">Gerado em</th>
                      <th className="px-10 py-8">Tamanho</th>
                      <th className="px-10 py-8 text-center">Acao</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {reports.map((r, i) => (
                      <tr key={i} className="hover:bg-white/5 transition-all">
                        <td className="px-10 py-8">
                           <div className="flex items-center gap-5">
                              <div className="w-12 h-12 rounded-2xl bg-red-500/10 text-red-500 flex items-center justify-center border border-red-500/20">
                                 <FileText size={24} />
                              </div>
                              <div>
                                 <div className="text-base font-black text-white italic tracking-tighter uppercase">{r.name}</div>
                                 <div className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Official PDF Audit</div>
                              </div>
                           </div>
                        </td>
                        <td className="px-10 py-8 text-sm font-mono text-slate-400">{new Date(r.date * 1000).toLocaleString()}</td>
                        <td className="px-10 py-8 text-sm text-slate-500 font-bold">{(r.size / 1024 / 1024).toFixed(2)} MB</td>
                        <td className="px-10 py-8 text-center">
                          <a href={`http://127.0.0.1:5000/api/reports/download/${r.name}`} className="inline-flex items-center gap-3 px-8 py-4 bg-sky-600 hover:bg-sky-500 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl shadow-sky-600/10">
                             <Download size={16}/> Download
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* LOGS */}
          {activeTab === 'logs' && (
            <div className="h-full p-10 animate-in fade-in duration-500 flex flex-col space-y-8">
               <h2 className="text-4xl font-black uppercase italic tracking-tighter text-white">System <span className="text-slate-500">Terminal</span></h2>
               <div className="flex-1 bg-black rounded-[3rem] border border-white/10 p-10 font-mono text-[11px] overflow-y-auto custom-scroll shadow-2xl ring-1 ring-white/5">
                  {data.ia_logs.map((log:string, i:number) => (
                    <div key={i} className="mb-2 flex gap-6 animate-in slide-in-from-left-4 duration-300">
                      <span className="text-slate-700 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                      <span className="text-slate-400 leading-relaxed font-bold uppercase">{log}</span>
                    </div>
                  ))}
                  <div className="mt-10 pt-10 border-t border-white/5 opacity-50 italic">Listening to kernel stream...</div>
               </div>
            </div>
          )}

        </div>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scroll::-webkit-scrollbar { width: 6px; }
        .custom-scroll::-webkit-scrollbar-track { background: transparent; }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        .custom-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
        @keyframes pulse-fast {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .animate-pulse-fast { animation: pulse-fast 1s infinite ease-in-out; }
      `}} />
    </div>
  );
};

const StatCard = ({ label, value, icon }: { label: string, value: any, icon: any }) => (
  <div className="bg-[#0f172a] rounded-[2rem] border border-white/10 p-8 shadow-2xl ring-1 ring-white/5 flex flex-col justify-between">
    <div className="flex items-center gap-3 mb-6 text-slate-500">
       {icon}
       <span className="text-[10px] font-black uppercase tracking-widest">{label}</span>
    </div>
    <div className="text-2xl font-black italic text-white uppercase truncate">{value || '---'}</div>
  </div>
);

export default Dashboard;
