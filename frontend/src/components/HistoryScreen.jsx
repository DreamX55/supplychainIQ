import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Archive, ArrowRight, ShieldAlert } from 'lucide-react';
import { getUserSessions } from '../utils/api';

export default function HistoryScreen({ onSelectSession }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUserSessions()
      .then(data => {
        setSessions(data.sessions || []);
      })
      .catch(err => {
        console.error(err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const getRiskColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'low': return 'text-emerald-400 border-emerald-400/20 bg-emerald-400/10';
      case 'medium': return 'text-amber-400 border-amber-400/20 bg-amber-400/10';
      case 'high': return 'text-orange-400 border-orange-400/20 bg-orange-400/10';
      case 'critical': return 'text-red-400 border-red-400/20 bg-red-400/10';
      default: return 'text-slate-400 border-slate-400/20 bg-slate-400/10';
    }
  };

  return (
    <div className="flex h-full flex-col bg-slate-950 p-6 overflow-y-auto">
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400">
          <Archive size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Vault</h1>
          <p className="text-sm text-slate-400">Your past supply chain risk analyses.</p>
        </div>
      </div>

      {loading ? (
        <div className="text-slate-500">Loading sessions...</div>
      ) : sessions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-12 text-center text-slate-500">
          <ShieldAlert className="mx-auto mb-4 h-12 w-12 opacity-50" />
          <p>No past analyses found. Start a new risk assessment to see your history.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session, i) => (
            <motion.div
              key={session.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onSelectSession(session.id)}
              className="group cursor-pointer rounded-xl border border-slate-800 bg-slate-900 p-5 transition-all hover:border-slate-700 hover:bg-slate-800/80"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${getRiskColor(session.overall_risk_level)}`}>
                  {session.overall_risk_level || 'Pending'} Risk
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(session.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="mb-4 line-clamp-3 text-sm text-slate-300">
                {session.description || 'Uploaded Document'}
              </p>
              <div className="flex items-center text-sm font-medium text-blue-400 opacity-0 transition-opacity group-hover:opacity-100">
                View Analysis <ArrowRight size={16} className="ml-1" />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
