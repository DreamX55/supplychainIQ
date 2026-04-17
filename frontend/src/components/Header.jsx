import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Github, Zap, LogOut, UserCircle2 } from 'lucide-react';

const PROVIDER_LABELS = {
  groq: 'Groq',
  claude: 'Claude',
  openai: 'OpenAI',
  gemini: 'Gemini',
};

function ProviderChip() {
  const stored = typeof window !== 'undefined'
    ? localStorage.getItem('supplychainiq_preferred_provider')
    : null;
  const label = stored ? (PROVIDER_LABELS[stored] || stored) : 'Demo Mode';
  const isLive = !!stored;

  return (
    <div
      className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
        isLive
          ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
          : 'bg-slate/20 border-slate/50 text-mist'
      }`}
      title={isLive ? `Powered by ${label}` : 'Running in demo mode (mock provider)'}
    >
      <Zap className="w-3 h-3" />
      <span className="text-[10px] font-semibold uppercase tracking-wider">{label}</span>
    </div>
  );
}

function UserPill({ currentUser, authState, onLogout }) {
  if (!currentUser) return null;
  const isGuest = authState === 'guest';
  const label = isGuest ? 'Guest' : (currentUser.email || 'Account');
  const initials = isGuest
    ? 'G'
    : (currentUser.email ? currentUser.email[0].toUpperCase() : 'A');

  return (
    <div className="hidden sm:flex items-center gap-2 pl-2 pr-1 py-1 rounded-full border border-slate/40 bg-graphite/50">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold ${
        isGuest
          ? 'bg-slate/40 text-mist'
          : 'bg-blue-500/20 text-blue-200'
      }`}>
        {initials}
      </div>
      <span className="text-[11px] text-mist max-w-[140px] truncate" title={label}>
        {label}
      </span>
      <button
        onClick={onLogout}
        title={isGuest ? 'Exit guest session' : 'Sign out'}
        className="p-1 rounded-full hover:bg-slate/40 text-mist hover:text-cloud transition-colors"
      >
        <LogOut className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export default function Header({ onHistoryClick, onNewChatClick, currentUser, authState, onLogout }) {
  return (
    <header className="border-b border-slate/30 bg-carbon/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-accent-primary/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-accent-primary" />
            </div>
            {/* Pulse effect */}
            <div className="absolute inset-0 rounded-xl bg-accent-primary/20 animate-ping" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-snow tracking-tight">
              SupplyChain<span className="text-accent-primary">IQ</span>
            </h1>
            <p className="text-xs text-mist -mt-0.5">
              AI Risk Intelligence
            </p>
          </div>
        </motion.div>
        
        {/* Status indicator */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          {/* AI Engine chip */}
          <ProviderChip />

          {/* Navigation Buttons */}
          <button
            onClick={onHistoryClick}
            className="hidden sm:block px-3 py-1.5 rounded-full bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700 transition"
          >
            History
          </button>
          
          <button
            onClick={onNewChatClick}
            className="hidden sm:block px-3 py-1.5 rounded-full bg-blue-600 outline-none text-white text-xs font-medium hover:bg-blue-500 transition"
          >
            New Analysis
          </button>

          {/* User pill — shows email or "Guest", with logout button */}
          <UserPill currentUser={currentUser} authState={authState} onLogout={onLogout} />

          {/* SDG badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/30">
            <span className="text-xs text-violet-400">SDG 9</span>
          </div>
          
          {/* Links */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg hover:bg-graphite transition-colors text-mist hover:text-cloud"
          >
            <Github className="w-5 h-5" />
          </a>
        </motion.div>
      </div>
    </header>
  );
}
