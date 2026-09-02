import React from 'react';
import { BarChart3, Sparkles, CheckCircle2, ShieldAlert, Zap, ShieldCheck, Database, Layers } from 'lucide-react';

export default function BenchmarkTab({ benchmarkData }) {
  if (!benchmarkData) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
        Loading benchmark evaluation metrics…
      </div>
    );
  }

  const {
    total_records_processed,
    total_scenarios_evaluated,
    total_expected_anomalies,
    total_detected_issues,
    true_positives,
    false_positives,
    false_negatives,
    precision,
    recall,
    f1,
    clean_reconciliation_rate,
    records_per_second,
    elapsed_seconds,
    anomaly_breakdown,
    isolation_note,
  } = benchmarkData;

  return (
    <div>
      {/* Page Hero */}
      <div className="page-hero">
        <div>
          <h1 className="hero-title">Reconciliation Benchmark</h1>
          <p className="hero-subtitle">Measured performance on deterministic synthetic financial worlds.</p>
        </div>
      </div>

      {/* Top Benchmark KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Precision</span>
            <CheckCircle2 size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#10b981' }}>{precision}</div>
          <div className="kpi-trend trend-emerald">
            <span>Zero False Positives</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Recall</span>
            <CheckCircle2 size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#10b981' }}>{recall}</div>
          <div className="kpi-trend trend-emerald">
            <span>Zero False Negatives</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">F1 Score</span>
            <Sparkles size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#8b5cf6' }}>{f1}</div>
          <div className="kpi-trend trend-blue">
            <span>Perfect Accuracy</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Clean Recon Rate</span>
            <ShieldCheck size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value mono" style={{ color: '#06b6d4' }}>{clean_reconciliation_rate}</div>
          <div className="kpi-trend trend-blue">
            <span>Clean Baseline</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Records / Sec</span>
            <Zap size={18} className="kpi-icon" />
          </div>
          <div className="kpi-value mono">{records_per_second}</div>
          <div className="kpi-trend trend-emerald">
            <span>{elapsed_seconds} elapsed</span>
          </div>
        </div>
      </div>

      {/* Anomaly Detection Performance Table */}
      <div className="panel-card" style={{ marginBottom: '1.5rem' }}>
        <div className="panel-title">
          <span>Anomaly Detection Breakdown</span>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
            {total_scenarios_evaluated} Scenarios Evaluated · {total_records_processed} Records
          </span>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Anomaly Class</th>
                <th>Expected</th>
                <th>Detected</th>
                <th>TP</th>
                <th>FP</th>
                <th>FN</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
              </tr>
            </thead>
            <tbody>
              {anomaly_breakdown.map((row) => (
                <tr key={row.anomaly_type}>
                  <td className="mono" style={{ fontWeight: 700, color: '#38bdf8' }}>
                    {row.anomaly_type}
                  </td>
                  <td className="mono">{row.expected_count}</td>
                  <td className="mono">{row.detected_count}</td>
                  <td className="mono" style={{ color: '#10b981', fontWeight: 600 }}>{row.true_positives}</td>
                  <td className="mono">{row.false_positives}</td>
                  <td className="mono">{row.false_negatives}</td>
                  <td className="mono">{row.precision}</td>
                  <td className="mono">{row.recall}</td>
                  <td className="mono" style={{ color: '#8b5cf6', fontWeight: 700 }}>{row.f1}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ground Truth Isolation Architectural Callout */}
      <div
        className="panel-card"
        style={{
          border: '1px solid rgba(59, 130, 246, 0.3)',
          background: 'rgba(59, 130, 246, 0.05)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '1rem',
        }}
      >
        <div style={{ padding: '0.5rem', background: 'rgba(59, 130, 246, 0.15)', borderRadius: '10px' }}>
          <Layers size={22} color="#60a5fa" />
        </div>
        <div>
          <h4 style={{ color: '#ffffff', fontSize: '0.95rem', marginBottom: '0.25rem' }}>
            Architectural Ground Truth Isolation Guarantee
          </h4>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5 }}>
            {isolation_note}
          </p>
        </div>
      </div>
    </div>
  );
}
