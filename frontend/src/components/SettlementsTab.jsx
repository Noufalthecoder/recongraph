import React, { useState, useMemo } from 'react';
import { Search, Filter, ArrowRight, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react';

export default function SettlementsTab({ settlements = [], onSelectSettlement }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filteredSettlements = useMemo(() => {
    return settlements.filter((s) => {
      const matchesSearch =
        s.settlement_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.utr.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || s.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [settlements, searchTerm, statusFilter]);

  return (
    <div>
      {/* Page Hero */}
      {/* Page Hero */}
      <section className="editorial-section" style={{ marginBottom: '4rem' }}>
        <h1 className="oversized-heading" style={{ fontSize: '3rem' }}>SETTLEMENTS</h1>
        <p className="editorial-copy">"Every payout, traced." Batch payout aggregations and bank-side statement credit tracking.</p>
      </section>

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ position: 'relative', minWidth: '320px' }}>
          <Search
            size={16}
            style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
          />
          <input
            type="text"
            className="ai-input"
            style={{ paddingLeft: '2.75rem' }}
            placeholder="Search by Settlement ID or UTR…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['ALL', 'RECONCILED', 'EXCEPTION', 'UNMATCHED'].map((st) => (
            <button
              key={st}
              className={`nav-tab-btn ${statusFilter === st ? 'active' : ''}`}
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Settlements Table */}
      <div className="panel-flat" style={{ padding: '0' }}>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Settlement ID</th>
                <th>UTR Reference</th>
                <th>Settlement Amount</th>
                <th>Bank Credit</th>
                <th>Discrepancy (Delta)</th>
                <th>Line Items</th>
                <th>Reconciliation Status</th>
                <th>Created At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredSettlements.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                    No settlements found matching your query.
                  </td>
                </tr>
              ) : (
                filteredSettlements.map((s) => (
                  <tr
                    key={s.settlement_id}
                    className="clickable-row"
                    onClick={() => onSelectSettlement(s.settlement_id)}
                  >
                    <td className="mono" style={{ fontWeight: 700, color: '#38bdf8' }}>
                      {s.settlement_id}
                    </td>
                    <td className="mono" style={{ color: '#94a3b8' }}>
                      {s.utr}
                    </td>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      {s.amount}
                    </td>
                    <td className="mono" style={{ color: '#94a3b8' }}>
                      {s.bank_amount || '—'}
                    </td>
                    <td
                      className={`mono ${
                        s.difference && !s.difference.includes('0.00') ? 'delta-negative' : 'delta-zero'
                      }`}
                    >
                      {s.difference || '₹0.00'}
                    </td>
                    <td className="mono">{s.transaction_count} items</td>
                    <td>
                      <span className={`status-text ${
                          s.status === 'RECONCILED' ? 'status-reconciled'
                          : s.status === 'EXCEPTION' ? 'status-exception'
                          : 'status-unmatched'
                        }`}>
                        {s.status === 'RECONCILED' && <CheckCircle2 size={14} />}
                        {s.status === 'EXCEPTION' && <AlertTriangle size={14} />}
                        {s.status}
                      </span>
                    </td>
                    <td style={{ color: '#64748b', fontSize: '0.8rem' }}>
                      {new Date(s.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectSettlement(s.settlement_id);
                        }}
                      >
                        Investigate <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
