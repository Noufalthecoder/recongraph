"""
Observation Generator and Anomaly Injection Engine for ReconGraph.

Transforms authoritative GroundTruth into ObservedWorld and AnomalyManifest
without mutating GroundTruth.
"""

import random
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from simulator.ground_truth.models import GroundTruth
from simulator.observed.config import AnomalySpec, ObservationConfig
from simulator.observed.models import (
    AnomalyManifest,
    AnomalyRecord,
    AnomalyType,
    ObservedWorld,
)


ENTITY_TYPE_MAP = {
    "merchant": ("merchants", "merchant_id"),
    "merchants": ("merchants", "merchant_id"),
    "order": ("orders", "order_id"),
    "orders": ("orders", "order_id"),
    "payment": ("payments", "payment_id"),
    "payments": ("payments", "payment_id"),
    "refund": ("refunds", "refund_id"),
    "refunds": ("refunds", "refund_id"),
    "adjustment": ("adjustments", "adjustment_id"),
    "adjustments": ("adjustments", "adjustment_id"),
    "transfer": ("transfers", "transfer_id"),
    "transfers": ("transfers", "transfer_id"),
    "settlement_transaction": ("settlement_transactions", "settlement_txn_id"),
    "settlement_transactions": ("settlement_transactions", "settlement_txn_id"),
    "stxn": ("settlement_transactions", "settlement_txn_id"),
    "stxns": ("settlement_transactions", "settlement_txn_id"),
    "settlement": ("settlements", "settlement_id"),
    "settlements": ("settlements", "settlement_id"),
    "bank_entry": ("bank_entries", "bank_entry_id"),
    "bank_entries": ("bank_entries", "bank_entry_id"),
    "bank": ("bank_entries", "bank_entry_id"),
}


class AnomalyInjector:
    """
    Applies deterministic controlled corruptions to working entity collections.
    """

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def inject(
        self,
        entity_collections: Dict[str, List[Any]],
        anomalies: List[AnomalySpec],
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []

        for idx, spec in enumerate(anomalies):
            target_key = spec.target_entity_type.lower()
            if target_key not in ENTITY_TYPE_MAP:
                raise ValueError(
                    f"Unsupported target_entity_type '{spec.target_entity_type}'. "
                    f"Supported types: {list(set(k for k, _ in ENTITY_TYPE_MAP.items()))}"
                )

            collection_name, id_field = ENTITY_TYPE_MAP[target_key]
            collection = entity_collections[collection_name]

            if not collection:
                raise ValueError(
                    f"No entities of type '{spec.target_entity_type}' (collection: '{collection_name}') "
                    f"found in dataset to inject anomaly."
                )

            # Sort candidate entities deterministically by their primary ID
            sorted_candidates = sorted(collection, key=lambda e: getattr(e, id_field, ""))

            # Select target entity
            if spec.target_entity_id is not None:
                matched = [e for e in sorted_candidates if getattr(e, id_field) == spec.target_entity_id]
                if not matched:
                    raise ValueError(
                        f"Target entity with {id_field}='{spec.target_entity_id}' not found in '{collection_name}'."
                    )
                target_entity = matched[0]
            else:
                target_idx = spec.target_index % len(sorted_candidates)
                target_entity = sorted_candidates[target_idx]

            # Find actual index of target_entity in the mutable working collection
            target_id = getattr(target_entity, id_field)
            list_idx = next(i for i, e in enumerate(collection) if getattr(e, id_field) == target_id)

            # Extract settlement_id context if available
            settlement_id = getattr(target_entity, "settlement_id", None)
            if settlement_id is None and collection_name == "bank_entries":
                # Look up matching settlement via UTR
                utr = getattr(target_entity, "utr", None)
                if utr:
                    matching_setl = next(
                        (s for s in entity_collections["settlements"] if s.utr == utr), None
                    )
                    if matching_setl:
                        settlement_id = matching_setl.settlement_id

            anomaly_id = f"anom_{idx + 1:04d}"

            # Apply anomaly transformation
            if spec.anomaly_type == AnomalyType.AMOUNT_MISMATCH:
                target_field = spec.target_field or "amount"
                if not hasattr(target_entity, target_field):
                    raise ValueError(
                        f"Entity of type '{collection_name}' has no field '{target_field}'."
                    )
                original_val = getattr(target_entity, target_field)
                if not isinstance(original_val, Decimal):
                    raise ValueError(
                        f"Field '{target_field}' on '{collection_name}' is not Decimal (got {type(original_val).__name__})."
                    )
                if spec.delta is None or spec.delta == Decimal("0.00"):
                    raise ValueError(
                        f"A non-zero Decimal delta must be provided for AMOUNT_MISMATCH on field '{target_field}'."
                    )

                new_val = (original_val + spec.delta).quantize(Decimal("0.01"))
                updated_entity = target_entity.model_copy(update={target_field: new_val})
                collection[list_idx] = updated_entity

                records.append(
                    AnomalyRecord(
                        anomaly_id=anomaly_id,
                        anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                        target_entity_type=collection_name,
                        target_entity_id=target_id,
                        target_field=target_field,
                        original_value=str(original_val),
                        observed_value=str(new_val),
                        settlement_id=settlement_id,
                        description=(
                            f"Injected AMOUNT_MISMATCH on {collection_name}.{target_field}: "
                            f"{original_val} -> {new_val} (delta: {spec.delta})"
                        ),
                    )
                )

            elif spec.anomaly_type == AnomalyType.MISSING_RECORD:
                collection.pop(list_idx)

                records.append(
                    AnomalyRecord(
                        anomaly_id=anomaly_id,
                        anomaly_type=AnomalyType.MISSING_RECORD,
                        target_entity_type=collection_name,
                        target_entity_id=target_id,
                        target_field=None,
                        original_value=target_id,
                        observed_value=None,
                        settlement_id=settlement_id,
                        description=f"Injected MISSING_RECORD: removed {collection_name} with {id_field}='{target_id}'",
                    )
                )

            elif spec.anomaly_type == AnomalyType.DUPLICATE_RECORD:
                duplicate_copy = target_entity.model_copy(deep=True)
                collection.insert(list_idx + 1, duplicate_copy)

                records.append(
                    AnomalyRecord(
                        anomaly_id=anomaly_id,
                        anomaly_type=AnomalyType.DUPLICATE_RECORD,
                        target_entity_type=collection_name,
                        target_entity_id=target_id,
                        target_field=None,
                        original_value=target_id,
                        observed_value=target_id,
                        settlement_id=settlement_id,
                        description=f"Injected DUPLICATE_RECORD: duplicated {collection_name} with {id_field}='{target_id}'",
                    )
                )

            elif spec.anomaly_type == AnomalyType.IDENTIFIER_MISMATCH:
                target_field = spec.target_field or ("utr" if hasattr(target_entity, "utr") else id_field)
                if not hasattr(target_entity, target_field):
                    raise ValueError(
                        f"Entity of type '{collection_name}' has no field '{target_field}'."
                    )
                original_val = getattr(target_entity, target_field)
                if original_val is None:
                    raise ValueError(
                        f"Field '{target_field}' on {collection_name} '{target_id}' is None; cannot mutate."
                    )

                new_val = f"{original_val}_MISMATCH"
                updated_entity = target_entity.model_copy(update={target_field: new_val})
                collection[list_idx] = updated_entity

                records.append(
                    AnomalyRecord(
                        anomaly_id=anomaly_id,
                        anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                        target_entity_type=collection_name,
                        target_entity_id=target_id,
                        target_field=target_field,
                        original_value=str(original_val),
                        observed_value=str(new_val),
                        settlement_id=settlement_id,
                        description=(
                            f"Injected IDENTIFIER_MISMATCH on {collection_name}.{target_field}: "
                            f"{original_val} -> {new_val}"
                        ),
                    )
                )

        return records


class ObservationGenerator:
    """
    Generates an ObservedWorld and AnomalyManifest from a given GroundTruth.
    """

    @classmethod
    def generate(
        cls,
        ground_truth: GroundTruth,
        config: ObservationConfig,
    ) -> Tuple[ObservedWorld, AnomalyManifest]:
        """
        Deep-clones GroundTruth entities into an ObservedWorld dataset and applies
        configured controlled anomalies if anomalies_enabled is True.
        """
        # 1. Deep clone all GroundTruth entity collections
        entity_collections: Dict[str, List[Any]] = {
            "merchants": [m.model_copy(deep=True) for m in ground_truth.merchants],
            "orders": [o.model_copy(deep=True) for o in ground_truth.orders],
            "payments": [p.model_copy(deep=True) for p in ground_truth.payments],
            "refunds": [r.model_copy(deep=True) for r in ground_truth.refunds],
            "adjustments": [a.model_copy(deep=True) for a in ground_truth.adjustments],
            "transfers": [t.model_copy(deep=True) for t in getattr(ground_truth, "transfers", [])],
            "settlement_transactions": [
                st.model_copy(deep=True) for st in ground_truth.settlement_transactions
            ],
            "settlements": [s.model_copy(deep=True) for s in ground_truth.settlements],
            "bank_entries": [b.model_copy(deep=True) for b in ground_truth.bank_entries],
        }

        records: List[AnomalyRecord] = []

        # 2. Inject anomalies if enabled
        if config.anomalies_enabled and config.anomalies:
            injector = AnomalyInjector(seed=config.seed)
            records = injector.inject(entity_collections, config.anomalies)

        observed_world = ObservedWorld(
            merchants=entity_collections["merchants"],
            orders=entity_collections["orders"],
            payments=entity_collections["payments"],
            refunds=entity_collections["refunds"],
            adjustments=entity_collections["adjustments"],
            transfers=entity_collections.get("transfers", []),
            settlement_transactions=entity_collections["settlement_transactions"],
            settlements=entity_collections["settlements"],
            bank_entries=entity_collections["bank_entries"],
        )

        manifest = AnomalyManifest(records=records)

        return observed_world, manifest
