# ReconGraph — Operator Demo Application

> **Authoritative Technical Documentation for Step 11: Demo Application & Operator Console**  
> Package: `backend/app/api/` & `frontend/`

---

## 1. System Architecture

ReconGraph delivers a full-stack, security-first financial reconciliation and AI investigation platform:

```mermaid
flowchart TD
    subgraph Data Generation (Isolated)
        GT[Ground Truth Simulator]
        AI_Inj[Anomaly Injection Engine]
        AM[Anomaly Manifest]
        GT --> AI_Inj
        AI_Inj --> AM
    end

    subgraph Runtime Data Layer
        OW[Observed World]
        AI_Inj --> OW
    end

    subgraph Deterministic Core
        DRE[Deterministic Reconciliation Engine]
        RR[Reconciliation Result]
        OW --> DRE
        DRE --> RR
    end

    subgraph Investigation Graph & Evidence
        FGB[Financial Graph Builder]
        FG[Financial Graph]
        GEL[Graph Evidence Layer]
        IQE[Investigation Query Engine]
        OW --> FGB
        RR --> FGB
        FGB --> FG
        FGB --> GEL
        FG --> IQE
        GEL --> IQE
    end

    subgraph Application API Layer
        API[FastAPI Backend: /api/*]
        DS[Demo State Manager]
        IQE --> DS
        RR --> DS
        DS --> API
    end

    subgraph AI Investigation Layer
        AIA[AI Investigation Agent]
        LLM[Deterministic Mock / OpenAI Provider]
        API --> AIA
        AIA --> IQE
        AIA --> LLM
    end

    subgraph Evaluation Harness (Isolated)
        BR[Benchmark Runner]
        GT -.-> BR
        AM -.-> BR
        OW -.-> BR
        RR -.-> BR
        BR --> API
    end

    subgraph Frontend Operator Console
        UI[React 18 + Vite Dashboard]
        API --> UI
    end
```

---

## 2. API Endpoints

All API endpoints are read-only and return exact `Decimal` strings for monetary values.

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | Service liveness and health status. |
| `/api/dashboard` | `GET` | High-level KPIs, settlement health counts, exception distribution, and recent exceptions. |
| `/api/scenarios` | `GET` | Catalogue of deterministic demo scenarios. |
| `/api/scenarios/{id}/load` | `POST` | Atomically loads a demo scenario into active application state. |
| `/api/settlements` | `GET` | Paginated list of settlement payout headers with bank credit and delta. |
| `/api/settlements/{id}` | `GET` | Detailed settlement intelligence: equation breakdown, constituent line items, exceptions, and evidence. |
| `/api/graph` | `GET` | Complete serialized nodes and directed edges for the active `ObservedWorld`. |
| `/api/graph/settlements/{id}` | `GET` | Focused causal subgraph around a specific settlement payout. |
| `/api/investigation` | `POST` | Natural language operator query executed via the AI Investigator with read-only tools. |
| `/api/benchmark` | `GET` | Authoritative benchmark metrics, precision, recall, F1, and anomaly type breakdown. |

---

## 3. Demo Datasets & Scenarios

The platform includes six pre-configured, deterministic synthetic scenarios:

1. **Production Demo (Large Batch - Default):** Realistic multi-settlement composite workload with ~100+ records, multiple payments, fee/tax calculations, refunds, adjustments, and an authentic ₹250 bank mismatch exception.
2. **Clean Batch (100% Reconciled):** Clean multi-settlement batch with zero exceptions and 100% clean reconciliation rate.
3. **Bank Amount Mismatch (-₹250):** Dedicated settlement with ₹250 discrepancy against bank credit statement.
4. **Missing Record:** Settlement transaction referencing a payment missing from the ingested batch.
5. **Duplicate Record:** Duplicate payment entity with duplicate primary key ingested into batch.
6. **Identifier Mismatch:** Bank entry containing corrupted UTR identifier preventing direct UTR settlement matching.

---

## 4. Frontend Operator Console

The frontend is built with React 18 and Vite:

- **Overview (Reconciliation Control Center):** Top KPI cards (Records Processed, Reconciliation Rate, Open Exceptions, Benchmark F1, Throughput), Settlement Health breakdown, Exception Distribution, and Recent Exceptions table.
- **Settlements View:** Comprehensive payout table with UTR, Amount, Bank Credit, and highlighted Shortfall Deltas.
- **Settlement Investigation:** Split-screen layout featuring an interactive SVG financial graph on the left and a settlement equation breakdown + deterministic evidence layer on the right.
- **Exception Operations Queue:** Categorized exception queue with filter tabs and one-click *"Why? (AI)"* investigation triggers.
- **AI Financial Investigator:** Conversational investigation interface with preset prompts, citation chips, structured finding cards, mathematical breakdowns, affected records, recommended next checks, and tool call traces.
- **Benchmark Dashboard:** Measured precision, recall, F1, and clean reconciliation rates across synthetic anomaly datasets.
- **Architecture Pipeline View:** Visual modal explaining Ground Truth isolation and deterministic reconciliation principles.

---

## 5. Security & Isolation Guarantees

1. **Read-Only Security Model:** No API endpoint or AI tool permits data mutation, arbitrary code execution, shell execution, or filesystem writes.
2. **Ground Truth Isolation:** `GroundTruth` and `AnomalyManifest` are architecturally isolated in evaluation harnesses and are never exposed to the runtime reconciliation engine, graph, or AI agent.
3. **Prompt Injection Defense:** Untrusted domain strings are wrapped and sanitized; prompt injection phrases trigger safe security refusals.
4. **Data Exfiltration Defense:** Rejects attempts to query API keys, environment variables, or internal prompts.
5. **Answer Validation:** Validates that all monetary figures and entity IDs in AI responses are present in retrieved evidence context.

---

## 6. How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ / npm

### Step 1: Install Dependencies
```bash
# Install Python backend dependencies
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend
npm install
npm run build
cd ..
```

### Step 2: Start Backend Server
```bash
uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### Step 3: Access Operator Console
- Open your browser to: `http://127.0.0.1:8000` (or `http://localhost:5173` if running Vite dev server `npm run dev` in `frontend/`).
