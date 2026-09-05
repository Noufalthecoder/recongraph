import React, { useState, useEffect } from 'react';
import { ArrowRight, Brain, Database, ShieldCheck, HelpCircle, RotateCcw } from 'lucide-react';
import { runInvestigation } from '../api.js';

export default function InvestigatorTab({ initialQuestion, targetType, targetId }) {
  const [question, setQuestion] = useState(initialQuestion || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (initialQuestion) {
      setQuestion(initialQuestion);
    }
  }, [initialQuestion]);

  const handleInvestigate = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await runInvestigation(question, targetType, targetId);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Investigation failed');
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "Why is this settlement short by ₹250?",
    "Trace this payment to the bank.",
    "Show refunds affecting this settlement.",
    "Why was this settlement not reconciled?",
    "Trace this payment end-to-end."
  ];

  return (
    <div>
      {/* Page Hero */}
      <section className="editorial-section" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h1 className="oversized-heading" style={{ fontSize: '3rem' }}>
          INVESTIGATE<br/>THE FINANCIAL WORLD.
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', borderRadius: '20px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.2)', fontSize: '0.75rem', fontWeight: 'bold', color: '#38bdf8', cursor: 'help' }} title={result?.provider_mode === 'live' ? "Live investigation mode." : "Offline investigation mode. No external LLM required."}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: result?.provider_mode === 'live' ? '#10b981' : '#38bdf8' }}></span>
          {result?.provider_mode === 'live' ? 'LIVE LLM' : 'DETERMINISTIC DEMO'}
        </div>
      </section>

      {/* Input Section */}
      <div className="ai-workspace">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleInvestigate();
          }}
        >
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              className="ai-input"
              style={{ paddingRight: '4rem' }}
              placeholder="Ask the financial graph..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !question.trim()}
              style={{ position: 'absolute', right: '0', top: '50%', transform: 'translateY(-50%)', padding: '0.65rem 1rem' }}
            >
              {loading ? 'Investigating...' : <ArrowRight size={18} />}
            </button>
          </div>
        </form>

        <div style={{ marginTop: '1rem', display: 'flex', gap: '2rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-emerald)' }}>
            <ShieldCheck size={14} /> VERIFIED FACT: Deterministic reconciliation rules
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-primary)' }}>
            <Brain size={14} /> INVESTIGATION EXPLANATION: Grounded in retrieved evidence
          </div>
        </div>
      </div>

      {error && (
        <div className="panel-card" style={{ marginTop: '2rem', border: '1px solid rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.06)', padding: '2rem', textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', marginBottom: '0.5rem' }}>
            INVESTIGATION UNAVAILABLE
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.5rem', lineHeight: 1.5 }}>
            {error}
          </p>
          <button
            className="ai-submit-btn"
            style={{ padding: '0.5rem 1.25rem', fontSize: '0.85rem' }}
            onClick={handleInvestigate}
          >
            <RotateCcw size={14} /> RETRY
          </button>
        </div>
      )}

      {/* Suggestions */}
      {!loading && !result && !error && (
        <div style={{ marginTop: '3rem' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Suggested Investigations
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            {suggestedQuestions.map((sq, i) => (
              <button
                key={i}
                className="btn-secondary"
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.85rem' }}
                onClick={() => setQuestion(sq)}
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Response Box */}
      {!loading && result && (
        <div className="ai-response-box">
          <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: '#fff' }}>FINDING</h3>
          <div style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: '2.5rem', lineHeight: 1.6 }}>
            {result.finding}
          </div>

          <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>EVIDENCE CITATIONS</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2.5rem' }}>
            {result.citations && result.citations.map((c, idx) => (
              <div key={idx} className="panel-flat" style={{ padding: '1rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '3px solid var(--accent-primary)' }}>
                <Database size={16} color="var(--accent-primary)" />
                <span className="mono" style={{ fontSize: '0.9rem' }}>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
