import React, { useState, useEffect } from 'react';
import { Brain, Send, Sparkles, CheckCircle2, ShieldCheck, AlertTriangle, Layers, ChevronDown, ChevronUp, Terminal, HelpCircle, ArrowRight } from 'lucide-react';
import { runInvestigation } from '../api.js';

const PRESET_PROMPTS = [
  'Why is settlement short by ₹250?',
  'Trace this payment to the bank.',
  'Show all refunds affecting this settlement.',
  'Why was this settlement not reconciled?',
  'Trace this payment end-to-end.',
];

export default function InvestigatorTab({ initialQuestion = '', targetType = null, targetId = null }) {
  const [question, setQuestion] = useState(initialQuestion || 'Why is settlement short by ₹250?');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showTools, setShowTools] = useState(false);

  useEffect(() => {
    if (initialQuestion) {
      setQuestion(initialQuestion);
      handleInvestigate(initialQuestion);
    }
  }, [initialQuestion]);

  const handleInvestigate = async (qText = question) => {
    if (!qText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runInvestigation(qText, targetType, targetId);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Investigation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1020px', margin: '0 auto' }}>
      {/* Hero Header */}
      <div className="page-hero" style={{ textAlign: 'center', display: 'block', marginBottom: '1.25rem' }}>
        <h1 className="hero-title" style={{ fontSize: '1.65rem' }}>AI Financial Investigator</h1>
        <p className="hero-subtitle">Ask questions. Get evidence-backed answers grounded in deterministic rules.</p>
      </div>

      {/* Preset Prompt Chips */}
      <div className="prompt-chips-row" style={{ justifyContent: 'center', marginBottom: '1rem' }}>
        {PRESET_PROMPTS.map((p, idx) => (
          <button
            key={idx}
            className="prompt-chip"
            onClick={() => {
              setQuestion(p);
              handleInvestigate(p);
            }}
          >
            <Sparkles size={12} style={{ marginRight: '0.35rem', color: '#38bdf8' }} />
            {p}
          </button>
        ))}
      </div>

      {/* Query Input Box */}
      <div className="ai-workspace" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <form
          className="ai-input-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleInvestigate();
          }}
          style={{ marginBottom: '0.75rem' }}
        >
          <input
            type="text"
            className="ai-input"
            placeholder="Ask about settlements, payment lifecycles, refunds, or exceptions…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button type="submit" className="ai-submit-btn" disabled={loading}>
            {loading ? 'Analyzing…' : <><Send size={15} /> Investigate</>}
          </button>
        </form>

        {/* Security & Grounding Banner */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#10b981' }}>
            <ShieldCheck size={14} />
            VERIFIED FACT: Deterministic reconciliation rules
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#38bdf8' }}>
            <Sparkles size={14} />
            AI EXPLANATION: Grounded in retrieved graph evidence
          </span>
        </div>
      </div>

      {/* Investigation Loading State */}
      {loading && (
        <div className="panel-card" style={{ padding: '2.5rem', textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{ display: 'inline-block', marginBottom: '1rem' }}>
            <Brain size={36} color="#38bdf8" className="kpi-icon" />
          </div>
          <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.35rem' }}>Analyzing Financial Evidence</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Querying relationship graph · Evaluating deterministic rules · Grounding explanation…
          </p>
        </div>
      )}

      {/* Investigation Error */}
      {error && (
        <div className="panel-card" style={{ border: '1px solid #f43f5e', background: 'rgba(244, 63, 94, 0.05)', color: '#fb7185', marginBottom: '1.5rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Investigation Result Card */}
      {!loading && result && (
        <div className="ai-response-box">
          {/* Header */}
          <div className="ai-response-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className={`badge ${result.status === 'COMPLETED' ? 'badge-reconciled' : 'badge-unmatched'}`}>
                {result.status === 'COMPLETED' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                {result.status}
              </span>
              <span className="badge badge-info">
                {result.confidence} CONFIDENCE
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: '#64748b' }}>
              <span className="mono">{result.tool_calls.length} read-only tool calls</span>
            </div>
          </div>

          {/* Finding Section */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#38bdf8', fontWeight: 800, marginBottom: '0.35rem' }}>
              FINDING
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.5 }}>
              {result.finding}
            </div>
          </div>

          {/* Evidence Citations */}
          {result.citations.length > 0 && (
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#10b981', fontWeight: 800, marginBottom: '0.45rem' }}>
                EVIDENCE CITATIONS
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {result.citations.map((c, idx) => (
                  <span
                    key={idx}
                    className="mono"
                    style={{
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      color: '#a7f3d0',
                      padding: '0.3rem 0.6rem',
                      borderRadius: '6px',
                      fontSize: '0.775rem',
                      fontWeight: 700,
                    }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Financial Breakdown Table if present */}
          {result.financial_breakdown && Object.keys(result.financial_breakdown).length > 0 && (
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#fbbf24', fontWeight: 800, marginBottom: '0.45rem' }}>
                FINANCIAL BREAKDOWN
              </div>
              <div
                style={{
                  background: 'var(--bg-tertiary)',
                  borderRadius: '8px',
                  padding: '0.85rem 1rem',
                  border: '1px solid var(--border-subtle)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
                  gap: '0.75rem',
                }}
              >
                {Object.entries(result.financial_breakdown).map(([k, v]) => (
                  <div key={k}>
                    <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                      {k.replace(/_/g, ' ')}
                    </div>
                    <div
                      className="mono"
                      style={{
                        fontSize: '0.95rem',
                        fontWeight: 700,
                        color: (k.includes('delta') || k.includes('discrepancy')) && v !== '0.00' && v !== '₹0.00' ? '#f43f5e' : '#fff',
                      }}
                    >
                      {String(v)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Affected Records */}
          {result.affected_records.length > 0 && (
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', fontWeight: 800, marginBottom: '0.35rem' }}>
                AFFECTED RECORDS
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                {result.affected_records.map((r, idx) => (
                  <span
                    key={idx}
                    className="mono"
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.775rem',
                      color: '#cbd5e1',
                    }}
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Next Check */}
          {result.recommended_next_check.length > 0 && (
            <div style={{ marginBottom: '1rem', padding: '0.85rem 1rem', background: 'rgba(59, 130, 246, 0.08)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
              <div style={{ fontSize: '0.725rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#60a5fa', fontWeight: 800, marginBottom: '0.25rem' }}>
                RECOMMENDED NEXT CHECK
              </div>
              <div style={{ fontSize: '0.875rem', color: '#e2e8f0' }}>
                {result.recommended_next_check.join(' ')}
              </div>
            </div>
          )}

          {/* Read-Only Tool Execution Drawer */}
          <div style={{ marginTop: '1rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              className="nav-tab-btn"
              style={{ padding: '0.3rem 0.55rem', fontSize: '0.75rem' }}
              onClick={() => setShowTools(!showTools)}
            >
              <Terminal size={13} />
              {showTools ? 'Hide Tool Execution Trace' : `Show Agent Tool Execution Trace (${result.tool_calls.length})`}
              {showTools ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {showTools && (
              <div style={{ marginTop: '0.65rem', background: '#090e18', padding: '0.85rem', borderRadius: '8px', fontSize: '0.75rem' }} className="mono">
                {result.tool_calls.map((tc, idx) => (
                  <div key={idx} style={{ marginBottom: '0.4rem', color: '#38bdf8' }}>
                    &gt; {tc.tool_name}({JSON.stringify(tc.arguments)})
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
