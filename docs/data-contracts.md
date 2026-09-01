# ReconGraph — Data Contracts

> This document defines the canonical data contracts for every entity in the ReconGraph settlement intelligence system.
> Both the **simulator** and the **backend reconciliation engine** MUST conform to these contracts.

---

## General Conventions

| Convention | Rule |
|---|---|
| **Financial amounts** | MUST use exact decimal arithmetic (e.g., Python `Decimal`). Binary floating-point (IEEE 754 `float` / `double`) is **forbidden** for any monetary value. |
| **Currency** | All amounts are denominated in **Indian Rupees (INR)** unless explicitly stated otherwise. Amounts are stored in **paise** (integer smallest-unit) OR as `Decimal` with exactly **2 decimal places**. The chosen representation must be consistent across the entire system. |
| **Timestamps** | ISO 8601 with timezone (`YYYY-MM-DDTHH:MM:SS+05:30`). All timestamps are in **IST (Asia/Kolkata)** unless otherwise noted. |
| **Identifiers** | Opaque strings. Format varies by entity (see below). Never parse or decode identifiers for business logic. |
| **Null vs. absent** | A field listed as *optional* may be `null` or absent. A field listed as *required* MUST be present and non-null. |

---

## Entity Definitions

---

### 1. Merchant

**Purpose:** Represents a business entity that accepts payments through the payment gateway. A merchant is the top-level organizational unit; all financial activity belongs to exactly one merchant.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `merchant_id` | `string` | ✅ | Unique identifier for the merchant (e.g., `"merch_ABC123"`). **Primary identifier.** |
| `name` | `string` | ✅ | Human-readable business name. |
| `mcc` | `string` | ❌ | Merchant Category Code (ISO 18245). |
| `settlement_schedule` | `string` | ❌ | Default settlement cadence (e.g., `"T+2"`, `"T+3"`). |
| `fee_plan_id` | `string` | ❌ | Reference to the merchant's fee/pricing plan. |
| `status` | `string` | ✅ | Account status: `active`, `suspended`, `deactivated`. |
| `created_at` | `datetime` | ✅ | When the merchant account was created. |

#### Identifier

`merchant_id` — globally unique across the system.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Order | A merchant **has many** orders. | 1 : N |

---

### 2. Order

**Purpose:** Represents a customer's intent to pay. An order is created before any payment attempt and serves as the logical container for one or more payment attempts.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `order_id` | `string` | ✅ | Unique order identifier (e.g., `"order_XYZ789"`). **Primary identifier.** |
| `merchant_id` | `string` | ✅ | The merchant this order belongs to. |
| `amount` | `Decimal` | ✅ | Total order amount (in INR). |
| `currency` | `string` | ✅ | ISO 4217 currency code (e.g., `"INR"`). |
| `status` | `string` | ✅ | Order status: `created`, `attempted`, `paid`. |
| `receipt` | `string` | ❌ | Merchant-supplied receipt/reference number. |
| `notes` | `map<string, string>` | ❌ | Arbitrary key-value metadata from the merchant. |
| `created_at` | `datetime` | ✅ | When the order was created. |

#### Identifier

`order_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Merchant | An order **belongs to** a merchant. | N : 1 |
| Payment | An order **has many** payment attempts. | 1 : N |

---

### 3. Payment

**Purpose:** Represents a single payment attempt (successful or otherwise) against an order. A payment captures the actual movement of money from the customer to the gateway.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `payment_id` | `string` | ✅ | Unique payment identifier (e.g., `"pay_DEF456"`). **Primary identifier.** |
| `order_id` | `string` | ✅ | The order this payment is associated with. |
| `merchant_id` | `string` | ✅ | The merchant this payment belongs to. |
| `amount` | `Decimal` | ✅ | Amount charged (in INR). |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `status` | `string` | ✅ | Payment status: `created`, `authorized`, `captured`, `failed`, `refunded`. |
| `method` | `string` | ✅ | Payment method: `card`, `upi`, `netbanking`, `wallet`, `bank_transfer`, `emi`. |
| `fee` | `Decimal` | ❌ | Gateway fee charged on this payment. Present only after capture. |
| `tax` | `Decimal` | ❌ | Tax (GST) on the fee. Present only after capture. |
| `settlement_id` | `string` | ❌ | The settlement this payment was settled in. May be `null` if not yet settled. |
| `captured_at` | `datetime` | ❌ | When the payment was captured. |
| `created_at` | `datetime` | ✅ | When the payment attempt was created. |
| `notes` | `map<string, string>` | ❌ | Arbitrary key-value metadata. |

#### Identifier

`payment_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Order | A payment **belongs to** an order. | N : 1 |
| Merchant | A payment **belongs to** a merchant. | N : 1 |
| Refund | A payment **has many** refunds. | 1 : N |
| Transfer | A payment **has many** transfers (route/marketplace). | 1 : N |
| SettlementTransaction | A payment **may appear as** a settlement transaction line item. | 1 : 0..N |

> **Note:** `settlement_id` on Payment is a denormalized convenience field. The authoritative settlement linkage is through SettlementTransaction.

---

### 4. Refund

**Purpose:** Represents a full or partial reversal of a captured payment. A refund reduces the net amount that will be settled to the merchant.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `refund_id` | `string` | ✅ | Unique refund identifier (e.g., `"rfnd_GHI012"`). **Primary identifier.** |
| `payment_id` | `string` | ✅ | The payment being refunded. |
| `merchant_id` | `string` | ✅ | The merchant this refund belongs to. |
| `amount` | `Decimal` | ✅ | Refund amount (in INR). May be less than the original payment amount (partial refund). |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `status` | `string` | ✅ | Refund status: `created`, `processed`, `failed`. |
| `speed` | `string` | ❌ | Refund speed: `normal`, `optimum` (instant). Defaults to `normal`. |
| `settlement_id` | `string` | ❌ | The settlement this refund is accounted in. May be `null` if not yet settled. |
| `created_at` | `datetime` | ✅ | When the refund was initiated. |
| `processed_at` | `datetime` | ❌ | When the refund was processed. |
| `notes` | `map<string, string>` | ❌ | Arbitrary key-value metadata. |

#### Identifier

`refund_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Payment | A refund **belongs to** a payment. | N : 1 |
| SettlementTransaction | A refund **may appear as** a settlement transaction line item (as a debit). | 1 : 0..N |

---

### 5. Transfer

**Purpose:** Represents a movement of funds from a payment to a linked account (Razorpay Route / marketplace model). Transfers split a payment's proceeds across multiple recipients.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `transfer_id` | `string` | ✅ | Unique transfer identifier (e.g., `"trf_JKL345"`). **Primary identifier.** |
| `payment_id` | `string` | ✅ | The source payment. |
| `source_merchant_id` | `string` | ✅ | The merchant initiating the transfer. |
| `recipient_merchant_id` | `string` | ✅ | The linked account receiving the transfer. |
| `amount` | `Decimal` | ✅ | Transfer amount (in INR). |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `status` | `string` | ✅ | Transfer status: `created`, `processed`, `reversed`, `failed`. |
| `settlement_id` | `string` | ❌ | The settlement this transfer is accounted in (on the recipient side). |
| `created_at` | `datetime` | ✅ | When the transfer was created. |
| `processed_at` | `datetime` | ❌ | When the transfer was processed. |
| `notes` | `map<string, string>` | ❌ | Arbitrary key-value metadata. |

#### Identifier

`transfer_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Payment | A transfer **originates from** a payment. | N : 1 |
| Merchant (source) | A transfer **debits** the source merchant. | N : 1 |
| Merchant (recipient) | A transfer **credits** the recipient merchant. | N : 1 |
| SettlementTransaction | A transfer **may appear as** a settlement transaction line item. | 1 : 0..N |

---

### 6. Adjustment

**Purpose:** Represents an out-of-band financial adjustment applied to a settlement. Adjustments cover scenarios such as chargebacks, manual corrections, penalty charges, or balance carryovers that are not captured by the normal payment–refund–transfer lifecycle.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `adjustment_id` | `string` | ✅ | Unique adjustment identifier (e.g., `"adj_MNO678"`). **Primary identifier.** |
| `merchant_id` | `string` | ✅ | The merchant this adjustment applies to. |
| `amount` | `Decimal` | ✅ | Adjustment amount. Positive = credit to merchant; negative = debit from merchant. |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `reason` | `string` | ✅ | Reason code or description (e.g., `"chargeback"`, `"correction"`, `"penalty"`, `"balance_carryover"`). |
| `settlement_id` | `string` | ❌ | The settlement this adjustment is applied to. May be `null` if pending. |
| `description` | `string` | ❌ | Human-readable description. |
| `created_at` | `datetime` | ✅ | When the adjustment was created. |

#### Identifier

`adjustment_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Merchant | An adjustment **belongs to** a merchant. | N : 1 |
| Settlement | An adjustment **affects** a settlement. | N : 0..1 |

> **Note:** Adjustments do NOT have a direct foreign key to a Payment or Refund. They are settlement-level entries.

---

### 7. SettlementTransaction

**Purpose:** Represents a single line item within a settlement. Each SettlementTransaction links exactly one financial entity (payment, refund, or transfer) to the settlement it is being settled in. This is the authoritative record of *what was included in a settlement*.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `settlement_txn_id` | `string` | ✅ | Unique line-item identifier (e.g., `"stxn_PQR901"`). **Primary identifier.** |
| `settlement_id` | `string` | ✅ | The settlement this line item belongs to. |
| `merchant_id` | `string` | ✅ | The merchant this line item belongs to. |
| `entity_type` | `string` | ✅ | Type of source entity: `payment`, `refund`, `transfer`, `adjustment`. |
| `entity_id` | `string` | ✅ | Identifier of the source entity (e.g., `payment_id`, `refund_id`, `transfer_id`, `adjustment_id`). |
| `amount` | `Decimal` | ✅ | Gross amount of this line item. |
| `fee` | `Decimal` | ✅ | Fee component (may be `0`). |
| `tax` | `Decimal` | ✅ | Tax component (may be `0`). |
| `net_amount` | `Decimal` | ✅ | Net amount = `amount - fee - tax` for credits; for debits (refunds), net amount reflects the deduction. |
| `type` | `string` | ✅ | `credit` or `debit`. Payments and inbound transfers are credits; refunds and outbound transfers are debits. |
| `created_at` | `datetime` | ✅ | When this line item was created. |

#### Identifier

`settlement_txn_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Settlement | A settlement transaction **belongs to** a settlement. | N : 1 |
| Payment | A settlement transaction **references** a payment (when `entity_type = "payment"`). | N : 0..1 |
| Refund | A settlement transaction **references** a refund (when `entity_type = "refund"`). | N : 0..1 |
| Transfer | A settlement transaction **references** a transfer (when `entity_type = "transfer"`). | N : 0..1 |
| Adjustment | A settlement transaction **references** an adjustment (when `entity_type = "adjustment"`). | N : 0..1 |

> **Important:** Exactly one of Payment / Refund / Transfer / Adjustment is referenced per line item, determined by `entity_type`. The other relationships are absent (not null — absent).

---

### 8. Settlement

**Purpose:** Represents a batch payout from the payment gateway to the merchant's bank account. A single settlement aggregates multiple financial transactions (payments, refunds, transfers, adjustments) into one net amount that is transferred to the merchant's bank.

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `settlement_id` | `string` | ✅ | Unique settlement identifier (e.g., `"setl_STU234"`). **Primary identifier.** |
| `merchant_id` | `string` | ✅ | The merchant receiving this settlement. |
| `amount` | `Decimal` | ✅ | Net settlement amount transferred to the merchant's bank account. |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `status` | `string` | ✅ | Settlement status: `created`, `processed`, `failed`. |
| `fees` | `Decimal` | ✅ | Total fees deducted across all transactions in this settlement. |
| `tax` | `Decimal` | ✅ | Total tax deducted across all transactions in this settlement. |
| `utr` | `string` | ❌ | Unique Transaction Reference — the bank reference number for the actual bank transfer. Present only after the settlement is processed by the bank. |
| `settled_at` | `datetime` | ❌ | When the settlement was processed. |
| `created_at` | `datetime` | ✅ | When the settlement batch was created. |

#### Identifier

`settlement_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Merchant | A settlement **belongs to** a merchant. | N : 1 |
| SettlementTransaction | A settlement **contains many** settlement transactions. | 1 : N |
| BankEntry | A settlement **corresponds to** a bank entry via UTR matching. | 1 : 0..1 |
| Adjustment | A settlement **may include** adjustments. | 1 : 0..N |

> **A single settlement can contain multiple financial transactions.** This is fundamental: payments, refunds, transfers, and adjustments are batched together. The settlement's `amount` equals the net sum of all its constituent SettlementTransaction `net_amount` values.

---

### 9. BankEntry

**Purpose:** Represents a single credit entry in the merchant's bank statement. This is the external, bank-side record of money received. BankEntries are matched to Settlements via the UTR (Unique Transaction Reference).

#### Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `bank_entry_id` | `string` | ✅ | Unique identifier for this bank entry (e.g., `"bnk_VWX567"`). **Primary identifier.** |
| `merchant_id` | `string` | ✅ | The merchant whose bank account received this entry. |
| `account_number` | `string` | ✅ | The bank account number that received the credit. |
| `amount` | `Decimal` | ✅ | Amount credited to the bank account. |
| `currency` | `string` | ✅ | ISO 4217 currency code. |
| `utr` | `string` | ✅ | Unique Transaction Reference from the bank. Used to match against Settlement. |
| `description` | `string` | ❌ | Bank-provided transaction description/narration. |
| `transaction_date` | `datetime` | ✅ | Date the transaction appeared in the bank statement. |
| `value_date` | `datetime` | ❌ | Value date assigned by the bank. |
| `balance` | `Decimal` | ❌ | Running balance after this entry (if available from bank statement). |

#### Identifier

`bank_entry_id` — globally unique.

#### Relationships

| Target | Relationship | Cardinality |
|---|---|---|
| Settlement | A bank entry **corresponds to** a settlement via UTR matching. | 1 : 0..1 |
| Merchant | A bank entry **belongs to** a merchant. | N : 1 |

> **Note:** The Settlement ↔ BankEntry relationship is established by matching `Settlement.utr = BankEntry.utr`. There is no direct foreign key; the UTR is the join evidence.

---

## Financial Graph Relationships

The following table defines the directed relationships in the ReconGraph financial knowledge graph. Each relationship is grounded in observable evidence — a shared identifier or logical derivation.

| Source | Relationship | Target | Evidence / Reason |
|---|---|---|---|
| Merchant | HAS_ORDER | Order | `order.merchant_id = merchant.merchant_id` |
| Order | HAS_PAYMENT | Payment | `payment.order_id = order.order_id` |
| Payment | BELONGS_TO | Merchant | `payment.merchant_id = merchant.merchant_id` |
| Payment | HAS_REFUND | Refund | `refund.payment_id = payment.payment_id` |
| Payment | HAS_TRANSFER | Transfer | `transfer.payment_id = payment.payment_id` |
| Payment | SETTLED_IN | Settlement | `payment.settlement_id = settlement.settlement_id` (denormalized) or via SettlementTransaction where `entity_type = "payment"` |
| Refund | SETTLED_IN | Settlement | Via SettlementTransaction where `entity_type = "refund"` and `entity_id = refund.refund_id` |
| Transfer | SETTLED_IN | Settlement | Via SettlementTransaction where `entity_type = "transfer"` and `entity_id = transfer.transfer_id` |
| Transfer | FROM_MERCHANT | Merchant (source) | `transfer.source_merchant_id = merchant.merchant_id` |
| Transfer | TO_MERCHANT | Merchant (recipient) | `transfer.recipient_merchant_id = merchant.merchant_id` |
| SettlementTransaction | PART_OF | Settlement | `settlement_txn.settlement_id = settlement.settlement_id` |
| SettlementTransaction | REFERENCES_PAYMENT | Payment | `settlement_txn.entity_id = payment.payment_id` when `entity_type = "payment"` |
| SettlementTransaction | REFERENCES_REFUND | Refund | `settlement_txn.entity_id = refund.refund_id` when `entity_type = "refund"` |
| SettlementTransaction | REFERENCES_TRANSFER | Transfer | `settlement_txn.entity_id = transfer.transfer_id` when `entity_type = "transfer"` |
| SettlementTransaction | REFERENCES_ADJUSTMENT | Adjustment | `settlement_txn.entity_id = adjustment.adjustment_id` when `entity_type = "adjustment"` |
| Settlement | BANKED_AS | BankEntry | `settlement.utr = bank_entry.utr` — UTR string match is the evidence |
| Adjustment | AFFECTS | Settlement | `adjustment.settlement_id = settlement.settlement_id` |
| Adjustment | BELONGS_TO | Merchant | `adjustment.merchant_id = merchant.merchant_id` |
| BankEntry | BELONGS_TO | Merchant | `bank_entry.merchant_id = merchant.merchant_id` |

### Relationship Notes

1. **Settlement ↔ BankEntry** is a *soft* join on UTR, not a foreign key. This is intentional: the bank statement is an external data source and may not always match.
2. **Payment → Settlement** can be derived from the denormalized `payment.settlement_id` field OR from the SettlementTransaction join table. When both are available they MUST agree; if they disagree this is an exception.
3. **Refunds and Transfers** do NOT have a direct `settlement_id` on the entity in all cases. The SettlementTransaction is the authoritative linkage.
4. **Not every entity has every foreign key.** For example, a Payment may not yet have a `settlement_id`. A BankEntry may not match any known Settlement. These are expected states, not errors.

---

## Entity Relationship Diagram (Textual)

```
Merchant
  │
  ├──< Order
  │      │
  │      └──< Payment
  │             │
  │             ├──< Refund
  │             │
  │             └──< Transfer ──> Merchant (recipient)
  │
  ├──< Adjustment ──> Settlement
  │
  └──< Settlement
         │
         ├──< SettlementTransaction ──> Payment | Refund | Transfer | Adjustment
         │
         └── (UTR) ── BankEntry
```

---

## Open Questions / To Be Verified

1. **Settlement ID on Refund entity:** Does the Razorpay Refund object directly carry a `settlement_id` field, or is the settlement linkage only available through the settlement transaction report? Our contract currently lists it as optional on the Refund entity.
2. **Adjustment entity structure:** Razorpay's public API documentation does not prominently feature a standalone "Adjustment" entity. Adjustments may appear only as line items in settlement reports. Verify the actual shape of adjustment data.
3. **Transfer settlement behavior:** When a transfer is made via Razorpay Route, does the settlement for the linked account carry its own `settlement_id` namespace, or does it reference the parent merchant's settlement? Verify settlement isolation across linked accounts.
4. **UTR uniqueness:** Is the UTR guaranteed to be unique across all banks and all time, or only within a specific bank? This affects the reliability of the Settlement ↔ BankEntry join.
5. **Fee and tax on refunds:** Are gateway fees refunded (fully or partially) when a refund is processed? If so, how does this appear in the settlement transaction?
6. **Multiple currencies:** While our system currently assumes INR-only, verify whether Razorpay settlement reports can contain multi-currency entries for international payments.
7. **SettlementTransaction as a Razorpay concept:** Verify whether Razorpay exposes individual settlement line items via API or only through downloadable reports. This affects how we model data ingestion.
