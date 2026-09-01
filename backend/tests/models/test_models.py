"""
Tests for ReconGraph financial domain models.

Validates that all models conform to docs/data-contracts.md:
- Correct field presence (required vs optional)
- Monetary values use Decimal, never float
- Enum fields enforce allowed values
- Serialization round-trips correctly
- Every entity can be instantiated from valid contract-compliant data
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from backend.app.models import (
    Merchant,
    MerchantStatus,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Refund,
    RefundSpeed,
    RefundStatus,
    Transfer,
    TransferStatus,
    Adjustment,
    SettlementTransaction,
    SettlementTransactionEntityType,
    SettlementTransactionType,
    Settlement,
    SettlementStatus,
    BankEntry,
    Currency,
)

# ---------------------------------------------------------------------------
# Fixtures — canonical valid data for each entity
# ---------------------------------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=IST)


@pytest.fixture
def valid_merchant_data() -> dict:
    return {
        "merchant_id": "merch_ABC123",
        "name": "Test Merchant Pvt Ltd",
        "status": "active",
        "created_at": NOW,
    }


@pytest.fixture
def valid_order_data() -> dict:
    return {
        "order_id": "order_XYZ789",
        "merchant_id": "merch_ABC123",
        "amount": Decimal("1500.00"),
        "currency": "INR",
        "status": "created",
        "created_at": NOW,
    }


@pytest.fixture
def valid_payment_data() -> dict:
    return {
        "payment_id": "pay_DEF456",
        "order_id": "order_XYZ789",
        "merchant_id": "merch_ABC123",
        "amount": Decimal("1500.00"),
        "currency": "INR",
        "status": "captured",
        "method": "upi",
        "created_at": NOW,
    }


@pytest.fixture
def valid_refund_data() -> dict:
    return {
        "refund_id": "rfnd_GHI012",
        "payment_id": "pay_DEF456",
        "merchant_id": "merch_ABC123",
        "amount": Decimal("500.00"),
        "currency": "INR",
        "status": "processed",
        "created_at": NOW,
    }


@pytest.fixture
def valid_transfer_data() -> dict:
    return {
        "transfer_id": "trf_JKL345",
        "payment_id": "pay_DEF456",
        "source_merchant_id": "merch_ABC123",
        "recipient_merchant_id": "merch_DEF456",
        "amount": Decimal("700.00"),
        "currency": "INR",
        "status": "processed",
        "created_at": NOW,
    }


@pytest.fixture
def valid_adjustment_data() -> dict:
    return {
        "adjustment_id": "adj_MNO678",
        "merchant_id": "merch_ABC123",
        "amount": Decimal("-5000.00"),
        "currency": "INR",
        "reason": "chargeback",
        "created_at": NOW,
    }


@pytest.fixture
def valid_settlement_txn_data() -> dict:
    return {
        "settlement_txn_id": "stxn_PQR901",
        "settlement_id": "setl_STU234",
        "merchant_id": "merch_ABC123",
        "entity_type": "payment",
        "entity_id": "pay_DEF456",
        "amount": Decimal("1500.00"),
        "fee": Decimal("30.00"),
        "tax": Decimal("5.40"),
        "net_amount": Decimal("1464.60"),
        "type": "credit",
        "created_at": NOW,
    }


@pytest.fixture
def valid_settlement_data() -> dict:
    return {
        "settlement_id": "setl_STU234",
        "merchant_id": "merch_ABC123",
        "amount": Decimal("14646.00"),
        "currency": "INR",
        "status": "processed",
        "fees": Decimal("300.00"),
        "tax": Decimal("54.00"),
        "created_at": NOW,
        "utr": "UTR1234567890",
        "settled_at": NOW,
    }


@pytest.fixture
def valid_bank_entry_data() -> dict:
    return {
        "bank_entry_id": "bnk_VWX567",
        "merchant_id": "merch_ABC123",
        "account_number": "1234567890",
        "amount": Decimal("14646.00"),
        "currency": "INR",
        "utr": "UTR1234567890",
        "transaction_date": NOW,
    }


# ===================================================================
# 1. Valid Payment can be created
# ===================================================================

class TestPaymentCreation:
    def test_valid_payment(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        assert payment.payment_id == "pay_DEF456"
        assert payment.amount == Decimal("1500.00")
        assert payment.status == PaymentStatus.CAPTURED

    def test_payment_with_optional_fields(self, valid_payment_data):
        valid_payment_data["fee"] = Decimal("30.00")
        valid_payment_data["tax"] = Decimal("5.40")
        valid_payment_data["settlement_id"] = "setl_STU234"
        valid_payment_data["captured_at"] = NOW
        valid_payment_data["notes"] = {"order_ref": "ORD-001"}
        payment = Payment(**valid_payment_data)
        assert payment.fee == Decimal("30.00")
        assert payment.tax == Decimal("5.40")
        assert payment.settlement_id == "setl_STU234"
        assert payment.notes == {"order_ref": "ORD-001"}


# ===================================================================
# 2. Valid Settlement can be created
# ===================================================================

class TestSettlementCreation:
    def test_valid_settlement(self, valid_settlement_data):
        settlement = Settlement(**valid_settlement_data)
        assert settlement.settlement_id == "setl_STU234"
        assert settlement.amount == Decimal("14646.00")
        assert settlement.fees == Decimal("300.00")
        assert settlement.tax == Decimal("54.00")
        assert settlement.utr == "UTR1234567890"

    def test_settlement_without_optional_fields(self):
        settlement = Settlement(
            settlement_id="setl_MIN",
            merchant_id="merch_ABC123",
            amount=Decimal("1000.00"),
            currency="INR",
            status="created",
            fees=Decimal("20.00"),
            tax=Decimal("3.60"),
            created_at=NOW,
        )
        assert settlement.utr is None
        assert settlement.settled_at is None


# ===================================================================
# 3. Valid BankEntry can be created
# ===================================================================

class TestBankEntryCreation:
    def test_valid_bank_entry(self, valid_bank_entry_data):
        entry = BankEntry(**valid_bank_entry_data)
        assert entry.bank_entry_id == "bnk_VWX567"
        assert entry.utr == "UTR1234567890"
        assert entry.amount == Decimal("14646.00")

    def test_bank_entry_with_optional_fields(self, valid_bank_entry_data):
        valid_bank_entry_data["description"] = "NEFT CR from Razorpay"
        valid_bank_entry_data["value_date"] = NOW
        valid_bank_entry_data["balance"] = Decimal("150000.00")
        entry = BankEntry(**valid_bank_entry_data)
        assert entry.description == "NEFT CR from Razorpay"
        assert entry.balance == Decimal("150000.00")


# ===================================================================
# 4. Monetary values are Decimal
# ===================================================================

class TestMonetaryDecimal:
    def test_payment_amount_is_decimal(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        assert isinstance(payment.amount, Decimal)

    def test_settlement_amounts_are_decimal(self, valid_settlement_data):
        settlement = Settlement(**valid_settlement_data)
        assert isinstance(settlement.amount, Decimal)
        assert isinstance(settlement.fees, Decimal)
        assert isinstance(settlement.tax, Decimal)

    def test_bank_entry_amount_is_decimal(self, valid_bank_entry_data):
        entry = BankEntry(**valid_bank_entry_data)
        assert isinstance(entry.amount, Decimal)

    def test_settlement_txn_amounts_are_decimal(self, valid_settlement_txn_data):
        txn = SettlementTransaction(**valid_settlement_txn_data)
        assert isinstance(txn.amount, Decimal)
        assert isinstance(txn.fee, Decimal)
        assert isinstance(txn.tax, Decimal)
        assert isinstance(txn.net_amount, Decimal)

    def test_amount_from_string(self, valid_payment_data):
        """Decimal can be constructed from a string representation."""
        valid_payment_data["amount"] = "2500.50"
        payment = Payment(**valid_payment_data)
        assert payment.amount == Decimal("2500.50")
        assert isinstance(payment.amount, Decimal)

    def test_amount_from_int(self, valid_payment_data):
        """Decimal can be constructed from an integer."""
        valid_payment_data["amount"] = 3000
        payment = Payment(**valid_payment_data)
        assert payment.amount == Decimal("3000")
        assert isinstance(payment.amount, Decimal)


# ===================================================================
# 5. Invalid monetary input is rejected
# ===================================================================

class TestInvalidMonetaryInput:
    def test_float_amount_rejected(self, valid_payment_data):
        """Float values MUST be rejected to prevent precision loss."""
        valid_payment_data["amount"] = 1500.00
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_invalid_string_amount_rejected(self, valid_payment_data):
        """Non-numeric strings must be rejected."""
        valid_payment_data["amount"] = "not_a_number"
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_float_fee_rejected(self, valid_payment_data):
        """Float values for optional monetary fields are also rejected."""
        valid_payment_data["fee"] = 30.0
        with pytest.raises(Exception):
            Payment(**valid_payment_data)


# ===================================================================
# 6. Required fields are enforced
# ===================================================================

class TestRequiredFields:
    def test_payment_missing_payment_id(self, valid_payment_data):
        del valid_payment_data["payment_id"]
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_payment_missing_amount(self, valid_payment_data):
        del valid_payment_data["amount"]
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_settlement_missing_settlement_id(self, valid_settlement_data):
        del valid_settlement_data["settlement_id"]
        with pytest.raises(Exception):
            Settlement(**valid_settlement_data)

    def test_bank_entry_missing_utr(self, valid_bank_entry_data):
        del valid_bank_entry_data["utr"]
        with pytest.raises(Exception):
            BankEntry(**valid_bank_entry_data)

    def test_merchant_missing_name(self, valid_merchant_data):
        del valid_merchant_data["name"]
        with pytest.raises(Exception):
            Merchant(**valid_merchant_data)

    def test_order_missing_currency(self, valid_order_data):
        del valid_order_data["currency"]
        with pytest.raises(Exception):
            Order(**valid_order_data)

    def test_settlement_txn_missing_entity_type(self, valid_settlement_txn_data):
        del valid_settlement_txn_data["entity_type"]
        with pytest.raises(Exception):
            SettlementTransaction(**valid_settlement_txn_data)


# ===================================================================
# 7. Optional fields can be absent
# ===================================================================

class TestOptionalFields:
    def test_payment_optional_fields_default_none(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        assert payment.fee is None
        assert payment.tax is None
        assert payment.settlement_id is None
        assert payment.captured_at is None
        assert payment.notes is None

    def test_merchant_optional_fields_default_none(self, valid_merchant_data):
        merchant = Merchant(**valid_merchant_data)
        assert merchant.mcc is None
        assert merchant.settlement_schedule is None
        assert merchant.fee_plan_id is None

    def test_refund_optional_fields_default_none(self, valid_refund_data):
        refund = Refund(**valid_refund_data)
        assert refund.speed is None
        assert refund.settlement_id is None
        assert refund.processed_at is None
        assert refund.notes is None

    def test_settlement_optional_fields_default_none(self):
        settlement = Settlement(
            settlement_id="setl_OPT",
            merchant_id="merch_ABC123",
            amount=Decimal("1000.00"),
            currency="INR",
            status="created",
            fees=Decimal("0"),
            tax=Decimal("0"),
            created_at=NOW,
        )
        assert settlement.utr is None
        assert settlement.settled_at is None


# ===================================================================
# 8. Model serialization works
# ===================================================================

class TestSerialization:
    def test_payment_to_dict(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        data = payment.model_dump()
        assert data["payment_id"] == "pay_DEF456"
        assert data["amount"] == Decimal("1500.00")
        assert data["currency"] == "INR"
        assert data["status"] == "captured"
        assert data["method"] == "upi"

    def test_settlement_to_json_and_back(self, valid_settlement_data):
        settlement = Settlement(**valid_settlement_data)
        json_str = settlement.model_dump_json()
        assert "14646.00" in json_str or "14646" in json_str
        restored = Settlement.model_validate_json(json_str)
        assert restored.amount == settlement.amount
        assert restored.settlement_id == settlement.settlement_id

    def test_bank_entry_round_trip(self, valid_bank_entry_data):
        entry = BankEntry(**valid_bank_entry_data)
        data = entry.model_dump()
        entry2 = BankEntry(**data)
        assert entry2.amount == entry.amount
        assert entry2.utr == entry.utr


# ===================================================================
# 9. Models do not silently convert to binary float
# ===================================================================

class TestNoFloatConversion:
    def test_payment_dump_preserves_decimal(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        data = payment.model_dump()
        assert isinstance(data["amount"], Decimal), (
            f"model_dump() converted amount to {type(data['amount']).__name__}"
        )

    def test_settlement_dump_preserves_decimal(self, valid_settlement_data):
        settlement = Settlement(**valid_settlement_data)
        data = settlement.model_dump()
        assert isinstance(data["amount"], Decimal)
        assert isinstance(data["fees"], Decimal)
        assert isinstance(data["tax"], Decimal)

    def test_settlement_txn_dump_preserves_decimal(self, valid_settlement_txn_data):
        txn = SettlementTransaction(**valid_settlement_txn_data)
        data = txn.model_dump()
        for field in ("amount", "fee", "tax", "net_amount"):
            assert isinstance(data[field], Decimal), (
                f"{field} was converted to {type(data[field]).__name__}"
            )


# ===================================================================
# 10. Every entity can be instantiated from valid contract data
# ===================================================================

class TestAllEntitiesInstantiation:
    def test_merchant(self, valid_merchant_data):
        m = Merchant(**valid_merchant_data)
        assert m.merchant_id == "merch_ABC123"

    def test_order(self, valid_order_data):
        o = Order(**valid_order_data)
        assert o.order_id == "order_XYZ789"

    def test_payment(self, valid_payment_data):
        p = Payment(**valid_payment_data)
        assert p.payment_id == "pay_DEF456"

    def test_refund(self, valid_refund_data):
        r = Refund(**valid_refund_data)
        assert r.refund_id == "rfnd_GHI012"

    def test_transfer(self, valid_transfer_data):
        t = Transfer(**valid_transfer_data)
        assert t.transfer_id == "trf_JKL345"

    def test_adjustment(self, valid_adjustment_data):
        a = Adjustment(**valid_adjustment_data)
        assert a.adjustment_id == "adj_MNO678"
        assert a.amount == Decimal("-5000.00")  # negative is valid

    def test_settlement_transaction(self, valid_settlement_txn_data):
        st = SettlementTransaction(**valid_settlement_txn_data)
        assert st.settlement_txn_id == "stxn_PQR901"

    def test_settlement(self, valid_settlement_data):
        s = Settlement(**valid_settlement_data)
        assert s.settlement_id == "setl_STU234"

    def test_bank_entry(self, valid_bank_entry_data):
        b = BankEntry(**valid_bank_entry_data)
        assert b.bank_entry_id == "bnk_VWX567"


# ===================================================================
# Additional: Enum validation
# ===================================================================

class TestEnumValidation:
    def test_invalid_payment_status(self, valid_payment_data):
        valid_payment_data["status"] = "invalid_status"
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_invalid_payment_method(self, valid_payment_data):
        valid_payment_data["method"] = "bitcoin"
        with pytest.raises(Exception):
            Payment(**valid_payment_data)

    def test_invalid_settlement_status(self, valid_settlement_data):
        valid_settlement_data["status"] = "pending"
        with pytest.raises(Exception):
            Settlement(**valid_settlement_data)

    def test_invalid_currency(self, valid_order_data):
        valid_order_data["currency"] = "USD"
        with pytest.raises(Exception):
            Order(**valid_order_data)

    def test_invalid_settlement_txn_entity_type(self, valid_settlement_txn_data):
        valid_settlement_txn_data["entity_type"] = "invoice"
        with pytest.raises(Exception):
            SettlementTransaction(**valid_settlement_txn_data)

    def test_invalid_settlement_txn_type(self, valid_settlement_txn_data):
        valid_settlement_txn_data["type"] = "reversal"
        with pytest.raises(Exception):
            SettlementTransaction(**valid_settlement_txn_data)


# ===================================================================
# Additional: Frozen model immutability
# ===================================================================

class TestImmutability:
    def test_payment_is_frozen(self, valid_payment_data):
        payment = Payment(**valid_payment_data)
        with pytest.raises(Exception):
            payment.amount = Decimal("9999.00")  # type: ignore[misc]

    def test_settlement_is_frozen(self, valid_settlement_data):
        settlement = Settlement(**valid_settlement_data)
        with pytest.raises(Exception):
            settlement.utr = "NEW_UTR"  # type: ignore[misc]
