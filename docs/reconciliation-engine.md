# ReconGraph — Deterministic Reconciliation Engine

> **Authoritative Technical Documentation for Step 7: Core Deterministic Reconciliation Engine**  
> Package: `backend/app/reconciliation/`

---

## 1. Overview & Core Philosophy

The ReconGraph Reconciliation Engine is the deterministic, rule-based truth-checking layer of the system. It validates financial records ingested via `ObservedWorld` and establishes:
- Reconciled settlements and transaction links
- Ledger composition and line-item arithmetic integrity
- Banking statement matches (Gateway payout $\leftrightarrow$ Bank statement credit)
- Structural referential integrity and duplicate detection
- Exact mathematical and identifier evidence for all discrepancies

### Non-Negotiable Tenet
> **RULES DETERMINE TRUTH.**  
> **EVIDENCE EXPLAINS TRUTH.**  
> **AI WILL LATER EXPLAIN THE EVIDENCE.**

The reconciliation engine operates with **zero AI / LLM dependencies**, **zero randomness**, and **zero floating-point math**.

---

## 2. Benchmark Boundary & GroundTruth Isolation

To guarantee benchmark integrity and avoid label leakage:
- The engine consumes **ONLY** `ObservedWorld`.
- The engine **NEVER** imports or receives `GroundTruth`, `ScenarioLabel`, `SettlementEquation` (from the simulator), `AnomalyManifest`, or `AnomalyRecord`.
- Discrepancies and exceptions are derived solely from observable financial evidence present in `ObservedWorld`.

```
┌────────────────────────────────────────────────────────┐
│                      GROUND TRUTH                      │
│        (Immutable, Authoritative Financial Reality)    │
└──────────────────────────┬─────────────────────────────┘
                           │
             [ObservationGenerator.generate]
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌──────────────────────┐        ┌──────────────────────┐
│   AnomalyManifest    │        │    ObservedWorld     │
│  (Benchmarking Only) │        │  (Ingested Dataset)  │
└──────────────────────┘        └──────────┬───────────┘
                                           │
                                           ▼
                                ┌──────────────────────┐
                                │   RECONCILIATION     │
                                │       ENGINE         │
                                │ (`backend.app.recon`)│
                                └──────────┬───────────┘
                                           │
                                           ▼
                                ┌──────────────────────┐
                                │ ReconciliationResult │
                                └──────────────────────┘
```

---

## 3. Package Structure

The reconciliation engine resides in `backend/app/reconciliation/`:

```
backend/app/reconciliation/
├── __init__.py           # Public exports: DeterministicReconciliationEngine, ReconciliationConfig, ReconciliationResult
├── models.py             # Pydantic v2 models: Results, Matches, Exceptions, Evidence, Metrics
├── exceptions.py         # Exception taxonomy & severity enums
├── indexer.py            # NormalizedObservationIndex (deterministic indexing & duplicate detection)
├── rules.py              # Pure rule predicates & evidence builders
├── composition.py        # Settlement composition & line-item arithmetic validator
├── matcher.py            # Multi-pass matcher (Settlement <-> Bank, referential integrity)
└── engine.py             # DeterministicReconciliationEngine orchestrator
```

---

## 4. Multi-Pass Matching Hierarchy

The engine processes financial entities in deterministic sequential passes:

1. **Pass 1 — Indexing & Duplicate Detection:**
   - Detects primary-key collisions across all ingested domain entities (`DUPLICATE_RECORD`).
   - Detects duplicate settlement participation (`(entity_type, entity_id)` referenced across multiple settlement transactions).
   - Detects duplicate banking references (`DUPLICATE_UTR`).

2. **Pass 2 — Referential & Lifecycle Integrity:**
   - Verifies Payment $\to$ Order linkages (`ORDER_PAYMENT_LINK` or `MISSING_FOREIGN_KEY`).
   - Verifies Refund $\to$ Payment linkages and cumulative refund caps ($\sum \text{Refunds} \le \text{Payment.amount}$).
   - Verifies SettlementTransaction $\to$ Target Entity references.
   - Verifies cross-reference consistency between `Payment.settlement_id` and `SettlementTransaction.settlement_id`.

3. **Pass 3 — Settlement Composition & Line-Item Arithmetic:**
   - Validates the fundamental settlement equation:
     $$\text{Settlement.amount} = \sum_{i} \text{SettlementTransaction}_i.\text{net\_amount}$$
   - Validates line-item math:
     - Credit: $\text{net\_amount} = \text{amount} - \text{fee} - \text{tax}$
     - Debit: $\text{net\_amount} = -(\text{amount} + \text{fee} + \text{tax})$

4. **Pass 4 — Settlement $\leftrightarrow$ Bank Reconciliation:**
   - **Exact UTR Match:** If `Settlement.utr == BankEntry.utr`:
     - If `Settlement.amount == BankEntry.amount` $\to$ `SETTLEMENT_BANK_EXACT_MATCH` (`RECONCILED`).
     - If `Settlement.amount != BankEntry.amount` $\to$ `BANK_AMOUNT_MISMATCH` (`EXCEPTION`).
   - **Identifier Mismatch Fallback:** If UTR differs but a unique orphan candidate pair exists with identical merchant and amount $\to$ `SETTLEMENT_BANK_IDENTIFIER_MISMATCH` (`EXCEPTION`).
   - **Missing Bank Entry:** If a processed settlement has a UTR but zero bank entries match $\to$ `MISSING_BANK_ENTRY` (`EXCEPTION`).
   - **Orphan Bank Entry:** Extra bank entries are recorded as `UNMATCHED_BANK_ENTRY` (`UNMATCHED`).

---

## 5. Exception Taxonomy & Severities

| Exception Type | Severity | Description |
|---|---|---|
| `AMOUNT_MISMATCH` | `CRITICAL` | Financial amounts disagree across components. |
| `SETTLEMENT_COMPOSITION_MISMATCH` | `CRITICAL` | Sum of line-item net amounts does not equal Settlement amount. |
| `BANK_AMOUNT_MISMATCH` | `CRITICAL` | Settlement amount does not equal BankEntry amount for matching UTR. |
| `LINE_ITEM_ARITHMETIC_MISMATCH` | `CRITICAL` | Line-item `net_amount` is mathematically inconsistent with amount/fee/tax. |
| `REFUND_EXCEEDS_PAYMENT` | `CRITICAL` | Cumulative refund amount exceeds original payment amount. |
| `IDENTIFIER_MISMATCH` | `WARNING` | Matching amount and merchant found on candidate pair with differing UTRs. |
| `CROSS_REFERENCE_MISMATCH` | `WARNING` | Payment `settlement_id` disagrees with SettlementTransaction join table. |
| `DUPLICATE_UTR` | `ERROR` | Same UTR appears multiple times in bank entries or settlements. |
| `DUPLICATE_RECORD` | `ERROR` | Primary key collision or duplicate settlement participation detected. |
| `MISSING_RECORD` | `ERROR` | Referenced entity or required banking credit missing from ObservedWorld. |
| `INVALID_RELATIONSHIP` | `ERROR` | Referential foreign key invalid or orphaned. |
| `INVALID_FINANCIAL_STATE` | `ERROR` | Entity lifecycle state is invalid for the attempted operation. |
| `UNMATCHED_RECORD` | `WARNING` | Orphan or pending record that cannot be safely reconciled. |

---

## 6. Determinism & Decimal Precision Guarantees

1. **Zero Randomness:** No `random` imports or non-deterministic operations in `backend/app/reconciliation/`.
2. **Deterministic Sorting:** All result arrays (`settlements`, `matches`, `exceptions`, `unmatched`) are sorted deterministically before output.
3. **Exact Decimal Arithmetic:** All financial numbers use `MoneyDecimal` (Python `Decimal`) quantized to `0.01` (`ROUND_HALF_UP`). Floats are strictly prohibited.
