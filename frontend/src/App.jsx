import React, { useState, useEffect } from 'react';
import Header from './components/Header.jsx';
import OverviewTab from './components/OverviewTab.jsx';
import SettlementsTab from './components/SettlementsTab.jsx';
import SettlementInvestigationTab from './components/SettlementInvestigationTab.jsx';
import ExceptionsTab from './components/ExceptionsTab.jsx';
import InvestigatorTab from './components/InvestigatorTab.jsx';
import BenchmarkTab from './components/BenchmarkTab.jsx';
import ArchitectureModal from './components/ArchitectureModal.jsx';
import {
  fetchDashboard,
  fetchScenarios,
  loadScenario,
  fetchSettlements,
  fetchSettlementDetail,
  fetchSettlementSubgraph,
  fetchBenchmark,
} from './api.js';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [scenarios, setScenarios] = useState([]);
  const [activeScenarioId, setActiveScenarioId] = useState('production_demo');
  const [dashboardData, setDashboardData] = useState(null);
  const [settlements, setSettlements] = useState([]);
  const [selectedSettlementId, setSelectedSettlementId] = useState(null);
  const [settlementDetail, setSettlementDetail] = useState(null);
  const [settlementSubgraph, setSettlementSubgraph] = useState(null);
  const [settlementLoading, setSettlementLoading] = useState(false);
  const [settlementError, setSettlementError] = useState(null);
  const latestSettlementRequestRef = React.useRef(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [exceptionsFilter, setExceptionsFilter] = useState('ALL');
  const [investigatorPreset, setInvestigatorPreset] = useState({ question: '', type: null, id: null });
  const [isArchitectureModalOpen, setIsArchitectureModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(null);

  // Initial Data Load
  const refreshAllData = async () => {
    try {
      setLoading(true);
      setApiError(null);
      const [scRes, dbRes, setlRes, bmRes] = await Promise.all([
        fetchScenarios(),
        fetchDashboard(),
        fetchSettlements(),
        fetchBenchmark(),
      ]);
      setScenarios(scRes.scenarios);
      setActiveScenarioId(scRes.active_scenario_id);
      setDashboardData(dbRes);
      setSettlements(setlRes.settlements);
      setBenchmarkData(bmRes);
    } catch (err) {
      console.error('Failed to load ReconGraph data:', err);
      setApiError(err.message || 'Backend service unreachable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  // Scenario Switcher
  const handleSelectScenario = async (scId) => {
    try {
      setLoading(true);
      latestSettlementRequestRef.current = null;
      setSelectedSettlementId(null);
      setSettlementDetail(null);
      setSettlementSubgraph(null);
      setSettlementLoading(false);
      setSettlementError(null);
      if (activeTab === 'settlement_investigation') {
        setActiveTab('settlements');
      }

      await loadScenario(scId);
      setActiveScenarioId(scId);
      await refreshAllData();
    } catch (err) {
      console.error('Failed to switch scenario:', err);
    } finally {
      setLoading(false);
    }
  };

  // Drill down into Settlement Investigation
  const handleSelectSettlement = async (setlId) => {
    if (!setlId) return;
    latestSettlementRequestRef.current = setlId;
    setSelectedSettlementId(setlId);
    setSettlementLoading(true);
    setSettlementError(null);
    setSettlementDetail(null);
    setSettlementSubgraph(null);
    setActiveTab('settlement_investigation');

    try {
      const [detRes, subRes] = await Promise.allSettled([
        fetchSettlementDetail(setlId),
        fetchSettlementSubgraph(setlId),
      ]);

      // Protect against race conditions / stale out-of-order responses
      if (latestSettlementRequestRef.current !== setlId) {
        return;
      }

      if (detRes.status === 'fulfilled') {
        setSettlementDetail(detRes.value);
        if (subRes.status === 'fulfilled') {
          setSettlementSubgraph(subRes.value);
        } else {
          console.warn(`Subgraph load failed for ${setlId}:`, subRes.reason);
          setSettlementSubgraph({ nodes: [], edges: [] });
        }
      } else {
        const errorMsg = detRes.reason?.message || `Unable to fetch settlement ${setlId}`;
        setSettlementError(errorMsg);
      }
    } catch (err) {
      if (latestSettlementRequestRef.current === setlId) {
        setSettlementError(err.message || `Failed to fetch settlement ${setlId}`);
      }
    } finally {
      if (latestSettlementRequestRef.current === setlId) {
        setSettlementLoading(false);
      }
    }
  };

  // Jump to AI Investigator
  const handleOpenAIInvestigator = (qText, targetType = null, targetId = null) => {
    setInvestigatorPreset({ question: qText, type: targetType, id: targetId });
    setActiveTab('investigator');
  };

  // Jump from Exception to AI Investigator
  const handleInvestigateException = (exc) => {
    const qText = `Why did ${exc.entity_type} ${exc.entity_id} fail reconciliation with rule ${exc.rule_code}?`;
    handleOpenAIInvestigator(qText, exc.entity_type, exc.entity_id);
  };

  // Navigate to Exceptions with filter
  const handleNavigateExceptions = (ruleFilter) => {
    setExceptionsFilter(ruleFilter);
    setActiveTab('exceptions');
  };

  return (
    <div className="app-container">
      {/* Global Header */}
      <Header
        activeTab={activeTab === 'settlement_investigation' ? 'settlements' : activeTab}
        setActiveTab={setActiveTab}
        scenarios={scenarios}
        activeScenarioId={activeScenarioId}
        onSelectScenario={handleSelectScenario}
        exceptionCount={dashboardData?.kpis?.exception_count || 0}
        onOpenArchitecture={() => setIsArchitectureModalOpen(true)}
      />

      {/* Backend Unavailable Error Banner */}
      {apiError && (
        <div style={{ maxWidth: '1560px', margin: '1rem auto 0', padding: '1rem 2rem', width: '100%' }}>
          <div className="panel-card" style={{ border: '1px solid #f43f5e', background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '0.25rem' }}>Backend Service Unavailable</h3>
            <p style={{ fontSize: '0.85rem' }}>Start the ReconGraph FastAPI server (`uvicorn backend.app.api.app:app`) to connect.</p>
          </div>
        </div>
      )}

      {/* Main Screen Content */}
      <main className="main-content">
        {activeTab === 'overview' && (
          <OverviewTab
            dashboardData={dashboardData}
            onSelectSettlement={handleSelectSettlement}
            onInvestigateException={handleInvestigateException}
            onNavigateExceptions={handleNavigateExceptions}
          />
        )}

        {activeTab === 'settlements' && (
          <SettlementsTab
            settlements={settlements}
            onSelectSettlement={handleSelectSettlement}
          />
        )}

        {activeTab === 'settlement_investigation' && (
          <SettlementInvestigationTab
            settlementId={selectedSettlementId}
            settlementDetail={settlementDetail}
            subgraph={settlementSubgraph}
            loading={settlementLoading}
            error={settlementError}
            onRetry={handleSelectSettlement}
            onBack={() => setActiveTab('settlements')}
            onOpenAIInvestigator={handleOpenAIInvestigator}
          />
        )}

        {activeTab === 'exceptions' && (
          <ExceptionsTab
            exceptions={dashboardData?.recent_exceptions || []}
            initialFilter={exceptionsFilter}
            onInvestigateException={handleInvestigateException}
            onSelectSettlement={handleSelectSettlement}
          />
        )}

        {activeTab === 'investigator' && (
          <InvestigatorTab
            initialQuestion={investigatorPreset.question}
            targetType={investigatorPreset.type}
            targetId={investigatorPreset.id}
          />
        )}

        {activeTab === 'benchmark' && (
          <BenchmarkTab benchmarkData={benchmarkData} />
        )}
      </main>

      {/* Architecture Modal */}
      <ArchitectureModal
        isOpen={isArchitectureModalOpen}
        onClose={() => setIsArchitectureModalOpen(false)}
      />
    </div>
  );
}
