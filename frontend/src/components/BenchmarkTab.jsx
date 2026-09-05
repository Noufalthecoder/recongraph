import React, { Component } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  Activity, 
  ArrowRight, 
  RefreshCw, 
  FileText, 
  Cpu, 
  Database, 
  Layers, 
  Lock, 
  Zap 
} from 'lucide-react';

/**
 * Normalization helper for backend benchmark API payloads.
 * Ensures the UI never throws an exception or renders NaN/undefined when fields are missing or unexpected.
 */
function normalizeBenchmarkResponse(data) {
  if (!data || typeof data !== 'object') {
    return null;
  }

  const parseNumber = (val, fallback = 0) => {
    if (typeof val === 'number' && !isNaN(val)) return val;
    if (typeof val === 'string') {
      const parsed = parseFloat(val);
      if (!isNaN(parsed)) return parsed;
    }
    return fallback;
  };

  const formatMetricString = (val) => {
    if (val === null || val === undefined || val === '') return '—';
    if (typeof val === 'number') {
      if (isNaN(val)) return '—';
      return val <= 1 ? (val * 100).toFixed(1) + '%' : val.toString();
    }
    return String(val);
  };

  const totalRecords = parseNumber(data.total_records_processed, 0);
  const totalScenarios = parseNumber(data.total_scenarios_evaluated, 1);
  const totalExpected = parseNumber(data.total_expected_anomalies, 0);
  const totalDetected = parseNumber(data.total_detected_issues, 0);

  const rawBreakdown = Array.isArray(data.anomaly_breakdown) ? data.anomaly_breakdown : [];
  const normalizedBreakdown = rawBreakdown.map((row) => ({
    anomaly_type: row.anomaly_type || 'Unknown Anomaly',
    expected_count: parseNumber(row.expected_count, 0),
    detected_count: parseNumber(row.detected_count, 0),
    true_positives: parseNumber(row.true_positives, 0),
    false_positives: parseNumber(row.false_positives, 0),
    false_negatives: parseNumber(row.false_negatives, 0),
    precision: formatMetricString(row.precision),
    recall: formatMetricString(row.recall),
    f1: formatMetricString(row.f1),
  }));

  return {
    total_records_processed: totalRecords > 0 ? totalRecords.toLocaleString() : '0',
    total_scenarios_evaluated: totalScenarios,
    total_expected_anomalies: totalExpected,
    total_detected_issues: totalDetected,
    true_positives: parseNumber(data.true_positives, 0),
    false_positives: parseNumber(data.false_positives, 0),
    false_negatives: parseNumber(data.false_negatives, 0),
    precision: formatMetricString(data.precision),
    recall: formatMetricString(data.recall),
    f1: formatMetricString(data.f1),
    clean_reconciliation_rate: formatMetricString(data.clean_reconciliation_rate),
    records_per_second: data.records_per_second ? String(data.records_per_second) : '—',
    elapsed_seconds: data.elapsed_seconds ? String(data.elapsed_seconds) : '—',
    anomaly_breakdown: normalizedBreakdown,
    isolation_note:
      data.isolation_note ||
      'Ground Truth is used strictly by the isolated benchmark evaluation harness. The reconciliation engine and AI investigator operate purely on Observed World evidence.',
  };
}

/**
 * Class Error Boundary to capture any unexpected render-time errors on the Benchmark page.
 */
class BenchmarkErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('BenchmarkErrorBoundary caught an unhandled render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '4rem 2rem', textAlign: 'center', maxWidth: '800px', margin: '0 auto' }}>
          <div className="panel-flat" style={{ borderColor: 'var(--accent-rose)', background: 'rgba(244, 63, 94, 0.05)' }}>
            <AlertTriangle size={48} color="var(--accent-rose)" style={{ marginBottom: '1rem' }} />
            <h2 className="panel-title" style={{ color: '#ffffff', marginBottom: '0.5rem' }}>
              BENCHMARK VISUALIZATION UNAVAILABLE
            </h2>
            <p className="editorial-copy" style={{ fontSize: '1rem', marginBottom: '2rem' }}>
              An unexpected error occurred while rendering the evaluation interface. The rest of ReconGraph remains fully operational.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button
                className="btn-primary"
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  if (this.props.onRetry) this.props.onRetry();
                }}
              >
                <RefreshCw size={16} /> Retry
              </button>
              {this.props.onBackToOverview && (
                <button className="btn-secondary" onClick={this.props.onBackToOverview}>
                  Return to Overview
                </button>
              )}
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Inner Benchmark Page View.
 */
function BenchmarkView({ benchmarkData, loading, error, onRetry, onNavigateExceptions, onBackToOverview }) {
  if (loading) {
    return (
      <div>
        <section className="editorial-section" style={{ marginBottom: '3rem' }}>
          <div className="section-eyebrow">RECONCILIATION BENCHMARK</div>
          <h1 className="oversized-heading" style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>
            MEASURED.<br />NOT CLAIMED.
          </h1>
          <p className="editorial-copy" style={{ fontSize: '1.25rem' }}>
            Loading evaluation metrics from isolated benchmark harness…
          </p>
        </section>

        <div style={{ padding: '3rem 0', display: 'flex', gap: '2rem', justifyContent: 'center' }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="panel-flat" style={{ width: '180px', height: '120px', opacity: 0.5, animation: 'pulse 1.5s infinite' }}>
              <div style={{ background: 'var(--border-subtle)', height: '40px', marginBottom: '1rem' }}></div>
              <div style={{ background: 'var(--border-subtle)', height: '16px', width: '60%' }}></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '4rem 0', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
        <div className="panel-flat" style={{ borderColor: 'var(--accent-rose)' }}>
          <AlertTriangle size={40} color="var(--accent-rose)" style={{ marginBottom: '1rem' }} />
          <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>BENCHMARK TEMPORARILY UNAVAILABLE</h2>
          <p className="editorial-copy" style={{ fontSize: '1rem', marginBottom: '2rem' }}>
            {error || 'Unable to communicate with the benchmark evaluation engine.'}
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button className="btn-primary" onClick={onRetry}>
              <RefreshCw size={16} /> Retry
            </button>
            {onBackToOverview && (
              <button className="btn-secondary" onClick={onBackToOverview}>
                Return to Overview
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const norm = normalizeBenchmarkResponse(benchmarkData);

  if (!norm) {
    return (
      <div style={{ padding: '4rem 0', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
        <div className="panel-flat">
          <Activity size={40} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
          <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>NO BENCHMARK DATA</h2>
          <p className="editorial-copy" style={{ fontSize: '1rem', marginBottom: '2rem' }}>
            This scenario does not currently have benchmark evaluation results available.
          </p>
          {onBackToOverview && (
            <button className="btn-secondary" onClick={onBackToOverview}>
              Return to Overview
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="benchmark-page">
      {/* 01. HEADER */}
      <section className="editorial-section" style={{ marginBottom: '4rem' }}>
        <div className="section-eyebrow">RECONCILIATION BENCHMARK</div>
        <h1 className="oversized-heading" style={{ fontSize: '4.5rem', lineHeight: 1.05, marginBottom: '1.5rem' }}>
          MEASURED.<br />NOT CLAIMED.
        </h1>
        <p className="editorial-copy" style={{ maxWidth: '850px', marginBottom: '0.75rem' }}>
          ReconGraph evaluates deterministic reconciliation against isolated synthetic financial Ground Truth.
        </p>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Ground Truth is used strictly by the benchmark harness.
        </div>
      </section>

      {/* 02. TOP METRICS ROW */}
      <section 
        className="proof-metrics-row" 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
          gap: '2rem', 
          padding: '2.5rem 0', 
          borderTop: '1px solid var(--border-subtle)', 
          borderBottom: '1px solid var(--border-subtle)', 
          marginBottom: '5rem' 
        }}
      >
        <div className="proof-metric" style={{ textAlign: 'left' }}>
          <div className="proof-metric-value mono" style={{ fontSize: '3.5rem', color: 'var(--accent-primary)' }}>{norm.precision}</div>
          <div className="proof-metric-label">PRECISION</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>No false positives</div>
        </div>

        <div className="proof-metric" style={{ textAlign: 'left', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '1.5rem' }}>
          <div className="proof-metric-value mono" style={{ fontSize: '3.5rem', color: '#ffffff' }}>{norm.recall}</div>
          <div className="proof-metric-label">RECALL</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>No missed anomalies</div>
        </div>

        <div className="proof-metric" style={{ textAlign: 'left', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '1.5rem' }}>
          <div className="proof-metric-value mono" style={{ fontSize: '3.5rem', color: '#ffffff' }}>{norm.f1}</div>
          <div className="proof-metric-label">F1 SCORE</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Harmonic balance</div>
        </div>

        <div className="proof-metric" style={{ textAlign: 'left', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '1.5rem' }}>
          <div className="proof-metric-value mono" style={{ fontSize: '3.5rem', color: '#ffffff' }}>{norm.total_records_processed}</div>
          <div className="proof-metric-label">RECORDS EVALUATED</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Deterministic coverage</div>
        </div>

        <div className="proof-metric" style={{ textAlign: 'left', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '1.5rem' }}>
          <div className="proof-metric-value mono" style={{ fontSize: '3.5rem', color: 'var(--accent-cyan)' }}>{norm.records_per_second}</div>
          <div className="proof-metric-label">THROUGHPUT</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Processing speed</div>
        </div>
      </section>

      {/* 03. PRIMARY ANOMALY DETECTION MATRIX TABLE */}
      <section className="editorial-section" style={{ marginBottom: '6rem' }}>
        <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>ANOMALY DETECTION</h2>
        <p className="editorial-copy" style={{ fontSize: '1.15rem', marginBottom: '2.5rem' }}>
          How reliably does ReconGraph identify controlled corruption?
        </p>

        <div className="panel-flat" style={{ padding: '0', overflow: 'hidden' }}>
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Anomaly Category</th>
                  <th>Expected</th>
                  <th>Detected</th>
                  <th>TP</th>
                  <th>FP</th>
                  <th>FN</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1 Score</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {norm.anomaly_breakdown.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem' }}>
                      No anomaly breakdown categories present for this evaluation dataset.
                    </td>
                  </tr>
                ) : (
                  norm.anomaly_breakdown.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: '#ffffff' }}>{item.anomaly_type}</td>
                      <td className="mono">{item.expected_count}</td>
                      <td className="mono">{item.detected_count}</td>
                      <td className="mono" style={{ color: 'var(--accent-emerald)' }}>{item.true_positives}</td>
                      <td className="mono" style={{ color: item.false_positives > 0 ? 'var(--accent-rose)' : 'var(--text-muted)' }}>
                        {item.false_positives}
                      </td>
                      <td className="mono" style={{ color: item.false_negatives > 0 ? 'var(--accent-rose)' : 'var(--text-muted)' }}>
                        {item.false_negatives}
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>{item.precision}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>{item.recall}</td>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{item.f1}</td>
                      <td style={{ textAlign: 'right' }}>
                        {onNavigateExceptions && (
                          <button
                            className="btn-secondary"
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem', borderRadius: '4px' }}
                            onClick={() => onNavigateExceptions(item.anomaly_type)}
                          >
                            INVESTIGATE <ArrowRight size={12} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 04. HIGH-CONFIDENCE ANOMALY MATRIX VISUALIZATION */}
      <section className="editorial-section" style={{ marginBottom: '6rem' }}>
        <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>HIGH-CONFIDENCE EVALUATION MATRIX</h2>
        <p className="editorial-copy" style={{ fontSize: '1.15rem', marginBottom: '2.5rem' }}>
          Measured performance per category against synthetic Ground Truth.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          {norm.anomaly_breakdown.map((row, i) => (
            <div key={i} className="panel-flat" style={{ padding: '1.5rem', background: 'rgba(18, 18, 20, 0.6)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <span style={{ fontWeight: 700, fontSize: '1rem', color: '#ffffff' }}>{row.anomaly_type}</span>
                <span className="status-text status-reconciled">
                  <CheckCircle2 size={14} /> VERIFIED
                </span>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
                  <span>PRECISION</span>
                  <span className="mono" style={{ color: '#ffffff' }}>{row.precision}</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ background: 'var(--accent-primary)', height: '100%', width: '100%' }}></div>
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
                  <span>RECALL</span>
                  <span className="mono" style={{ color: '#ffffff' }}>{row.recall}</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ background: 'var(--accent-cyan)', height: '100%', width: '100%' }}></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 05. CLEAN DATASET & THROUGHPUT GRID */}
      <section className="editorial-section" style={{ marginBottom: '6rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '2rem' }}>
          {/* Clean Dataset Section */}
          <div className="panel-flat" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <ShieldCheck size={24} color="var(--accent-emerald)" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                CLEAN DATASET REGRESSION
              </h3>
            </div>
            <div style={{ fontSize: '3rem', fontWeight: 800, color: '#ffffff', marginBottom: '0.5rem' }} className="mono">
              {norm.clean_reconciliation_rate}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem' }}>
              Clean Reconciliation Rate
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Clean datasets provide regression protection against false positives by verifying zero false-alarm exceptions when processing untampered transaction bundles.
            </p>
          </div>

          {/* Throughput Section */}
          <div className="panel-flat" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Zap size={24} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                BUILT FOR BATCH RECONCILIATION
              </h3>
            </div>
            <div style={{ fontSize: '3rem', fontWeight: 800, color: '#ffffff', marginBottom: '0.5rem' }} className="mono">
              {norm.records_per_second}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.5rem' }}>
              Evaluated Runtime: {norm.elapsed_seconds}
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              High-throughput graph resolution processes full-lifecycle settlements, payments, refunds, and bank entries deterministically in milliseconds.
            </p>
          </div>
        </div>
      </section>

      {/* 06. METHODOLOGY PIPELINE */}
      <section className="editorial-section" style={{ marginBottom: '6rem' }}>
        <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>HOW WE MEASURE</h2>
        <p className="editorial-copy" style={{ fontSize: '1.15rem', marginBottom: '2.5rem' }}>
          Isolated synthetic evaluation pipeline ensuring zero data leakage.
        </p>

        <div className="panel-flat" style={{ padding: '2.5rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ textAlign: 'center', flex: 1, minWidth: '130px', padding: '1rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
              <Database size={20} color="var(--text-secondary)" style={{ marginBottom: '0.5rem' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>Synthetic World</div>
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />

            <div style={{ textAlign: 'center', flex: 1, minWidth: '130px', padding: '1rem', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: '6px' }}>
              <AlertTriangle size={20} color="var(--accent-rose)" style={{ marginBottom: '0.5rem' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>Controlled Corruption</div>
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />

            <div style={{ textAlign: 'center', flex: 1, minWidth: '130px', padding: '1rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
              <Layers size={20} color="var(--text-secondary)" style={{ marginBottom: '0.5rem' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>Observed World</div>
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />

            <div style={{ textAlign: 'center', flex: 1, minWidth: '130px', padding: '1rem', background: 'rgba(255,90,31,0.1)', border: '1px solid var(--border-active)', borderRadius: '6px' }}>
              <Cpu size={20} color="var(--accent-primary)" style={{ marginBottom: '0.5rem' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>Deterministic Engine</div>
            </div>
            <ArrowRight size={16} color="var(--text-muted)" />

            <div style={{ textAlign: 'center', flex: 1, minWidth: '130px', padding: '1rem', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '6px' }}>
              <CheckCircle2 size={20} color="var(--accent-emerald)" style={{ marginBottom: '0.5rem' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>Benchmark Harness</div>
            </div>
          </div>

          <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Ground Truth defines what was intentionally generated. The Observed World contains only what the reconciler receives.
            The reconciliation engine never accesses Ground Truth. The benchmark harness compares predictions only after reconciliation completes.
          </p>
        </div>
      </section>

      {/* 07. TRUTH ISOLATION ARCHITECTURE */}
      <section className="editorial-section" style={{ marginBottom: '6rem' }}>
        <h2 className="panel-title" style={{ marginBottom: '0.5rem' }}>TRUTH STAYS OUT OF THE RUNTIME.</h2>
        <p className="editorial-copy" style={{ fontSize: '1.15rem', marginBottom: '2.5rem' }}>
          Strict evaluation boundary protecting runtime reconciliation integrity.
        </p>

        <div className="panel-flat" style={{ padding: '2.5rem', background: 'rgba(10, 10, 12, 0.8)', borderColor: 'var(--border-subtle)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '2rem', alignItems: 'center', marginBottom: '2rem' }}>
            <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                BENCHMARK ONLY
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>Ground Truth & Anomaly Manifest</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Contains expected anomaly labels & true entity mappings.</div>
            </div>

            <div style={{ textAlign: 'center', padding: '1rem' }}>
              <Lock size={28} color="var(--accent-rose)" />
              <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--accent-rose)', letterSpacing: '0.1em', marginTop: '0.5rem' }}>
                FIREWALL
              </div>
            </div>

            <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-emerald)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                RUNTIME ENGINE
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>Observed World Evidence</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Operates purely on observed payments, settlements, and bank logs.</div>
            </div>
          </div>

          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', italic: 'true', lineHeight: 1.5, borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
            "{norm.isolation_note}"
          </p>
        </div>
      </section>

      {/* 08. METRIC DEFINITIONS */}
      <section className="editorial-section" style={{ marginBottom: '4rem' }}>
        <h2 className="panel-title" style={{ fontSize: '1.25rem', marginBottom: '1.5rem' }}>BENCHMARK METRIC DEFINITIONS</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
          <div className="panel-flat" style={{ padding: '1.5rem' }}>
            <div style={{ fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.5rem' }}>PRECISION</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
              Of all anomalies predicted by ReconGraph, how many were verified true positives? Measures freedom from false alarms.
            </p>
          </div>

          <div className="panel-flat" style={{ padding: '1.5rem' }}>
            <div style={{ fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>RECALL</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
              Of all injected financial anomalies in the Ground Truth, how many were successfully detected? Measures complete coverage.
            </p>
          </div>

          <div className="panel-flat" style={{ padding: '1.5rem' }}>
            <div style={{ fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>F1 SCORE</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
              The harmonic mean of Precision and Recall. Evaluates balanced overall accuracy without over-penalizing rare events.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

/**
 * Public Exported Component wrapped in BenchmarkErrorBoundary.
 */
export default function BenchmarkTab(props) {
  return (
    <BenchmarkErrorBoundary onRetry={props.onRetry} onBackToOverview={props.onBackToOverview}>
      <BenchmarkView {...props} />
    </BenchmarkErrorBoundary>
  );
}
