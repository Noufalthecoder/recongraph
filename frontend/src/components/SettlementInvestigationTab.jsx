import React, { useState } from 'react';
import { ArrowLeft, Brain, ShieldAlert, CheckCircle2, AlertTriangle, GitFork, ArrowRight, ShieldCheck, Sparkles, RotateCcw } from 'lucide-react';
import FinancialGraphView from './FinancialGraphView.jsx';

class GraphErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('Financial Graph render error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="graph-viewport-card" style={{ height: '100%', minHeight: '560px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', textAlign: 'center' }}>
          <AlertTriangle size={36} color="#fbbf24" style={{ marginBottom: '1rem' }} />
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.35rem' }}>Graph Render Fallback</div>
          <p style={{ fontSize: '0.825rem', color: '#94a3b8', maxWidth: '360px', marginBottom: '1.25rem', lineHeight: 1.4 }}>
            The financial relationship graph could not be rendered, but all deterministic settlement details and evidence remain available.
          </p>
          <button
            className="nav-tab-btn"
            style={{ padding: '0.45rem 1rem', background: 'rgba(255,255,255,0.08)', fontSize: '0.8rem' }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            <RotateCcw size={14} /> Retry Graph Render
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function SettlementInvestigationTab({
  settlementId,
  settlementDetail,
  subgraph,
  loading,
  error,
  onRetry,
  onBack,
  onOpenAIInvestigator,
}) {
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // 1. Loading State
  if (loading) {
    return (
      <div style={{ padding: '5rem 2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div
          style={{
            margin: '0 auto 1.25rem',
            width: '36px',
            height: '36px',
            border: '3px solid rgba(56, 189, 248, 0.2)',
            borderTopColor: '#38bdf8',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.35rem' }}>
          Loading settlement investigation…
        </div>
        <div className="mono" style={{ fontSize: '0.85rem', color: '#64748b' }}>
          Settlement ID: {settlementId || '—'}
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error || !settlementDetail) {
    return (
      <div style={{ padding: '3rem 1.5rem', maxWidth: '600px', margin: '2rem auto 0' }}>
        <div className="panel-card" style={{ border: '1px solid rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.06)', padding: '2.5rem 2rem', textAlign: 'center' }}>
          <ShieldAlert size={44} color="#f43f5e" style={{ margin: '0 auto 1rem' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.5rem' }}>
            Unable to load settlement
          </h2>
          <div className="mono" style={{ fontSize: '0.9rem', color: '#38bdf8', marginBottom: '0.85rem', fontWeight: 700 }}>
            Settlement: {settlementId || 'Unknown'}
          </div>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.5rem', lineHeight: 1.5 }}>
            {error || 'The requested settlement data could not be retrieved from the server.'}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            {onRetry && settlementId && (
              <button
                className="ai-submit-btn"
                style={{ padding: '0.5rem 1.25rem', fontSize: '0.85rem' }}
                onClick={() => onRetry(settlementId)}
              >
                <RotateCcw size={14} /> Retry
              </button>
            )}
            <button
              className="nav-tab-btn"
              style={{ padding: '0.5rem 1.25rem', fontSize: '0.85rem', background: 'rgba(255, 255, 255, 0.08)' }}
              onClick={onBack}
            >
              <ArrowLeft size={14} /> Back to Settlements
            </button>
          </div>
        </div>
      </div>
    );
  }

  const {
    settlement_id,
    utr,
    amount,
    fees,
    tax,
    status,
    equation_components,
    exceptions,
    evidence,
    constituent_transactions,
    payments,
    refunds,
    adjustments,
    bank_entry,
  } = settlementDetail;

  const isException = status === 'EXCEPTION';

  // Helper to find node by entity
  const handleHighlightEvidence = (ev) => {
    if (ev.primary_entity) {
      const targetId = `${ev.primary_entity.entity_type}:${ev.primary_entity.entity_id}`;
      setSelectedNodeId(targetId);
    }
  };

  return (
    <div>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            className="nav-tab-btn"
            style={{ padding: '0.45rem 0.85rem' }}
            onClick={onBack}
          >
            <ArrowLeft size={16} /> Back to Settlements
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 className="hero-title" style={{ fontSize: '1.35rem', margin: 0 }}>
                Settlement <span className="mono" style={{ color: '#38bdf8' }}>{settlement_id}</span>
              </h1>
              <span className={`badge ${status === 'RECONCILED' ? 'badge-reconciled' : 'badge-exception'}`}>
                {status === 'RECONCILED' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                {status}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }} className="mono">
              UTR: {utr} · Payout Header: {amount}
            </div>
          </div>
        </div>

        <button
          className="ai-submit-btn"
          style={{ padding: '0.6rem 1.25rem' }}
          onClick={() =>
            onOpenAIInvestigator(
              `Why is settlement ${settlement_id} ${isException ? 'short by ₹250?' : 'reconciled?'}`,
              'settlement',
              settlement_id
            )
          }
        >
          <Brain size={16} />
          Investigate with AI
        </button>
      </div>

      {/* Split Investigation Layout */}
      <div className="split-investigation-layout">
        {/* Left Column: Interactive Graph with Failure Isolation */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <GraphErrorBoundary>
            <FinancialGraphView
              nodes={subgraph?.nodes || []}
              edges={subgraph?.edges || []}
              selectedNodeId={selectedNodeId}
              onSelectNode={(n) => setSelectedNodeId(n.node_id)}
            />
          </GraphErrorBoundary>
        </div>

        {/* Right Column: Settlement Intelligence Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Financial Equation Breakdown */}
          <div className="panel-card">
            <div className="panel-title">
              <span>Financial Equation Breakdown</span>
              <span className="mono" style={{ fontSize: '0.75rem', color: '#64748b' }}>Deterministic Sum</span>
            </div>

            <div className="equation-card">
              <div className="equation-flex">
                {equation_components.map((c, idx) => (
                  <React.Fragment key={idx}>
                    {idx > 0 && <span className="equation-sign">{c.sign}</span>}
                    <div className="equation-node">
                      <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
                        {c.label}
                      </div>
                      <div className="mono" style={{ fontSize: '1.05rem', fontWeight: 800, color: c.type === 'bank' && isException ? '#f43f5e' : '#fff' }}>
                        {c.amount}
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#64748b' }}>
                        {c.count} {c.count === 1 ? 'record' : 'records'}
                      </div>
                    </div>
                  </React.Fragment>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#94a3b8' }}>
              <span>Batch Fees: <strong className="mono" style={{ color: '#e2e8f0' }}>{fees}</strong></span>
              <span>Batch Tax: <strong className="mono" style={{ color: '#e2e8f0' }}>{tax}</strong></span>
              <span>Constituent Items: <strong className="mono" style={{ color: '#e2e8f0' }}>{constituent_transactions.length}</strong></span>
            </div>
          </div>

          {/* Reconciliation Exception Alert Card */}
          {exceptions.length > 0 ? (
            <div className="panel-card" style={{ border: '1px solid rgba(244, 63, 94, 0.35)', background: 'rgba(244, 63, 94, 0.05)' }}>
              <div className="panel-title" style={{ color: '#fb7185', marginBottom: '0.75rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShieldAlert size={18} /> {exceptions[0].rule_code}
                </span>
                <span className="badge badge-exception">{exceptions[0].severity}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '0.85rem' }}>
                <div style={{ background: 'var(--bg-tertiary)', padding: '0.65rem', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Expected Payout</div>
                  <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 700 }}>{exceptions[0].expected_value || amount}</div>
                </div>

                <div style={{ background: 'var(--bg-tertiary)', padding: '0.65rem', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Observed Bank</div>
                  <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 700 }}>{exceptions[0].observed_value || bank_entry?.amount || '—'}</div>
                </div>

                <div style={{ background: 'rgba(244, 63, 94, 0.15)', padding: '0.65rem', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.68rem', color: '#fecdd3', textTransform: 'uppercase', fontWeight: 700 }}>Discrepancy Delta</div>
                  <div className="mono delta-negative" style={{ fontSize: '0.95rem', fontWeight: 800 }}>{exceptions[0].difference || '—'}</div>
                </div>
              </div>

              <div style={{ fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.4, marginBottom: '0.5rem' }}>
                {exceptions[0].description}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#10b981' }}>
                <ShieldCheck size={14} />
                <span>Verified by deterministic reconciliation engine</span>
              </div>
            </div>
          ) : (
            <div className="panel-card" style={{ border: '1px solid rgba(16, 185, 129, 0.3)', background: 'rgba(16, 185, 129, 0.04)' }}>
              <div className="panel-title" style={{ color: '#34d399', margin: 0 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={18} /> Perfectly Reconciled
                </span>
                <span className="badge badge-reconciled">Zero Discrepancies</span>
              </div>
              <p style={{ fontSize: '0.825rem', color: '#94a3b8', marginTop: '0.4rem' }}>
                All constituent payments, refunds, fee/tax calculations, and bank statement credits balance with exact precision.
              </p>
            </div>
          )}

          {/* Evidence Stack */}
          <div className="panel-card">
            <div className="panel-title">
              <span>Deterministic Evidence Stack</span>
              <span className="mono" style={{ fontSize: '0.75rem', color: '#64748b' }}>{evidence.length} proofs</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
              {evidence.map((ev, idx) => (
                <div
                  key={idx}
                  onClick={() => handleHighlightEvidence(ev)}
                  style={{
                    padding: '0.65rem 0.85rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#38bdf8')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                  title="Click to highlight graph node"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                    <span className="mono" style={{ fontWeight: 700, color: '#38bdf8' }}>
                      [E{idx + 1}] {ev.rule_code}
                    </span>
                    {ev.difference && (
                      <span className="mono delta-negative">Δ {ev.difference}</span>
                    )}
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
                    {ev.rule_description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
