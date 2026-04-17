import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, CheckCircle, KeyRound, Zap, ExternalLink, ShieldCheck } from 'lucide-react';
import {
  getUserProfile,
  updateUserProfile,
  storeApiKey,
  listKeys,
} from '../utils/api';

const PROVIDER_OPTIONS = [
  {
    id: 'groq',
    name: 'Groq',
    tagline: 'Fast OSS inference — recommended for live demo',
    keyUrl: 'https://console.groq.com/keys',
    keyHint: 'gsk_...',
  },
  {
    id: 'claude',
    name: 'Claude (Anthropic)',
    tagline: 'Highest-quality reasoning',
    keyUrl: 'https://console.anthropic.com/settings/keys',
    keyHint: 'sk-ant-...',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    tagline: 'GPT-4o family',
    keyUrl: 'https://platform.openai.com/api-keys',
    keyHint: 'sk-...',
  },
  {
    id: 'gemini',
    name: 'Gemini (Google)',
    tagline: 'Free tier available',
    keyUrl: 'https://aistudio.google.com/app/apikey',
    keyHint: 'AIza...',
  },
];

export default function SetupScreen({ onComplete }) {
  const [companyName, setCompanyName] = useState('');
  const [companyType, setCompanyType] = useState('General Manufacturer');
  const [providerId, setProviderId] = useState(
    () => localStorage.getItem('supplychainiq_preferred_provider') || 'groq'
  );
  const [apiKey, setApiKey] = useState('');
  const [storedProviders, setStoredProviders] = useState([]);
  const [keyError, setKeyError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    Promise.all([
      getUserProfile().catch(() => null),
      listKeys().catch(() => null),
    ]).then(([profile, keys]) => {
      if (profile?.company_name) setCompanyName(profile.company_name);
      if (profile?.company_type) setCompanyType(profile.company_type);
      if (keys?.providers) setStoredProviders(keys.providers);
      setFetched(true);
    });
  }, []);

  const selectedProvider = PROVIDER_OPTIONS.find((p) => p.id === providerId);
  const hasStoredKey = storedProviders.includes(providerId);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setKeyError(null);

    try {
      const finalName = companyName.trim() === '' ? 'Guest Manufacturer' : companyName;
      await updateUserProfile(finalName, companyType);
      try {
        localStorage.setItem('supplychainiq_company_name', finalName);
      } catch {
        /* ignore */
      }

      // Store API key only if a new one was entered (otherwise keep existing)
      if (apiKey.trim()) {
        try {
          await storeApiKey(providerId, apiKey.trim());
        } catch (err) {
          setKeyError(err.message || 'Failed to save API key');
          setLoading(false);
          return;
        }
      }

      // Persist preferred provider so api.js sends X-Preferred-Provider
      localStorage.setItem('supplychainiq_preferred_provider', providerId);
      onComplete();
    } catch (err) {
      console.error(err);
      onComplete();
    } finally {
      setLoading(false);
    }
  };

  const skipToDemo = () => {
    // Demo mode = no preferred provider, router falls through to mock
    localStorage.removeItem('supplychainiq_preferred_provider');
    onComplete();
  };

  if (!fetched) {
    return <div className="flex h-full items-center justify-center text-slate-400">Loading…</div>;
  }

  return (
    <div
      className="w-full min-h-full flex flex-col items-center justify-start bg-slate-950 px-4 py-6"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl backdrop-blur-xl"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <Settings size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Configure SupplyChainIQ</h1>
            <p className="text-sm text-slate-400">Tell us about your business and pick an AI engine.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ----- Company profile ----- */}
          <div className="space-y-4">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
              1. Your Business
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Company Name</label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g., Acme Corp (leave blank for Guest)"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-black placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Industry Type</label>
              <select
                value={companyType}
                onChange={(e) => setCompanyType(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-black focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="General Manufacturer">General Manufacturer</option>
                <option value="Electronics & Semiconductors">Electronics & Semiconductors</option>
                <option value="Automotive">Automotive</option>
                <option value="Food & Beverage">Food & Beverage</option>
                <option value="Textiles & Apparel">Textiles & Apparel</option>
                <option value="Healthcare & Pharma">Healthcare & Pharma</option>
              </select>
            </div>
          </div>

          {/* ----- AI engine ----- */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                2. AI Engine
              </div>
              <div className="flex items-center gap-1 text-[10px] text-emerald-400">
                <ShieldCheck size={12} />
                Encrypted at rest
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {PROVIDER_OPTIONS.map((p) => {
                const active = providerId === p.id;
                const stored = storedProviders.includes(p.id);
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setProviderId(p.id)}
                    className={`text-left rounded-xl border px-3 py-2.5 transition-all ${
                      active
                        ? 'border-blue-500 bg-blue-500/10 text-white shadow-lg shadow-blue-500/10'
                        : 'border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold flex items-center gap-1.5">
                        {p.id === 'groq' && <Zap size={12} className="text-amber-400" />}
                        {p.name}
                      </span>
                      {stored && (
                        <span className="text-[9px] uppercase tracking-wider text-emerald-400">
                          saved
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{p.tagline}</div>
                  </button>
                );
              })}
            </div>

            <div className="space-y-2">
              <label className="flex items-center justify-between text-sm font-medium text-slate-300">
                <span className="flex items-center gap-1.5">
                  <KeyRound size={14} />
                  {selectedProvider.name} API Key
                </span>
                <a
                  href={selectedProvider.keyUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300"
                >
                  Get a key <ExternalLink size={10} />
                </a>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={
                  hasStoredKey
                    ? '••••••••  (key already saved — leave blank to keep it)'
                    : selectedProvider.keyHint
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-black placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-sm"
              />
              {keyError && (
                <div className="text-xs text-red-400">{keyError}</div>
              )}
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Keys are encrypted with Fernet and stored locally. You can switch engines anytime —
                if your chosen provider fails, the system falls back automatically.
              </p>
            </div>
          </div>

          {/* ----- Actions ----- */}
          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={skipToDemo}
              className="flex-1 rounded-xl border border-slate-700 bg-transparent py-3 font-medium text-slate-300 transition-colors hover:bg-slate-800"
            >
              Skip — Use Demo Mode
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-[1.5] flex items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 px-6 font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Saving…' : 'Save & Continue'}
              <CheckCircle size={18} />
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
