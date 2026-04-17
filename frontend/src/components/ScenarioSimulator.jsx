import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  PlayCircle,
  Loader2,
  Repeat,
  Route,
  Layers,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  DollarSign,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { runScenario } from '../utils/api';

/* ------------------------------------------------------------------ */
/*  Tokens                                                              */
/* ------------------------------------------------------------------ */

const SEVERITY = {
  Low: { label: 'Low', text: 'text-emerald-300', bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', fill: '#10b981' },
  Medium: { label: 'Medium', text: 'text-amber-300', bg: 'bg-amber-500/15', border: 'border-amber-500/40', fill: '#f59e0b' },
  High: { label: 'High', text: 'text-orange-300', bg: 'bg-orange-500/15', border: 'border-orange-500/40', fill: '#f97316' },
  Critical: { label: 'Critical', text: 'text-red-300', bg: 'bg-red-500/15', border: 'border-red-500/40', fill: '#ef4444' },
};

const VERDICT = {
  improved: {
    label: 'Improved',
    text: 'text-emerald-300',
    bg: 'bg-emerald-500/15',
    border: 'border-emerald-500/40',
    Icon: TrendingDown,
  },
  neutral: {
    label: 'Neutral',
    text: 'text-mist',
    bg: 'bg-slate/20',
    border: 'border-slate/50',
    Icon: Minus,
  },
  worsened: {
    label: 'Worsened',
    text: 'text-red-300',
    bg: 'bg-red-500/15',
    border: 'border-red-500/40',
    Icon: TrendingUp,
  },
};

const SCENARIO_TYPES = [
  {
    id: 'supplier_switch',
    label: 'Supplier Switch',
    tagline: 'Replace a supplier with one from another country',
    Icon: Repeat,
  },
  {
    id: 'route_change',
    label: 'Route Change',
    tagline: 'Reroute shipping through a different corridor',
    Icon: Route,
  },
  {
    id: 'inventory_buffer',
    label: 'Inventory Buffer',
    tagline: 'Hold extra safety stock for critical inputs',
    Icon: Layers,
  },
];

/* ------------------------------------------------------------------ */
/*  Severity badge                                                      */
/* ------------------------------------------------------------------ */

function SeverityBadge({ level }) {
  const s = SEVERITY[level] || SEVERITY.Medium;
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider border ${s.border} ${s.bg} ${s.text}`}
    >
      {s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Scenario type picker                                                */
/* ------------------------------------------------------------------ */

function ScenarioTypePicker({ value, onChange }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
      {SCENARIO_TYPES.map((t) => {
        const active = value === t.id;
        const TIcon = t.Icon;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            className={`text-left rounded-xl border px-3 py-2.5 transition-all ${
              active
                ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/10'
                : 'border-slate/40 bg-graphite/60 hover:border-slate'
            }`}
          >
            <div className="flex items-center gap-2">
              <TIcon className={`h-4 w-4 ${active ? 'text-accent-glow' : 'text-mist'}`} />
              <span className={`text-xs font-semibold ${active ? 'text-snow' : 'text-cloud'}`}>
                {t.label}
              </span>
            </div>
            <div className="mt-1 text-[10px] text-slate leading-snug">{t.tagline}</div>
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Parameter forms (one per scenario type)                             */
/* ------------------------------------------------------------------ */

function FormField({ label, children }) {
  return (
    <label className="block space-y-1">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-mist">
        {label}
      </span>
      {children}
    </label>
  );
}

const inputClass =
  'w-full rounded-lg border border-slate/40 bg-carbon/80 px-3 py-2 text-xs text-cloud placeholder:text-slate focus:border-accent-primary/60 focus:outline-none focus:ring-1 focus:ring-accent-primary/40';

function SupplierSwitchForm({ params, setParams, supplierOptions }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <FormField label="Supplier to replace">
        {supplierOptions.length > 0 ? (
          <select
            value={params.from_node || ''}
            onChange={(e) => setParams({ ...params, from_node: e.target.value })}
            className={inputClass}
          >
            <option value="">— Select a supplier —</option>
            {supplierOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        ) : (
          <input
            type="text"
            value={params.from_node || ''}
            onChange={(e) => setParams({ ...params, from_node: e.target.value })}
            placeholder="e.g. Taiwan Semiconductors"
            className={inputClass}
          />
        )}
      </FormField>
      <FormField label="Replacement country">
        <input
          type="text"
          value={params.to_country || ''}
          onChange={(e) => setParams({ ...params, to_country: e.target.value })}
          placeholder="e.g. South Korea, India, Mexico"
          className={inputClass}
        />
      </FormField>
    </div>
  );
}

function RouteChangeForm({ params, setParams }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <FormField label="Current route">
        <input
          type="text"
          value={params.from_route || ''}
          onChange={(e) => setParams({ ...params, from_route: e.target.value })}
          placeholder="e.g. Suez Canal"
          className={inputClass}
        />
      </FormField>
      <FormField label="New route">
        <input
          type="text"
          value={params.to_route || ''}
          onChange={(e) => setParams({ ...params, to_route: e.target.value })}
          placeholder="e.g. Cape of Good Hope"
          className={inputClass}
          list="route-suggestions"
        />
        <datalist id="route-suggestions">
          <option value="Cape of Good Hope" />
          <option value="Trans-Pacific" />
          <option value="Northern Sea Route" />
          <option value="Air Freight" />
          <option value="Trans-Siberian Rail" />
        </datalist>
      </FormField>
    </div>
  );
}

function InventoryBufferForm({ params, setParams }) {
  return (
    <FormField label="Additional buffer (days)">
      <input
        type="number"
        min={1}
        max={365}
        value={params.buffer_days || 30}
        onChange={(e) => setParams({ ...params, buffer_days: Number(e.target.value) })}
        className={inputClass}
      />
    </FormField>
  );
}

/* ------------------------------------------------------------------ */
/*  Result rendering                                                    */
/* ------------------------------------------------------------------ */

function TradeoffChip({ Icon, label, value }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-slate/40 bg-carbon/60 px-3 py-2">
      <Icon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-accent-glow" />
      <div className="min-w-0">
        <div className="text-[9px] font-semibold uppercase tracking-wider text-slate">{label}</div>
        <div className="text-[11px] text-cloud">{value}</div>
      </div>
    </div>
  );
}

function SnapshotColumn({ title, snapshot, tone }) {
  if (!snapshot) return null;
  const sev = SEVERITY[snapshot.overall_risk_level] || SEVERITY.Medium;
  return (
    <div className="flex-1 rounded-xl border border-slate/40 bg-carbon/40 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate">{title}</div>
        <span
          className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${sev.border} ${sev.bg} ${sev.text}`}
        >
          {sev.label}
        </span>
      </div>
      <div className="space-y-1.5">
        {(snapshot.affected_nodes || []).length === 0 && (
          <div className="text-[11px] text-mist italic">No specific nodes affected.</div>
        )}
        {(snapshot.affected_nodes || []).map((n, i) => (
          <div
            key={i}
            className="rounded-lg border border-slate/30 bg-graphite/60 px-2.5 py-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-snow truncate">{n.node}</span>
              <SeverityBadge level={n.risk_level} />
            </div>
            {n.delta_explanation && (
              <p className="mt-1 text-[10px] leading-snug text-mist">{n.delta_explanation}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioResultPanel({ result }) {
  if (!result) return null;
  const v = VERDICT[result.verdict] || VERDICT.neutral;
  const VIcon = v.Icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-3 rounded-xl border border-slate/40 bg-graphite/70 p-4"
    >
      {/* Header: verdict + label */}
      <div className="flex flex-wrap items-center gap-2">
        <div
          className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${v.border} ${v.bg} ${v.text}`}
        >
          <VIcon className="h-3 w-3" />
          {v.label}
        </div>
        <div className="text-xs font-semibold text-snow">{result.scenario_label}</div>
      </div>

      {/* Tradeoffs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <TradeoffChip Icon={Clock} label="Latency" value={result.tradeoffs?.latency || 'Unchanged'} />
        <TradeoffChip Icon={DollarSign} label="Cost" value={result.tradeoffs?.cost || 'Unchanged'} />
        <TradeoffChip Icon={ShieldAlert} label="Risk" value={result.tradeoffs?.risk || 'Unchanged'} />
      </div>

      {/* Narrative */}
      {result.narrative && (
        <p className="text-xs leading-relaxed text-cloud">{result.narrative}</p>
      )}

      {/* Before / After columns */}
      <div className="flex flex-col sm:flex-row items-stretch gap-2">
        <SnapshotColumn title="Before" snapshot={result.before} />
        <div className="flex items-center justify-center px-1 text-mist">
          <ArrowRight className="hidden sm:block h-4 w-4" />
        </div>
        <SnapshotColumn title="After" snapshot={result.after} />
      </div>

      {/* Provider chip */}
      {result.provider_meta && (
        <div className="flex items-center gap-2 border-t border-slate/30 pt-2 text-[10px] uppercase tracking-widest text-slate">
          <span>AI Engine: {result.provider_meta.provider_used}</span>
          {result.provider_meta.is_mock && (
            <span className="rounded bg-amber-500/20 px-1 text-amber-400 font-bold">
              Demo Mode
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main export                                                         */
/* ------------------------------------------------------------------ */

export default function ScenarioSimulator({ analysis, sessionId }) {
  const [scenarioType, setScenarioType] = useState('supplier_switch');
  const [params, setParams] = useState({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Pre-populate the supplier dropdown from the graph's supplier nodes
  const supplierOptions = useMemo(() => {
    const nodes = analysis?.supply_chain_graph?.nodes || [];
    return nodes
      .filter((n) => n.role === 'supplier' || n.role === 'factory')
      .map((n) => n.label);
  }, [analysis]);

  const canRun = !!sessionId && !running;

  const handleRun = async () => {
    if (!sessionId) {
      setError('Run an analysis first to enable scenarios.');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const res = await runScenario(sessionId, scenarioType, params);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Scenario simulation failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Type picker */}
      <div className="space-y-1.5">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate">
          Scenario type
        </div>
        <ScenarioTypePicker value={scenarioType} onChange={(t) => { setScenarioType(t); setParams({}); setResult(null); setError(null); }} />
      </div>

      {/* Parameter form */}
      <div className="rounded-xl border border-slate/40 bg-graphite/60 p-3 space-y-3">
        {scenarioType === 'supplier_switch' && (
          <SupplierSwitchForm
            params={params}
            setParams={setParams}
            supplierOptions={supplierOptions}
          />
        )}
        {scenarioType === 'route_change' && (
          <RouteChangeForm params={params} setParams={setParams} />
        )}
        {scenarioType === 'inventory_buffer' && (
          <InventoryBufferForm params={params} setParams={setParams} />
        )}

        <button
          type="button"
          onClick={handleRun}
          disabled={!canRun}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-primary px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Running scenario…
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4" />
              Run scenario
            </>
          )}
        </button>

        {error && (
          <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-[11px] text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Result */}
      {result && <ScenarioResultPanel result={result} />}
    </div>
  );
}
