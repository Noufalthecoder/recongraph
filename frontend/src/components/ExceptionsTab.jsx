import React, { useState } from 'react';
import { ShieldAlert, ArrowRight, Brain, Filter, ShieldCheck, AlertOctagon, AlertTriangle, Info } from 'lucide-react';

export default function ExceptionsTab({ exceptions = [], onInvestigateException, onSelectSettlement, initialFilter = 'ALL' }) {
  const [filterType, setFilterType] = useState(initialFilter);

  const criticalCount = exceptions.filter((e) => e.severity === 'CRITICAL').length;
  const errorCount = exceptions.filter((e) => e.severity === 'ERROR').length;
  const warningCount = exceptions.filter((e) => e.severity === 'WARNING').length;

  const filteredExceptions = exceptions.filter((exc) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'CRITICAL') return exc.severity === 'CRITICAL';
    if (filterType === 'ERROR') return exc.severity === 'ERROR';
    if (filterType === 'WARNING') return exc.severity === 'WARNING';
    return exc.rule_code.toUpperCase().includes(filterType.toUpperCase());
  });

  return (
    <div>
      {/* Page Hero */}
      <div className="page-hero">
        <div>
          <h1 className="hero-title">Exception Operations Queue</h1>
          <p className="hero-subtitle">Deterministic reconciliation rule breaks, ledger shortfalls, and identity mismatches.</p>
        </div>
      </div>

      {/* Severity Counters & Filter Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {[
            { key: 'ALL', label: `All (${exceptions.length})` },
            { key: 'AMOUNT', label: 'Amount Mismatch' },
            { key: 'MISSING', label: 'Missing Record' },
            { key: 'DUPLICATE', label: 'Duplicate Record' },
            { key: 'IDENTIFIER', label: 'Identifier Mismatch' },
          ].map((tab) => (
            <button
              key={tab.key}
              className={`nav-tab-btn ${filterType === tab.key ? 'active' : ''}`}
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}
              onClick={() => setFilterType(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Severity Counters */}
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem' }}>
          <span style={{ color: '#fb7185', background: 'rgba(244, 63, 94, 0.1)', padding: '0.3rem 0.65rem', borderRadius: '6px', border: '1px solid rgba(244, 63, 94, 0.25)' }}>
            <strong>{criticalCount}</strong> Critical
          </span>
          <span style={{ color: '#fbbf24', background: 'rgba(245, 158, 11, 0.1)', padding: '0.3rem 0.65rem', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
            <strong>{errorCount}</strong> Error
          </span>
          <span style={{ color: '#60a5fa', background: 'rgba(59, 130, 246, 0.1)', padding: '0.3rem 0.65rem', borderRadius: '6px', border: '1px solid rgba(59, 130, 246, 0.25)' }}>
            <strong>{warningCount}</strong> Warning
          </span>
        </div>
      </div>

      {/* Exceptions List */}
      {filteredExceptions.length === 0 ? (
        <div className="panel-card" style={{ padding: '3.5rem', textAlign: 'center', color: '#64748b' }}>
          <ShieldCheck size={40} color="#10b981" style={{ margin: '0 auto 0.75rem' }} />
          <h3 style={{ color: '#fff', marginBottom: '0.35rem' }}>No Exceptions in Selected View</h3>
          <p style={{ fontSize: '0.85rem' }}>The active dataset contains zero exceptions matching this filter criteria.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filteredExceptions.map((exc) => (
            <div
              key={exc.exception_id}
              className="panel-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1.15rem 1.35rem',
                borderLeft: '4px solid #f43f5e',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div style={{ flex: 1, minWidth: '320px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
                  <span className="mono" style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f8fafc' }}>
                    {exc.rule_code}
                  </span>
                  <span className="badge badge-exception">{exc.severity}</span>
                  {exc.settlement_id && (
                    <span className="mono" style={{ fontSize: '0.8rem', color: '#38bdf8' }}>
                      Settlement: {exc.settlement_id}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: '0.825rem', color: '#94a3b8', marginBottom: '0.45rem' }}>
                  {exc.description}
                </div>

                <div style={{ display: 'flex', gap: '1.25rem', fontSize: '0.775rem', color: '#cbd5e1' }} className="mono">
                  <span>Expected: <strong>{exc.expected_value || '—'}</strong></span>
                  <span>Observed: <strong>{exc.observed_value || '—'}</strong></span>
                  <span>Discrepancy: <strong className="delta-negative">{exc.difference || '₹0.00'}</strong></span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center' }}>
                {exc.settlement_id && (
                  <button
                    className="nav-tab-btn"
                    style={{ fontSize: '0.75rem', padding: '0.45rem 0.8rem' }}
                    onClick={() => onSelectSettlement(exc.settlement_id)}
                  >
                    View Settlement
                  </button>
                )}

                <button
                  className="ai-submit-btn"
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.95rem' }}
                  onClick={() => onInvestigateException(exc)}
                >
                  <Brain size={13} />
                  Why? (AI)
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
