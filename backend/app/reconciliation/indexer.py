"""
Deterministic indexing and normalization for ObservedWorld datasets.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from backend.app.models.adjustment import Adjustment
from backend.app.models.bank_entry import BankEntry
from backend.app.models.merchant import Merchant
from backend.app.models.order import Order
from backend.app.models.payment import Payment
from backend.app.models.refund import Refund
from backend.app.models.settlement import Settlement
from backend.app.models.settlement_transaction import SettlementTransaction
from simulator.observed.models import ObservedWorld


class NormalizedObservationIndex:
    """
    In-memory deterministic index over an ObservedWorld.

    Indexes all primary keys as Dict[str, List[Entity]] to capture duplicate IDs
    and provides constant-time relational traversals.
    """

    def __init__(self, observed: ObservedWorld):
        self.observed = observed

        # Primary Key Indexes: Dict[id, List[Entity]]
        self.merchants_by_id: Dict[str, List[Merchant]] = defaultdict(list)
        self.orders_by_id: Dict[str, List[Order]] = defaultdict(list)
        self.payments_by_id: Dict[str, List[Payment]] = defaultdict(list)
        self.refunds_by_id: Dict[str, List[Refund]] = defaultdict(list)
        self.adjustments_by_id: Dict[str, List[Adjustment]] = defaultdict(list)
        self.settlements_by_id: Dict[str, List[Settlement]] = defaultdict(list)
        self.stxns_by_id: Dict[str, List[SettlementTransaction]] = defaultdict(list)
        self.bank_entries_by_id: Dict[str, List[BankEntry]] = defaultdict(list)

        # Relational Indexes
        self.stxns_by_settlement_id: Dict[str, List[SettlementTransaction]] = defaultdict(list)
        self.stxns_by_target_entity: Dict[Tuple[str, str], List[SettlementTransaction]] = defaultdict(list)
        self.bank_entries_by_utr: Dict[str, List[BankEntry]] = defaultdict(list)
        self.settlements_by_utr: Dict[str, List[Settlement]] = defaultdict(list)
        self.payments_by_order_id: Dict[str, List[Payment]] = defaultdict(list)
        self.refunds_by_payment_id: Dict[str, List[Refund]] = defaultdict(list)
        self.adjustments_by_settlement_id: Dict[str, List[Adjustment]] = defaultdict(list)

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populates all deterministic indexes."""
        # 1. Merchants
        for m in self.observed.merchants:
            self.merchants_by_id[m.merchant_id].append(m)

        # 2. Orders
        for o in self.observed.orders:
            self.orders_by_id[o.order_id].append(o)

        # 3. Payments
        for p in self.observed.payments:
            self.payments_by_id[p.payment_id].append(p)
            if p.order_id:
                self.payments_by_order_id[p.order_id].append(p)

        # 4. Refunds
        for r in self.observed.refunds:
            self.refunds_by_id[r.refund_id].append(r)
            if r.payment_id:
                self.refunds_by_payment_id[r.payment_id].append(r)

        # 5. Adjustments
        for a in self.observed.adjustments:
            self.adjustments_by_id[a.adjustment_id].append(a)
            if a.settlement_id:
                self.adjustments_by_settlement_id[a.settlement_id].append(a)

        # 6. Settlement Transactions
        for st in self.observed.settlement_transactions:
            self.stxns_by_id[st.settlement_txn_id].append(st)
            self.stxns_by_settlement_id[st.settlement_id].append(st)
            target_key = (st.entity_type, st.entity_id)
            self.stxns_by_target_entity[target_key].append(st)

        # 7. Settlements
        for s in self.observed.settlements:
            self.settlements_by_id[s.settlement_id].append(s)
            if s.utr:
                self.settlements_by_utr[s.utr].append(s)

        # 8. Bank Entries
        for b in self.observed.bank_entries:
            self.bank_entries_by_id[b.bank_entry_id].append(b)
            if b.utr:
                self.bank_entries_by_utr[b.utr].append(b)

    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        records = self.merchants_by_id.get(merchant_id)
        return records[0] if records else None

    def get_order(self, order_id: str) -> Optional[Order]:
        records = self.orders_by_id.get(order_id)
        return records[0] if records else None

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        records = self.payments_by_id.get(payment_id)
        return records[0] if records else None

    def get_refund(self, refund_id: str) -> Optional[Refund]:
        records = self.refunds_by_id.get(refund_id)
        return records[0] if records else None

    def get_adjustment(self, adjustment_id: str) -> Optional[Adjustment]:
        records = self.adjustments_by_id.get(adjustment_id)
        return records[0] if records else None

    def get_settlement(self, settlement_id: str) -> Optional[Settlement]:
        records = self.settlements_by_id.get(settlement_id)
        return records[0] if records else None

    def get_stxns_for_settlement(self, settlement_id: str) -> List[SettlementTransaction]:
        return self.stxns_by_settlement_id.get(settlement_id, [])

    def get_bank_entries_for_utr(self, utr: str) -> List[BankEntry]:
        return self.bank_entries_by_utr.get(utr, [])

    def get_settlements_for_utr(self, utr: str) -> List[Settlement]:
        return self.settlements_by_utr.get(utr, [])
