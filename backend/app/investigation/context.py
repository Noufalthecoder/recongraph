"""
Evidence-first context model and builder for grounded AI investigations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestigationContext(BaseModel):
    """
    Compact, structured context passed to the AI investigator.
    Contains only tool-retrieved facts, evidence, and graph relationships.
    """
    model_config = ConfigDict(frozen=True)

    target_entity_type: Optional[str] = None
    target_entity_id: Optional[str] = None
    reconciliation_status: str = "UNKNOWN"
    facts: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    graph_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    graph_edges: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    untrusted_data_warnings: List[str] = Field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Renders the context into a clean, structured string block for prompt injection."""
        lines = [
            "<investigation_context>",
            f"Target: {self.target_entity_type or 'None'}:{self.target_entity_id or 'None'}",
            f"Reconciliation Status: {self.reconciliation_status}",
            "",
            "FACTS:",
        ]

        for k, v in sorted(self.facts.items()):
            if isinstance(v, dict):
                lines.append(f"  {k}:")
                for sub_k, sub_v in sorted(v.items()):
                    lines.append(f"    {sub_k} = {sub_v}")
            else:
                lines.append(f"  {k} = {v}")

        lines.append("")
        lines.append("EVIDENCE CITATIONS:")
        for cit in self.citations:
            lines.append(f"  - {cit}")

        if self.evidence:
            lines.append("")
            lines.append("EVIDENCE DETAILS:")
            for idx, ev in enumerate(self.evidence):
                rule = ev.get("rule_code", "UNKNOWN")
                diff = ev.get("difference")
                exp = ev.get("expected_value")
                obs = ev.get("observed_value")
                lines.append(f"  [E{idx+1}] Rule: {rule} | Diff: {diff} | Exp: {exp} | Obs: {obs}")

        lines.append("</investigation_context>")
        return "\n".join(lines)


class InvestigationContextBuilder:
    """
    Assembles an immutable InvestigationContext from raw tool execution results.
    """

    @classmethod
    def build(
        cls,
        target_entity_type: Optional[str],
        target_entity_id: Optional[str],
        tool_results: List[Dict[str, Any]],
    ) -> InvestigationContext:
        facts: Dict[str, Any] = {}
        evidence: List[Dict[str, Any]] = []
        graph_nodes: List[Dict[str, Any]] = []
        graph_edges: List[Dict[str, Any]] = []
        citations_set: List[str] = []
        recon_status = "UNKNOWN"

        for tr in tool_results:
            data = tr.get("structured_data", {})
            if "status" in data:
                recon_status = data["status"]

            if "summary_facts" in data and isinstance(data["summary_facts"], dict):
                facts.update(data["summary_facts"])

            if "evidence" in data and isinstance(data["evidence"], list):
                evidence.extend(data["evidence"])

            if "exceptions" in data and isinstance(data["exceptions"], list):
                for exc in data["exceptions"]:
                    rule = exc.get("rule_code")
                    if rule and f"Rule: {rule}" not in citations_set:
                        citations_set.append(f"Rule: {rule}")

            for ref in tr.get("evidence_refs", []):
                if ref not in citations_set:
                    citations_set.append(ref)

        return InvestigationContext(
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            reconciliation_status=recon_status,
            facts=facts,
            evidence=evidence,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            citations=sorted(citations_set),
            untrusted_data_warnings=[],
        )
