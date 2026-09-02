import React from 'react';
import { Database, Percent, AlertOctagon, Sparkles, Zap, ArrowRight, ShieldCheck, CheckCircle2, ChevronRight } from 'lucide-react';

export default function OverviewTab({
  dashboardData,
  onSelectSettlement,
  onInvestigateException,
  onNavigateExceptions,
}) {
  if (!dashboardData) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>Loading dashboard control center…</div>;
  }

  const { kpis, settlement_health, exception_distribution, recent_exceptions } = dashboardData;

  return (
    <div>
      {/* Page Hero */}
      <div className="page-hero">
        <div>
          <h1 className="hero-title">Reconciliation Control Center</h1>
          <p className="hero-subtitle">Reconstruct every rupee. Explain every exception.</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 800, letterSpacing: '0.05em' }}>
            Current Demo Scenario
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8' }}>
            {kpis.active_scenario_label}
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Records Processed</span>
            <Database size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value mono">{kpis.total_records}</div>
          <div className="kpi-trend trend-blue">
            <span>Observed Dataset</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Reconciliation Rate</span>
            <Percent size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#10b981' }}>{kpis.reconciliation_rate}</div>
          <div className="kpi-trend trend-emerald">
            <CheckCircle2 size={13} />
            <span>{kpis.reconciled_count} / {kpis.settlement_count} Clean</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Open Exceptions</span>
            <AlertOctagon size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: kpis.exception_count > 0 ? '#f43f5e' : '#10b981' }}>
            {kpis.exception_count}
          </div>
          <div className="kpi-trend trend-rose">
            <span>{kpis.exception_count > 0 ? 'Requires investigation' : 'All clear'}</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Benchmark F1</span>
            <Sparkles size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#8b5cf6' }}>{kpis.benchmark_f1}</div>
          <div className="kpi-trend trend-blue">
            <span>100% Precision & Recall</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Throughput</span>
            <Zap size={16} className="kpi-icon" />
          </div>
          <div className="kpi-value mono">{kpis.throughput_display}</div>
          <div className="kpi-trend trend-emerald">
            <span>Deterministic Core</span>
          </div>
        </div>
      </div>

      {/* 2-Column Section: Settlement Health & Exception Distribution */}
      <div className="dashboard-grid-2col">
        {/* Settlement Health */}
        <div className="panel-card">
          <div className="panel-title">
            <span>Settlement Health</span>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Total: {kpis.settlement_count} settlements</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.85rem', marginBottom: '1.25rem' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '0.85rem', borderRadius: '10px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#34d399' }} className="mono">
                {settlement_health.RECONCILED || 0}
              </div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a7f3d0', textTransform: 'uppercase' }}>
                Reconciled
              </div>
            </div>

            <div style={{ background: 'rgba(244, 63, 94, 0.08)', border: '1px solid rgba(244, 63, 94, 0.25)', padding: '0.85rem', borderRadius: '10px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fb7185' }} className="mono">
                {settlement_health.EXCEPTION || 0}
              </div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fecdd3', textTransform: 'uppercase' }}>
                Exceptions
              </div>
            </div>

            <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', padding: '0.85rem', borderRadius: '10px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fbbf24' }} className="mono">
                {settlement_health.UNMATCHED || 0}
              </div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fde68a', textTransform: 'uppercase' }}>
                Unmatched
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', color: '#94a3b8' }}>
            <span>Settlement Volume: <strong className="mono" style={{ color: '#fff' }}>{kpis.total_settlement_value}</strong></span>
            <span>Bank Statement: <strong className="mono" style={{ color: '#fff' }}>{kpis.total_bank_value}</strong></span>
          </div>
        </div>

        {/* Exception Distribution */}
        <div className="panel-card">
          <div className="panel-title">
            <span>Exception Distribution</span>
            <span className="badge badge-exception">{kpis.exception_count} Detected</span>
          </div>

          {Object.keys(exception_distribution).length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
              <ShieldCheck size={36} color="#10b981" style={{ margin: '0 auto 0.5rem' }} />
              <div>Zero reconciliation exceptions in active dataset</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {Object.entries(exception_distribution).map(([rule, count]) => (
                <div
                  key={rule}
                  onClick={() => onNavigateExceptions && onNavigateExceptions(rule)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.7rem 0.95rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#f43f5e')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                  title="Click to view in Exceptions queue"
                >
                  <span className="mono" style={{ fontSize: '0.825rem', fontWeight: 600, color: '#f8fafc' }}>
                    {rule}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="badge badge-exception">{count}</span>
                    <ChevronRight size={14} color="#64748b" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Exceptions Table */}
      <div className="panel-card">
        <div className="panel-title">
          <span>Reconciliation Exceptions</span>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Click row or action to investigate</span>
        </div>

        {recent_exceptions.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: '#64748b' }}>
            No exceptions present in current dataset.
          </div>
        ) : (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Settlement / Entity</th>
                  <th>Issue / Rule</th>
                  <th>Expected</th>
                  <th>Observed</th>
                  <th>Delta</th>
                  <th>Severity</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recent_exceptions.map((exc) => (
                  <tr
                    key={exc.exception_id}
                    className="clickable-row"
                    onClick={() => exc.settlement_id && onSelectSettlement(exc.settlement_id)}
                  >
                    <td className="mono" style={{ fontWeight: 700, color: '#38bdf8' }}>
                      {exc.settlement_id || exc.entity_id}
                    </td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>{exc.rule_code}</td>
                    <td className="mono">{exc.expected_value || '—'}</td>
                    <td className="mono">{exc.observed_value || '—'}</td>
                    <td className={`mono ${exc.difference ? 'delta-negative' : 'delta-zero'}`}>
                      {exc.difference || '₹0.00'}
                    </td>
                    <td>
                      <span className={`badge badge-${exc.severity.toLowerCase()}`}>
                        {exc.severity}
                      </span>
                    </td>
                    <td>
                      <button
                        className="nav-tab-btn"
                        style={{ padding: '0.3rem 0.65rem', fontSize: '0.75rem', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onInvestigateException(exc);
                        }}
                      >
                        Investigate <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
