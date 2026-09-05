import React from 'react';
import { Home, List, ShieldAlert, Search, Activity, Network } from 'lucide-react';
import DatasetSelector from './DatasetSelector.jsx';

export default function Sidebar({
  activeTab,
  setActiveTab,
  scenarios,
  activeScenarioId,
  onSelectScenario,
  isSwitching,
  scenarioError,
  exceptionCount,
  onOpenArchitecture
}) {
  const tabs = [
    { id: 'overview', label: 'Control Center', icon: Home },
    { id: 'settlements', label: 'Settlements', icon: List },
    { id: 'exceptions', label: 'Exceptions', icon: ShieldAlert, count: exceptionCount },
    { id: 'investigator', label: 'Investigator', icon: Search },
    { id: 'benchmark', label: 'Benchmark', icon: Activity },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <Network className="brand-icon" size={24} />
        <div>
          <div className="brand-title">RECONGRAPH</div>
          <div className="brand-subtitle">Financial Reconciliation</div>
        </div>
      </div>

      <div className="sidebar-scenario" style={{ marginBottom: '2rem' }}>
        <DatasetSelector 
          scenarios={scenarios}
          activeScenarioId={activeScenarioId}
          onSelectScenario={onSelectScenario}
          isSwitching={isSwitching}
          scenarioError={scenarioError}
        />
      </div>

      <nav className="sidebar-nav">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`sidebar-nav-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <tab.icon size={18} />
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span className="nav-badge">{tab.count}</span>
            )}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-nav-item" onClick={onOpenArchitecture}>
          <Network size={18} />
          <span>System Architecture</span>
        </button>
      </div>
    </aside>
  );
}
