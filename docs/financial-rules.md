# ReconGraph — Financial Rules

> This document defines the financial rules, lifecycle states, reconciliation logic, and scenario families
> that govern both the **simulator** (synthetic data generation) and the **reconciliation engine** (backend).
>
> **Foundational principle:** The AI must NEVER determine financial truth.
> Financial truth must come from deterministic calculations and source records.

### Classification Convention

Rules and behaviors in this document are classified as:
- **OFFICIAL / DOCUMENTED:** Supported by official Razorpay documentation.
- **SIMULATION ASSUMPTION:** Chosen intentionally for our synthetic benchmark.
- **UNVERIFIED:** Known/possible behavior that must not be treated as established truth. The simulator implementation must never silently convert an UNVERIFIED rule into a hard-coded production claim.

---

## 1. Money Representation

| Rule | Detail |
|---|---|
| **Exact arithmetic** | All monetary calculations MUST use exact decimal arithmetic (e.g., Python `Decimal` with appropriate precision). Binary floating-point (`float`, `double`) is **forbidden**. |
| **Precision** | Monetary values carry exactly **2 decimal places** for INR. |
| **Rounding** | When rounding is unavoidable, the rounding mode is defined by a configurable simulation policy. All rounding operations MUST be explicit, never implicit. |

> **SIMULATION ASSUMPTION:** The rounding policy (e.g., `ROUND_HALF_UP`) is a configurable benchmark value. The implementation must not assume this is verified Razorpay behavior unless established by official documentation.
| **Representation** | Amounts may be stored as either: (a) integer **paise** (1 INR = 100 paise), or (b) `Decimal` strings with 2 decimal places. The system MUST use one representation consistently. |
| **Zero** | Zero amounts are valid. Negative amounts are valid only for adjustments (debits). |

---

## 2. Currency

| Rule | Detail |
|---|---|
| **Default currency** | INR (Indian Rupee), ISO 4217 code `"INR"`. |
| **Multi-currency** | Not supported in the initial implementation. All entities assume INR. |
| **Currency field** | Every entity with an `amount` field MUST also carry a `currency` field set to `"INR"`. |

> **SIMULATION ASSUMPTION:** The simulator generates INR-only data. Multi-currency support is deferred.

---

## 3. Payment Lifecycle

A payment progresses through these states:

```
created → authorized → captured → [refunded]
                   ↘ failed
         ↘ failed
```

| State | Meaning |
|---|---|
| `created` | Payment attempt initiated. No money has moved. |
| `authorized` | Funds are authorized (held) but not yet captured. |
| `captured` | Funds are captured. Money has moved from customer to gateway. This payment is now eligible for settlement. |
| `failed` | Payment attempt failed at any stage. No money moved (or authorization was released). |
| `refunded` | The full amount of a captured payment has been refunded. Partial refunds do NOT change the payment status to `refunded` — the payment remains `captured`. |

### Rules

- Only `captured` payments are eligible for settlement.
- A payment can only be refunded after it is `captured`.
- Multiple partial refunds are allowed up to the original payment amount. The sum of all refund amounts for a payment MUST NOT exceed the payment amount.
- `authorized` payments that are not captured within a gateway-defined window are automatically released (treated as `failed`).

> **SIMULATION ASSUMPTION:** Authorization hold window is **5 days**. Payments not captured within this window become `failed`.

---

## 4. Settlement Lifecycle

A settlement progresses through these states:

```
created → processed → [failed]
```

| State | Meaning |
|---|---|
| `created` | Settlement batch has been assembled. The net amount has been calculated. Bank transfer has not yet occurred. |
| `processed` | Funds have been transferred to the merchant's bank account. UTR is available. |
| `failed` | Bank transfer failed (e.g., invalid account details, bank rejection). |

### Rules

- A settlement is created by the gateway, not by the merchant.
- A settlement aggregates all eligible transactions (payments, refunds, transfers, adjustments) for a merchant within a settlement cycle.
- Once a settlement is `processed`, its constituent transactions are considered settled.

---

## 5. Settlement Grouping

| Rule | Detail |
|---|---|
| **Batching** | Multiple payments, refunds, transfers, and adjustments are grouped into a single settlement. |
| **Per-merchant** | Each settlement belongs to exactly one merchant. Transactions from different merchants are never co-mingled in a single settlement. |
| **Settlement cycle** | Transactions captured within a settlement cycle window are grouped together. |
| **Net amount** | `settlement.amount = SUM(settlement_txn.net_amount)` across all constituent SettlementTransactions. |

> **SIMULATION ASSUMPTION:** The default settlement cycle groups all captured transactions from a calendar day and settles them as one batch. Custom settlement schedules (hourly, on-demand) are not simulated in the initial version.

---

## 6. Fees

| Rule | Detail |
|---|---|
| **Fee basis** | Fees are charged as a percentage of the payment amount, varying by payment method. |
| **Fee deduction** | Fees are deducted from the settlement amount, not charged separately. The merchant receives `amount - fee - tax`. |
| **Per-transaction** | Fees are calculated per payment, not per settlement. |
| **Fee on refunds** | When a refund is issued, the original fee is **not** refunded back to the merchant. |

### Fee Rates (SIMULATION ASSUMPTION)

| Payment Method | Fee Rate |
|---|---|
| UPI | 0% (zero MDR per RBI regulation) |
| Debit Card (≤ ₹2,000) | 0.40% |
| Debit Card (> ₹2,000) | 0.90% |
| Credit Card | 2.00% |
| Netbanking | ₹5 flat per transaction |
| Wallet | 1.75% |

> **SIMULATION ASSUMPTION:** These fee rates are simplified assumptions for synthetic benchmark data. Actual Razorpay pricing varies by merchant agreement, volume tiers, and negotiated contracts.

---

## 7. Tax

| Rule | Detail |
|---|---|
| **Tax type** | GST (Goods and Services Tax) on the gateway fee. |
| **Tax rate** | 18% of the fee amount. |
| **Calculation** | `tax = fee × 0.18`, rounded to 2 decimal places using ROUND_HALF_UP. |
| **Applicability** | Tax is applied to every non-zero fee. Zero-fee transactions (e.g., UPI) have zero tax. |

> **SIMULATION ASSUMPTION:** A flat 18% GST rate is used. Actual GST rules may vary based on merchant registration state, type of service, etc.
>
> **SIMULATION ASSUMPTION:** Adjustments may carry applicable fee and tax components where the contract permits. We do not assert that Razorpay actually applies a specific tax treatment to every adjustment until verified.

---

## 8. Refunds

| Rule | Detail |
|---|---|
| **Eligibility** | Only `captured` payments can be refunded. |
| **Partial refunds** | Multiple partial refunds are allowed. `SUM(refund.amount) ≤ payment.amount`. |
| **Full refund** | A single refund for the full payment amount. Payment status changes to `refunded`. |
| **Settlement impact** | A refund appears as a **debit** line item in the settlement. It reduces the net settlement amount. |
| **Timing** | A refund may appear in the same settlement cycle as the original payment, or in a later cycle. |
| **Fee handling** | The fee treatment on refunds is a configurable simulation policy (e.g., `no_reversal`, `full_reversal`, `partial_reversal`). |
| **Refund speed** | `normal` refunds are processed in the next settlement cycle. `optimum` (instant) refunds are processed immediately from the merchant's balance. |

> **SIMULATION ASSUMPTION:** Refund fee treatment is configured via policy. The V1 benchmark may use a `no_reversal` policy, but we do not claim this represents universal Razorpay behavior unless officially documented.

---

## 9. Transfers

| Rule | Detail |
|---|---|
| **Purpose** | Transfers (Razorpay Route) split payment proceeds across linked accounts (marketplace model). |
| **Source** | A transfer originates from a captured payment. |
| **Settlement impact** | On the source merchant's side, the transfer amount is deducted from the settlement. On the recipient's side, the transfer amount is added to their settlement. |
| **Multiple transfers** | A single payment can have multiple transfers to different linked accounts. `SUM(transfer.amount) ≤ payment.amount`. |
| **Independent settlement** | The recipient linked account has its own independent settlement cycle. |

> **SIMULATION ASSUMPTION:** Transfers settle into the recipient's settlement cycle independently. The source merchant's settlement is reduced by the transfer amount.
>
> **SIMULATION ASSUMPTION:** Transfer fee responsibility is a configurable simulation policy (e.g. source bears all, or proportional split). The V1 benchmark may assume the source merchant bears the fee, but this is an unverified assumption.

---

## 10. Adjustments

| Rule | Detail |
|---|---|
| **Purpose** | Adjustments represent non-standard financial entries: chargebacks, penalties, corrections, balance carryovers. |
| **Direction** | Positive amount = credit to merchant. Negative amount = debit from merchant. |
| **Settlement association** | An adjustment is associated with a specific settlement. It appears as a line item in that settlement. |
| **No payment link** | Adjustments do NOT reference a specific payment. They are settlement-level entries. |

> **SIMULATION ASSUMPTION:** The set of adjustment reasons is: `chargeback`, `correction`, `penalty`, `balance_carryover`. Actual Razorpay adjustment types may differ.

---

## 11. UTR / Bank Relationship

| Rule | Detail |
|---|---|
| **UTR** | The Unique Transaction Reference is an external banking reference represented as a string for the actual NEFT/RTGS/IMPS transfer from the gateway's account to the merchant's bank account. The simulator may generate a deterministic mock UTR. |

> **SIMULATION ASSUMPTION:** We do not claim a universal Razorpay UTR format. Mock UTRs generated by the simulator are explicitly synthetic. ReconGraph V1 is not required to validate real banking UTR formats.
| **Matching** | Settlement ↔ BankEntry matching is performed by comparing `settlement.utr` with `bank_entry.utr`. |
| **One-to-one** | Each settlement maps to at most one bank entry, and each bank entry maps to at most one settlement (via UTR). |
| **Availability** | UTR is available on the Settlement entity only after the settlement status is `processed`. |
| **Soft join** | The UTR match is not a foreign key. Mismatches are possible and constitute reconciliation exceptions. |

### UTR Mismatch Scenarios

| Scenario | Cause |
|---|---|
| Settlement has UTR but no matching BankEntry | Bank statement not yet available, or entry not yet credited. |
| BankEntry has UTR but no matching Settlement | Unknown deposit; may be from a different source or a gateway-side reporting gap. |
| UTR matches but amounts differ | Partial credit, bank charges deducted, or data error. |

---

## 12. Settlement Timing

| Rule | Detail |
|---|---|
| **T+N model** | Settlements are processed N business days after the transaction capture date. |
| **Default schedule** | T+2 (two business days after capture). |
| **Business days** | Excludes weekends (Saturday, Sunday) and Indian bank holidays. |
| **Cutoff time** | Transactions captured before the daily cutoff are included in that day's settlement cycle. Transactions after the cutoff roll to the next cycle. |

> **SIMULATION ASSUMPTION:** Default settlement schedule is T+2. Cutoff time is configurable (V1 simulation default is 00:00 IST / midnight, but this is not presented as verified Razorpay behavior). Bank holidays are not simulated in the initial version (all weekdays are treated as business days).

---

## 13. Partial Settlement Scenarios

| Scenario | Description |
|---|---|
| **Partial settlement** | Not all eligible transactions are included in a single settlement batch. Some transactions may be held back and settled in a subsequent cycle. |
| **Split settlement** | A single payment's proceeds may theoretically appear across multiple settlements (e.g., if a refund is processed between settlement cycles). |
| **Held transactions** | The gateway may hold specific transactions from settlement due to risk review or compliance checks. |

### Rules

- A payment should normally appear in exactly one settlement. If a payment appears in zero settlements, it is unsettled. If it appears in more than one, this is an exception.

> **SIMULATION ASSUMPTION:** For the ReconGraph V1 benchmark, a captured Payment credit is assigned to exactly one SettlementTransaction/Settlement. Refunds or adjustments may affect later settlements. This is a V1 benchmark constraint, not a universal claim about all Razorpay products.
- Refunds may appear in a different settlement cycle than the original payment.
- Cross-cycle interactions (payment in cycle N, refund in cycle N+3) are normal and expected.

> **SIMULATION ASSUMPTION:** Partial settlements are simulated by randomly withholding a subset of eligible transactions from a settlement cycle. These are then included in the next cycle.

---

## 14. Reconciliation Rules

### The Settlement Equation

For any settlement, the following equation MUST hold within the configured tolerance:

```
settlement.amount = SUM(credit_components) - SUM(debit_components)
```

The components for the V1 simulation include:
- payment credits
- refund debits
- transfer debits where applicable
- adjustment credits/debits
- fee debits
- tax debits
- fee/tax components associated with other financial events where the model permits them (without double-counting fees or taxes).

Where all sums are taken over the SettlementTransactions belonging to that settlement.

Equivalently:

```
settlement.amount = SUM(settlement_txn.net_amount) for all txn in settlement
```

### Tolerance

| Rule | Detail |
|---|---|
| **Default tolerance** | ₹0.00 (exact match). |
| **Configurable** | The tolerance may be configured to allow small rounding discrepancies (e.g., ₹0.01). |
| **Application** | `|settlement.amount - calculated_amount| ≤ tolerance` → RECONCILED. Otherwise → EXCEPTION. |

### Bank Reconciliation

```
settlement.amount = bank_entry.amount  (where UTR matches)
```

If the amounts match (within tolerance), the settlement is considered bank-reconciled. If not, an exception is raised.

### Three-Way Reconciliation

Full reconciliation requires agreement across three dimensions:

1. **Transaction-level:** The settlement amount can be reconstructed from constituent transactions.
2. **Gateway-level:** The settlement record from the gateway matches the calculated amount.
3. **Bank-level:** The bank statement entry matches the settlement amount via UTR.

---

## 15. Exception Rules

An **exception** is any case where reconciliation cannot be deterministically confirmed.

### Exception Types

| Exception Type | Description |
|---|---|
| `AMOUNT_MISMATCH` | Calculated settlement amount does not match the reported settlement amount. |
| `MISSING_SETTLEMENT` | Transactions exist that reference a settlement ID with no corresponding Settlement record. |
| `MISSING_TRANSACTION` | A settlement references transactions that cannot be found in the source records. |
| `MISSING_BANK_ENTRY` | A processed settlement has a UTR but no matching bank entry. |
| `UNMATCHED_BANK_ENTRY` | A bank entry exists with no matching settlement UTR. |
| `BANK_AMOUNT_MISMATCH` | Settlement amount and bank entry amount disagree (UTR matches). |
| `DUPLICATE_TRANSACTION` | The same transaction ID appears multiple times in settlement records. |
| `DUPLICATE_UTR` | The same UTR appears on multiple settlements or multiple bank entries. |
| `CROSS_REFERENCE_MISMATCH` | A payment's denormalized `settlement_id` disagrees with the SettlementTransaction linkage. |

### Exception Handling

1. Exceptions are logged with full context (entity IDs, amounts, calculated vs. observed values).
2. The AI investigation agent may propose a **hypothesis** to explain an exception.
3. **An AI hypothesis is NEVER sufficient to mark a case as RESOLVED.**
4. The **financial verifier** (a deterministic, rule-based module) must independently validate the hypothesis using source evidence before the exception can be resolved.
5. If the verifier cannot confirm the hypothesis, the exception is **ESCALATED** for human review.

---

## 16. Ground-Truth Rules

### Definitions

| Concept | Definition |
|---|---|
| **GROUND TRUTH** | What actually happened in the synthetic financial world. This is the simulator's internal, complete, uncorrupted record of every financial event. Ground truth is NEVER exposed to the reconciliation engine. |
| **OBSERVED DATA** | The records supplied to ReconGraph. This is what the reconciliation engine sees. The simulator may deliberately corrupt, omit, or duplicate records from observed data while keeping ground truth unchanged. |

### Rules

1. Ground truth is deterministic. Given the same random seed, the simulator produces identical ground truth.
2. Observed data is derived from ground truth by applying **corruption scenarios** (see Scenario Families below).
3. The reconciliation engine and AI agent operate ONLY on observed data. They never have access to ground truth.
4. Benchmark scoring compares the reconciliation engine's conclusions against ground truth to measure accuracy.
5. Ground truth includes: all entities (with correct field values), all relationships, the settlement equation result for every settlement, and the list of deliberate corruptions applied.

---

## Conceptual States

### Reconciliation States

| State | Definition |
|---|---|
| **RECONCILED** | The observed settlement can be deterministically reconstructed from the available financial records within the configured tolerance. No discrepancies exist. |
| **EXCEPTION** | The observed settlement cannot currently be reconstructed. A discrepancy has been detected between expected and observed values. |
| **RESOLVED** | An exception has been explained by a hypothesis AND the deterministic financial verifier has independently confirmed the explanation using source evidence. |
| **ESCALATED** | The system cannot prove an explanation. The exception must be forwarded for human review. The system MUST NOT resolve the exception on its own. |

### State Transitions

```
    ┌──────────────┐
    │   RECONCILED  │ ← deterministic check passes
    └──────────────┘

    ┌──────────────┐
    │   EXCEPTION   │ ← deterministic check fails
    └──────┬───────┘
           │
     AI proposes hypothesis
     Verifier checks hypothesis
           │
     ┌─────┴─────┐
     │           │
 Confirmed    Not confirmed
     │           │
     ▼           ▼
┌──────────┐ ┌──────────┐
│ RESOLVED │ │ ESCALATED│
└──────────┘ └──────────┘
```

### Critical Rule

> **An AI hypothesis is never sufficient to mark a case as RESOLVED.**
>
> The financial verifier must independently validate the hypothesis against source records.
> This is a non-negotiable system invariant.

---

## Scenario Families

The following scenarios define the test cases for the simulator and the expected behavior of the reconciliation engine.

---

### Scenario 1: Normal Settlement

**What the true world looks like:**
- A merchant has N payments captured during a settlement cycle.
- No refunds, transfers, or adjustments.
- Fees and tax are calculated per payment.
- A settlement is created with the correct net amount.
- The settlement is processed and a UTR is assigned.
- A matching bank entry exists with the same UTR and amount.

**What observed data looks like:**
- All records are present, complete, and accurate.

**What ReconGraph should do:**
- Deterministically reconcile the settlement. Status = `RECONCILED`.
- No exceptions raised.

---

### Scenario 2: Many Payments → One Settlement

**What the true world looks like:**
- A merchant has a large number of payments (e.g., 50–500) captured across the settlement cycle.
- Multiple payment methods with varying fee rates.
- All payments are batched into a single settlement.
- Net amount = SUM(payment amounts) - SUM(fees) - SUM(tax).

**What observed data looks like:**
- All records are present, complete, and accurate.

**What ReconGraph should do:**
- Reconstruct the settlement amount by summing all constituent transactions.
- Status = `RECONCILED`.

---

### Scenario 3: Partial Settlement

**What the true world looks like:**
- A merchant has 20 captured payments eligible for settlement.
- Only 15 are included in the current settlement; 5 are held for the next cycle.

**What observed data looks like:**
- The settlement and its 15 SettlementTransactions are provided.
- The 5 held payments exist but are not linked to this settlement.

**What ReconGraph should do:**
- Reconcile the settlement using only the 15 included transactions. Status = `RECONCILED`.
- The 5 unsettled payments should be flagged as pending/unsettled, not as exceptions.

---

### Scenario 4: Multiple Partial Refunds

**What the true world looks like:**
- A payment of ₹10,000 is captured.
- Three partial refunds are issued: ₹2,000, ₹3,000, ₹1,500.
- The payment and refunds settle in different cycles.
- Each refund appears as a debit in its respective settlement.

**What observed data looks like:**
- All records are present. The payment appears as a credit in Settlement A. Refunds appear as debits in Settlements B and C.

**What ReconGraph should do:**
- Reconcile each settlement independently.
- Verify that total refunds (₹6,500) ≤ payment amount (₹10,000).
- Status = `RECONCILED` for all settlements.

---

### Scenario 5: Fees and Tax

**What the true world looks like:**
- A settlement contains payments with different payment methods (UPI at 0%, credit card at 2%, debit card at 0.9%).
- Fees are calculated per transaction. Tax (18% GST) is applied to each fee.
- The net settlement amount reflects all deductions.

**What observed data looks like:**
- All records are present. Fee and tax fields are populated on each SettlementTransaction.

**What ReconGraph should do:**
- Independently recalculate fees and tax per transaction.
- Verify the net amount matches. Status = `RECONCILED`.
- If fee recalculation differs from the reported fee, raise an `AMOUNT_MISMATCH` exception on the specific transaction.

---

### Scenario 6: Adjustment

**What the true world looks like:**
- A settlement includes normal payments plus a chargeback adjustment (negative ₹5,000) and a correction adjustment (positive ₹200).
- The net settlement amount accounts for both adjustments.

**What observed data looks like:**
- All records are present including adjustment entries.

**What ReconGraph should do:**
- Include adjustments in the settlement equation.
- Verify net amount. Status = `RECONCILED`.

---

### Scenario 7: Transfer

**What the true world looks like:**
- A marketplace merchant receives a ₹10,000 payment.
- ₹7,000 is transferred to Linked Account A, ₹2,000 to Linked Account B.
- The source merchant's settlement is reduced by ₹9,000 (transfer total).
- Each linked account receives their transfer amount in their own settlement.

**What observed data looks like:**
- All records are present across source and linked accounts.

**What ReconGraph should do:**
- Reconcile the source merchant's settlement (payment credit minus transfer debits minus fees/tax).
- Reconcile each linked account's settlement independently.
- Status = `RECONCILED` for all.

---

### Scenario 8: Cross-Cycle Event

**What the true world looks like:**
- A payment is captured in cycle N and settled in Settlement A.
- A refund for this payment is processed in cycle N+3 and appears in Settlement D.
- The two settlements are independent.

**What observed data looks like:**
- All records are present. The temporal gap between capture and refund is visible in timestamps.

**What ReconGraph should do:**
- Reconcile Settlement A (with the payment credit) independently.
- Reconcile Settlement D (with the refund debit) independently.
- Recognize the cross-cycle relationship between the payment and its refund.
- Status = `RECONCILED` for both.

---

### Scenario 9: Missing Record

**What the true world looks like:**
- A settlement with 10 payments. All correct.

**What observed data looks like:**
- One payment record is deliberately omitted from observed data.
- The settlement still references the missing payment via SettlementTransaction.

**What ReconGraph should do:**
- Detect that the settlement cannot be fully reconstructed.
- Raise `MISSING_TRANSACTION` exception.
- AI agent investigates and hypothesizes a missing payment.
- Verifier checks: can the gap be explained by a single missing payment of amount X? If so → `RESOLVED`. If not → `ESCALATED`.

---

### Scenario 10: Incorrect Amount

**What the true world looks like:**
- A payment of ₹5,000 is correctly captured and settled.

**What observed data looks like:**
- The payment's `amount` field is corrupted to ₹5,500 in observed data.
- The settlement amount remains based on the true ₹5,000.

**What ReconGraph should do:**
- Detect `AMOUNT_MISMATCH`: reconstructed settlement amount (using ₹5,500) does not match the reported settlement amount.
- AI agent investigates and hypothesizes an incorrect payment amount.
- Verifier checks: does correcting the payment amount to ₹X restore the settlement equation? If exactly one correction resolves the discrepancy → `RESOLVED`. Otherwise → `ESCALATED`.

---

### Scenario 11: Duplicate Record

**What the true world looks like:**
- A payment exists once in the financial world.

**What observed data looks like:**
- The same payment appears twice in the settlement transaction records (duplicate row).

**What ReconGraph should do:**
- Detect `DUPLICATE_TRANSACTION`: the same entity_id appears more than once.
- Raise an exception.
- AI agent hypothesizes a duplicate entry.
- Verifier checks: does removing the duplicate restore the settlement equation? If so → `RESOLVED`. Otherwise → `ESCALATED`.

---

### Scenario 12: Unexplainable Discrepancy

**What the true world looks like:**
- A settlement with correct data.

**What observed data looks like:**
- Multiple records are corrupted simultaneously in ways that cannot be explained by any single hypothesis.

**What ReconGraph should do:**
- Detect exceptions.
- AI agent attempts investigation but cannot form a single coherent hypothesis.
- Verifier cannot confirm any proposed explanation.
- Status = `ESCALATED`. The system explicitly does NOT guess.

---

## Corruption Strategies (Simulator)

The simulator uses the following strategies to derive observed data from ground truth:

| Strategy | Description |
|---|---|
| `OMIT_RECORD` | Remove a record entirely from observed data. |
| `CORRUPT_AMOUNT` | Modify a financial amount by a random delta. |
| `DUPLICATE_RECORD` | Insert an identical copy of an existing record. |
| `SWAP_REFERENCE` | Replace a foreign key with an incorrect but valid reference. |
| `OMIT_FIELD` | Set an optional field to `null` that should have a value. |
| `DELAY_RECORD` | Shift a timestamp to simulate late reporting. |
| `COMPOSITE` | Apply multiple strategies to the same dataset. |

> **SIMULATION ASSUMPTION:** Corruption rates and strategy selection are configurable. Default corruption rate is 5–10% of records per scenario.

---

## Summary of Key Invariants

1. **Financial truth is deterministic.** It is never inferred by AI.
2. **An AI hypothesis is never sufficient to mark a case as RESOLVED.** The financial verifier must independently validate.
3. **The settlement equation must hold.** `settlement.amount = SUM(settlement_txn.net_amount)`.
4. **UTR is the bridge between gateway and bank.** Settlement ↔ BankEntry is a soft join.
5. **Ground truth is never exposed to the reconciliation engine.** It exists only for benchmarking.
6. **Exact decimal arithmetic is mandatory.** No floating-point for money. Ever.
7. **Exceptions that cannot be proven are ESCALATED, never silently resolved.**

---

## Open Questions / To Be Verified

1. **Fee reversal on refund:** Does Razorpay refund the gateway fee (fully or partially) when a merchant issues a refund? Our simulation assumes fees are NOT reversed, but this should be verified.
2. **Adjustment data format:** How do adjustments appear in Razorpay's settlement reports? Are they standalone records or embedded within the settlement CSV? Verify the actual schema.
3. **Instant refund impact:** For `optimum` (instant) refunds, is the amount deducted from the merchant's available balance immediately, or does it appear in the next settlement cycle?
4. **Settlement frequency options:** Does Razorpay support settlement frequencies other than daily (e.g., hourly, weekly, on-demand)? This affects simulation parameters.
5. **Tax on adjustments:** Is GST charged on adjustment amounts (e.g., on chargeback fees)? Verify the tax treatment.
6. **Partial settlement triggers:** Under what circumstances does Razorpay hold back transactions from a settlement cycle? Risk review thresholds? KYC status?
7. **Transfer fee responsibility:** In the Route/marketplace model, who pays the fee — the source merchant, the linked account, or both? How does this appear in the settlement?
8. **UTR format and length:** What is the standard format of a UTR across Indian banks? Is there a guaranteed structure (e.g., 16 or 22 characters)?
9. **Bank entry timing:** What is the typical lag between settlement processing and bank entry appearance? Is it same-day or T+1?
10. **Dispute/chargeback lifecycle:** Does Razorpay expose a structured dispute lifecycle (open → under_review → won/lost), or are chargebacks communicated only as adjustments?
