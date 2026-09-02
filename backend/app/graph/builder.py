"""
Deterministic builder constructing FinancialGraph and GraphEvidenceLayer from ObservedWorld.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.graph.evidence import GraphEvidenceLayer
from backend.app.graph.models import FinancialGraph, GraphEdge, GraphNode
from backend.app.reconciliation.models import ReconciliationResult
from simulator.observed.models import ObservedWorld


def _val(x: Any) -> str:
    if hasattr(x, "value"):
        return str(x.value)
    return str(x)


class FinancialGraphBuilder:
    """
    Constructs an immutable, fully-indexed FinancialGraph and attached GraphEvidenceLayer
    from ObservedWorld and optional ReconciliationResult.
    """

    @classmethod
    def build(
        cls,
        observed_world: ObservedWorld,
        reconciliation_result: Optional[ReconciliationResult] = None,
    ) -> Tuple[FinancialGraph, GraphEvidenceLayer]:
        nodes_dict: Dict[str, GraphNode] = {}
        edges_set: Set[Tuple[str, str, str]] = set()
        edges_list: List[GraphEdge] = []

        # ---------------------------------------------------------------------
        # 1. Construct Nodes
        # ---------------------------------------------------------------------
        # Merchants
        for m in observed_world.merchants:
            node_id = f"merchant:{m.merchant_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="merchant",
                entity_id=m.merchant_id,
                display_label=f"Merchant: {m.name}",
                attributes={
                    "name": m.name,
                    "status": _val(m.status),
                    "created_at": m.created_at.isoformat(),
                },
            )

        # Orders
        for o in observed_world.orders:
            node_id = f"order:{o.order_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="order",
                entity_id=o.order_id,
                display_label=f"Order: {o.order_id} ({_val(o.currency)} {o.amount})",
                attributes={
                    "merchant_id": o.merchant_id,
                    "amount": str(o.amount),
                    "currency": _val(o.currency),
                    "status": _val(o.status),
                    "created_at": o.created_at.isoformat(),
                },
            )

        # Payments
        for p in observed_world.payments:
            node_id = f"payment:{p.payment_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="payment",
                entity_id=p.payment_id,
                display_label=f"Payment: {p.payment_id} ({_val(p.currency)} {p.amount})",
                attributes={
                    "order_id": p.order_id,
                    "merchant_id": p.merchant_id,
                    "amount": str(p.amount),
                    "currency": _val(p.currency),
                    "status": _val(p.status),
                    "method": _val(p.method),
                    "fee": str(p.fee),
                    "tax": str(p.tax),
                    "settlement_id": p.settlement_id,
                    "created_at": p.created_at.isoformat(),
                },
            )

        # Refunds
        for r in getattr(observed_world, "refunds", []):
            node_id = f"refund:{r.refund_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="refund",
                entity_id=r.refund_id,
                display_label=f"Refund: {r.refund_id} ({_val(r.currency)} {r.amount})",
                attributes={
                    "payment_id": r.payment_id,
                    "merchant_id": r.merchant_id,
                    "amount": str(r.amount),
                    "currency": _val(r.currency),
                    "status": _val(r.status),
                    "speed": _val(r.speed),
                    "settlement_id": r.settlement_id,
                    "created_at": r.created_at.isoformat(),
                },
            )

        # Adjustments
        for a in getattr(observed_world, "adjustments", []):
            node_id = f"adjustment:{a.adjustment_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="adjustment",
                entity_id=a.adjustment_id,
                display_label=f"Adjustment: {a.adjustment_id} ({_val(a.currency)} {a.amount})",
                attributes={
                    "merchant_id": a.merchant_id,
                    "amount": str(a.amount),
                    "currency": _val(a.currency),
                    "reason": _val(a.reason),
                    "settlement_id": a.settlement_id,
                    "description": a.description,
                    "created_at": a.created_at.isoformat(),
                },
            )

        # Transfers
        for t in getattr(observed_world, "transfers", []):
            node_id = f"transfer:{t.transfer_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="transfer",
                entity_id=t.transfer_id,
                display_label=f"Transfer: {t.transfer_id} ({_val(t.currency)} {t.amount})",
                attributes={
                    "payment_id": t.payment_id,
                    "source_merchant_id": t.source_merchant_id,
                    "recipient_merchant_id": t.recipient_merchant_id,
                    "amount": str(t.amount),
                    "currency": _val(t.currency),
                    "status": _val(t.status),
                    "settlement_id": t.settlement_id,
                    "created_at": t.created_at.isoformat(),
                },
            )

        # SettlementTransactions
        for st in observed_world.settlement_transactions:
            node_id = f"settlement_transaction:{st.settlement_txn_id}"
            st_type = _val(st.type)
            st_entity_type = _val(st.entity_type)
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="settlement_transaction",
                entity_id=st.settlement_txn_id,
                display_label=f"STXN: {st.settlement_txn_id} ({st_type} net {st.net_amount})",
                attributes={
                    "settlement_id": st.settlement_id,
                    "merchant_id": st.merchant_id,
                    "entity_type": st_entity_type,
                    "entity_id": st.entity_id,
                    "amount": str(st.amount),
                    "fee": str(st.fee),
                    "tax": str(st.tax),
                    "net_amount": str(st.net_amount),
                    "type": st_type,
                    "created_at": st.created_at.isoformat(),
                },
            )

        # Settlements
        for s in observed_world.settlements:
            node_id = f"settlement:{s.settlement_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="settlement",
                entity_id=s.settlement_id,
                display_label=f"Settlement: {s.settlement_id} ({_val(s.currency)} {s.amount})",
                attributes={
                    "merchant_id": s.merchant_id,
                    "amount": str(s.amount),
                    "currency": _val(s.currency),
                    "status": _val(s.status),
                    "fees": str(s.fees),
                    "tax": str(s.tax),
                    "utr": s.utr,
                    "created_at": s.created_at.isoformat(),
                },
            )

        # BankEntries
        for b in observed_world.bank_entries:
            node_id = f"bank_entry:{b.bank_entry_id}"
            nodes_dict[node_id] = GraphNode(
                node_id=node_id,
                entity_type="bank_entry",
                entity_id=b.bank_entry_id,
                display_label=f"BankEntry: {b.bank_entry_id} ({_val(b.currency)} {b.amount})",
                attributes={
                    "merchant_id": b.merchant_id,
                    "account_number": b.account_number,
                    "amount": str(b.amount),
                    "currency": _val(b.currency),
                    "utr": b.utr,
                    "transaction_date": b.transaction_date.isoformat(),
                },
            )

        # ---------------------------------------------------------------------
        # 2. Construct Edges
        # ---------------------------------------------------------------------
        def add_edge(src: str, tgt: str, rel: str, attrs: Optional[Dict[str, str]] = None) -> None:
            if (src, tgt, rel) not in edges_set and src in nodes_dict and tgt in nodes_dict:
                edges_set.add((src, tgt, rel))
                edge_id = f"edge:{src}->{tgt}:{rel}"
                edges_list.append(
                    GraphEdge(
                        edge_id=edge_id,
                        source_node_id=src,
                        target_node_id=tgt,
                        relationship_type=rel,
                        directed=True,
                        attributes=attrs or {},
                    )
                )

        # Merchant -> Order
        for o in observed_world.orders:
            add_edge(f"merchant:{o.merchant_id}", f"order:{o.order_id}", "OWNS_ORDER")

        # Order -> Payment
        for p in observed_world.payments:
            add_edge(f"order:{p.order_id}", f"payment:{p.payment_id}", "HAS_PAYMENT")

        # Payment -> Refund
        for r in getattr(observed_world, "refunds", []):
            add_edge(f"payment:{r.payment_id}", f"refund:{r.refund_id}", "HAS_REFUND")

        # Payment -> Transfer
        for t in getattr(observed_world, "transfers", []):
            add_edge(f"payment:{t.payment_id}", f"transfer:{t.transfer_id}", "HAS_TRANSFER")

        # Constituent Entity -> SettlementTransaction
        for st in observed_world.settlement_transactions:
            st_etype = st.entity_type.value if hasattr(st.entity_type, "value") else str(st.entity_type)
            st_node_id = f"settlement_transaction:{st.settlement_txn_id}"

            if st_etype == "payment":
                add_edge(f"payment:{st.entity_id}", st_node_id, "SETTLED_AS")
            elif st_etype == "refund":
                add_edge(f"refund:{st.entity_id}", st_node_id, "SETTLED_AS")
            elif st_etype == "adjustment":
                add_edge(f"adjustment:{st.entity_id}", st_node_id, "SETTLED_AS")
            elif st_etype == "transfer":
                add_edge(f"transfer:{st.entity_id}", st_node_id, "SETTLED_AS")

            # SettlementTransaction -> Settlement
            add_edge(st_node_id, f"settlement:{st.settlement_id}", "BELONGS_TO_SETTLEMENT")

        # Adjustment -> Settlement (Direct relationship if settlement_id present)
        for a in getattr(observed_world, "adjustments", []):
            if a.settlement_id:
                add_edge(f"adjustment:{a.adjustment_id}", f"settlement:{a.settlement_id}", "AFFECTS_SETTLEMENT")

        # Settlement -> BankEntry
        # Multi-strategy linking: by exact UTR matching or reconciliation matches
        bank_by_utr: Dict[str, str] = {b.utr: b.bank_entry_id for b in observed_world.bank_entries if b.utr}
        for s in observed_world.settlements:
            s_node_id = f"settlement:{s.settlement_id}"
            if s.utr and s.utr in bank_by_utr:
                add_edge(s_node_id, f"bank_entry:{bank_by_utr[s.utr]}", "SETTLED_TO_BANK", {"utr": s.utr})

        # If ReconciliationResult provided additional settlement-bank pairings:
        if reconciliation_result:
            for s_res in reconciliation_result.settlements:
                if s_res.bank_entry_id:
                    add_edge(
                        f"settlement:{s_res.settlement_id}",
                        f"bank_entry:{s_res.bank_entry_id}",
                        "SETTLED_TO_BANK",
                        {"status": s_res.status},
                    )

        # Sort nodes and edges deterministically
        sorted_nodes = sorted(nodes_dict.values(), key=lambda n: (n.entity_type, n.entity_id, n.node_id))
        sorted_edges = sorted(edges_list, key=lambda e: (e.source_node_id, e.target_node_id, e.relationship_type, e.edge_id))

        graph = FinancialGraph(nodes=sorted_nodes, edges=sorted_edges)
        evidence_layer = GraphEvidenceLayer(reconciliation_result)

        return graph, evidence_layer
