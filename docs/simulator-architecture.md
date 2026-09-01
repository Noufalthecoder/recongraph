# ReconGraph — Simulator Architecture

> This document defines the architecture, deterministic rules, and design decisions for
> the ReconGraph financial-world simulator. The simulator generates synthetic, internally
> consistent financial event histories for benchmarking the reconciliation engine and
> AI investigation agent.
>
> **Authoritative sources:** [data-contracts.md](file:///c:/Users/Mohammed%20Noufal%20V/recongraph/docs/data-contracts.md),
> [financial-rules.md](file:///c:/Users/Mohammed%20Noufal%20V/recongraph/docs/financial-rules.md)

### Classification Convention

Behaviors and rules are classified into three categories throughout this document:

- **OFFICIAL / DOCUMENTED:** Supported by official Razorpay documentation.
- **SIMULATION ASSUMPTION:** Chosen intentionally for our synthetic benchmark, because the behavior is variable, configurable, or a suitable synthetic proxy.
- **UNVERIFIED:** Known/possible behavior that must not be treated as established truth. The simulator implementation must never silently convert an UNVERIFIED rule into a hard-coded production claim.

---

## 1. Simulator Purpose

The simulator serves three functions:

1. **Synthetic data generation:** Produce realistic financial datasets (merchants, orders, payments, settlements, bank entries) that conform to `data-contracts.md`.
2. **Ground-truth recording:** Maintain a hidden, complete, uncorrupted record of the true financial world — the *answer key* for benchmarking.
3. **Controlled anomaly injection:** Produce an *observed data* copy derived from ground truth, with deliberate, auditable corruptions that create reconciliation challenges.

### Non-Goals

- The simulator does NOT perform reconciliation.
- The simulator does NOT invoke AI/agent logic.
- The simulator does NOT validate hypotheses.
- The simulator is NOT a database — it produces in-memory data structures and serialised output files.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    SimulationConfig                           │
│  (seed, merchant_count, date_range, volume, anomaly_rate)    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               Financial World Generator                       │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ Merchant   │→ │   Order    │→ │  Payment   │              │
│  │ Generator  │  │ Generator  │  │ Generator  │              │
│  └────────────┘  └────────────┘  └─────┬──────┘              │
│                                        │                      │
│                        ┌───────────────┼───────────────┐      │
│                        ▼               ▼               ▼      │
│                 ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│                 │  Refund    │  │ Transfer   │  │Adjustment│ │
│                 │ Generator  │  │ Generator  │  │Generator │ │
│                 └────────────┘  └────────────┘  └──────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           Settlement Constructor                         │  │
│  │  (settlement cycle → group → fee/tax → net → UTR)       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                         │                                     │
│                         ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           Bank Entry Constructor                         │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 Ground Truth Recorder                         │
│  (all entities, relationships, settlement equations,          │
│   scenario labels, expected outcomes)                         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Observed Data Projector                          │
│  (deep copy of ground truth → initial observed data)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Anomaly Injector                                 │
│  (apply controlled corruptions to observed data copy)        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Simulation Output                                │
│  (ground_truth.json, observed_data.json, anomaly_log.json)   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Simulator Pipeline

### Stage 1: Merchant Generation

| Property | Detail |
|---|---|
| **Inputs** | `SimulationConfig.merchant_count`, `seed` |
| **Outputs** | `List[Merchant]` — domain model instances from `backend.app.models` |
| **Determinism** | Deterministic given seed. Faker is seeded. |
| **Stochastic elements** | Business name, MCC, settlement schedule selection |
| **Invariants** | Every `merchant_id` is globally unique. At least one merchant has `status = "active"`. |
| **Dependencies** | None (first stage). |

Generated attributes:
- `merchant_id`: Prefixed opaque string (`"merch_"` + random suffix).
- `name`: Realistic Indian business name via seeded Faker.
- `mcc`: Random selection from a curated MCC subset (retail, food, travel, digital).
- `settlement_schedule`: Random selection from `["T+2", "T+3"]`.
- `fee_plan_id`: Optional; generated for a configurable percentage of merchants.
- `status`: `"active"` for all initially; scenarios may set `"suspended"`.
- `created_at`: Random datetime within the configured date range, offset by merchant index.

> **SIMULATION ASSUMPTION:** All generated merchants use IST timestamps. Settlement schedule values are limited to T+2 and T+3.

---

### Stage 2: Time / Calendar Generation

| Property | Detail |
|---|---|
| **Inputs** | `SimulationConfig.date_range` (start date, end date) |
| **Outputs** | `Calendar` — ordered list of settlement cycle dates with business-day flags |
| **Determinism** | Fully deterministic (no randomness). |
| **Invariants** | Settlement cycles are contiguous. No gaps. Weekends are marked as non-business days. |
| **Dependencies** | None. |

The calendar defines:
- **Settlement cycle boundaries:** Each calendar day (00:00 IST to 23:59:59 IST) is one cycle.
- **Business day flags:** Saturday and Sunday are non-business days.
- **Settlement processing dates:** For each capture day, the settlement processing date = capture day + T+N (skipping non-business days).

> **SIMULATION ASSUMPTION:** Bank holidays are not simulated in the initial version. All weekdays are treated as business days.
>
> **SIMULATION ASSUMPTION:** Cutoff time is configurable. The V1 simulation default is midnight IST (00:00), but this is not presented as verified Razorpay behavior for all products.

---

### Stage 3: Order Generation

| Property | Detail |
|---|---|
| **Inputs** | `List[Merchant]`, `Calendar`, `SimulationConfig.event_volume`, `seed` |
| **Outputs** | `List[Order]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Order amount, creation timestamp, merchant assignment |
| **Invariants** | Every `order_id` is globally unique. Every order references a valid `merchant_id`. `amount > 0`. `currency = "INR"`. |
| **Dependencies** | Stage 1 (merchants), Stage 2 (calendar). |

Generation rules:
- Orders are distributed across merchants using a weighted distribution (some merchants are "busier").
- Order amounts are drawn from a log-normal distribution (most orders are small, some are large).
- Amount range: ₹10.00 – ₹500,000.00.
- `status` starts as `"created"`.
- `created_at` is distributed across the calendar's date range.

> **SIMULATION ASSUMPTION:** Order amount distribution (log-normal) is a benchmark assumption, not based on actual Razorpay data.

---

### Stage 4: Payment Generation

| Property | Detail |
|---|---|
| **Inputs** | `List[Order]`, `seed` |
| **Outputs** | `List[Payment]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Payment method selection, success/failure rate, capture timing |
| **Invariants** | Every `payment_id` is globally unique. `payment.order_id` references a valid order. `payment.merchant_id = order.merchant_id`. `payment.amount = order.amount` for successful payments. Only `captured` payments proceed to settlement. |
| **Dependencies** | Stage 3 (orders). |

Generation rules:
- Each order gets 1–3 payment attempts (weighted: ~85% succeed on first attempt).
- Payment method distribution (configurable, default):
  - UPI: 40%, Card: 30% (split: 60% debit, 40% credit), Netbanking: 15%, Wallet: 10%, EMI: 3%, Bank Transfer: 2%.
- Success rate: ~90% of attempts succeed (status = `captured`).
- Failed payments: status = `failed`, no further processing.
- `created_at`: order creation time + small random offset (seconds to minutes).
- `captured_at`: for captured payments, `created_at` + random offset (seconds to hours).
- `fee` and `tax`: calculated at settlement construction time, NOT at payment creation time. Left as `None` on the Payment entity initially.

> **SIMULATION ASSUMPTION:** Payment method distribution and success rates are benchmark assumptions.

---

### Stage 5: Refund Generation

| Property | Detail |
|---|---|
| **Inputs** | `List[Payment]` (only captured), refund configuration, `seed` |
| **Outputs** | `List[Refund]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Which payments get refunded, refund amount, refund timing, number of partial refunds |
| **Invariants** | `refund.payment_id` references a captured payment. `SUM(refunds for a payment) ≤ payment.amount`. Refund `created_at` ≥ payment `captured_at`. |
| **Dependencies** | Stage 4 (payments). |

Generation rules:
- Configurable refund rate (default: ~10% of captured payments receive at least one refund).
- Refund type distribution: 60% full refund, 40% partial refund.
- Partial refunds: 1–3 refunds per payment, amounts drawn randomly ensuring sum ≤ payment amount.
- If total refund amount equals payment amount, payment status is updated to `"refunded"`.
- `speed`: 90% `"normal"`, 10% `"optimum"`.
- `created_at`: payment `captured_at` + random offset (hours to days, potentially crossing settlement cycles).

> **SIMULATION ASSUMPTION:** Refund rate, type distribution, and timing are benchmark assumptions.
>
> **SIMULATION ASSUMPTION:** Refund fee treatment is a configurable simulation policy (e.g., `no_reversal`, `full_reversal`, `partial_reversal`). The V1 default may be `no_reversal`, but this does not claim these policies represent universal Razorpay behavior.

---

### Stage 6: Transfer Generation

| Property | Detail |
|---|---|
| **Inputs** | `List[Payment]` (only captured), `List[Merchant]`, transfer configuration, `seed` |
| **Outputs** | `List[Transfer]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Which payments generate transfers, number of splits, recipient selection |
| **Invariants** | `transfer.payment_id` references a captured payment. `SUM(transfers for a payment) ≤ payment.amount`. `source_merchant_id ≠ recipient_merchant_id`. Recipient must be a valid merchant. |
| **Dependencies** | Stage 4 (payments), Stage 1 (merchants). |

Generation rules:
- Only a configurable subset of merchants are "marketplace" merchants (default: ~10%).
- Only payments to marketplace merchants generate transfers.
- 1–3 transfers per eligible payment.
- Transfer amounts sum to ≤ payment amount (typically 70–90% of payment amount; remainder is marketplace commission).
- `status`: `"processed"` for most; small percentage `"failed"`.

> **SIMULATION ASSUMPTION:** Marketplace merchant percentage and transfer split ratios are benchmark assumptions.
>
> **SIMULATION ASSUMPTION:** Transfer fee responsibility is a configurable simulation policy (e.g., source merchant bears all, or proportional split). The V1 default assumes the source merchant bears the fee, but this is an unverified assumption.

---

### Stage 7: Adjustment Generation

| Property | Detail |
|---|---|
| **Inputs** | `List[Merchant]`, `Calendar`, adjustment configuration, `seed` |
| **Outputs** | `List[Adjustment]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Adjustment frequency, amount, reason, settlement association |
| **Invariants** | `adjustment.merchant_id` references a valid merchant. Amount may be negative (debit) or positive (credit). |
| **Dependencies** | Stage 1 (merchants), Stage 2 (calendar). |

Generation rules:
- Configurable adjustment rate per merchant per settlement cycle (default: ~2% of settlements contain adjustments).
- Reason distribution: 50% `"chargeback"` (negative), 20% `"correction"` (positive or negative), 15% `"penalty"` (negative), 15% `"balance_carryover"` (positive or negative).
- Amount range: ₹100–₹50,000.
- `settlement_id` is assigned during settlement construction (Stage 8).

> **SIMULATION ASSUMPTION:** Adjustment frequency and reason distribution are benchmark assumptions.
>
> **SIMULATION ASSUMPTION:** Adjustments may carry applicable fee and tax components where the contract permits. The simulator does not hard-code them to zero, but also does not assert that Razorpay applies a specific tax treatment to every adjustment.

---

### Stage 8: Settlement Construction

| Property | Detail |
|---|---|
| **Inputs** | `List[Payment]`, `List[Refund]`, `List[Transfer]`, `List[Adjustment]`, `Calendar`, `List[Merchant]` |
| **Outputs** | `List[Settlement]`, `List[SettlementTransaction]` — domain model instances. Side effect: updates `payment.fee`, `payment.tax`, `payment.settlement_id`, `refund.settlement_id`, `transfer.settlement_id`, `adjustment.settlement_id`. |
| **Determinism** | Fully deterministic. No randomness in the settlement equation. |
| **Stochastic elements** | Partial settlement selection (which transactions are held back) uses seeded random. |
| **Invariants** | **THE SETTLEMENT EQUATION MUST HOLD:** `settlement.amount = SUM(settlement_txn.net_amount)`. Every SettlementTransaction references exactly one source entity. UTR is unique per settlement. Per-merchant isolation. |
| **Dependencies** | Stages 1–7. |

#### Construction Algorithm

```
FOR each merchant:
    FOR each settlement cycle day in the calendar:

        1. COLLECT eligible transactions:
           - Captured payments with captured_at in this cycle
           - Processed refunds with created_at in this cycle
           - Processed transfers with created_at in this cycle
           - Adjustments assigned to this cycle

        2. APPLY partial settlement (if configured):
           - Randomly withhold a subset of eligible payments
           - Withheld payments roll to the next cycle

        3. CALCULATE fees and tax per payment:
           - fee = calculate_fee(payment.amount, payment.method)
           - tax = fee × Decimal("0.18"), rounded ROUND_HALF_UP to 2 dp
           - Update payment.fee and payment.tax

        4. BUILD SettlementTransactions:
           FOR each payment in this cycle:
               net_amount = payment.amount - fee - tax
               Create SettlementTransaction(
                   entity_type="payment", entity_id=payment.payment_id,
                   amount=payment.amount, fee=fee, tax=tax,
                   net_amount=net_amount, type="credit")

           FOR each refund in this cycle:
               Create SettlementTransaction(
                   entity_type="refund", entity_id=refund.refund_id,
                   amount=refund.amount, fee=Decimal("0"), tax=Decimal("0"),
                   net_amount=-refund.amount, type="debit")

           FOR each transfer in this cycle (source merchant side):
               Create SettlementTransaction(
                   entity_type="transfer", entity_id=transfer.transfer_id,
                   amount=transfer.amount, fee=Decimal("0"), tax=Decimal("0"),
                   net_amount=-transfer.amount, type="debit")

           FOR each adjustment in this cycle:
               direction = "credit" if adjustment.amount > 0 else "debit"
               adj_fee = resolve_adjustment_fee(adjustment) # SIMULATION ASSUMPTION: may be non-zero
               adj_tax = resolve_adjustment_tax(adj_fee)
               
               if direction == "credit":
                   net_amount = adjustment.amount - adj_fee - adj_tax
               else:
                   net_amount = adjustment.amount + adj_fee + adj_tax # Adjustments with direction=debit have amount expressed as positive absolute value.
               
               Create SettlementTransaction(
                   entity_type="adjustment", entity_id=adjustment.adjustment_id,
                   amount=abs(adjustment.amount), fee=adj_fee, tax=adj_tax,
                   net_amount=net_amount, type=direction)

        5. COMPUTE settlement amount:
           settlement_amount = SUM(stxn.net_amount for stxn in settlement_transactions)

        6. SKIP if no transactions (empty cycle).

        7. CREATE Settlement:
           settlement = Settlement(
               settlement_id=generate_id("setl_"),
               merchant_id=merchant.merchant_id,
               amount=settlement_amount,
               fees=SUM(stxn.fee),
               tax=SUM(stxn.tax),
               status="processed",
               utr=generate_utr(),
               settled_at=settlement_processing_date,
               ...)

        8. BACKFILL settlement_id on source entities:
           Update payment.settlement_id, refund.settlement_id,
           transfer.settlement_id, adjustment.settlement_id
```

#### Fee Calculation Function

```
def calculate_fee(amount: Decimal, method: PaymentMethod) -> Decimal:
    """
    Per financial-rules.md § 6.

    Returns fee rounded to 2 decimal places, ROUND_HALF_UP.
    """
    if method == "upi":
        return Decimal("0.00")
    elif method == "card":
        # Simplified: use credit card rate (2%) for simulation
        # Debit card distinction requires card_type sub-field
        # which is not in our data contract.
        # For debit card simulation, see debit_card branch below.
        rate = Decimal("0.02")
    elif method == "netbanking":
        return Decimal("5.00")  # Flat fee
    elif method == "wallet":
        rate = Decimal("0.0175")
    elif method == "emi":
        rate = Decimal("0.02")  # Treated same as credit card
    elif method == "bank_transfer":
        return Decimal("0.00")  # No MDR
    else:
        rate = Decimal("0.02")  # Default fallback

    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

> **SIMULATION ASSUMPTION:** The fee calculation uses simplified rates. The debit card tiered rate (0.40% ≤ ₹2,000 / 0.90% > ₹2,000) requires distinguishing debit from credit cards. Since our `PaymentMethod` enum uses `"card"` (not `"debit_card"` / `"credit_card"`), the simulator must internally track card sub-type for accurate fee calculation. This is an internal simulator detail, not a change to the data contract.

#### Settlement Equation Verification

After constructing every settlement, the simulator MUST verify:

```
assert settlement.amount == sum(stxn.net_amount for stxn in settlement_transactions)
assert settlement.fees == sum(stxn.fee for stxn in settlement_transactions)
assert settlement.tax == sum(stxn.tax for stxn in settlement_transactions)
```

If the equation does not hold, this is a **simulator bug**, not a scenario.

---

### Stage 9: Bank Entry Construction

| Property | Detail |
|---|---|
| **Inputs** | `List[Settlement]` (only `status = "processed"`), `seed` |
| **Outputs** | `List[BankEntry]` — domain model instances |
| **Determinism** | Deterministic given seed. |
| **Stochastic elements** | Transaction date offset from settlement date |
| **Invariants** | `bank_entry.utr = settlement.utr`. `bank_entry.amount = settlement.amount`. One bank entry per processed settlement. `bank_entry.merchant_id = settlement.merchant_id`. |
| **Dependencies** | Stage 8 (settlements). |

Generation rules:
- Each processed settlement produces exactly one bank entry.
- `bank_entry.utr = settlement.utr` (exact match — this is the ground truth).
- `bank_entry.amount = settlement.amount` (exact match — ground truth).
- `transaction_date`: settlement `settled_at` + 0–1 business days (bank processing lag).
- `account_number`: generated per merchant (consistent across all entries for the same merchant).
- `description`: template string: `"NEFT CR RAZORPAY {settlement_id}"`.

> **SIMULATION ASSUMPTION:** Bank entry timing lag of 0–1 days is a benchmark assumption. Actual bank processing time varies.

---

### Stage 10: Ground-Truth Recording

| Property | Detail |
|---|---|
| **Inputs** | All entities from Stages 1–9, scenario metadata |
| **Outputs** | `GroundTruth` structure |
| **Determinism** | Fully deterministic (recording, not generation). |
| **Invariants** | Ground truth is complete — every entity, every relationship, every settlement equation, every scenario label. |
| **Dependencies** | Stages 1–9 (all generation complete). |

The ground-truth structure records:

```
GroundTruth:
    config: SimulationConfig
    merchants: List[Merchant]
    orders: List[Order]
    payments: List[Payment]
    refunds: List[Refund]
    transfers: List[Transfer]
    adjustments: List[Adjustment]
    settlement_transactions: List[SettlementTransaction]
    settlements: List[Settlement]
    bank_entries: List[BankEntry]
    settlement_equations: Dict[settlement_id, SettlementEquation]
    scenario_labels: Dict[settlement_id, ScenarioLabel]
    relationships: List[Relationship]
```

Where `SettlementEquation` captures:
```
SettlementEquation:
    settlement_id: str
    expected_amount: Decimal
    sum_of_net_amounts: Decimal
    total_fees: Decimal
    total_tax: Decimal
    is_balanced: bool   # Must always be True in ground truth
```

And `ScenarioLabel` captures:
```
ScenarioLabel:
    settlement_id: str
    scenario_type: str                    # e.g., "normal", "many_payments", etc.
    expected_recon_status: str            # RECONCILED | EXCEPTION
    expected_resolution: str | None       # RESOLVED | ESCALATED | None
    is_auto_resolvable: bool
    requires_human_escalation: bool
    anomalies_applied: List[AnomalyRecord]
```

---

### Stage 11: Observed-Data Projection

| Property | Detail |
|---|---|
| **Inputs** | `GroundTruth` |
| **Outputs** | `ObservedData` — a deep copy of ground truth entities |
| **Determinism** | Fully deterministic (deep copy). |
| **Invariants** | Initially, `ObservedData` is identical to `GroundTruth` (all entities, same values). |
| **Dependencies** | Stage 10 (ground truth). |

The projection creates a deep, independent copy of every entity list from ground truth. After this stage, the observed data can be mutated without affecting ground truth.

> **Important:** Since domain models are frozen (Pydantic `frozen=True`), "mutation" for anomaly injection means creating a new model instance with modified fields via `model.model_copy(update={...})`.

---

### Stage 12: Controlled Anomaly Injection

| Property | Detail |
|---|---|
| **Inputs** | `ObservedData`, `AnomalyConfig`, `seed` |
| **Outputs** | Mutated `ObservedData`, `List[AnomalyRecord]` |
| **Determinism** | Deterministic given seed and config. |
| **Invariants** | Ground truth is never modified. Every anomaly is recorded with a unique ID. The anomaly log is complete. |
| **Dependencies** | Stage 11 (observed data). |

See § 8. Anomaly Injection for detailed design.

---

## 4. Ground Truth vs. Observed Data

### Conceptual Separation

**GROUND TRUTH** represents the complete synthetic financial world generated by the simulator under the active `SimulationConfig`. It is NOT a claim that every simulation rule exactly reproduces Razorpay production behavior. The benchmark measures whether ReconGraph correctly reconstructs the synthetic world presented to it.

```
                    ┌─────────────────────┐
                    │    GROUND TRUTH      │
                    │  (simulator's brain) │
                    │                      │
                    │  Complete, correct,  │
                    │  uncorrupted.        │
                    │  NEVER seen by       │
                    │  ReconGraph runtime. │
                    └──────────┬──────────┘
                               │
                          deep copy
                               │
                               ▼
                    ┌─────────────────────┐
                    │   OBSERVED DATA      │
                    │  (what ReconGraph    │
                    │   actually sees)     │
                    │                      │
                    │  May be corrupted,   │
                    │  incomplete, or      │
                    │  duplicated.         │
                    └─────────────────────┘
```

### Rules (from financial-rules.md § 16)

1. Ground truth is deterministic. Same seed → same truth.
2. Observed data is derived from ground truth by applying corruption scenarios.
3. The reconciliation engine and AI agent operate ONLY on observed data.
4. Benchmark scoring compares ReconGraph's conclusions against ground truth.
5. Ground truth includes all entities, relationships, settlement equations, and corruption logs.

### Data Structures

```
GroundTruth:
    entities:       all domain model instances (complete, correct)
    equations:      settlement equation for every settlement (must balance)
    scenarios:      labels for each settlement (scenario type, expected outcome)
    anomaly_log:    list of every anomaly applied to observed data

ObservedData:
    entities:       domain model instances (potentially corrupted)
    # No equations, no scenario labels, no anomaly log
    # This is what ReconGraph sees — it has no "answer key"
```

---

## 5. Financial World Lifecycle

The simulator models a financial world that progresses through time:

```
Day 1          Day 2          Day 3          Day 4          Day 5
──────────────────────────────────────────────────────────────────►

│ Orders       │ Orders       │ Orders       │ Orders       │
│ Payments     │ Payments     │ Payments     │ Payments     │
│ (captures)   │ (captures)   │ (captures)   │ (captures)   │
│              │ Refunds      │ Refunds      │ Refunds      │
│              │ Transfers    │ Transfers    │ Transfers    │
│              │              │              │              │
│              │              │ Settlement   │              │
│              │              │ for Day 1    │              │
│              │              │ (T+2)        │ Settlement   │
│              │              │              │ for Day 2    │
│              │              │ Bank Entry   │ (T+2)        │
│              │              │ for Day 1    │              │
│              │              │ settlement   │ Bank Entry   │
│              │              │              │ for Day 2    │
│              │              │              │ settlement   │
```

### Event Ordering Within a Day

1. Orders are created throughout the day.
2. Payment attempts follow orders (seconds to minutes later).
3. Captures happen after authorization (seconds to hours).
4. Refunds can happen same-day or later.
5. Transfers are processed after capture.
6. Adjustments are applied at settlement time.
7. Settlement is constructed at end-of-day cutoff.
8. Bank entry follows settlement processing (0–1 days).

### Relationship Flow

```
Merchant
   │
   ├── creates ──► Order
   │                  │
   │                  └── receives ──► Payment (attempt 1, 2, ...)
   │                                      │
   │                         ┌────────────┼────────────┐
   │                         ▼            ▼            ▼
   │                      Refund      Transfer     (no action)
   │                         │            │
   │                         ▼            ▼
   │              SettlementTransaction  SettlementTransaction
   │                         │            │
   │                         └─────┬──────┘
   │                               ▼
   └──────────────────────► Settlement
                                │
                                ▼
                           Bank Entry
```

---

## 6. Settlement Construction — Detailed Design

### 6.1 Settlement Cycle Definition

A settlement cycle is a time window during which financial events are collected for batching:

- **Window:** One calendar day, 00:00:00 IST to 23:59:59 IST.
- **Eligibility:** A payment is eligible for the cycle in which its `captured_at` falls.
- **Processing date:** Cycle day + T+N business days (default T+2).
- **Per-merchant:** Each merchant has independent settlement cycles.

### 6.2 Transaction Collection

For merchant M on cycle day D:

| Entity Type | Collection Rule |
|---|---|
| **Payments** | `status = "captured"` AND `captured_at` falls within day D AND not already settled AND not held back |
| **Refunds** | `status = "processed"` AND `created_at` falls within day D AND not already settled |
| **Transfers** | `status = "processed"` AND `created_at` falls within day D AND source_merchant_id = M AND not already settled |
| **Adjustments** | Assigned to this merchant and this cycle |

### 6.3 Fee and Tax Calculation

For each payment in the cycle:

```
fee = calculate_fee(payment.amount, payment.method)   # See § 3 Stage 8
tax = (fee * Decimal("0.18")).quantize(Decimal("0.01"), rounding=rounding_mode)
```

**Rounding rule:** The rounding mode is a configurable simulation policy. 

> **SIMULATION ASSUMPTION:** The V1 benchmark value may use `ROUND_HALF_UP`, but this rounding mode must be explicitly configurable so the benchmark behavior can be changed after official verification. The implementation must not claim that Razorpay uses this rounding mode unless official documentation establishes it.

### 6.4 SettlementTransaction Construction

| Source | `entity_type` | `type` | `amount` | `fee` | `tax` | `net_amount` |
|---|---|---|---|---|---|---|
| Payment | `"payment"` | `"credit"` | payment.amount | fee | tax | payment.amount − fee − tax |
| Refund | `"refund"` | `"debit"` | refund.amount | 0 | 0 | −refund.amount |
| Transfer (source) | `"transfer"` | `"debit"` | transfer.amount | 0 | 0 | −transfer.amount |
| Adjustment (+) | `"adjustment"` | `"credit"` | abs(adj.amount) | 0 | 0 | adj.amount |
| Adjustment (−) | `"adjustment"` | `"debit"` | abs(adj.amount) | 0 | 0 | adj.amount (negative) |

### 6.5 Settlement Amount

```python
settlement_amount = sum(stxn.net_amount for stxn in settlement_transactions)
settlement_fees   = sum(stxn.fee for stxn in settlement_transactions)
settlement_tax    = sum(stxn.tax for stxn in settlement_transactions)
```

> **SIMULATION ASSUMPTION / V1 CONSTRAINT:** Because the V1 contract defines BankEntry strictly as a positive credit and restricts negative Settlement amounts to adjustments, a refund-only settlement (which would yield a negative total) is mathematically invalid under the current V1 synthetic constraints. The refund settlement scenario therefore requires at least one positive credit component (e.g., another Payment) in the same cycle to absorb the refund and yield a net positive settlement. This is explicitly a V1 simulation constraint and not a universal Razorpay production claim.

### 6.6 UTR Generation

UTR is an external banking reference represented as a string. The simulator may generate a deterministic mock UTR.

```python
def generate_utr(seed_component: str) -> str:
    """
    Generate a unique mock UTR string.
    Must be unique across all settlements in the simulation.
    """
```

> **SIMULATION ASSUMPTION:** We do not claim a universal Razorpay UTR format. If a banking-format-looking value is generated (e.g., 16-char alphanumeric), it is explicitly synthetic. ReconGraph V1 is not required to validate real banking UTR formats.

### 6.7 Partial Settlement Support

For partial settlement scenarios:

```python
def apply_partial_settlement(
    eligible_payments: List[Payment],
    holdback_rate: Decimal,
    rng: Random,
) -> Tuple[List[Payment], List[Payment]]:
    """
    Split eligible payments into:
    - included: payments that enter this settlement
    - held_back: payments deferred to the next cycle

    holdback_rate: fraction of eligible payments to withhold (e.g., 0.25)
    """
```

Held-back payments are added to the next cycle's eligible pool.

### 6.8 Cross-Cycle Event Support and Split Settlements

Refunds and transfers can reference payments from earlier cycles. The simulator handles this naturally:

- A payment captured on Day 1 is settled in Settlement A.
- A refund for that payment issued on Day 5 appears as a debit in Settlement C (the cycle containing Day 5).
- The two settlements are independent. No special handling needed — the cross-cycle relationship is visible via the shared `payment_id`.

> **SIMULATION ASSUMPTION:** For the ReconGraph V1 benchmark, a captured Payment credit is assigned to **exactly one** SettlementTransaction/Settlement for the synthetic settlement model. Refunds, adjustments, or later financial events may affect later settlements. This is an explicit V1 benchmark constraint, not a universal claim about all Razorpay products (which may or may not prohibit split settlements).

---

## 7. Scenario System

### 7.1 Scenario Architecture

Each scenario is a self-contained recipe that:

1. Configures the financial world (entities, relationships, amounts).
2. Defines expected ground truth.
3. Optionally specifies anomaly injections for observed data.
4. Declares the expected ReconGraph outcome.

```
Scenario:
    scenario_id: str
    scenario_type: ScenarioType     # enum of 12 families
    description: str
    world_config: WorldConfig       # overrides for entity generation
    anomaly_config: AnomalyConfig   # what corruptions to apply
    expected_outcome: ExpectedOutcome
```

### 7.2 Scenario Families

---

#### Scenario 1: Normal Settlement

| Property | Value |
|---|---|
| **Initial world** | 1 merchant, 3–10 payments in a single cycle, no refunds/transfers/adjustments |
| **Event sequence** | Orders → Payments → Settlement → Bank Entry |
| **Expected settlement** | `amount = SUM(payment.amount - fee - tax)` |
| **Ground truth** | All entities correct, settlement equation balanced |
| **Observed-data transformation** | None (clean data) |
| **Expected ReconGraph classification** | `RECONCILED` |
| **Auto-resolvable** | N/A (no exception) |
| **Human escalation** | No |

---

#### Scenario 2: Many Payments → One Settlement

| Property | Value |
|---|---|
| **Initial world** | 1 merchant, 50–500 payments in a single cycle, mixed payment methods |
| **Event sequence** | Orders → Payments → Settlement → Bank Entry |
| **Expected settlement** | `amount = SUM(net_amounts)` across all payments |
| **Ground truth** | All entities correct, settlement equation balanced |
| **Observed-data transformation** | None (clean data) |
| **Expected ReconGraph classification** | `RECONCILED` |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 3: Partial Settlement

| Property | Value |
|---|---|
| **Initial world** | 1 merchant, 20 eligible payments, 15 included + 5 held back |
| **Event sequence** | Orders → Payments → Partial Settlement (15) → Next Cycle Settlement (5) → Bank Entries |
| **Expected settlement** | Settlement A contains 15 payments. Settlement B contains the 5 held-back. |
| **Ground truth** | Both settlements correct, equations balanced |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` for both settlements. Unsettled payments are pending, not exceptions. |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 4: Multiple Partial Refunds

| Property | Value |
|---|---|
| **Initial world** | 1 payment of ₹10,000 + 3 partial refunds (₹2,000 + ₹3,000 + ₹1,500) across different cycles |
| **Event sequence** | Payment settled in cycle N. Refunds settled in cycles N+1, N+2. |
| **Expected settlement** | Payment credit in Settlement A. Refund debits across Settlements B, C. |
| **Ground truth** | All settlements correct. SUM(refunds) = ₹6,500 ≤ ₹10,000. |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` for all settlements |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 5: Fees and Tax

| Property | Value |
|---|---|
| **Initial world** | 1 settlement with mixed payment methods: UPI (0%), credit card (2%), debit card (0.9%), netbanking (₹5 flat) |
| **Event sequence** | Standard payment → settlement flow |
| **Expected settlement** | Net amount correctly reflects per-method fee deductions + 18% GST on each fee |
| **Ground truth** | Fee and tax fields populated, settlement equation balanced |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 6: Adjustment

| Property | Value |
|---|---|
| **Initial world** | Normal payments + chargeback (−₹5,000) + correction (+₹200) in one settlement |
| **Event sequence** | Payments → Adjustments created → Settlement includes both |
| **Expected settlement** | Net amount includes adjustment debits and credits |
| **Ground truth** | All correct |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 7: Transfer

| Property | Value |
|---|---|
| **Initial world** | Marketplace merchant, ₹10,000 payment, transfers to 2 linked accounts (₹7,000 + ₹2,000) |
| **Event sequence** | Payment → Transfers → Source settlement (reduced) + Recipient settlements |
| **Expected settlement** | Source: payment credit − transfer debits − fees. Recipients: transfer credit in their own settlements. |
| **Ground truth** | All three settlements correct |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` for all |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 8: Cross-Cycle Event

| Property | Value |
|---|---|
| **Initial world** | Payment in cycle N, refund in cycle N+3 |
| **Event sequence** | Payment settled in Settlement A. Refund settled in Settlement D. |
| **Expected settlement** | Both settlements independently balanced |
| **Ground truth** | Cross-cycle relationship recorded via shared payment_id |
| **Observed-data transformation** | None |
| **Expected ReconGraph classification** | `RECONCILED` for both |
| **Auto-resolvable** | N/A |
| **Human escalation** | No |

---

#### Scenario 9: Missing Record

| Property | Value |
|---|---|
| **Initial world** | Settlement with 10 payments, all correct |
| **Event sequence** | Standard |
| **Expected settlement** | Balanced in ground truth |
| **Ground truth** | All 10 payments present |
| **Observed-data transformation** | `OMIT_RECORD`: Remove 1 payment record from observed data. Settlement and its SettlementTransaction referencing the missing payment remain. |
| **Expected ReconGraph classification** | `EXCEPTION` → `MISSING_TRANSACTION` |
| **Auto-resolvable** | Yes — the gap can be explained by a single missing payment |
| **Human escalation** | No (if AI + verifier can confirm) |

---

#### Scenario 10: Incorrect Amount

| Property | Value |
|---|---|
| **Initial world** | Payment of ₹5,000, correctly settled |
| **Event sequence** | Standard |
| **Expected settlement** | Balanced in ground truth |
| **Ground truth** | Payment amount = ₹5,000 |
| **Observed-data transformation** | `CORRUPT_AMOUNT`: Change payment amount to ₹5,500 in observed data. Settlement amount unchanged. |
| **Expected ReconGraph classification** | `EXCEPTION` → `AMOUNT_MISMATCH` |
| **Auto-resolvable** | Yes — single correction restores the equation |
| **Human escalation** | No |

---

#### Scenario 11: Duplicate Record

| Property | Value |
|---|---|
| **Initial world** | Payment exists once |
| **Event sequence** | Standard |
| **Expected settlement** | Balanced in ground truth |
| **Ground truth** | One SettlementTransaction for this payment |
| **Observed-data transformation** | `DUPLICATE_RECORD`: Insert duplicate SettlementTransaction with same entity_id |
| **Expected ReconGraph classification** | `EXCEPTION` → `DUPLICATE_TRANSACTION` |
| **Auto-resolvable** | Yes — removing the duplicate restores the equation |
| **Human escalation** | No |

---

#### Scenario 12: Unexplainable Discrepancy

| Property | Value |
|---|---|
| **Initial world** | Normal settlement |
| **Event sequence** | Standard |
| **Expected settlement** | Balanced in ground truth |
| **Ground truth** | All correct |
| **Observed-data transformation** | `COMPOSITE`: Multiple simultaneous corruptions — e.g., corrupt 2 amounts + omit 1 record + alter 1 UTR |
| **Expected ReconGraph classification** | `EXCEPTION` → (multiple types) |
| **Auto-resolvable** | No — no single hypothesis can explain all discrepancies |
| **Human escalation** | **Yes** — must be `ESCALATED` |

---

## 8. Anomaly Injection

### 8.1 Design Principles

- The anomaly injector is a **separate, independent module** from the world generator.
- It operates on the `ObservedData` copy, never on ground truth.
- Every anomaly is deterministic given a seed.
- Every anomaly is recorded with a unique ID and full audit trail.

### 8.2 Anomaly Types

| Anomaly Type | Code | Operation | Target Entities |
|---|---|---|---|
| Remove record | `OMIT_RECORD` | Delete an entity from observed data | Payment, Refund, Transfer, Adjustment, SettlementTransaction, BankEntry |
| Duplicate record | `DUPLICATE_RECORD` | Insert an identical copy of an entity | SettlementTransaction (most common), Payment, BankEntry |
| Alter amount | `CORRUPT_AMOUNT` | Change a monetary field by a random delta | Payment.amount, Refund.amount, Settlement.amount, BankEntry.amount |
| Alter timestamp | `DELAY_RECORD` | Shift a datetime field | Payment.captured_at, Settlement.settled_at, BankEntry.transaction_date |
| Alter settlement reference | `SWAP_REFERENCE` | Change settlement_id to a different valid settlement | Payment.settlement_id, SettlementTransaction.settlement_id |
| Alter UTR | `CORRUPT_UTR` | Change UTR to break Settlement ↔ BankEntry match | Settlement.utr, BankEntry.utr |
| Omit field | `OMIT_FIELD` | Set an optional field to `null` | Payment.fee, Payment.tax, Settlement.utr |
| Composite | `COMPOSITE` | Apply multiple anomaly types to the same dataset | Any |

### 8.3 Anomaly Record

```
AnomalyRecord:
    anomaly_id: str                    # Unique ID (e.g., "anom_001")
    anomaly_type: str                  # OMIT_RECORD, CORRUPT_AMOUNT, etc.
    target_entity_type: str            # "payment", "settlement", etc.
    target_entity_id: str              # The entity ID that was modified
    target_field: str | None           # The field that was changed (for CORRUPT_AMOUNT, etc.)
    original_value: str | None         # The original value (serialized)
    corrupted_value: str | None        # The new value (serialized), or None for OMIT_RECORD
    settlement_id: str                 # The settlement affected
    scenario_id: str                   # The scenario this anomaly belongs to
    expected_exception_type: str       # The exception type ReconGraph should raise
    is_resolvable: bool                # Whether the anomaly can be deterministically resolved
```

### 8.4 Injection Algorithm

```
def inject_anomalies(
    observed_data: ObservedData,
    anomaly_config: AnomalyConfig,
    rng: Random,
) -> Tuple[ObservedData, List[AnomalyRecord]]:
    """
    Apply controlled corruptions to observed data.

    1. Select target settlements based on anomaly_rate.
    2. For each selected settlement, choose an anomaly type.
    3. Apply the anomaly to the relevant entities.
    4. Record the anomaly.
    5. Return the mutated observed data + anomaly log.
    """
```

### 8.5 Determinism

- The injector uses a `random.Random` instance seeded from the simulation seed.
- The order of anomaly application is deterministic (sorted by settlement_id, then by anomaly type).
- Same config + seed → same anomalies, same positions, same values.

---

## 9. Reproducibility

### Configuration Model

```
SimulationConfig:
    seed: int                          # Master random seed
    merchant_count: int                # Number of merchants (default: 5)
    date_range: Tuple[date, date]      # Simulation date range (default: 30 days)
    event_volume: str                  # "low" | "medium" | "high" (controls orders/day)
    anomaly_rate: Decimal              # Fraction of settlements to corrupt (default: 0.10)
    scenario_distribution: Dict[str, float]  # Weights for scenario family selection
    settlement_schedule: str           # Default "T+2"
    partial_settlement_rate: Decimal   # Fraction of cycles with partial settlement (default: 0.05)
    refund_rate: Decimal               # Fraction of captured payments refunded (default: 0.10)
    transfer_rate: Decimal             # Fraction of merchants that are marketplaces (default: 0.10)
    adjustment_rate: Decimal           # Fraction of settlements with adjustments (default: 0.02)
```

### Volume Presets

| Preset | Orders/Day/Merchant | Approximate Total (30 days, 5 merchants) |
|---|---|---|
| `low` | 5–10 | ~1,000 orders |
| `medium` | 20–50 | ~5,000 orders |
| `high` | 100–500 | ~45,000 orders |

### Reproducibility Guarantee

```python
# These two runs MUST produce identical output:
sim_a = Simulator(SimulationConfig(seed=42, ...))
result_a = sim_a.run()

sim_b = Simulator(SimulationConfig(seed=42, ...))
result_b = sim_b.run()

assert result_a == result_b  # Byte-identical
```

---

## 10. Proposed Package Structure

```
simulator/
│
├── __init__.py                     # Package init
│
├── config.py                       # SimulationConfig, volume presets, defaults
│
├── engine.py                       # Top-level Simulator class, orchestrates the pipeline
│
├── calendar.py                     # Calendar/time utilities, business day logic,
│                                   # settlement cycle management
│
├── entities/
│   ├── __init__.py
│   ├── merchant_gen.py             # Merchant generation
│   ├── order_gen.py                # Order generation
│   ├── payment_gen.py              # Payment generation (includes fee calculation)
│   ├── refund_gen.py               # Refund generation
│   ├── transfer_gen.py             # Transfer generation
│   └── adjustment_gen.py           # Adjustment generation
│
├── generators/
│   ├── __init__.py
│   ├── id_generator.py             # Deterministic ID generation (merchant_id, order_id, etc.)
│   ├── amount_generator.py         # Amount distribution (log-normal, etc.)
│   └── utr_generator.py            # UTR generation with uniqueness guarantee
│
├── scenarios/
│   ├── __init__.py
│   ├── base.py                     # Base Scenario class / interface
│   ├── normal.py                   # Scenario 1: Normal settlement
│   ├── many_payments.py            # Scenario 2: Many payments → one settlement
│   ├── partial_settlement.py       # Scenario 3: Partial settlement
│   ├── partial_refunds.py          # Scenario 4: Multiple partial refunds
│   ├── fees_and_tax.py             # Scenario 5: Fees and tax
│   ├── adjustment.py               # Scenario 6: Adjustment
│   ├── transfer.py                 # Scenario 7: Transfer
│   ├── cross_cycle.py              # Scenario 8: Cross-cycle event
│   ├── missing_record.py           # Scenario 9: Missing record
│   ├── incorrect_amount.py         # Scenario 10: Incorrect amount
│   ├── duplicate_record.py         # Scenario 11: Duplicate record
│   └── unexplainable.py            # Scenario 12: Unexplainable discrepancy
│
├── ground_truth/
│   ├── __init__.py
│   ├── recorder.py                 # GroundTruth recording and serialization
│   ├── settlement_equation.py      # Settlement equation computation and verification
│   └── models.py                   # GroundTruth, SettlementEquation, ScenarioLabel,
│                                   # AnomalyRecord data structures (Pydantic models)
│
├── anomaly/
│   ├── __init__.py
│   ├── injector.py                 # Top-level anomaly injection orchestrator
│   ├── strategies.py               # Individual anomaly strategies
│   │                               # (OMIT_RECORD, CORRUPT_AMOUNT, etc.)
│   └── registry.py                 # Anomaly type registry and configuration
│
├── output/
│   ├── __init__.py
│   └── serializer.py               # Serialize GroundTruth + ObservedData to JSON/Parquet
│
└── tests/
    ├── __init__.py
    ├── test_determinism.py          # Same seed → same output
    ├── test_entity_generation.py    # Valid entities generated
    ├── test_relationships.py        # Relationship integrity
    ├── test_money_conservation.py   # Money in = money out (no leaks)
    ├── test_settlement.py           # Settlement equation holds
    ├── test_utr_uniqueness.py       # UTR uniqueness within simulation
    ├── test_ground_truth.py         # Ground truth completeness
    ├── test_anomaly_injection.py    # Observed data correctly corrupted
    └── test_scenarios.py            # Each scenario family produces expected structure
```

### Key Design Decisions

1. **Domain models are NOT duplicated.** The simulator imports from `backend.app.models` and instantiates those Pydantic models.
2. **Ground-truth-specific models** (GroundTruth, AnomalyRecord, ScenarioLabel, SettlementEquation) live in `simulator/ground_truth/models.py` because they are simulator-only concepts.
3. **Anomaly injection is a separate subpackage** (`simulator/anomaly/`) to enforce clean separation from world generation.
4. **Each scenario is a separate module** for clarity and testability, sharing a common base class.

---

## 11. V1 Implementation Boundary

The first V1 implementation should cover only behavior whose financial semantics are sufficiently defined for a deterministic benchmark. 

**V1 includes:**
- Merchant, Order, Payment generation
- Basic settlement & SettlementTransaction
- BankEntry
- Ground truth

**Deferred to later versions:**
- Refunds, Fees, Tax, Adjustments, Transfers
- Partial settlement, Cross-cycle events, Anomaly injection

This boundary allows us to validate the core financial lifecycle before adding complexity.

---

## 12. Test Strategy

### Test Categories

| Category | Test File | What It Verifies |
|---|---|---|
| **Determinism** | `test_determinism.py` | Two runs with the same `SimulationConfig(seed=42)` produce byte-identical output. Different seeds produce different output. |
| **Entity validity** | `test_entity_generation.py` | Every generated entity passes Pydantic validation. All required fields are present. Monetary values are `Decimal`. IDs are unique. |
| **Relationship integrity** | `test_relationships.py` | Every `payment.order_id` references a real order. Every `refund.payment_id` references a captured payment. `SUM(refunds) ≤ payment.amount`. `SUM(transfers) ≤ payment.amount`. Every `settlement_txn.settlement_id` references a real settlement. |
| **Money conservation** | `test_money_conservation.py` | No money is created or destroyed. For each settlement: `SUM(payment credits) - SUM(refund debits) - SUM(transfer debits) + SUM(adjustment net) - SUM(fees) - SUM(tax) = settlement.amount`. |
| **Settlement consistency** | `test_settlement.py` | The settlement equation holds for every settlement. `settlement.fees = SUM(stxn.fee)`. `settlement.tax = SUM(stxn.tax)`. |
| **UTR uniqueness** | `test_utr_uniqueness.py` | No two settlements share a UTR. No two bank entries share a UTR. Each settlement UTR has exactly one matching bank entry in ground truth. |
| **Ground-truth completeness** | `test_ground_truth.py` | Ground truth contains every generated entity. Every settlement has a settlement equation record. Every settlement has a scenario label. The anomaly log is complete. |
| **Anomaly injection** | `test_anomaly_injection.py` | For `OMIT_RECORD`: entity is absent in observed data, present in ground truth. For `CORRUPT_AMOUNT`: observed amount ≠ ground truth amount. For `DUPLICATE_RECORD`: entity appears twice in observed data, once in ground truth. Anomaly records correctly describe each mutation. |
| **Scenario correctness** | `test_scenarios.py` | Each of the 12 scenario families produces the expected entity structure, ground truth labels, and observed data transformations. |

### Test Execution

```bash
# Run all simulator tests
pytest simulator/tests/ -v

# Run specific test category
pytest simulator/tests/test_settlement.py -v

# Run with coverage
pytest simulator/tests/ --cov=simulator --cov-report=term-missing
```

---

## 13. Invariants

These invariants MUST hold at all times in the simulator's output. Violation of any invariant is a simulator bug.

### Entity Invariants

| # | Invariant |
|---|---|
| E1 | Every entity ID is globally unique within its type. |
| E2 | Every monetary value is a `Decimal`, never a `float`. |
| E3 | Every entity with an `amount` field has `currency = "INR"`. |
| E4 | All timestamps are timezone-aware (IST). |
| E5 | Every foreign key references a valid entity. |

### Financial Invariants

| # | Invariant |
|---|---|
| F1 | `SUM(refund.amount for payment) ≤ payment.amount` |
| F2 | `SUM(transfer.amount for payment) ≤ payment.amount` |
| F3 | Only `captured` payments appear in settlements. |
| F4 | `fee = calculate_fee(payment.amount, payment.method)` — deterministic. |
| F5 | `tax = (fee × 0.18).quantize(Decimal("0.01"), ROUND_HALF_UP)` |
| F6 | Refund fee is `Decimal("0")` and refund tax is `Decimal("0")`. |

### Settlement Invariants

| # | Invariant |
|---|---|
| S1 | `settlement.amount = SUM(stxn.net_amount)` for all stxn in settlement. |
| S2 | `settlement.fees = SUM(stxn.fee)` for all stxn in settlement. |
| S3 | `settlement.tax = SUM(stxn.tax)` for all stxn in settlement. |
| S4 | Each settlement belongs to exactly one merchant. |
| S5 | Each SettlementTransaction references exactly one source entity. |
| S6 | Each processed settlement has a unique UTR. |
| S7 | In ground truth: `bank_entry.utr = settlement.utr` AND `bank_entry.amount = settlement.amount`. |

### Ground Truth Invariants

| # | Invariant |
|---|---|
| G1 | Ground truth is never modified after creation. |
| G2 | Ground truth is deterministic: same seed → same truth. |
| G3 | Every settlement in ground truth has a balanced equation (S1–S3). |
| G4 | Every anomaly is recorded with a unique `anomaly_id`. |
| G5 | Observed data before anomaly injection is identical to ground truth. |
| G6 | Observed data after anomaly injection differs from ground truth only where anomalies were applied. |

---

## 14. Simulation Assumptions

The following behaviors are benchmark assumptions, NOT official Razorpay behavior. Each is labeled for future verification.

| # | Assumption | Reference |
|---|---|---|
| SA1 | Settlement cycle = one calendar day (00:00–23:59 IST). | financial-rules.md § 5 |
| SA2 | Default settlement schedule = T+2 business days. | financial-rules.md § 12 |
| SA3 | Bank holidays are not simulated; all weekdays are business days. | financial-rules.md § 12 |
| SA4 | Cutoff time is midnight IST. | financial-rules.md § 12 |
| SA5 | Fee rates: UPI 0%, Credit Card 2%, Debit Card ≤₹2K 0.4% / >₹2K 0.9%, Netbanking ₹5 flat, Wallet 1.75%. | financial-rules.md § 6 |
| SA6 | Tax (GST) rate = 18% of fee, rounded ROUND_HALF_UP to 2 dp. | financial-rules.md § 7 |
| SA7 | Fees are NOT reversed on refund. | financial-rules.md § 8 |
| SA8 | Adjustment reasons: chargeback, correction, penalty, balance_carryover. | financial-rules.md § 10 |
| SA9 | UTR format: 16-character alphanumeric. | financial-rules.md § 11 |
| SA10 | Bank entry timing: 0–1 business days after settlement processing. | financial-rules.md § 11 |
| SA11 | Order amount distribution: log-normal, range ₹10–₹500,000. | Benchmark assumption |
| SA12 | Payment method distribution: UPI 40%, Card 30%, Netbanking 15%, Wallet 10%, EMI 3%, Bank Transfer 2%. | Benchmark assumption |
| SA13 | Payment success rate: ~90%. | Benchmark assumption |
| SA14 | Refund rate: ~10% of captured payments. | Benchmark assumption |
| SA15 | Partial settlement holdback rate: ~5% of cycles. | Benchmark assumption |
| SA16 | Default anomaly/corruption rate: 5–10% of settlements. | financial-rules.md § Corruption Strategies |

---

## 15. Open Questions

### To Be Verified Against Official Razorpay Documentation

1. **Fee reversal on refund:** Does Razorpay refund the gateway fee (fully or partially) when a merchant issues a refund? Our simulation assumes fees are NOT reversed (SA7).

2. **Debit vs. credit card distinction:** Our `PaymentMethod` enum uses `"card"`. Does Razorpay distinguish debit and credit cards in settlement reports? This affects fee calculation accuracy. The simulator may need an internal `card_sub_type` field not exposed in the domain model.

3. **Adjustment entity in Razorpay API:** Does Razorpay expose adjustments as standalone API entities, or only as line items in settlement CSVs? This affects whether `adjustment_id` is a real Razorpay concept.

4. **UTR format and uniqueness:** What is the actual UTR format for NEFT/RTGS/IMPS? Is UTR guaranteed unique across all banks? Our simulator uses 16-char alphanumeric (SA9).

5. **Settlement cycle frequency:** Does Razorpay support intra-day settlements or on-demand settlements? Our simulator assumes daily cycles (SA1).

6. **Instant refund settlement impact:** For `optimum` (instant) refunds, does the deduction appear immediately in the current cycle or in a separate transaction?

7. **Transfer fee responsibility:** In Razorpay Route, who pays the gateway fee — source merchant, linked account, or split? This affects fee calculation for transfer scenarios.

8. **Tax on adjustments:** Is GST applied to adjustment amounts (e.g., chargeback processing fees)?

9. **Bank entry timing:** What is the actual lag between Razorpay processing a settlement and the merchant seeing the credit in their bank statement?

10. **Settlement report data format:** Does Razorpay provide settlement data as CSV, API response, or both? What are the exact column names? This affects data ingestion design.

11. **Partial settlement triggers:** Under what conditions does Razorpay hold back transactions from a settlement? Risk flags? KYC status? Our simulator uses random holdback (SA15).

12. **Dispute/chargeback lifecycle:** Does Razorpay model chargebacks as a lifecycle (open → under_review → won/lost) or as one-time adjustment entries?

---

## Open Questions / To Be Verified

> This section consolidates all items from the document above that require verification
> before implementation begins.

1. Fee reversal on refund (SA7)
2. Debit vs. credit card distinction in settlement data
3. Adjustment entity existence in Razorpay API
4. UTR format, length, and uniqueness guarantees (SA9)
5. Settlement cycle frequency options (SA1)
6. Instant refund (`optimum`) settlement mechanics
7. Transfer fee responsibility in Razorpay Route
8. Tax treatment on adjustments
9. Bank entry timing after settlement processing (SA10)
10. Settlement report data format and column names
11. Partial settlement trigger conditions (SA15)
12. Dispute/chargeback lifecycle modeling
13. Whether Razorpay exposes SettlementTransaction as an API concept or only in reports
14. Maximum number of partial refunds allowed per payment
15. Whether a payment can appear in multiple settlements (split settlement)
