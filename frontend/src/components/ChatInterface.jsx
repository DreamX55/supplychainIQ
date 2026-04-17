import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Loader2, Sparkles, RotateCcw, Paperclip,
  LayoutGrid, Network, Sliders, Download,
  Shirt, Cpu, Leaf, ArrowRight, MapPin,
} from 'lucide-react';
import RiskBrief from './RiskBrief';
import SupplyChainGraph from './SupplyChainGraph';
import ScenarioSimulator from './ScenarioSimulator';
import { getPersonas, updateUserProfile } from '../utils/api';
import { exportAnalysisAsMarkdown, exportAnalysisAsHTML, exportAnalysisAsPDF } from '../utils/exportReport';

const PERSONA_ICONS = {
  shirt: Shirt,
  cpu: Cpu,
  leaf: Leaf,
};

const PERSONA_ACCENTS = {
  amber: { border: 'border-amber-500/40', glow: 'shadow-amber-500/10', icon: 'text-amber-300', bg: 'bg-amber-500/10' },
  blue: { border: 'border-blue-500/40', glow: 'shadow-blue-500/10', icon: 'text-blue-300', bg: 'bg-blue-500/10' },
  emerald: { border: 'border-emerald-500/40', glow: 'shadow-emerald-500/10', icon: 'text-emerald-300', bg: 'bg-emerald-500/10' },
};

function PersonaPicker({ onPick, disabled }) {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getPersonas()
      .then((data) => {
        if (mounted) setPersonas(data.personas || []);
      })
      .catch(() => {
        if (mounted) setPersonas([]);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="text-xs text-mist text-center py-4">
        <Loader2 className="inline h-3 w-3 animate-spin mr-1.5" />
        Loading demo personas…
      </div>
    );
  }

  if (personas.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-3xl mx-auto">
      {personas.map((p, i) => {
        const PIcon = PERSONA_ICONS[p.icon] || Sparkles;
        const accent = PERSONA_ACCENTS[p.accent] || PERSONA_ACCENTS.blue;
        return (
          <motion.button
            key={p.id}
            type="button"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.08 }}
            disabled={disabled}
            onClick={() => onPick(p)}
            className={`group text-left rounded-xl border bg-graphite/60 p-4 transition-all hover:bg-graphite hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${accent.border} ${accent.glow}`}
          >
            <div className="flex items-center gap-2.5 mb-2">
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent.bg}`}>
                <PIcon className={`h-4 w-4 ${accent.icon}`} />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold text-snow truncate">{p.name}</div>
                <div className="text-[10px] uppercase tracking-wider text-slate truncate">
                  {p.industry}
                </div>
              </div>
            </div>
            <p className="text-[11px] leading-snug text-mist mb-3">{p.tagline}</p>
            <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-accent-glow opacity-70 group-hover:opacity-100 transition-opacity">
              Run analysis
              <ArrowRight className="h-3 w-3" />
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-2">
      <motion.div
        className="w-2 h-2 rounded-full bg-accent-primary"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
      />
      <motion.div
        className="w-2 h-2 rounded-full bg-accent-primary"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
      />
      <motion.div
        className="w-2 h-2 rounded-full bg-accent-primary"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
      />
    </div>
  );
}

function SuggestionChips({ suggestions, onSelect, disabled }) {
  if (!suggestions || suggestions.length === 0) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-wrap gap-2 mt-3"
    >
      {suggestions.map((suggestion, i) => (
        <motion.button
          key={i}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(suggestion)}
          disabled={disabled}
          className="
            px-3 py-1.5 rounded-full text-xs
            bg-graphite border border-slate/50
            text-mist hover:text-cloud hover:border-accent-primary/50
            transition-colors disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {suggestion}
        </motion.button>
      ))}
    </motion.div>
  );
}

function FollowUpContent({ data }) {
  if (!data || !data.suggestions) return null;
  
  return (
    <div className="mt-3 space-y-2">
      {data.suggestions.map((item, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.1 }}
          className="p-3 rounded-lg bg-carbon/50 border border-slate/30"
        >
          {item.category && (
            <div className="text-xs font-semibold text-accent-primary mb-2">
              {item.category}
            </div>
          )}
          {item.options && item.options.map((opt, j) => (
            <div key={j} className="flex justify-between text-xs py-1 border-b border-slate/20 last:border-0">
              <span className="text-cloud">{opt.country}: {opt.companies}</span>
              <span className="text-mist">{opt.lead_time}</span>
            </div>
          ))}
          {item.route && (
            <div className="flex justify-between text-xs">
              <span className="text-cloud">{item.route}</span>
              <span className="text-mist">{item.transit_time}</span>
            </div>
          )}
          {item.status && (
            <div className="text-xs text-amber-400 mt-1">{item.status}</div>
          )}
          {item.strategy && (
            <>
              <div className="font-semibold text-cloud">{item.strategy}</div>
              <div className="text-mist text-xs mt-1">{item.description}</div>
            </>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function AnalysisWorkspace({ analysis, sessionId }) {
  const [view, setView] = useState('brief');
  const hasGraph =
    analysis?.supply_chain_graph &&
    Array.isArray(analysis.supply_chain_graph.nodes) &&
    analysis.supply_chain_graph.nodes.length > 0;
  const canSimulate = !!sessionId;

  return (
    <div className="space-y-3">
      {/* View toggle + export */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex items-center gap-1 rounded-lg border border-slate/40 bg-carbon/60 p-0.5">
          <button
            type="button"
            onClick={() => setView('brief')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors ${
              view === 'brief'
                ? 'bg-accent-primary/20 text-accent-glow'
                : 'text-mist hover:text-cloud'
            }`}
          >
            <LayoutGrid className="h-3 w-3" />
            Brief
          </button>
          <button
            type="button"
            onClick={() => setView('graph')}
            disabled={!hasGraph}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
              view === 'graph'
                ? 'bg-accent-primary/20 text-accent-glow'
                : 'text-mist hover:text-cloud'
            }`}
          >
            <Network className="h-3 w-3" />
            Graph
          </button>
          <button
            type="button"
            onClick={() => setView('simulate')}
            disabled={!canSimulate}
            title={canSimulate ? 'Run a what-if scenario' : 'Run an analysis first to enable scenarios'}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
              view === 'simulate'
                ? 'bg-accent-primary/20 text-accent-glow'
                : 'text-mist hover:text-cloud'
            }`}
          >
            <Sliders className="h-3 w-3" />
            Simulate
          </button>
        </div>

        <div className="inline-flex items-center rounded-lg border border-slate/40 bg-carbon/60 overflow-hidden">
          <button
            type="button"
            onClick={() => {
              const companyName =
                (typeof window !== 'undefined' &&
                  localStorage.getItem('supplychainiq_company_name')) ||
                'SupplyChainIQ';
              exportAnalysisAsPDF(analysis, { companyName });
            }}
            title="Open print dialog — pick 'Save as PDF' to download a board-ready report"
            className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-mist hover:text-cloud hover:bg-graphite/60 transition-colors"
          >
            <Download className="h-3 w-3" />
            PDF
          </button>
          <div className="w-px self-stretch bg-slate/40" />
          <button
            type="button"
            onClick={() => {
              const companyName =
                (typeof window !== 'undefined' &&
                  localStorage.getItem('supplychainiq_company_name')) ||
                'SupplyChainIQ';
              exportAnalysisAsHTML(analysis, { companyName });
            }}
            title="Download as standalone HTML report (opens in any browser)"
            className="px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-mist hover:text-cloud hover:bg-graphite/60 transition-colors"
          >
            HTML
          </button>
          <div className="w-px self-stretch bg-slate/40" />
          <button
            type="button"
            onClick={() => {
              const companyName =
                (typeof window !== 'undefined' &&
                  localStorage.getItem('supplychainiq_company_name')) ||
                'SupplyChainIQ';
              exportAnalysisAsMarkdown(analysis, { companyName });
            }}
            title="Download as Markdown (.md) report"
            className="px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-mist hover:text-cloud hover:bg-graphite/60 transition-colors"
          >
            .md
          </button>
        </div>
      </div>

      {view === 'brief' && <RiskBrief analysis={analysis} />}
      {view === 'graph' && <SupplyChainGraph analysis={analysis} />}
      {view === 'simulate' && <ScenarioSimulator analysis={analysis} sessionId={sessionId} />}
    </div>
  );
}

function MessageBubble({ message, onSuggestionSelect, isLatest, sessionId }) {
  const isUser = message.role === 'user';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Bubble */}
        <div
          className={`
            px-4 py-3 rounded-2xl
            ${isUser
              ? 'message-user text-white rounded-br-md'
              : 'message-assistant text-cloud rounded-bl-md'
            }
            ${message.error ? 'border-red-500/50' : ''}
          `}
        >
          {!message.analysis && (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          )}
          
          {/* Risk Brief / Graph / Simulate workspace for analysis messages */}
          {message.analysis && (
            <div className="mt-1">
              <AnalysisWorkspace analysis={message.analysis} sessionId={sessionId} />
            </div>
          )}
          
          {/* Follow-up content */}
          {message.followUp && (
            <FollowUpContent data={message.followUp} />
          )}

          {/* Provider Metadata */}
          {!isUser && message.meta && (
            <div className="mt-2 flex items-center gap-2 border-t border-white/10 pt-2 text-[10px] uppercase tracking-widest opacity-50">
              <span>AI Engine: {message.meta.provider_used || 'Unknown'}</span>
              {message.meta.is_mock && (
                <span className="rounded bg-amber-500/20 px-1 text-amber-400 font-bold">Fallback Mode</span>
              )}
            </div>
          )}
        </div>
        
        {/* Suggestions */}
        {isLatest && !isUser && (message.analysis?.follow_up_suggestions || message.followUp?.follow_up_suggestions) && (
          <SuggestionChips
            suggestions={message.analysis?.follow_up_suggestions || message.followUp?.follow_up_suggestions}
            onSelect={onSuggestionSelect}
          />
        )}
        
        {/* Timestamp */}
        <div className={`text-xs text-slate mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </div>
      </div>
    </motion.div>
  );
}

export default function ChatInterface({ messages, isLoading, onSend, onReset, onFileUpload, sessionId }) {
  const [input, setInput] = useState('');
  const [localFocus, setLocalFocus] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // Best-effort focus country guess from the user's saved profile.
  // The backend will also infer this server-side, so this is purely
  // for the UI chip — it never blocks the request.
  const inferredFocusCountry = (() => {
    try {
      const blob = (
        (localStorage.getItem('supplychainiq_company_name') || '') + ' ' +
        (localStorage.getItem('supplychainiq_company_type') || '')
      ).toLowerCase();
      if (blob.includes('india')) return 'India';
      if (blob.includes('usa') || blob.includes('united states') || blob.includes('america')) return 'United States';
      if (blob.includes('uk') || blob.includes('britain')) return 'United Kingdom';
      return null;
    } catch {
      return null;
    }
  })();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      if (onFileUpload && !isLoading) {
        onFileUpload(e.target.files[0]);
      }
      e.target.value = null;
    }
  };
  
  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    onSend(input.trim(), {
      intraCountryFocus: localFocus,
      focusCountry: localFocus ? inferredFocusCountry : null,
    });
    setInput('');
  };
  
  const handleSuggestionSelect = (suggestion) => {
    if (isLoading) return;
    onSend(suggestion, {
      intraCountryFocus: localFocus,
      focusCountry: localFocus ? inferredFocusCountry : null,
    });
  };

  const handlePersonaPick = async (persona) => {
    if (isLoading) return;
    // Best-effort profile update so the analysis is industry-personalized.
    // Fire-and-forget — don't block the analysis on this.
    try {
      localStorage.setItem('supplychainiq_company_name', persona.name);
      updateUserProfile(persona.name, persona.industry).catch(() => {});
    } catch {
      /* ignore */
    }
    onSend(persona.description, {
      intraCountryFocus: localFocus,
      focusCountry: localFocus ? inferredFocusCountry : null,
    });
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Welcome message if no messages */}
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-10"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent-primary/20 mb-4">
              <Sparkles className="w-8 h-8 text-accent-primary" />
            </div>
            <h2 className="text-2xl font-bold text-snow mb-2 tracking-tight">
              Map your supply chain risk in 30 seconds
            </h2>
            <p className="text-sm text-mist max-w-xl mx-auto mb-8">
              Pick a demo persona to see SupplyChainIQ in action — or describe your own
              chain below. You'll get a grounded risk brief, a visual graph of your nodes,
              and what-if scenarios you can run instantly.
            </p>

            <PersonaPicker onPick={handlePersonaPick} disabled={isLoading} />

            <div className="mt-6 text-[10px] uppercase tracking-[0.2em] text-slate">
              · or type your own description below ·
            </div>
          </motion.div>
        )}
        
        {/* Messages */}
        <AnimatePresence mode="popLayout">
          {messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              onSuggestionSelect={handleSuggestionSelect}
              isLatest={index === messages.length - 1}
              sessionId={sessionId}
            />
          ))}
        </AnimatePresence>
        
        {/* Loading indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="message-assistant rounded-2xl rounded-bl-md">
              <TypingIndicator />
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <div className="border-t border-slate/30 p-4">
        {/* Local Focus toggle row */}
        <div className="flex items-center justify-between mb-3 px-1">
          <button
            type="button"
            onClick={() => setLocalFocus(v => !v)}
            disabled={isLoading}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
              border transition-all duration-200
              ${localFocus
                ? 'bg-emerald-500/15 border-emerald-400/50 text-emerald-200 shadow-[0_0_12px_-2px_rgba(16,185,129,0.4)]'
                : 'bg-graphite border-slate/40 text-mist hover:text-cloud hover:border-slate'}
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
            title="Pivot the analysis from global trade risks to intra-country logistics"
          >
            <MapPin className={`w-3.5 h-3.5 ${localFocus ? 'text-emerald-300' : ''}`} />
            <span>Local Focus</span>
            <span
              className={`
                relative inline-block w-7 h-3.5 rounded-full transition-colors
                ${localFocus ? 'bg-emerald-400/70' : 'bg-slate/60'}
              `}
            >
              <span
                className={`
                  absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white transition-all
                  ${localFocus ? 'left-4' : 'left-0.5'}
                `}
              />
            </span>
          </button>

          {localFocus && (
            <motion.span
              initial={{ opacity: 0, x: 6 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-[11px] text-emerald-300/80 font-medium"
            >
              {inferredFocusCountry
                ? `Focused on ${inferredFocusCountry} — intra-country risks only`
                : 'Country auto-detected from your description'}
            </motion.span>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-3">
          {/* Reset button */}
          {messages.length > 0 && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              type="button"
              onClick={onReset}
              className="
                p-3 rounded-xl bg-graphite border border-slate/50
                text-mist hover:text-cloud hover:border-slate
                transition-colors
              "
              title="Start new analysis"
            >
              <RotateCcw className="w-5 h-5" />
            </motion.button>
          )}

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept=".csv,.xlsx,.xls,.txt,.pdf"
          />
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="
              p-3 rounded-xl bg-graphite border border-slate/50
              text-mist hover:text-cloud hover:border-slate
              transition-colors disabled:opacity-50
            "
            title="Upload Context Data (Excel, CSV, TXT)"
          >
            <Paperclip className="w-5 h-5" />
          </motion.button>
          
          {/* Input field */}
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={messages.length === 0 
                ? "Describe your supply chain..." 
                : "Ask a follow-up question..."
              }
              disabled={isLoading}
              className="
                w-full px-4 py-3 pr-12 rounded-xl
                bg-graphite border border-slate/50
                text-cloud placeholder:text-slate
                focus:outline-none focus:border-accent-primary/50 input-glow
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors
              "
            />
          </div>
          
          {/* Send button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            disabled={!input.trim() || isLoading}
            className="
              p-3 rounded-xl
              bg-accent-primary text-white
              hover:bg-accent-primary/90
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors btn-pulse
            "
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </motion.button>
        </form>
      </div>
    </div>
  );
}
