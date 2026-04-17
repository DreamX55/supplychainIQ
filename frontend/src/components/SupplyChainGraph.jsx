import React, { useMemo, useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Factory,
  Anchor,
  MapPin,
  Package,
  Globe,
  Cloud,
  Truck,
  AlertTriangle,
  CheckCircle2,
  X,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Tokens                                                              */
/* ------------------------------------------------------------------ */

const SEVERITY_FILL = {
  Low: '#10b981',
  Medium: '#f59e0b',
  High: '#f97316',
  Critical: '#ef4444',
};

const SEVERITY_RANK = { Low: 1, Medium: 2, High: 3, Critical: 4 };

const NEUTRAL_FILL = '#3a3a48';

const ROLE_ORDER = ['supplier', 'factory', 'port', 'destination'];

const ROLE_META = {
  supplier: { label: 'Suppliers', Icon: Package },
  factory: { label: 'Factories', Icon: Factory },
  port: { label: 'Ports & Transit', Icon: Anchor },
  destination: { label: 'Destinations', Icon: MapPin },
  other: { label: 'Other', Icon: MapPin },
};

const CATEGORY_ICONS = {
  geopolitical: Globe,
  climate: Cloud,
  logistics: Truck,
  supplier: Factory,
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

function linkRisksToNode(node, riskNodes) {
  if (!Array.isArray(riskNodes)) return [];
  const label = (node.label || '').toLowerCase();
  const loc = (node.location || '').toLowerCase();
  if (!label && !loc) return [];

  return riskNodes.filter((r) => {
    const target = (r.node || '').toLowerCase();
    if (!target) return false;
    return (
      (label && (target.includes(label) || label.includes(target))) ||
      (loc && target.includes(loc))
    );
  });
}

function pickPeakSeverity(risks) {
  let peak = null;
  for (const r of risks) {
    if (!peak || (SEVERITY_RANK[r.risk_level] || 0) > (SEVERITY_RANK[peak] || 0)) {
      peak = r.risk_level;
    }
  }
  return peak;
}

/* ------------------------------------------------------------------ */
/*  Layout math                                                         */
/* ------------------------------------------------------------------ */

const VIEWBOX_W = 720;
const VIEWBOX_H = 420;
const NODE_W = 150;
const NODE_H = 56;
const COL_PAD_X = 60;

function computeLayout(nodes) {
  const byRole = {};
  for (const n of nodes) {
    const r = ROLE_ORDER.includes(n.role) ? n.role : 'other';
    if (!byRole[r]) byRole[r] = [];
    byRole[r].push(n);
  }

  const activeRoles = ROLE_ORDER.filter((r) => byRole[r] && byRole[r].length > 0);
  if (activeRoles.length === 0 && byRole.other) {
    activeRoles.push('other');
  } else if (byRole.other) {
    activeRoles.push('other');
  }

  if (activeRoles.length === 0) return { positions: {}, columns: [] };

  const usableW = VIEWBOX_W - COL_PAD_X * 2;
  const colSpacing = activeRoles.length === 1 ? 0 : usableW / (activeRoles.length - 1);

  const positions = {};
  const columns = [];

  activeRoles.forEach((role, colIdx) => {
    const colNodes = byRole[role];
    const cx =
      activeRoles.length === 1
        ? VIEWBOX_W / 2
        : COL_PAD_X + colIdx * colSpacing;

    const rowHeight = NODE_H + 26;
    const totalH = colNodes.length * rowHeight - 26;
    const startY = (VIEWBOX_H - totalH) / 2;

    colNodes.forEach((n, rowIdx) => {
      const cy = startY + rowIdx * rowHeight + NODE_H / 2;
      positions[n.id] = { cx, cy };
    });

    columns.push({ role, x: cx });
  });

  return { positions, columns };
}

/* ------------------------------------------------------------------ */
/*  SVG primitives                                                      */
/* ------------------------------------------------------------------ */

function NodeShape({ node, pos, fill, isSelected, isHovered, onClick, onEnter, onLeave }) {
  const stroke = isSelected ? '#60a5fa' : isHovered ? '#8888a0' : 'rgba(58,58,72,0.8)';
  const strokeWidth = isSelected ? 2 : 1;
  const x = pos.cx - NODE_W / 2;
  const y = pos.cy - NODE_H / 2;

  return (
    <g
      style={{ cursor: 'pointer' }}
      onClick={() => onClick(node.id)}
      onMouseEnter={() => onEnter(node.id)}
      onMouseLeave={() => onLeave()}
    >
      {/* Halo */}
      {(isSelected || isHovered) && (
        <rect
          x={x - 4}
          y={y - 4}
          width={NODE_W + 8}
          height={NODE_H + 8}
          rx={12}
          fill={fill}
          fillOpacity={0.18}
        />
      )}

      {/* Card */}
      <rect
        x={x}
        y={y}
        width={NODE_W}
        height={NODE_H}
        rx={10}
        fill="#12121a"
        stroke={stroke}
        strokeWidth={strokeWidth}
      />

      {/* Severity color rail on left edge */}
      <rect x={x} y={y} width={4} height={NODE_H} rx={2} fill={fill} />

      {/* Label */}
      <text
        x={pos.cx}
        y={pos.cy - 4}
        textAnchor="middle"
        fontSize={12}
        fontWeight={600}
        fill="#f0f0f8"
        style={{ pointerEvents: 'none' }}
      >
        {truncate(node.label, 22)}
      </text>
      {/* Location subtitle */}
      {node.location && (
        <text
          x={pos.cx}
          y={pos.cy + 12}
          textAnchor="middle"
          fontSize={9}
          fill="#8888a0"
          style={{ pointerEvents: 'none', textTransform: 'uppercase', letterSpacing: '0.1em' }}
        >
          {truncate(node.location, 24)}
        </text>
      )}
    </g>
  );
}

function truncate(text, max) {
  if (!text) return '';
  return text.length > max ? text.slice(0, max - 1) + '…' : text;
}

function EdgePath({ from, to, highlighted }) {
  const x1 = from.cx + NODE_W / 2;
  const y1 = from.cy;
  const x2 = to.cx - NODE_W / 2;
  const y2 = to.cy;
  const midX = (x1 + x2) / 2;
  const d = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;

  return (
    <path
      d={d}
      fill="none"
      stroke={highlighted ? '#60a5fa' : '#3a3a48'}
      strokeWidth={highlighted ? 2 : 1.4}
      strokeOpacity={highlighted ? 0.95 : 0.6}
      markerEnd="url(#arrowhead)"
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Detail panel                                                        */
/* ------------------------------------------------------------------ */

function NodeDetailPanel({ node, risks, onClose }) {
  if (!node) return null;
  const RoleIcon = ROLE_META[node.role]?.Icon || MapPin;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-xl border border-slate/40 bg-graphite/70 p-4"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-primary/15 text-accent-glow">
            <RoleIcon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-snow truncate">{node.label}</div>
            <div className="text-[10px] uppercase tracking-wider text-slate">
              {ROLE_META[node.role]?.label || node.role}
              {node.location ? ` · ${node.location}` : ''}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-mist hover:bg-carbon hover:text-cloud transition-colors"
          aria-label="Close detail"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {risks.length === 0 && (
        <div className="rounded-lg border border-slate/30 bg-carbon/60 p-3 text-[11px] text-mist">
          No specific risks linked to this node in the current analysis.
        </div>
      )}

      <div className="space-y-2">
        {risks.map((r, i) => {
          const fill = SEVERITY_FILL[r.risk_level] || NEUTRAL_FILL;
          const CatIcon = CATEGORY_ICONS[r.category] || AlertTriangle;
          return (
            <div
              key={i}
              className="relative overflow-hidden rounded-lg border border-slate/30 bg-carbon/60 pl-3 pr-3 py-2.5"
            >
              <div
                className="absolute left-0 top-0 bottom-0 w-[3px]"
                style={{ backgroundColor: fill }}
              />
              <div className="flex items-start gap-2">
                <CatIcon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" style={{ color: fill }} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs font-semibold text-snow truncate">{r.node}</div>
                    <span
                      className="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                      style={{ color: fill, backgroundColor: `${fill}22` }}
                    >
                      {r.risk_level}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-snug text-cloud">{r.cause}</p>
                  <div className="mt-2 flex items-start gap-1.5 text-[11px] text-accent-glow/90">
                    <CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0" />
                    <span className="text-cloud">{r.recommended_action}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main export                                                         */
/* ------------------------------------------------------------------ */

export default function SupplyChainGraph({ analysis }) {
  const graph = analysis?.supply_chain_graph;
  const riskNodes = analysis?.risk_nodes || [];

  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];

  // Auto-select the highest-severity node on first render
  const defaultSelected = useMemo(() => {
    if (nodes.length === 0) return null;
    let best = null;
    let bestRank = -1;
    for (const n of nodes) {
      const linked = linkRisksToNode(n, riskNodes);
      const peak = pickPeakSeverity(linked);
      const rank = peak ? SEVERITY_RANK[peak] || 0 : 0;
      if (rank > bestRank) {
        bestRank = rank;
        best = n.id;
      }
    }
    return best || nodes[0].id;
  }, [nodes, riskNodes]);

  const [selectedId, setSelectedId] = useState(defaultSelected);
  const [hoveredId, setHoveredId] = useState(null);

  // Re-sync auto-selection if the analysis changes (e.g. on history switch)
  React.useEffect(() => {
    setSelectedId(defaultSelected);
  }, [defaultSelected]);

  const { positions } = useMemo(() => computeLayout(nodes), [nodes]);

  const nodeFill = useMemo(() => {
    const map = {};
    for (const n of nodes) {
      const linked = linkRisksToNode(n, riskNodes);
      const peak = pickPeakSeverity(linked);
      map[n.id] = peak ? SEVERITY_FILL[peak] : NEUTRAL_FILL;
    }
    return map;
  }, [nodes, riskNodes]);

  /* ---- Canvas pan + zoom state ---- */
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const ZOOM_STEP = 0.2;
  const ZOOM_MIN = 0.4;
  const ZOOM_MAX = 2.5;

  const panRef = useRef(null);
  const svgRef = useRef(null);
  const isPanning = useRef(false);
  // Keep zoom in a ref so mousemove handler always reads latest value
  const zoomRef = useRef(zoom);
  React.useEffect(() => { zoomRef.current = zoom; }, [zoom]);

  const handleBgMouseDown = useCallback((e) => {
    if (e.target !== svgRef.current && e.target.dataset.bg !== 'true') return;
    isPanning.current = true;
    panRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      originPanX: pan.x,
      originPanY: pan.y,
    };
    e.preventDefault();
  }, [pan]);

  const handleMouseMove = useCallback((e) => {
    if (!isPanning.current || !panRef.current) return;
    const dx = e.clientX - panRef.current.startX;
    const dy = e.clientY - panRef.current.startY;
    const svg = svgRef.current;
    // Scale pixel delta to SVG coordinate space, corrected for current zoom
    const svgScale = svg ? VIEWBOX_W / svg.getBoundingClientRect().width : 1;
    const effectiveScale = svgScale / zoomRef.current;
    setPan({
      x: panRef.current.originPanX + dx * effectiveScale,
      y: panRef.current.originPanY + dy * effectiveScale,
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    isPanning.current = false;
    panRef.current = null;
  }, []);

  const zoomIn = useCallback(() => {
    setZoom((z) => Math.min(ZOOM_MAX, parseFloat((z + ZOOM_STEP).toFixed(2))));
  }, []);

  const zoomOut = useCallback(() => {
    setZoom((z) => Math.max(ZOOM_MIN, parseFloat((z - ZOOM_STEP).toFixed(2))));
  }, []);

  const resetView = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-slate/40 bg-graphite/60 p-6 text-center text-xs text-mist">
        No supply chain graph available for this analysis.
      </div>
    );
  }

  const selectedNode = nodes.find((n) => n.id === selectedId) || null;
  const selectedRisks = selectedNode ? linkRisksToNode(selectedNode, riskNodes) : [];

  const cursor = isPanning.current ? 'grabbing' : 'grab';

  return (
    <div className="space-y-3">
      {/* SVG canvas */}
      <div className="rounded-xl border border-slate/40 bg-gradient-to-br from-graphite/80 to-carbon/80 p-3">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-2">
          {/* Zoom controls */}
          <div className="inline-flex items-center rounded-lg border border-slate/40 bg-carbon/60 overflow-hidden">
            <button
              type="button"
              onClick={zoomOut}
              disabled={zoom <= ZOOM_MIN}
              title="Zoom out"
              className="flex items-center justify-center px-2.5 py-1.5 text-mist hover:text-cloud hover:bg-graphite/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <div className="min-w-[3.5rem] text-center text-[11px] font-mono font-semibold text-cloud border-x border-slate/40 py-1.5 select-none">
              {Math.round(zoom * 100)}%
            </div>
            <button
              type="button"
              onClick={zoomIn}
              disabled={zoom >= ZOOM_MAX}
              title="Zoom in"
              className="flex items-center justify-center px-2.5 py-1.5 text-mist hover:text-cloud hover:bg-graphite/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Reset button */}
          <button
            type="button"
            onClick={resetView}
            title="Reset view"
            className="flex items-center gap-1.5 rounded-lg border border-slate/40 bg-carbon/60 px-2.5 py-1 text-[11px] font-medium text-mist hover:text-cloud hover:border-slate/70 transition-colors"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </button>
        </div>

        <svg
          ref={svgRef}
          viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
          width="100%"
          preserveAspectRatio="xMidYMid meet"
          className="block"
          style={{ cursor }}
          onMouseDown={handleBgMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path d="M 0 0 L 8 4 L 0 8 z" fill="#3a3a48" />
            </marker>
            <pattern
              id="grid"
              width="40"
              height="40"
              patternUnits="userSpaceOnUse"
              x={pan.x % 40}
              y={pan.y % 40}
            >
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(59,130,246,0.05)"
                strokeWidth="1"
              />
            </pattern>
          </defs>

          {/* Background — marks itself as bg so pan can detect it */}
          <rect
            width={VIEWBOX_W}
            height={VIEWBOX_H}
            fill="url(#grid)"
            data-bg="true"
          />

          {/* Pannable + zoomable content group — scale from canvas center */}
          <g transform={`translate(${VIEWBOX_W / 2 + pan.x}, ${VIEWBOX_H / 2 + pan.y}) scale(${zoom}) translate(${-VIEWBOX_W / 2}, ${-VIEWBOX_H / 2})`}>
            {/* Edges */}
            {edges.map((e, i) => {
              const src = positions[e.from || e.source];
              const tgt = positions[e.to || e.target];
              if (!src || !tgt) return null;
              const highlighted =
                hoveredId === (e.from || e.source) ||
                hoveredId === (e.to || e.target) ||
                selectedId === (e.from || e.source) ||
                selectedId === (e.to || e.target);
              return <EdgePath key={i} from={src} to={tgt} highlighted={highlighted} />;
            })}

            {/* Nodes */}
            {nodes.map((n) => {
              const pos = positions[n.id];
              if (!pos) return null;
              return (
                <NodeShape
                  key={n.id}
                  node={n}
                  pos={pos}
                  fill={nodeFill[n.id] || NEUTRAL_FILL}
                  isSelected={n.id === selectedId}
                  isHovered={n.id === hoveredId}
                  onClick={setSelectedId}
                  onEnter={setHoveredId}
                  onLeave={() => setHoveredId(null)}
                />
              );
            })}
          </g>
        </svg>

        {/* Legend */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-[10px] text-mist">
          <span className="uppercase tracking-wider text-slate">Severity</span>
          {['Critical', 'High', 'Medium', 'Low'].map((lvl) => (
            <span key={lvl} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: SEVERITY_FILL[lvl] }}
              />
              <span className="text-cloud">{lvl}</span>
            </span>
          ))}
          <span className="ml-auto text-slate">
            Drag to pan · Scroll +/− to zoom · Click node for risks · {nodes.length} nodes · {edges.length} edges
          </span>
        </div>
      </div>

      {/* Detail panel */}
      <NodeDetailPanel
        node={selectedNode}
        risks={selectedRisks}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
