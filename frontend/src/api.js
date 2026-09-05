/**
 * API client for ReconGraph Backend endpoints.
 */

const BASE_URL = '/api';

// Stateless scenario tracking
let currentScenarioId = 'production_demo';

export function getActiveScenarioId() {
  return currentScenarioId;
}

function getHeaders(extraHeaders = {}) {
  return {
    'X-Scenario-Id': currentScenarioId,
    ...extraHeaders
  };
}

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchDashboard() {
  const res = await fetch(`${BASE_URL}/dashboard`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${BASE_URL}/scenarios`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function loadScenario(scenarioId) {
  // Update local client state
  currentScenarioId = scenarioId;
  
  // Make call to backend to verify it exists and get new list
  const res = await fetch(`${BASE_URL}/scenarios/${scenarioId}/load`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to switch scenario');
  return res.json();
}

export async function fetchSettlements() {
  const res = await fetch(`${BASE_URL}/settlements`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch settlements');
  return res.json();
}

export async function fetchSettlementDetail(settlementId) {
  const res = await fetch(`${BASE_URL}/settlements/${settlementId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch settlement ${settlementId}`);
  return res.json();
}

export async function fetchGraph() {
  const res = await fetch(`${BASE_URL}/graph`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to fetch graph');
  return res.json();
}

export async function fetchSettlementSubgraph(settlementId) {
  const res = await fetch(`${BASE_URL}/graph/settlements/${settlementId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch subgraph for ${settlementId}`);
  return res.json();
}

export async function runInvestigation(question, targetType = null, targetId = null) {
  const res = await fetch(`${BASE_URL}/investigation`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      question,
      target_type: targetType,
      target_id: targetId,
    }),
  });
  if (!res.ok) throw new Error('Failed to run investigation');
  return res.json();
}

export async function fetchBenchmark() {
  const res = await fetch(`${BASE_URL}/benchmark`);
  if (!res.ok) throw new Error('Failed to fetch benchmark');
  return res.json();
}
