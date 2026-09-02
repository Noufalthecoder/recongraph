import React from 'react';
import { X, Layers, ArrowDown, ShieldCheck, Brain, Database, Cpu, Lock } from 'lucide-react';

export default function ArchitectureModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const steps = [
    {
      icon: <Database size={18} color="#8b5cf6" />,
      title: '1. Ground Truth (Simulator)',
      desc: 'Immutable synthetic financial universe with mathematically exact settlement equations.',
      isolated: true,
    },
    {
      icon: <ShieldCheck size={18} color="#f59e0b" />,
      title: '2. Anomaly Injection',
      desc: 'Deterministic corruption layer injecting controlled amount mismatches, missing records, or identifier corruptions.',
      isolated: true,
    },
    {
      icon: <Layers size={18} color="#3b82f6" />,
      title: '3. Observed World (Ingested Evidence)',
      desc: 'The only data seen by reconciliation. Contains zero ground truth labels or anomaly metadata.',
      isolated: false,
    },
    {
      icon: <Cpu size={18} color="#10b981" />,
      title: '4. Deterministic Reconciliation Engine',
      desc: '100% deterministic rule engine calculating exact Decimal sums, matches, and exceptions.',
      isolated: false,
    },
    {
      icon: <Layers size={18} color="#06b6d4" />,
      title: '5. Financial Graph & Evidence Layer',
      desc: 'Directed graph indexing causal relationships and binding deterministic mathematical evidence.',
      isolated: false,
    },
    {
      icon: <Brain size={18} color="#ec4899" />,
      title: '6. AI Investigation Agent',
      desc: 'Security-guarded LLM layer using read-only graph tools to explain reconciliation evidence in natural language.',
      isolated: false,
    },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>
          <X size={20} />
        </button>

        <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff', marginBottom: '0.25rem' }}>
          ReconGraph Architecture Pipeline
        </h2>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.5rem' }}>
          Security-first deterministic financial reconciliation and evidence-grounded investigation.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {steps.map((step, idx) => (
            <div key={idx}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: step.isolated ? 'rgba(245, 158, 11, 0.05)' : 'var(--bg-tertiary)',
                  border: `1px solid ${step.isolated ? 'rgba(245, 158, 11, 0.25)' : 'var(--border-subtle)'}`,
                  borderRadius: '10px',
                  padding: '0.75rem 1rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <div style={{ background: '#090e18', padding: '0.5rem', borderRadius: '8px' }}>
                    {step.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc' }}>
                      {step.title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {step.desc}
                    </div>
                  </div>
                </div>

                {step.isolated ? (
                  <span className="badge badge-unmatched" style={{ fontSize: '0.65rem' }}>
                    <Lock size={10} /> Isolated Benchmark
                  </span>
                ) : (
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                    Production Runtime
                  </span>
                )}
              </div>

              {idx < steps.length - 1 && (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '0.15rem 0' }}>
                  <ArrowDown size={14} style={{ margin: '0 auto' }} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer Principles */}
        <div
          style={{
            marginTop: '1.25rem',
            padding: '1rem',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '10px',
            fontSize: '0.8rem',
            color: '#a7f3d0',
            lineHeight: 1.4,
          }}
        >
          <strong>Core Axiom:</strong> <em>"Rules determine financial truth. Evidence explains truth. AI explains the evidence."</em> The AI layer is an interpreter, not a financial ledger authority.
        </div>
      </div>
    </div>
  );
}
