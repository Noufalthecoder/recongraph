"""
Settlement listing and drill-down investigation routes.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import (
    ExceptionSummaryItem,
    FinancialEquationComponent,
    SettlementDetailResponse,
    SettlementListItem,
    SettlementListResponse,
)

router = APIRouter(prefix="/api/settlements", tags=["settlements"])


def _val(obj: Any) -> str:
    if hasattr(obj, "value"):
        return str(obj.value)
    return str(obj)


def _fmt_money(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        if d < 0:
            return f"-₹{abs(d):,.2f}"
        return f"₹{d:,.2f}"
    except Exception:
        return str(val)


@router.get("", response_model=SettlementListResponse)
def list_settlements():
    bundle = demo_state.active_scenario
    obs = bundle.observed_world
    res = bundle.recon_result
    engine = bundle.query_engine

    items: List[SettlementListItem] = []

    for s in obs.settlements:
        inv = engine.get_settlement_investigation(s.settlement_id)
        status = inv.reconciliation_status

        # Find bank entry amount if linked
        bank_amt_str = None
        diff_str = None
        if inv.target_node:
            bk_break = inv.summary_facts.get("mathematical_breakdown", {})
            if "bank_amount" in bk_break:
                bank_amt_str = f"₹{Decimal(bk_break['bank_amount']):,.2f}"
            if "bank_delta" in bk_break:
                diff_str = f"₹{Decimal(bk_break['bank_delta']):,.2f}"

        # Count constituent transactions
        stxn_count = len(
            [st for st in obs.settlement_transactions if st.settlement_id == s.settlement_id]
        )

        items.append(
            SettlementListItem(
                settlement_id=s.settlement_id,
                utr=s.utr or "N/A",
                amount=f"₹{s.amount:,.2f}",
                currency=_val(s.currency),
                status=status,
                bank_amount=bank_amt_str,
                difference=diff_str,
                exception_count=len(inv.exceptions),
                transaction_count=stxn_count,
                created_at=s.created_at.isoformat(),
            )
        )

    return SettlementListResponse(settlements=items, total_count=len(items))


@router.get("/{settlement_id}", response_model=SettlementDetailResponse)
def get_settlement_detail(settlement_id: str):
    bundle = demo_state.active_scenario
    obs = bundle.observed_world
    engine = bundle.query_engine

    s = next((setl for setl in obs.settlements if setl.settlement_id == settlement_id), None)
    if not s:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found.")

    inv = engine.get_settlement_investigation(settlement_id)

    # Build exact observed equation components
    eq_components: List[FinancialEquationComponent] = []

    # 1. Payments Net Total
    stxns = [st for st in obs.settlement_transactions if st.settlement_id == settlement_id]
    pay_stxns = [st for st in stxns if _val(st.entity_type) == "payment"]
    pay_sum = sum((st.net_amount for st in pay_stxns), Decimal("0.00"))
    if pay_stxns:
        eq_components.append(
            FinancialEquationComponent(
                label="Payment Credits (Net)",
                type="payment",
                amount=f"₹{pay_sum:,.2f}",
                count=len(pay_stxns),
                sign="+",
            )
        )

    # 2. Refunds Net Total
    ref_stxns = [st for st in stxns if _val(st.entity_type) == "refund"]
    ref_sum = sum((st.net_amount for st in ref_stxns), Decimal("0.00"))
    if ref_stxns:
        eq_components.append(
            FinancialEquationComponent(
                label="Refund Debits (Net)",
                type="refund",
                amount=f"₹{ref_sum:,.2f}",
                count=len(ref_stxns),
                sign="-",
            )
        )

    # 3. Adjustments Net Total
    adj_stxns = [st for st in stxns if _val(st.entity_type) == "adjustment"]
    adj_sum = sum((st.net_amount for st in adj_stxns), Decimal("0.00"))
    if adj_stxns:
        eq_components.append(
            FinancialEquationComponent(
                label="Dispute / Fee Adjustments",
                type="adjustment",
                amount=f"₹{adj_sum:,.2f}",
                count=len(adj_stxns),
                sign="-" if adj_sum < 0 else "+",
            )
        )

    # 4. Settlement Header
    eq_components.append(
        FinancialEquationComponent(
            label="Calculated Payout",
            type="settlement",
            amount=f"₹{s.amount:,.2f}",
            count=1,
            sign="=",
        )
    )

    # 5. Bank Entry if present
    bank_entry_dict = None
    b_entry = next((b for b in obs.bank_entries if b.utr == s.utr), None)
    if b_entry:
        bank_entry_dict = {
            "bank_entry_id": b_entry.bank_entry_id,
            "utr": b_entry.utr,
            "amount": f"₹{b_entry.amount:,.2f}",
            "currency": _val(b_entry.currency),
            "bank_name": getattr(b_entry, "bank_name", "Primary Settlement Account"),
            "posted_at": b_entry.transaction_date.isoformat(),
        }
        eq_components.append(
            FinancialEquationComponent(
                label="Bank Credit Received",
                type="bank",
                amount=f"₹{b_entry.amount:,.2f}",
                count=1,
                sign="=",
            )
        )

    # Format exceptions
    exceptions_list: List[ExceptionSummaryItem] = []
    for exc in inv.exceptions:
        if isinstance(exc, dict):
            exp_v = exc.get("expected_value")
            obs_v = exc.get("observed_value")
            diff_v = exc.get("difference")
            rule_code = exc.get("rule_code", "UNKNOWN")
            sev_str = exc.get("severity", "ERROR")
            exc_id = exc.get("exception_id", "exc_000")
            desc = exc.get("details", {}).get("description") or exc.get("description") or rule_code
            ent_parts = str(exc.get("primary_entity", "")).split(":")
            ent_type = ent_parts[0] if len(ent_parts) > 1 else "settlement"
            ent_id = ent_parts[1] if len(ent_parts) > 1 else settlement_id
        else:
            exp_v = getattr(exc, "expected_value", None)
            obs_v = getattr(exc, "observed_value", None)
            diff_v = getattr(exc, "difference", None)
            rule_code = getattr(exc, "rule_code", "UNKNOWN")
            sev = getattr(exc, "severity", "ERROR")
            sev_str = sev.value if hasattr(sev, "value") else str(sev)
            exc_id = getattr(exc, "exception_id", "exc_000")
            desc = exc.evidence.rule_description if hasattr(exc, "evidence") and exc.evidence else rule_code
            ent_type = exc.primary_entity.entity_type if hasattr(exc, "primary_entity") else "settlement"
            ent_id = exc.primary_entity.entity_id if hasattr(exc, "primary_entity") else settlement_id

        exp_str = _fmt_money(exp_v)
        obs_str = _fmt_money(obs_v)
        diff_str = _fmt_money(diff_v)

        exceptions_list.append(
            ExceptionSummaryItem(
                exception_id=exc_id,
                rule_code=rule_code,
                severity=sev_str,
                entity_type=ent_type,
                entity_id=ent_id,
                settlement_id=settlement_id,
                expected_value=exp_str,
                observed_value=obs_str,
                difference=diff_str,
                description=desc,
            )
        )

    # Extract payments, refunds, adjustments dictionaries
    pay_ids = {st.entity_id for st in pay_stxns}
    payments_data = [
        {
            "payment_id": p.payment_id,
            "order_id": p.order_id,
            "amount": f"₹{p.amount:,.2f}",
            "fee": f"₹{p.fee:,.2f}",
            "tax": f"₹{p.tax:,.2f}",
            "net": f"₹{(p.amount - p.fee - p.tax):,.2f}",
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "method": p.method.value if hasattr(p.method, "value") else str(p.method),
            "created_at": p.created_at.isoformat(),
        }
        for p in obs.payments
        if p.payment_id in pay_ids
    ]

    ref_ids = {st.entity_id for st in ref_stxns}
    refunds_data = [
        {
            "refund_id": r.refund_id,
            "payment_id": r.payment_id,
            "amount": f"₹{r.amount:,.2f}",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "reason": getattr(r, "reason", "Customer Requested Reversal") or "Customer Requested Reversal",
            "created_at": r.created_at.isoformat(),
        }
        for r in obs.refunds
        if r.refund_id in ref_ids
    ]

    adj_ids = {st.entity_id for st in adj_stxns}
    adjustments_data = [
        {
            "adjustment_id": a.adjustment_id,
            "amount": f"₹{a.amount:,.2f}",
            "reason": str(a.reason),
            "description": a.description or str(a.reason),
            "created_at": a.created_at.isoformat(),
        }
        for a in obs.adjustments
        if a.adjustment_id in adj_ids
    ]

    stxns_data = [
        {
            "settlement_txn_id": st.settlement_txn_id,
            "entity_type": st.entity_type.value if hasattr(st.entity_type, "value") else str(st.entity_type),
            "entity_id": st.entity_id,
            "amount": f"₹{st.amount:,.2f}",
            "fee": f"₹{st.fee:,.2f}",
            "tax": f"₹{st.tax:,.2f}",
            "net_amount": f"₹{st.net_amount:,.2f}",
            "type": st.type.value if hasattr(st.type, "value") else str(st.type),
        }
        for st in stxns
    ]

    return SettlementDetailResponse(
        settlement_id=s.settlement_id,
        merchant_id=s.merchant_id,
        utr=s.utr or "N/A",
        amount=f"₹{s.amount:,.2f}",
        fees=f"₹{s.fees:,.2f}",
        tax=f"₹{s.tax:,.2f}",
        currency=s.currency.value if hasattr(s.currency, "value") else str(s.currency),
        status=inv.reconciliation_status,
        created_at=s.created_at.isoformat(),
        bank_entry=bank_entry_dict,
        equation_components=eq_components,
        exceptions=exceptions_list,
        evidence=[e.model_dump() for e in inv.evidence],
        constituent_transactions=stxns_data,
        payments=payments_data,
        refunds=refunds_data,
        adjustments=adjustments_data,
    )
