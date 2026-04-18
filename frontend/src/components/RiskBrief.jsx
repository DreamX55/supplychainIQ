import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Globe,
  Cloud,
  Truck,
  Factory,
  CheckCircle2,
  FileText,
  Sparkles,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Tokens                                                             */
/* ------------------------------------------------------------------ */

const SEVERITY = {
  Low: {
    label: 'Low',
    rail: 'bg-emerald-500',
    badgeBg: 'bg-emerald-500/15',
    badgeText: 'text-emerald-300',
    badgeBorder: 'border-emerald-500/40',
    fill: '#10b981',
    icon: ShieldCheck,
    rank: 1,
  },
  Medium: {
    label: 'Medium',
    rail: 'bg-amber-500',
    badgeBg: 'bg-amber-500/15',
    badgeText: 'text-amber-300',
    badgeBorder: 'border-amber-500/40',
    fill: '#f59e0b',
    icon: AlertTriangle,
    rank: 2,
  },
  High: {
    label: 'High',
    rail: 'bg-orange-500',
    badgeBg: 'bg-orange-500/15',
    badgeText: 'text-orange-300',
    badgeBorder: 'border-orange-500/40',
    fill: '#f97316',
    icon: AlertTriangle,
    rank: 3,
  },
  Critical: {
    label: 'Critical',
    rail: 'bg-red-500',
    badgeBg: 'bg-red-500/15',
    badgeText: 'text-red-300',
    badgeBorder: 'border-red-500/40',
    fill: '#ef4444',
    icon: ShieldAlert,
    rank: 4,
  },
};

const CATEGORY_ICONS = {
  geopolitical: Globe,
  climate: Cloud,
  logistics: Truck,
  supplier: Factory,
};

const SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low'];

/* ------------------------------------------------------------------ */
/*  Hero strip — overall risk + summary + stats                         */
/* ------------------------------------------------------------------ */

function HeroStrip({ overall, summary, stats }) {
  const sev = SEVERITY[overall] || SEVERITY.Medium;
  const SevIcon = sev.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl border border-slate/40 bg-gradient-to-br from-graphite/80 to-carbon/80 p-5"
    >
      {/* soft severity glow in the corner */}
      <div
        className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full blur-3xl opacity-20"
        style={{ backgroundColor: sev.fill }}
      />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center">
        {/* Severity pill */}
        <div
          className={`flex items-center gap-3 self-start rounded-xl border ${sev.badgeBorder} ${sev.badgeBg} px-4 py-3`}
        >
          <SevIcon className={`h-6 w-6 ${sev.badgeText}`} />
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-mist">
              Overall Risk
            </div>
            <div className={`text-xl font-bold leading-tight ${sev.badgeText}`}>
              {sev.label}
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="flex-1">
          <p className="text-sm leading-relaxed text-cloud">{summary}</p>
        </div>
      </div>

      {/* Stat row */}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate/30 pt-3 text-[11px] text-mist">
        <Stat label="Risks identified" value={stats.total} />
        <Stat label="Highest severity" value={stats.peak} accent={SEVERITY[stats.peak]?.badgeText} />
        <Stat
          label="Avg confidence"
          value={`${Math.round(stats.avgConfidence * 100)}%`}
        />
        <Stat label="Categories covered" value={stats.categories} />
      </div>
    </motion.div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="uppercase tracking-wider text-slate">{label}</span>
      <span className={`font-semibold ${accent || 'text-cloud'}`}>{value}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Severity breakdown — horizontal pill bar                            */
/* ------------------------------------------------------------------ */

function SeverityBar({ counts }) {
  return (
    <div className="flex flex-wrap gap-2">
      {SEVERITY_ORDER.map((level) => {
        const count = counts[level] || 0;
        if (count === 0) return null;
        const sev = SEVERITY[level];
        return (
          <div
            key={level}
            className={`flex items-center gap-1.5 rounded-full border ${sev.badgeBorder} ${sev.badgeBg} px-2.5 py-1`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${sev.rail}`} />
            <span className={`text-[10px] font-semibold uppercase tracking-wider ${sev.badgeText}`}>
              {sev.label}
            </span>
            <span className="text-[10px] text-cloud">×{count}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-node risk card                                                  */
/* ------------------------------------------------------------------ */

function RiskCard({ node, index }) {
  const sev = SEVERITY[node.risk_level] || SEVERITY.Medium;
  const CategoryIcon = CATEGORY_ICONS[node.category] || AlertTriangle;
  const evidence = Array.isArray(node.evidence) ? node.evidence.filter(Boolean) : [];
  const confidence = Math.round((node.confidence_score || 0) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06 }}
      className="relative overflow-hidden rounded-xl border border-slate/40 bg-graphite/60 backdrop-blur-sm"
    >
      {/* Severity color rail on the left */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${sev.rail}`} />

      <div className="pl-4 pr-4 py-4 space-y-3">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`flex h-7 w-7 items-center justify-center rounded-md ${sev.badgeBg}`}>
              <CategoryIcon className={`h-3.5 w-3.5 ${sev.badgeText}`} />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-semibold text-snow truncate">{node.node}</h4>
              <div className="text-[10px] uppercase tracking-wider text-slate">
                {node.category}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div
              className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${sev.badgeBorder} ${sev.badgeBg} ${sev.badgeText}`}
            >
              {sev.label}
            </div>
          </div>
        </div>

        {/* Cause */}
        <p className="text-xs leading-relaxed text-cloud">{node.cause}</p>

        {/* Confidence bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[10px]">
            <span className="uppercase tracking-wider text-slate">Confidence</span>
            <span className={sev.badgeText}>{confidence}%</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-carbon">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${confidence}%` }}
              transition={{ duration: 0.6, delay: index * 0.06 + 0.2 }}
              className="h-full rounded-full"
              style={{ backgroundColor: sev.fill }}
            />
          </div>
        </div>

        {/* Evidence card */}
        {evidence.length > 0 && (
          <div className="rounded-lg border border-slate/30 bg-carbon/60 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-mist">
              <FileText className="h-3 w-3" />
              Grounded in
            </div>
            <ul className="space-y-1">
              {evidence.slice(0, 3).map((bullet, i) => (
                <li key={i} className="flex gap-2 text-[11px] leading-snug text-cloud">
                  <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-accent-glow/70" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Mitigation */}
        <div className="rounded-lg border border-accent-primary/30 bg-accent-primary/10 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-accent-glow">
            <CheckCircle2 className="h-3 w-3" />
            Recommended action
          </div>
          <p className="text-[12px] leading-relaxed text-cloud">{node.recommended_action}</p>
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main export                                                         */
/* ------------------------------------------------------------------ */

export default function RiskBrief({ analysis }) {
  const nodes = Array.isArray(analysis?.risk_nodes) ? analysis.risk_nodes : [];

  // Sort risks by severity (Critical first), preserving original order within a severity
  const sortedNodes = useMemo(() => {
    return [...nodes].sort((a, b) => {
      const ra = SEVERITY[b.risk_level]?.rank || 0;
      const rb = SEVERITY[a.risk_level]?.rank || 0;
      return ra - rb;
    });
  }, [nodes]);

  // Stats for the hero strip
  const stats = useMemo(() => {
    const counts = {};
    let confidenceSum = 0;
    const cats = new Set();
    let peak = 'Low';

    nodes.forEach((n) => {
      counts[n.risk_level] = (counts[n.risk_level] || 0) + 1;
      confidenceSum += n.confidence_score || 0;
      if (n.category) cats.add(n.category);
      if ((SEVERITY[n.risk_level]?.rank || 0) > (SEVERITY[peak]?.rank || 0)) {
        peak = n.risk_level;
      }
    });

    return {
      total: nodes.length,
      avgConfidence: confidenceSum / Math.max(1, nodes.length),
      categories: cats.size,
      peak,
      counts,
    };
  }, [nodes]);

  if (nodes.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Section label */}
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent-glow">
        <Sparkles className="h-3 w-3" />
        Risk Brief
      </div>

      <HeroStrip
        overall={analysis.overall_risk_level || stats.peak}
        summary={analysis.summary || ''}
        stats={stats}
      />

      <SeverityBar counts={stats.counts} />

      <div className="space-y-3">
        {sortedNodes.map((node, i) => (
          <RiskCard key={`${node.node}-${i}`} node={node} index={i} />
        ))}
      </div>
    </div>
  );
}
