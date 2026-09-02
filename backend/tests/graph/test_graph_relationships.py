"""
Tests for domain relationships, many-to-one settlements, refunds, and adjustments.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.graph import FinancialGraphBuilder, GraphIndex
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_many_to_one_settlement_relationships():
    """Verify many-to-one scenario preserves 5 distinct payments and 5 STXNs converging into 1 settlement."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=5,
        scenario_type="many_to_one_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    # 1 merchant + 5 orders + 5 payments + 5 stxns + 1 settlement + 1 bank = 18 nodes
    assert graph.node_count == 18
    assert len(index.nodes_by_type["payment"]) == 5
    assert len(index.nodes_by_type["settlement_transaction"]) == 5
    assert len(index.nodes_by_type["settlement"]) == 1

    # Verify each payment has an outgoing SETTLED_AS edge to its respective STXN
    for p_node in index.nodes_by_type["payment"]:
        out_edges = index.get_outgoing_edges(p_node.node_id)
        assert any(e.relationship_type == "SETTLED_AS" for e in out_edges)

    # Verify all 5 STXNs have incoming edges to the single settlement
    setl_node = index.nodes_by_type["settlement"][0]
    in_edges = index.get_incoming_edges(setl_node.node_id)
    assert len(in_edges) == 5
    assert all(e.relationship_type == "BELONGS_TO_SETTLEMENT" for e in in_edges)


def test_multiple_refunds_relationships():
    """Verify multiple refunds are linked as separate child nodes from their parent payment."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=4,
        scenario_type="multiple_refunds_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    refund_nodes = index.nodes_by_type["refund"]
    assert len(refund_nodes) == 3

    for r_node in refund_nodes:
        # Each refund has incoming HAS_REFUND from payment and outgoing SETTLED_AS to STXN
        in_edges = index.get_incoming_edges(r_node.node_id)
        out_edges = index.get_outgoing_edges(r_node.node_id)
        assert any(e.relationship_type == "HAS_REFUND" for e in in_edges)
        assert any(e.relationship_type == "SETTLED_AS" for e in out_edges)


def test_adjustment_relationships():
    """Verify adjustment is linked to STXN and settlement."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=2,
        scenario_type="adjustment_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    graph, _ = FinancialGraphBuilder.build(obs_world)
    index = GraphIndex(graph)

    adj_nodes = index.nodes_by_type["adjustment"]
    assert len(adj_nodes) == 1
    adj_node = adj_nodes[0]

    out_edges = index.get_outgoing_edges(adj_node.node_id)
    assert any(e.relationship_type == "SETTLED_AS" for e in out_edges)


def test_transfer_relationships():
    """Verify transfer domain relationships are properly constructed when present."""
    from datetime import datetime, timezone
    from backend.app.models.common import Currency
    from backend.app.models.merchant import Merchant, MerchantStatus
    from backend.app.models.order import Order, OrderStatus
    from backend.app.models.payment import Payment, PaymentMethod, PaymentStatus
    from backend.app.models.settlement import Settlement, SettlementStatus
    from backend.app.models.settlement_transaction import (
        SettlementTransaction,
        SettlementTransactionEntityType,
        SettlementTransactionType,
    )
    from backend.app.models.transfer import Transfer, TransferStatus
    from simulator.observed.models import ObservedWorld

    t_base = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    m1 = Merchant(merchant_id="merch_1", name="Merchant 1", status=MerchantStatus.ACTIVE, created_at=t_base)
    m2 = Merchant(merchant_id="merch_2", name="Merchant 2", status=MerchantStatus.ACTIVE, created_at=t_base)
    o1 = Order(order_id="ord_1", merchant_id="merch_1", amount=Decimal("1000.00"), currency=Currency.INR, status=OrderStatus.PAID, created_at=t_base)
    p1 = Payment(payment_id="pay_1", order_id="ord_1", merchant_id="merch_1", amount=Decimal("1000.00"), currency=Currency.INR, status=PaymentStatus.CAPTURED, method=PaymentMethod.UPI, fee=Decimal("20.00"), tax=Decimal("3.60"), created_at=t_base)
    tr1 = Transfer(transfer_id="trf_1", payment_id="pay_1", source_merchant_id="merch_1", recipient_merchant_id="merch_2", amount=Decimal("500.00"), currency=Currency.INR, status=TransferStatus.PROCESSED, created_at=t_base)
    st1 = SettlementTransaction(settlement_txn_id="stxn_1", settlement_id="setl_1", merchant_id="merch_1", entity_type=SettlementTransactionEntityType.TRANSFER, entity_id="trf_1", amount=Decimal("500.00"), fee=Decimal("0.00"), tax=Decimal("0.00"), net_amount=Decimal("-500.00"), type=SettlementTransactionType.DEBIT, created_at=t_base)
    s1 = Settlement(settlement_id="setl_1", merchant_id="merch_1", amount=Decimal("476.40"), currency=Currency.INR, status=SettlementStatus.PROCESSED, fees=Decimal("20.00"), tax=Decimal("3.60"), utr="MOCKUTR123", created_at=t_base)

    obs = ObservedWorld(
        merchants=[m1, m2],
        orders=[o1],
        payments=[p1],
        transfers=[tr1],
        settlement_transactions=[st1],
        settlements=[s1],
        bank_entries=[],
    )

    graph, _ = FinancialGraphBuilder.build(obs)
    index = GraphIndex(graph)

    trf_node = index.get_node("transfer:trf_1")
    assert trf_node is not None

    # Payment -> Transfer edge
    p_edges = index.get_outgoing_edges("payment:pay_1")
    assert any(e.relationship_type == "HAS_TRANSFER" and e.target_node_id == "transfer:trf_1" for e in p_edges)

    # Transfer -> STXN edge
    t_edges = index.get_outgoing_edges("transfer:trf_1")
    assert any(e.relationship_type == "SETTLED_AS" and e.target_node_id == "settlement_transaction:stxn_1" for e in t_edges)

