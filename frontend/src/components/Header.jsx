import React from 'react';

export default function Header({
  activeTab,
  setActiveTab,
  scenarios,
  activeScenarioId,
  onSelectScenario,
}) {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'settlements', label: 'Settlements' },
    { id: 'exceptions', label: 'Exceptions' },
    { id: 'investigator', label: 'Investigator' },
    { id: 'benchmark', label: 'Benchmark' },
  ];

  return (
    <header className="app-header">
      <div className="header-inner">
        {/* Brand */}
        <div className="brand-section">
          <div className="brand-logo" onClick={() => setActiveTab('overview')} style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="6" cy="6" r="3" fill="#38bdf8" />
              <circle cx="18" cy="18" r="3" fill="#10b981" />
              <circle cx="6" cy="18" r="3" fill="#fbbf24" />
              <path d="M 6 9 L 6 15" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
              <path d="M 8 7.5 L 16 16.5" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
            </svg>
            <div>
              <div className="brand-title">RECONGRAPH</div>
              <div className="brand-subtitle">Financial Reconciliation Intelligence</div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="nav-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Controls */}
        <div className="header-controls">
          <select
            className="scenario-select"
            value={activeScenarioId}
            onChange={(e) => onSelectScenario(e.target.value)}
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.label}
              </option>
            ))}
          </select>
          <div className="status-indicator">
            <div className="status-dot"></div>
            System Operational
          </div>
        </div>
      </div>
    </header>
  );
}
