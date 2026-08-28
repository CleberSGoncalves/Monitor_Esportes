import React, { useState } from 'react';
import { Lock, User, ShieldCheck } from 'lucide-react';

interface LoginProps {
  onLogin: (user: string) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (user === 'mdna' && password === 'kafjtwev') {
      onLogin(user);
    } else {
      setError('Credenciais inválidas. Tente novamente.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl p-8 space-y-8">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-sky-500/10 text-sky-500 mb-4">
            <ShieldCheck size={32} />
          </div>
          <h1 className="text-3xl font-bold text-slate-100 italic tracking-tight">MDNA <span className="text-sky-500">Edition</span></h1>
          <p className="text-slate-400">Monitor de Esportes v2.0</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Usuário</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 outline-none transition-all"
                placeholder="mdna"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Senha</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 outline-none transition-all"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-400/10 p-2 rounded text-center">{error}</p>
          )}

          <button
            type="submit"
            className="w-full bg-sky-600 hover:bg-sky-500 text-white font-semibold py-3 rounded-lg shadow-lg shadow-sky-600/20 transition-all active:scale-[0.98]"
          >
            Acessar Monitor
          </button>
        </form>

        <div className="text-center">
          <p className="text-xs text-slate-500">Desenvolvido por MDNA para monitoramento inteligente.</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
