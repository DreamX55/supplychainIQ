import { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Mail, Building2, ShieldCheck, ArrowRight, UserCircle2 } from 'lucide-react';
import { register, login, continueAsGuest } from '../utils/api';

/**
 * Login + Register screen.
 *
 * Two tabs (Login / Register) plus a "Continue as guest" escape hatch
 * so the demo path stays one-click for judges who don't want to sign up.
 *
 * On any successful auth, calls onAuthSuccess(user) so the parent can
 * unmount this and render the main app.
 */
export default function LoginScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyType, setCompanyType] = useState('General Manufacturer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      let user;
      if (mode === 'login') {
        user = await login(email, password);
      } else {
        user = await register(email, password, companyName || null, companyType);
      }
      onAuthSuccess?.(user);
    } catch (err) {
      setError(err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = () => {
    continueAsGuest();
    onAuthSuccess?.({ user_id: localStorage.getItem('supplychainiq_user_id'), email: null });
  };

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border border-blue-400/30 mb-4">
            <ShieldCheck className="w-7 h-7 text-blue-300" />
          </div>
          <h1 className="text-2xl font-bold text-cloud mb-2">SupplyChainIQ</h1>
          <p className="text-sm text-mist">
            {mode === 'login'
              ? 'Sign in to your workspace'
              : 'Create a workspace for your company'}
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-graphite/60 border border-slate/40 rounded-xl p-1 mb-6">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(null); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
              mode === 'login'
                ? 'bg-accent-primary/20 text-accent-glow'
                : 'text-mist hover:text-cloud'
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setError(null); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
              mode === 'register'
                ? 'bg-accent-primary/20 text-accent-glow'
                : 'text-mist hover:text-cloud'
            }`}
          >
            Create account
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div>
            <label className="block text-xs font-medium text-mist mb-1.5 uppercase tracking-wider">
              Work email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                placeholder="you@company.com"
                className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-graphite border border-slate/50 text-cloud placeholder:text-slate focus:outline-none focus:border-accent-primary/50 disabled:opacity-50"
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-medium text-mist mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === 'register' ? 6 : 1}
                disabled={loading}
                placeholder={mode === 'register' ? 'At least 6 characters' : '••••••••'}
                className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-graphite border border-slate/50 text-cloud placeholder:text-slate focus:outline-none focus:border-accent-primary/50 disabled:opacity-50"
              />
            </div>
          </div>

          {/* Register-only fields */}
          {mode === 'register' && (
            <>
              <div>
                <label className="block text-xs font-medium text-mist mb-1.5 uppercase tracking-wider">
                  Company name
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate" />
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    disabled={loading}
                    placeholder="Acme Manufacturing"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-graphite border border-slate/50 text-cloud placeholder:text-slate focus:outline-none focus:border-accent-primary/50 disabled:opacity-50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-mist mb-1.5 uppercase tracking-wider">
                  Industry
                </label>
                <select
                  value={companyType}
                  onChange={(e) => setCompanyType(e.target.value)}
                  disabled={loading}
                  className="w-full px-3 py-2.5 rounded-lg bg-graphite border border-slate/50 text-cloud focus:outline-none focus:border-accent-primary/50 disabled:opacity-50"
                >
                  <option>General Manufacturer</option>
                  <option>Apparel & Textiles</option>
                  <option>Electronics</option>
                  <option>Automotive</option>
                  <option>Food & Agriculture</option>
                  <option>Pharmaceutical</option>
                  <option>Retail / Distributor</option>
                </select>
              </div>
            </>
          )}

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-red-300 bg-red-500/10 border border-red-400/30 rounded-lg px-3 py-2"
            >
              {error}
            </motion.div>
          )}

          {/* Submit */}
          <motion.button
            type="submit"
            disabled={loading || !email || !password}
            whileTap={{ scale: 0.98 }}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-accent-primary text-white font-medium hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Please wait…' : (mode === 'login' ? 'Sign in' : 'Create account')}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </motion.button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 h-px bg-slate/30" />
          <span className="text-[10px] uppercase tracking-wider text-slate">or</span>
          <div className="flex-1 h-px bg-slate/30" />
        </div>

        {/* Guest path — preserved so the demo stays one-click */}
        <button
          type="button"
          onClick={handleGuest}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-graphite/60 border border-slate/40 text-mist hover:text-cloud hover:border-slate transition-colors disabled:opacity-50"
        >
          <UserCircle2 className="w-4 h-4" />
          Continue as guest
        </button>

        <p className="text-[11px] text-slate text-center mt-4 leading-relaxed">
          Guest mode skips authentication. Your data is isolated to this browser
          session and not shared across devices.
        </p>
      </motion.div>
    </div>
  );
}
