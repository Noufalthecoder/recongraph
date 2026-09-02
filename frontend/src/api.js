/**
 * API client for ReconGraph Backend endpoints.
 */

const BASE_URL = '/api';

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchDashboard() {
  const res = await fetch(`${BASE_URL}/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${BASE_URL}/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function loadScenario(scenarioId) {
  const res = await fetch(`${BASE_URL}/scenarios/${scenarioId}/load`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to switch scenario');
  return res.json();
}

export async function fetchSettlements() {
  const res = await fetch(`${BASE_URL}/settlements`);
  if (!res.ok) throw new Error('Failed to fetch settlements');
  return res.json();
}

export async function fetchSettlementDetail(settlementId) {
  const res = await fetch(`${BASE_URL}/settlements/${settlementId}`);
  if (!res.ok) throw new Error(`Failed to fetch settlement ${settlementId}`);
  return res.json();
}

export async function fetchGraph() {
  const res = await fetch(`${BASE_URL}/graph`);
  if (!res.ok) throw new Error('Failed to fetch graph');
  return res.json();
}

export async function fetchSettlementSubgraph(settlementId) {
  const res = await fetch(`${BASE_URL}/graph/settlements/${settlementId}`);
  if (!res.ok) throw new Error(`Failed to fetch subgraph for ${settlementId}`);
  return res.json();
}

export async function runInvestigation(question, targetType = null, targetId = null) {
  const res = await fetch(`${BASE_URL}/investigation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
