# ReconGraph — Financial Reconciliation Intelligence Platform

> **Deterministic Financial Reconciliation & Evidence-Grounded AI Investigation**  
> *Built for the Razorpay AI Buildathon*

---

## 🚀 Overview

**ReconGraph** is an enterprise-grade financial reconciliation engine and AI investigation platform. It solves the multi-party reconciliation problem across payment gateways, merchants, bank statements, and ledger accounts by enforcing deterministic financial rules and using an AI agent strictly to **explain verified evidence**, never to invent financial truth.

> **Foundational Axiom:**  
> *"RULES DETERMINE TRUTH. EVIDENCE EXPLAINS TRUTH. AI EXPLAINS THE EVIDENCE."*

---

## 🏛️ Architecture Pipeline

```
Ground Truth (Simulator)
   │
   ▼
Anomaly Injection ─────────► Anomaly Manifest (Isolated Benchmark Truth)
   │
   ▼
Observed World (Ingested Evidence)
   │
   ▼
Deterministic Reconciliation Engine ──► Reconciliation Result
   │                                          │
   ▼                                          ▼
Financial Relationship Graph ────────► Graph Evidence Layer
   │                                          │
   └───────────────────┬──────────────────────┘
                       │
                       ▼
             AI Investigation Agent
          (Read-Only Graph & Rule Tools)
                       │
                       ▼
             Operator Demo Console
```

---

## 🌟 Key Capabilities

1. **Deterministic Reconciliation Engine:** 100% rule-based ledger reconciliation with Decimal money safety (zero float conversions).
2. **Financial Relationship Graph:** In-memory directed graph modeling Merchants, Orders, Payments, Refunds, Adjustments, Transfers, Settlement Transactions, Settlements, and Bank Entries.
3. **Many-to-One Payout Aggregation:** Supports batch payout aggregation, fee/tax calculations, refund debits, and dispute adjustments.
4. **AI Financial Investigator:** Operator-facing natural language investigation assistant equipped with 11 read-only graph and evidence tools.
5. **Security Guardrails & Grounding:** Prompt-injection defense, data exfiltration protection, and deterministic answer validation preventing financial hallucinations.
6. **Isolated Benchmark Harness:** GroundTruth isolation measuring precision, recall, and F1 across synthetic anomaly datasets.
7. **Operator Console:** Full-stack dashboard with interactive SVG financial graph, settlement intelligence panels, and exception queues.

---

## 📊 Benchmark & Evaluation Results

Across **534+ synthetic financial records** and **30 benchmark scenario runs**:

| Metric | Measured Value |
|---|---|
| **Precision** | **1.00 (100.0%)** |
| **Recall** | **1.00 (100.0%)** |
| **F1 Score** | **1.00 (100.0%)** |
| **False Positives** | **0** |
| **False Negatives** | **0** |
| **Clean Reconciliation Rate** | **100.0%** |
| **Engine Throughput** | **25,000+ records / sec** |

---

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
# Python backend
pip install -r requirements.txt

# React frontend
cd frontend
npm install
npm run build
cd ..
```

### 2. Run Test Suite
```bash
pytest
```
*180 tests passing in ~1.1s.*

### 3. Launch Demo Application
```bash
uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 🔒 Security & AI Guardrails

- **Read-Only Tools:** The AI Investigator has no write or mutation capabilities.
- **Ground Truth Isolation:** The runtime reconciliation engine and AI agent operate strictly on `ObservedWorld`.
- **Exact Decimals:** Financial numbers are serialized strictly as strings without floating-point rounding errors.
- **Offline Mock Provider:** Full testability and demo capabilities without external API dependencies.
