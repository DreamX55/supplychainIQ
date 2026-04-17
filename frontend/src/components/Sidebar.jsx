import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Radio,
  Globe,
  Cloud,
  Truck,
  Factory,
  Loader2,
  TrendingUp,
  ExternalLink,
} from 'lucide-react';
import { getAlerts } from '../utils/api';

const SEVERITY = {
  Low: { label: 'Low', text: 'text-emerald-300', bg: 'bg-emerald-500/15', dot: 'bg-emerald-500' },
  Medium: { label: 'Medium', text: 'text-amber-300', bg: 'bg-amber-500/15', dot: 'bg-amber-500' },
  High: { label: 'High', text: 'text-orange-300', bg: 'bg-orange-500/15', dot: 'bg-orange-500' },
  Critical: { label: 'Critical', text: 'text-red-300', bg: 'bg-red-500/15', dot: 'bg-red-500' },
};

const CATEGORY_ICONS = {
  geopolitical: Globe,
  climate: Cloud,
  logistics: Truck,
  supplier: Factory,
};

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const then = new Date(dateStr);
  if (isNaN(then.getTime())) return dateStr;
  const diffMs = Date.now() - then.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days < 1) return 'today';
  if (days === 1) return '1d ago';
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function AlertItem({ alert, index }) {
  const sev = SEVERITY[alert.risk_level] || SEVERITY.Medium;
  const CatIcon = CATEGORY_ICONS[alert.category] || Globe;
  const hasLink = !!alert.link;

  const inner = (
    <div className="flex items-start gap-2">
      <span className={`mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full ${sev.dot}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-1.5">
          <span className="text-[11px] font-semibold leading-tight text-cloud line-clamp-2">
            {alert.title}
          </span>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className={`rounded px-1 py-0.5 text-[8px] font-bold uppercase ${sev.bg} ${sev.text}`}>
              {sev.label}
            </span>
            {hasLink && (
              <ExternalLink className="h-2.5 w-2.5 text-slate opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </div>
        </div>
        <div className="mt-1 flex items-center gap-1.5 text-[9px] text-slate">
          <CatIcon className="h-2.5 w-2.5" />
          <span>{alert.region}</span>
          <span className="text-slate/60">·</span>
          <span>{timeAgo(alert.last_updated)}</span>
        </div>
      </div>
    </div>
  );

  const sharedClass = `group rounded-lg border border-slate/30 bg-graphite/50 p-2.5 transition-colors ${
    hasLink ? 'hover:border-accent-primary/50 hover:bg-graphite/80 cursor-pointer' : ''
  }`;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
    >
      {hasLink ? (
        <a
          href={alert.link}
          target="_blank"
          rel="noopener noreferrer"
          className={`block ${sharedClass}`}
        >
          {inner}
        </a>
      ) : (
        <div className={sharedClass}>{inner}</div>
      )}
    </motion.div>
  );
}

function AlertFeed() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const data = await getAlerts(8);
        if (mounted) setAlerts(data.alerts || []);
      } catch (err) {
        // Silent — feed is non-critical
        console.warn('Alert feed failed:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    // Refresh every 60s for the "live" feel
    const interval = setInterval(load, 60000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Radio className="h-4 w-4 text-accent-primary" />
        <h3 className="text-sm font-semibold text-cloud">Intelligence Feed</h3>
        <span className="ml-auto flex items-center gap-1 text-[9px] uppercase tracking-wider text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          live
        </span>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-xs text-mist py-3">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading risk feed…
        </div>
      )}

      {!loading && alerts.length === 0 && (
        <div className="text-[11px] text-mist italic py-2">
          No active alerts in the demo dataset.
        </div>
      )}

      <div className="space-y-2">
        {alerts.map((a, i) => (
          <AlertItem key={a.id || i} alert={a} index={i} />
        ))}
      </div>
    </div>
  );
}

function AnalysisStats({ analysis }) {
  if (!analysis) return null;
  const overall = analysis.overall_risk_level;
  const overallClass =
    overall === 'Critical' ? 'text-red-400' :
    overall === 'High' ? 'text-orange-400' :
    overall === 'Medium' ? 'text-amber-400' :
    'text-emerald-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="h-4 w-4 text-accent-primary" />
        <h3 className="text-sm font-semibold text-cloud">Current Analysis</h3>
      </div>
      <div className="space-y-1.5 rounded-lg border border-slate/30 bg-graphite/50 p-2.5">
        <div className="flex justify-between text-xs">
          <span className="text-mist">Risk nodes</span>
          <span className="font-semibold text-cloud">{analysis.risk_nodes?.length || 0}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-mist">Regions</span>
          <span className="font-semibold text-cloud">
            {analysis.entities_detected?.regions?.length || 0}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-mist">Industries</span>
          <span className="font-semibold text-cloud">
            {analysis.entities_detected?.industries?.length || 0}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-mist">Overall</span>
          <span className={`font-semibold ${overallClass}`}>{overall || '—'}</span>
        </div>
        {analysis.entities_detected?.industries?.length > 0 && (
          <div className="border-t border-slate/20 pt-1.5 mt-1">
            <div className="flex flex-wrap gap-1">
              {analysis.entities_detected.industries.slice(0, 4).map((ind) => (
                <span
                  key={ind}
                  className="rounded-full border border-slate/40 bg-carbon/60 px-2 py-0.5 text-[9px] uppercase tracking-wider text-mist"
                >
                  {ind}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function RiskLegend() {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Shield className="h-3.5 w-3.5 text-mist" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-mist">Severity</h3>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {['Critical', 'High', 'Medium', 'Low'].map((lvl) => {
          const sev = SEVERITY[lvl];
          return (
            <div key={lvl} className="flex items-center gap-1.5">
              <div className={`h-2 w-2 rounded-full ${sev.dot}`} />
              <span className="text-[10px] text-cloud">{lvl}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Sidebar({ analysis }) {
  return (
    <aside className="w-64 border-r border-slate/30 bg-carbon/50 p-4 space-y-5 hidden lg:block overflow-y-auto">
      <AlertFeed />

      {analysis && <AnalysisStats analysis={analysis} />}

      <RiskLegend />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-lg bg-violet-500/10 border border-violet-500/20 p-3"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-300 mb-1">
          SDG 9 Aligned
        </p>
        <p className="text-[10px] leading-snug text-violet-200/70">
          Democratizing supply chain risk intelligence for SMEs.
        </p>
      </motion.div>
    </aside>
  );
}
