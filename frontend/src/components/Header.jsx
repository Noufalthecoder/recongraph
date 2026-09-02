import React from 'react';
import { Layers, ShieldCheck, Activity, Brain, BarChart3, Info, GitFork } from 'lucide-react';

export default function Header({
  activeTab,
  setActiveTab,
  scenarios = [],
  activeScenarioId,
  onSelectScenario,
  exceptionCount = 0,
  onOpenArchitecture,
}) {
  return (
    <header className="app-header">
      <div className="header-inner">
        {/* Brand Section */}
        <div className="brand-section">
          <div className="brand-logo" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('overview')}>
            <div className="logo-badge">
              <Layers size={20} />
            </div>
            <div>
              <div className="brand-title">RECONGRAPH</div>
              <div className="brand-subtitle">Financial Reconciliation Intelligence</div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={15} />
            Overview
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'settlements' ? 'active' : ''}`}
            onClick={() => setActiveTab('settlements')}
          >
            <GitFork size={15} />
            Settlements
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'exceptions' ? 'active' : ''}`}
            onClick={() => setActiveTab('exceptions')}
          >
            <ShieldCheck size={15} />
            Exceptions
            {exceptionCount > 0 && <span className="tab-badge">{exceptionCount}</span>}
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'investigator' ? 'active' : ''}`}
            onClick={() => setActiveTab('investigator')}
          >
            <Brain size={15} />
            AI Investigator
          </button>

          <button
            className={`nav-tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`}
            onClick={() => setActiveTab('benchmark')}
          >
            <BarChart3 size={15} />
            Benchmark
          </button>
        </nav>

        {/* Header Right Controls */}
        <div className="header-controls">
          <button
            className="nav-tab-btn"
            style={{ padding: '0.45rem 0.75rem', background: 'rgba(255,255,255,0.04)', fontSize: '0.8rem' }}
            onClick={onOpenArchitecture}
            title="View Architecture Pipeline"
          >
            <Info size={15} />
            Architecture
          </button>

          <select
            className="scenario-select"
            value={activeScenarioId}
            onChange={(e) => onSelectScenario(e.target.value)}
            title="Switch Demo Scenario"
          >
            {scenarios.map((sc) => (
              <option key={sc.scenario_id} value={sc.scenario_id}>
                {sc.name}
              </option>
            ))}
          </select>

          <div className="status-indicator">
            <div className="status-dot" />
            <span>SYSTEM OPERATIONAL</span>
          </div>
        </div>
      </div>
    </header>
  );
}
