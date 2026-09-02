import React, { useState, useMemo } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, CheckCircle2, AlertTriangle, HelpCircle, Layers, Info } from 'lucide-react';

const TYPE_CONFIG = {
  merchant: { bg: '#8b5cf6', border: '#a78bfa', text: '#ffffff', label: 'Merchant' },
  order: { bg: '#2563eb', border: '#60a5fa', text: '#ffffff', label: 'Order' },
  payment: { bg: '#0284c7', border: '#38bdf8', text: '#ffffff', label: 'Payment' },
  refund: { bg: '#d97706', border: '#fbbf24', text: '#ffffff', label: 'Refund' },
  adjustment: { bg: '#db2777', border: '#f472b6', text: '#ffffff', label: 'Adjustment' },
  transfer: { bg: '#4f46e5', border: '#818cf8', text: '#ffffff', label: 'Transfer' },
  settlement_transaction: { bg: '#334155', border: '#64748b', text: '#e2e8f0', label: 'STXN' },
  settlement: { bg: '#059669', border: '#34d399', text: '#ffffff', label: 'Settlement' },
  bank_entry: { bg: '#0d9488', border: '#2dd4bf', text: '#ffffff', label: 'Bank Entry' },
};

const COLUMN_X = {
  merchant: 40,
  order: 190,
  payment: 360,
  refund: 360,
  adjustment: 360,
  transfer: 360,
  settlement_transaction: 540,
  settlement: 720,
  bank_entry: 900,
};

export default function FinancialGraphView({
  nodes = [],
  edges = [],
  onSelectNode,
  selectedNodeId,
}) {
  const [zoom, setZoom] = useState(0.92);
  const [pan, setPan] = useState({ x: 20, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  // Compute node coordinates deterministically by grouping into columns
  const layoutNodes = useMemo(() => {
    const colGroups = {
      merchant: [],
      order: [],
      payment_group: [],
      settlement_transaction: [],
      settlement: [],
      bank_entry: [],
    };

    if (!Array.isArray(nodes) || nodes.length === 0) return {};

    nodes.forEach((n) => {
      if (!n || !n.entity_type) return;
      if (['payment', 'refund', 'adjustment', 'transfer'].includes(n.entity_type)) {
        colGroups.payment_group.push(n);
      } else if (colGroups[n.entity_type]) {
        colGroups[n.entity_type].push(n);
      }
    });

    const result = {};
    const heightPerNode = 64;

    Object.entries(colGroups).forEach(([groupKey, groupNodes]) => {
      const totalH = groupNodes.length * heightPerNode;
      const startY = Math.max(40, 240 - totalH / 2);

      groupNodes.forEach((node, idx) => {
        const x = COLUMN_X[node.entity_type] || 360;
        const y = startY + idx * heightPerNode;
        result[node.node_id] = { ...node, x, y };
      });
    });

    return result;
  }, [nodes]);

  // Active node for lineage focus
  const activeNodeId = selectedNodeId || hoveredNodeId;

  // Compute directly connected nodes and edges
  const { connectedNodeIds, connectedEdgeIds } = useMemo(() => {
    if (!activeNodeId) return { connectedNodeIds: new Set(), connectedEdgeIds: new Set() };
    const nSet = new Set([activeNodeId]);
    const eSet = new Set();

    edges.forEach((e) => {
      if (e.source === activeNodeId) {
        eSet.add(e.edge_id);
        nSet.add(e.target);
      } else if (e.target === activeNodeId) {
        eSet.add(e.edge_id);
        nSet.add(e.source);
      }
    });

    return { connectedNodeIds: nSet, connectedEdgeIds: eSet };
  }, [activeNodeId, edges]);

  const selectedNodeObj = activeNodeId ? layoutNodes[activeNodeId] : null;

  const handleMouseDown = (e) => {
    if (e.target.tagName === 'svg' || e.target.tagName === 'g' || e.target.tagName === 'path') {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setZoom(0.92);
    setPan({ x: 20, y: 30 });
  };

  if (!nodes || nodes.length === 0) {
    return (
      <div className="graph-viewport-card" style={{ height: '100%', minHeight: '560px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', textAlign: 'center' }}>
        <Layers size={40} color="#64748b" style={{ marginBottom: '0.75rem' }} />
        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.35rem' }}>Financial Subgraph</div>
        <p style={{ fontSize: '0.85rem', color: '#64748b', maxWidth: '340px' }}>
          No graph entities or relationships recorded for this settlement.
        </p>
      </div>
    );
  }

  return (
    <div className="graph-viewport-card" style={{ height: '100%', minHeight: '560px', display: 'flex', flexDirection: 'column' }}>
      {/* Top Toolbar */}
      <div className="graph-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.01em' }}>
            Financial Relationship Graph
          </span>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }} className="mono">
            {nodes.length} nodes · {edges.length} edges
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <button
            className="nav-tab-btn"
            style={{ padding: '0.35rem 0.6rem' }}
            onClick={() => setZoom((z) => Math.min(z + 0.15, 2.0))}
            title="Zoom In"
          >
            <ZoomIn size={15} />
          </button>
          <button
            className="nav-tab-btn"
            style={{ padding: '0.35rem 0.6rem' }}
            onClick={() => setZoom((z) => Math.max(z - 0.15, 0.4))}
            title="Zoom Out"
          >
            <ZoomOut size={15} />
          </button>
          <button
            className="nav-tab-btn"
            style={{ padding: '0.35rem 0.6rem' }}
            onClick={resetView}
            title="Fit / Reset View"
          >
            <RotateCcw size={15} />
          </button>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <svg
          className="svg-graph-canvas"
          viewBox="0 0 1060 520"
          preserveAspectRatio="xMidYMid meet"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(148, 163, 184, 0.4)" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
            </marker>
          </defs>

          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Edges */}
            {edges.map((edge) => {
              const src = layoutNodes[edge.source];
              const tgt = layoutNodes[edge.target];
              if (!src || !tgt) return null;

              const isEdgeActive = connectedEdgeIds.has(edge.edge_id);
              const isDimmed = activeNodeId && !isEdgeActive;

              const startX = src.x + 120;
              const startY = src.y + 20;
              const endX = tgt.x;
              const endY = tgt.y + 20;
              const cX1 = startX + (endX - startX) * 0.5;
              const cX2 = startX + (endX - startX) * 0.5;
              const pathD = `M ${startX} ${startY} C ${cX1} ${startY}, ${cX2} ${endY}, ${endX} ${endY}`;

              return (
                <path
                  key={edge.edge_id}
                  d={pathD}
                  fill="none"
                  stroke={isEdgeActive ? '#38bdf8' : isDimmed ? 'rgba(148, 163, 184, 0.08)' : 'rgba(148, 163, 184, 0.28)'}
                  strokeWidth={isEdgeActive ? 2.5 : 1.2}
                  strokeDasharray={edge.relationship_type === 'AFFECTS_SETTLEMENT' ? '4 3' : undefined}
                  markerEnd={isEdgeActive ? 'url(#arrow-active)' : 'url(#arrow)'}
                  style={{ transition: 'all 0.2s ease' }}
                />
              );
            })}

            {/* Nodes */}
            {Object.values(layoutNodes).map((node) => {
              const isSelected = selectedNodeId === node.node_id;
              const isHovered = hoveredNodeId === node.node_id;
              const isConnected = connectedNodeIds.has(node.node_id);
              const isDimmed = activeNodeId && !isConnected && !isSelected;

              const typeConfig = TYPE_CONFIG[node.entity_type] || TYPE_CONFIG.settlement_transaction;
              const isException = node.status === 'EXCEPTION';

              const nodeBorder = isSelected
                ? '#38bdf8'
                : isException
                ? '#f43f5e'
                : isConnected
                ? typeConfig.border
                : isDimmed
                ? 'rgba(255,255,255,0.06)'
                : typeConfig.border;

              return (
                <g
                  key={node.node_id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => onSelectNode && onSelectNode(node)}
                  onMouseEnter={() => setHoveredNodeId(node.node_id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  style={{ cursor: 'pointer', opacity: isDimmed ? 0.35 : 1, transition: 'all 0.2s ease' }}
                >
                  {/* Node Box */}
                  <rect
                    width={120}
                    height={40}
                    rx={7}
                    fill={isSelected ? '#0c1a30' : '#0f172a'}
                    stroke={nodeBorder}
                    strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.2}
                    filter={isSelected ? 'drop-shadow(0 0 10px rgba(56, 189, 248, 0.4))' : undefined}
                  />

                  {/* Entity Type Label */}
                  <text
                    x={9}
                    y={14}
                    fill={typeConfig.border}
                    fontSize={8.5}
                    fontWeight={800}
                    letterSpacing="0.05em"
                    textTransform="uppercase"
                  >
                    {typeConfig.label}
                  </text>

                  {/* Status Indicator Icon */}
                  <circle
                    cx={109}
                    cy={13}
                    r={3.5}
                    fill={node.status === 'RECONCILED' ? '#10b981' : isException ? '#f43f5e' : '#f59e0b'}
                  />

                  {/* Primary Entity ID / Label */}
                  <text
                    x={9}
                    y={30}
                    fill="#f8fafc"
                    fontSize={10.5}
                    fontWeight={600}
                    fontFamily="'JetBrains Mono', monospace"
                  >
                    {node.entity_id.length > 13 ? node.entity_id.slice(0, 12) + '…' : node.entity_id}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Selected Node Details Bar */}
        {selectedNodeObj && (
          <div
            style={{
              position: 'absolute',
              bottom: '48px',
              left: '12px',
              right: '12px',
              background: 'rgba(15, 23, 42, 0.92)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '0.5rem 0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              zIndex: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                {selectedNodeObj.entity_type}
              </span>
              <span className="mono" style={{ fontWeight: 700, color: '#f8fafc' }}>
                {selectedNodeObj.entity_id}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: '#94a3b8' }}>
              <span>Status: <strong style={{ color: selectedNodeObj.status === 'RECONCILED' ? '#10b981' : selectedNodeObj.status === 'EXCEPTION' ? '#f43f5e' : '#f59e0b' }}>{selectedNodeObj.status}</strong></span>
              <span>Connected Nodes: <strong className="mono" style={{ color: '#38bdf8' }}>{connectedNodeIds.size - 1}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* Graph Legend (Bottom) */}
      <div
        style={{
          padding: '0.5rem 1rem',
          background: 'rgba(13, 18, 31, 0.95)',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.725rem',
          color: '#94a3b8',
        }}
      >
        {Object.entries(TYPE_CONFIG).map(([typeKey, cfg]) => (
          <div key={typeKey} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '2px',
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
              }}
            />
            <span>{cfg.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
