import React from 'react';
import { ArrowRight, Brain, Database, ShieldCheck, ExternalLink } from 'lucide-react';

export default function OverviewTab({
  dashboardData,
  benchmarkData,
  firstSettlementId,
  onSelectSettlement,
  onInvestigateException,
  setActiveTab
}) {
  if (!dashboardData || !benchmarkData) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>Loading infrastructure components…</div>;
  }

  const { kpis, recent_exceptions } = dashboardData;
  const criticalException = recent_exceptions && recent_exceptions.length > 0 ? recent_exceptions[0] : null;

  return (
    <div className="landing-page">
      {/* 01. HERO */}
      <section className="editorial-hero">
        <div className="section-eyebrow">FINANCIAL RECONCILIATION INTELLIGENCE</div>
        <h1 className="oversized-heading">
          RECONSTRUCT<br/>EVERY RUPEE.
        </h1>
        <p className="editorial-copy">
          Trace payments, settlements, refunds and adjustments through one evidence-backed financial graph.
        </p>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', justifyContent: 'flex-start' }}>
          <button className="btn-primary" onClick={() => firstSettlementId ? onSelectSettlement(firstSettlementId) : setActiveTab('settlements')}>
            INVESTIGATE A SETTLEMENT <ArrowRight size={16} />
          </button>
          <button className="btn-secondary" onClick={() => setActiveTab('investigator')}>
            EXPLORE THE GRAPH
          </button>
        </div>



        {/* Hero Proof Metrics */}
        <div style={{ display: 'flex', justifyContent: 'flex-start', gap: '5rem', marginTop: '3rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: '#fff' }}>{kpis.total_records}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>RECORDS PROCESSED</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: '#fff' }}>{kpis.reconciliation_rate}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>CLEAN RECONCILIATION</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: '#fff' }}>{kpis.benchmark_f1}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>BENCHMARK F1</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="mono" style={{ fontSize: '2rem', fontWeight: 700, color: '#fff' }}>{kpis.throughput_display}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>RECORDS / SEC</div>
          </div>
        </div>
      </section>

      {/* 02. THE PROBLEM */}
      <section className="editorial-section">
        <div className="section-eyebrow">THE PROBLEM</div>
        <h2 className="oversized-heading" style={{ fontSize: '4.5rem' }}>
          FINANCIAL RECORDS<br/>DON'T ARRIVE<br/>AS A CLEAN LEDGER.
        </h2>
        <p className="editorial-copy" style={{ fontSize: '1.25rem', marginBottom: '3rem', maxWidth: '800px', textAlign: 'left' }}>
          One payment can become multiple financial events. Multiple payments can converge into one settlement. Refunds and adjustments can alter what ultimately reaches the bank.
        </p>

        <div className="panel-flat mono" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 2 }}>
          <div>Payment P1 ──┐</div>
          <div>Payment P2 ──┤</div>
          <div>Payment P3 ──┼──► Settlement ───► Bank Entry</div>
          <div>Payment P4 ──┤</div>
          <div>Refund     ──────┘</div>
        </div>
      </section>

      {/* 03. THE RECONGRAPH DIFFERENCE */}
      <section className="editorial-section">
        <h2 className="oversized-heading" style={{ fontSize: '3.5rem' }}>
          DON'T JUST MATCH RECORDS.<br/>RECONSTRUCT THE WORLD.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '2rem', marginTop: '4rem' }}>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
            <div className="mono" style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>01</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>DETERMINISTIC RECONCILIATION</h3>
            <p style={{ color: 'var(--text-secondary)' }}>Rules establish what the observed evidence supports.</p>
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
            <div className="mono" style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>02</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>FINANCIAL GRAPH</h3>
            <p style={{ color: 'var(--text-secondary)' }}>Relationships turn isolated records into an investigable financial system.</p>
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
            <div className="mono" style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }}>03</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>GROUNDED AI</h3>
            <p style={{ color: 'var(--text-secondary)' }}>AI explains verified evidence without determining financial truth.</p>
          </div>
        </div>
      </section>

      {/* 04. THE GRAPH */}
      <section className="editorial-section">
        <h2 className="oversized-heading" style={{ fontSize: '4.5rem' }}>
          EVERY TRANSACTION<br/>HAS A TRACE.
        </h2>
        <p className="editorial-copy" style={{ maxWidth: '800px', textAlign: 'left' }}>
          ReconGraph transforms fragmented financial records into a navigable causal graph.
        </p>
        
        <div className="panel-flat mono" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '3rem', lineHeight: 2 }}>
          <div>Merchant</div>
          <div>      ↓</div>
          <div>Order</div>
          <div>      ↓</div>
          <div>Payment ──────────┐</div>
          <div>      ↓           │</div>
          <div>Settlement Txn    │</div>
          <div>      ↓           │</div>
          <div>Settlement ← Refund</div>
          <div>      ↓</div>
          <div>Bank Entry</div>
        </div>
      </section>

      {/* 05. EXCEPTION */}
      {criticalException && (
        <section className="editorial-section">
          <div className="section-eyebrow">WHEN THE NUMBERS BREAK</div>
          <h2 className="oversized-heading" style={{ fontSize: '5.5rem' }}>
            SHOW ME<br/>WHY.
          </h2>

          <div className="panel-flat" style={{ marginTop: '3rem' }}>
            <div className="mono" style={{ fontSize: '1.5rem', color: '#fff', marginBottom: '3rem' }}>{criticalException.rule_code}</div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr auto 1fr', alignItems: 'center', gap: '2rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>SETTLEMENT</div>
                <div className="mono" style={{ fontSize: '2rem', color: '#fff' }}>{criticalException.expected_value}</div>
              </div>
              <ArrowRight color="var(--text-muted)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>BANK</div>
                <div className="mono" style={{ fontSize: '2rem', color: '#fff' }}>{criticalException.observed_value}</div>
              </div>
              <ArrowRight color="var(--text-muted)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>DELTA</div>
                <div className="mono delta-negative" style={{ fontSize: '2.5rem' }}>{criticalException.difference}</div>
              </div>
            </div>

            <div style={{ marginTop: '4rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--accent-emerald)' }}>
              <ShieldCheck size={16} /> Verified by deterministic reconciliation.
            </div>
          </div>
        </section>
      )}

      {/* 06. INVESTIGATION */}
      <section className="editorial-section">
        <h2 className="oversized-heading" style={{ fontSize: '4.5rem' }}>
          ASK THE<br/>FINANCIAL GRAPH.
        </h2>
        
        <div className="panel-flat" style={{ border: 'none', background: 'rgba(255,255,255,0.02)', marginTop: '3rem' }}>
          <div className="mono" style={{ fontSize: '1.5rem', color: '#fff', marginBottom: '3rem' }}>
            "Why is this settlement short by ₹250?"
          </div>

          <div style={{ display: 'flex', gap: '4rem' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: 'var(--accent-emerald)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={14}/> VERIFIED FACT <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>Deterministic reconciliation</span>
              </div>
              <p style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '2rem' }}>
                Settlement has a bank discrepancy. Rule {criticalException?.rule_code || 'BANK_AMOUNT_MISMATCH'} failed.
              </p>
              
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>FINANCIAL BREAKDOWN</div>
              <div className="mono" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                <div>Settlement: {criticalException?.expected_value || '₹14,396.00'}</div>
                <div>Bank: {criticalException?.observed_value || '₹14,146.00'}</div>
                <div className="delta-negative">Delta: {criticalException?.difference || '−₹250.00'}</div>
              </div>
            </div>
            
            <div style={{ width: '1px', background: 'var(--border-subtle)' }}></div>
            
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: 'var(--accent-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Brain size={14}/> AI EXPLANATION <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>Grounded in retrieved evidence</span>
              </div>
              <p style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '2rem' }}>
                The evidence indicates a missing transaction fee adjustment.
              </p>
              
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>EVIDENCE</div>
              <div className="mono" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: '2rem' }}>
                <div>[E1] Settlement</div>
                <div>[E2] BankEntry</div>
                <div>[E3] {criticalException?.rule_code || 'BANK_AMOUNT_MISMATCH'}</div>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>RECOMMENDED NEXT CHECK</div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Inspect the corresponding bank statement transaction for hidden deductions.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 07. BENCHMARK */}
      <section className="editorial-section">
        <h2 className="oversized-heading" style={{ fontSize: '4.5rem' }}>
          MEASURED.<br/>NOT CLAIMED.
        </h2>
        <p className="editorial-copy" style={{ maxWidth: '800px', textAlign: 'left' }}>
          ReconGraph evaluates reconciliation performance against isolated synthetic Ground Truth.
        </p>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4rem', marginTop: '4rem', marginBottom: '4rem' }}>
          <div>
            <div className="mono" style={{ fontSize: '3rem', fontWeight: 800, color: '#fff' }}>{benchmarkData.precision}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>PRECISION</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: '3rem', fontWeight: 800, color: '#fff' }}>{benchmarkData.recall}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>RECALL</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: '3rem', fontWeight: 800, color: '#fff' }}>{benchmarkData.f1_score}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>F1</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: '3rem', fontWeight: 800, color: '#fff' }}>{benchmarkData.total_records}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>RECORDS EVALUATED</div>
          </div>
        </div>

        <div className="panel-flat" style={{ padding: 0 }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Anomaly Categories</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>AMOUNT MISMATCH</td>
                <td><span className="status-text status-reconciled">VERIFIED</span></td>
              </tr>
              <tr>
                <td>MISSING RECORD</td>
                <td><span className="status-text status-reconciled">VERIFIED</span></td>
              </tr>
              <tr>
                <td>DUPLICATE RECORD</td>
                <td><span className="status-text status-reconciled">VERIFIED</span></td>
              </tr>
              <tr>
                <td>IDENTIFIER MISMATCH</td>
                <td><span className="status-text status-reconciled">VERIFIED</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 08. SECURITY / TRUST */}
      <section className="editorial-section">
        <h2 className="oversized-heading" style={{ fontSize: '4.5rem' }}>
          TRUTH FIRST.<br/>AI SECOND.
        </h2>
        
        <div style={{ display: 'flex', gap: '4rem', marginTop: '4rem' }}>
          <div className="mono" style={{ flex: 1, fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 2 }}>
            <div>GROUND TRUTH</div>
            <div>↓</div>
            <div>OBSERVED WORLD</div>
            <div>↓</div>
            <div style={{ color: '#fff' }}>DETERMINISTIC RECONCILIATION</div>
            <div>↓</div>
            <div>FINANCIAL GRAPH</div>
            <div>↓</div>
            <div>EVIDENCE</div>
            <div>↓</div>
            <div style={{ color: 'var(--accent-primary)' }}>AI INVESTIGATOR</div>
          </div>

          <div style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '3rem' }}>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem' }}>READ-ONLY AI</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>No financial mutation tools.</p>
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem' }}>EVIDENCE GROUNDED</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>Answers are validated against retrieved facts.</p>
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem' }}>TRUTH ISOLATED</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>Benchmark Ground Truth never enters runtime investigation.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 09. FINAL CTA */}
      <section className="editorial-hero" style={{ marginTop: '12rem', marginBottom: '4rem' }}>
        <h2 className="oversized-heading" style={{ fontSize: '6rem' }}>
          EVERY<br/>RUPEE.<br/>ACCOUNTED FOR.
        </h2>
        <p className="editorial-copy">
          Investigate the financial graph.
        </p>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', justifyContent: 'flex-start' }}>
          <button className="btn-primary" onClick={() => setActiveTab('settlements')}>
            OPEN RECONGRAPH <ArrowRight size={16} />
          </button>
          <button className="btn-secondary" onClick={() => setActiveTab('benchmark')}>
            VIEW BENCHMARK
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '4rem', paddingBottom: '4rem', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 800, color: '#fff', marginBottom: '0.5rem' }}>RECONGRAPH</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '2rem' }}>Financial Reconciliation Intelligence</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Built for financial operations.</div>
        </div>
        <div style={{ display: 'flex', gap: '3rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.85rem' }}>
            <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('overview'); }} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Overview</a>
            <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('settlements'); }} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Settlements</a>
            <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('exceptions'); }} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Exceptions</a>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.85rem' }}>
            <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('investigator'); }} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Investigator</a>
            <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('benchmark'); }} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Benchmark</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
