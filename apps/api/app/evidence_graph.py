from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from .domain import AnalysisReport, AssumptionRegisterItem, EvidenceItem, Finding
from .intelligence import CanonicalNodeType, IntelligenceRelationship, SQLiteRelationshipRepository


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class EvidenceGraphNode(BaseModel):
    node_id: str
    node_type: CanonicalNodeType
    label: str
    summary: str | None = None
    material: bool = False
    metadata: dict = Field(default_factory=dict)


class EvidenceGraphCase(BaseModel):
    case_id: str
    nodes: list[EvidenceGraphNode]
    edges: list[IntelligenceRelationship]


class LineageIssue(BaseModel):
    code: Literal["BROKEN_MATERIAL_LINEAGE"]
    node_id: str
    message: str


class RecommendationLineage(BaseModel):
    recommendation: EvidenceGraphNode
    findings: list[EvidenceGraphNode]
    calculations: list[EvidenceGraphNode]
    assumptions: list[EvidenceGraphNode]
    claims: list[EvidenceGraphNode]
    passages: list[EvidenceGraphNode]
    sources: list[EvidenceGraphNode]
    edges: list[IntelligenceRelationship]
    issues: list[LineageIssue]
    report_ready: bool


class EvidenceGraphService:
    """Builds auditable decision lineage over the existing relational edge store."""

    def build_case(self, report: AnalysisReport) -> EvidenceGraphCase:
        nodes: dict[str, EvidenceGraphNode] = {}
        edges: list[IntelligenceRelationship] = []

        def node(node_id: str, node_type: CanonicalNodeType, label: str, *, summary: str | None = None, material: bool = False, metadata: dict | None = None) -> None:
            nodes[node_id] = EvidenceGraphNode(
                node_id=node_id, node_type=node_type, label=label, summary=summary,
                material=material, metadata=metadata or {},
            )

        def edge(from_id: str, from_type: CanonicalNodeType, relationship_type: str, to_id: str, to_type: CanonicalNodeType, *, material: bool = False) -> None:
            edges.append(IntelligenceRelationship(
                relationship_id=f"rel_{_slug(from_id)}_{relationship_type.lower()}_{_slug(to_id)}",
                case_id=report.analysis_id,
                from_type=from_type,
                from_id=from_id,
                relationship_type=relationship_type,
                to_type=to_type,
                to_id=to_id,
                metadata={"material": material},
            ))

        for company in report.companies:
            node(f"entity_{company.company_id}", "ENTITY", company.display_name, summary=f"Synthetic peer · {company.status}")

        for evidence in report.evidence:
            self._add_evidence_chain(node, edge, evidence)

        for finding in report.findings:
            node(finding.finding_id, "FINDING", finding.title, summary=finding.summary, material=finding.finding_id == "finding_asset_timing", metadata={"confidence": finding.confidence.value})
            for evidence_id in finding.evidence_ids:
                edge(f"claim_{evidence_id}", "CLAIM", "SUPPORTS_FINDING", finding.finding_id, "FINDING", material=finding.finding_id == "finding_asset_timing")

        material_assumptions = self._add_assumptions(node, edge, report.assumptions)
        calculation_id = "calc_capacity_commitment_guard"
        base = next(item for item in report.financial_scenarios if item.name == "BASE")
        node(
            calculation_id,
            "CALCULATION",
            "Capacity-commitment guard",
            summary=f"Fixture base case reconciles at {base.break_even_utilization:.1%} break-even utilization before capital is committed.",
            material=True,
            metadata={"model": "deterministic_fixture", "reconciled": base.reconciliation_passed},
        )
        for assumption_id in material_assumptions:
            edge(calculation_id, "CALCULATION", "CALCULATED_FROM", assumption_id, "ASSUMPTION", material=True)
        edge(calculation_id, "CALCULATION", "SUPPORTS_FINDING", "finding_asset_timing", "FINDING", material=True)

        recommendation_id = report.decision_brief.recommendation_id
        node(
            recommendation_id,
            "RECOMMENDATION",
            report.decision_brief.recommendation,
            summary=report.decision_brief.decision,
            material=True,
            metadata={"status": report.decision_brief.recommendation_status, "data_mode": report.data_mode},
        )
        edge("finding_asset_timing", "FINDING", "JUSTIFIES_RECOMMENDATION", recommendation_id, "RECOMMENDATION", material=True)

        return EvidenceGraphCase(case_id=report.analysis_id, nodes=sorted(nodes.values(), key=lambda item: item.node_id), edges=sorted(edges, key=lambda item: item.relationship_id))

    @staticmethod
    def _add_evidence_chain(node, edge, evidence: EvidenceItem) -> None:
        entity_id = f"entity_{evidence.company_id}"
        source_id = f"source_{evidence.evidence_id}"
        passage_id = f"passage_{evidence.evidence_id}"
        claim_id = f"claim_{evidence.evidence_id}"
        event_id = f"event_{evidence.evidence_id}"
        node(source_id, "SOURCE", evidence.source_title, summary=f"{evidence.publisher} · {evidence.publication_date}", material=True, metadata={"uri": evidence.source_uri, "verification_status": evidence.verification_status})
        node(passage_id, "PASSAGE", evidence.fact, summary=f"{evidence.period} source passage", material=True)
        node(claim_id, "CLAIM", evidence.normalized_fact, summary="Normalized analytical claim", material=True, metadata={"confidence": evidence.confidence})
        node(event_id, "EVENT", f"{evidence.period} business event", summary=evidence.fact)
        edge(passage_id, "PASSAGE", "DERIVED_FROM", source_id, "SOURCE", material=True)
        edge(passage_id, "PASSAGE", "SUPPORTS", claim_id, "CLAIM", material=True)
        edge(claim_id, "CLAIM", "CONCERNS", event_id, "EVENT")
        edge(event_id, "EVENT", "CONCERNS", entity_id, "ENTITY")

    @staticmethod
    def _add_assumptions(node, edge, assumptions: list[AssumptionRegisterItem]) -> list[str]:
        material_assumptions: list[str] = []
        for assumption in assumptions:
            assumption_id = f"assumption_{_slug(assumption.metric)}"
            metric_id = f"metric_{_slug(assumption.metric)}"
            material = assumption.review_status == "ACCEPTED" and bool(assumption.evidence_ids)
            node(metric_id, "METRIC", assumption.metric, summary=assumption.value)
            node(assumption_id, "ASSUMPTION", f"{assumption.metric}: {assumption.value}", material=material, metadata={"origin": assumption.origin, "review_status": assumption.review_status})
            edge(assumption_id, "ASSUMPTION", "CONCERNS", metric_id, "METRIC")
            for evidence_id in assumption.evidence_ids:
                edge(assumption_id, "ASSUMPTION", "DERIVED_FROM", f"claim_{evidence_id}", "CLAIM", material=material)
            if material:
                material_assumptions.append(assumption_id)
        return material_assumptions

    def persist_case(self, case: EvidenceGraphCase, relationships: SQLiteRelationshipRepository) -> None:
        relationships.save_many(case.edges)

    def explain_recommendation(self, case: EvidenceGraphCase, recommendation_id: str) -> RecommendationLineage:
        nodes = {node.node_id: node for node in case.nodes}
        recommendation = nodes.get(recommendation_id)
        if recommendation is None or recommendation.node_type != "RECOMMENDATION":
            raise KeyError(recommendation_id)

        incoming = lambda node_id, edge_type: [edge for edge in case.edges if edge.to_id == node_id and edge.relationship_type == edge_type]
        outgoing = lambda node_id, edge_type: [edge for edge in case.edges if edge.from_id == node_id and edge.relationship_type == edge_type]
        issues: list[LineageIssue] = []

        def issue(node_id: str, message: str) -> None:
            issues.append(LineageIssue(code="BROKEN_MATERIAL_LINEAGE", node_id=node_id, message=message))

        finding_edges = incoming(recommendation_id, "JUSTIFIES_RECOMMENDATION")
        findings = self._nodes(nodes, [edge.from_id for edge in finding_edges])
        if not findings:
            issue(recommendation_id, "Recommendation has no finding that justifies it.")

        calculation_edges = [edge for finding in findings for edge in incoming(finding.node_id, "SUPPORTS_FINDING") if edge.from_type == "CALCULATION"]
        calculations = self._nodes(nodes, [edge.from_id for edge in calculation_edges])
        if not calculations:
            issue(recommendation_id, "Recommendation finding has no supporting calculation.")

        assumption_edges = [edge for calculation in calculations for edge in outgoing(calculation.node_id, "CALCULATED_FROM")]
        assumptions = self._nodes(nodes, [edge.to_id for edge in assumption_edges])
        material_assumptions = [item for item in assumptions if item.material]
        if not material_assumptions:
            issue(calculations[0].node_id if calculations else recommendation_id, "Calculation has no accepted, evidence-backed material assumption.")

        claim_edges = [edge for assumption in material_assumptions for edge in outgoing(assumption.node_id, "DERIVED_FROM")]
        finding_claim_edges = [edge for finding in findings for edge in incoming(finding.node_id, "SUPPORTS_FINDING") if edge.from_type == "CLAIM"]
        claims = self._nodes(nodes, [edge.to_id for edge in claim_edges] + [edge.from_id for edge in finding_claim_edges])
        if not claim_edges:
            issue(material_assumptions[0].node_id if material_assumptions else recommendation_id, "Material assumption has no source claim.")

        passage_edges = [edge for claim in claims for edge in incoming(claim.node_id, "SUPPORTS") if edge.from_type == "PASSAGE"]
        passages = self._nodes(nodes, [edge.from_id for edge in passage_edges])
        if not passages:
            issue(claims[0].node_id if claims else recommendation_id, "Claim has no supporting passage.")

        source_edges = [edge for passage in passages for edge in outgoing(passage.node_id, "DERIVED_FROM") if edge.to_type == "SOURCE"]
        sources = self._nodes(nodes, [edge.to_id for edge in source_edges])
        if not sources:
            issue(passages[0].node_id if passages else recommendation_id, "Passage has no source lineage.")

        lineage_node_ids = {recommendation_id, *(node.node_id for node in findings), *(node.node_id for node in calculations), *(node.node_id for node in assumptions), *(node.node_id for node in claims), *(node.node_id for node in passages), *(node.node_id for node in sources)}
        lineage_edges = [edge for edge in case.edges if edge.from_id in lineage_node_ids and edge.to_id in lineage_node_ids]
        return RecommendationLineage(
            recommendation=recommendation,
            findings=findings,
            calculations=calculations,
            assumptions=assumptions,
            claims=claims,
            passages=passages,
            sources=sources,
            edges=sorted(lineage_edges, key=lambda item: item.relationship_id),
            issues=issues,
            report_ready=not issues,
        )

    @staticmethod
    def _nodes(nodes: dict[str, EvidenceGraphNode], node_ids: list[str]) -> list[EvidenceGraphNode]:
        return [nodes[node_id] for node_id in sorted(set(node_ids)) if node_id in nodes]
