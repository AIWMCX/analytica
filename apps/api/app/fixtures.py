from __future__ import annotations

from .domain import (
    AnalysisReport,
    AnalysisStatus,
    CohortSummary,
    CompanyTrajectory,
    ConfidenceClass,
    EvidenceItem,
    Finding,
    Lesson,
    TrajectoryPoint,
)


def _state(score: float) -> str:
    if score < 40:
        return "red"
    if score < 58:
        return "yellow"
    if score < 75:
        return "blue"
    return "green"


def _trajectory(values: list[tuple[int, float]], evidence_by_year: dict[int, list[str]]) -> list[TrajectoryPoint]:
    return [
        TrajectoryPoint(
            year=year,
            performance_score=score,
            risk_score=round(1 - score / 100, 2),
            state=_state(score),
            evidence_ids=evidence_by_year.get(year, []),
        )
        for year, score in values
    ]


def build_demo_report() -> AnalysisReport:
    """Return a deterministic synthetic report for product/R&D validation.

    No company in this fixture represents a real legal entity. The fixture validates
    contracts, analytics behavior, and UI semantics before lawful data providers are
    connected.
    """
    evidence = [
        EvidenceItem(evidence_id="ev_northstar_2021_margin", company_id="cmp_northstar", source_type="synthetic_fixture", source_title="Northstar Packaging synthetic operating note", publisher="Analytica R&D Fixture", publication_date="2021-12-31", period=2021, fact="Input costs rose while management delayed new fixed-asset purchases.", normalized_fact="Input-cost pressure was paired with conservative capital expenditure.", confidence=0.98, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_northstar_2023_mix", company_id="cmp_northstar", source_type="synthetic_fixture", source_title="Northstar Packaging synthetic product-mix note", publisher="Analytica R&D Fixture", publication_date="2023-12-31", period=2023, fact="Higher-margin recyclable film became a larger share of sales.", normalized_fact="Product-mix shift improved modeled operating quality.", confidence=0.96, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_hudson_2020_expansion", company_id="cmp_hudson", source_type="synthetic_fixture", source_title="Hudson Carton synthetic expansion note", publisher="Analytica R&D Fixture", publication_date="2020-12-31", period=2020, fact="Two facilities were opened before utilization recovered.", normalized_fact="Premature fixed-cost expansion increased modeled risk.", confidence=0.97, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_hudson_2022_restructure", company_id="cmp_hudson", source_type="synthetic_fixture", source_title="Hudson Carton synthetic restructuring note", publisher="Analytica R&D Fixture", publication_date="2022-12-31", period=2022, fact="One site was consolidated and equipment moved to leased capacity.", normalized_fact="Asset-light restructuring preceded modeled recovery.", confidence=0.95, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_empire_2021_customer", company_id="cmp_empire", source_type="synthetic_fixture", source_title="Empire Flex synthetic customer concentration note", publisher="Analytica R&D Fixture", publication_date="2021-12-31", period=2021, fact="One customer represented an unusually large modeled revenue share.", normalized_fact="Customer concentration increased modeled downside exposure.", confidence=0.94, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_empire_2022_loss", company_id="cmp_empire", source_type="synthetic_fixture", source_title="Empire Flex synthetic loss event", publisher="Analytica R&D Fixture", publication_date="2022-12-31", period=2022, fact="The largest customer contract ended and the synthetic business later closed.", normalized_fact="Concentrated revenue loss was associated with fixture failure.", confidence=0.99, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_liberty_2019_supplier", company_id="cmp_liberty", source_type="synthetic_fixture", source_title="Liberty Wrap synthetic supplier note", publisher="Analytica R&D Fixture", publication_date="2019-12-31", period=2019, fact="The company diversified resin suppliers before a modeled price shock.", normalized_fact="Supplier diversification reduced modeled procurement volatility.", confidence=0.93, verification_status="fixture_verified"),
        EvidenceItem(evidence_id="ev_liberty_2024_automation", company_id="cmp_liberty", source_type="synthetic_fixture", source_title="Liberty Wrap synthetic automation note", publisher="Analytica R&D Fixture", publication_date="2024-12-31", period=2024, fact="Automation was added after sustained utilization exceeded the fixture threshold.", normalized_fact="Staged automation followed validated demand rather than preceding it.", confidence=0.95, verification_status="fixture_verified"),
    ]

    companies = [
        CompanyTrajectory(company_id="cmp_northstar", display_name="Northstar Packaging (synthetic)", status="high_performer", comparability_score=0.94, trajectory=_trajectory([(2016, 58), (2017, 62), (2018, 66), (2019, 70), (2020, 64), (2021, 61), (2022, 72), (2023, 82), (2024, 87), (2025, 90)], {2021: ["ev_northstar_2021_margin"], 2023: ["ev_northstar_2023_mix"]})),
        CompanyTrajectory(company_id="cmp_hudson", display_name="Hudson Carton Works (synthetic)", status="active", comparability_score=0.89, trajectory=_trajectory([(2016, 55), (2017, 59), (2018, 61), (2019, 65), (2020, 42), (2021, 38), (2022, 51), (2023, 64), (2024, 69), (2025, 73)], {2020: ["ev_hudson_2020_expansion"], 2022: ["ev_hudson_2022_restructure"]})),
        CompanyTrajectory(company_id="cmp_empire", display_name="Empire Flex Supply (synthetic)", status="failed", comparability_score=0.87, trajectory=_trajectory([(2016, 63), (2017, 66), (2018, 67), (2019, 65), (2020, 60), (2021, 49), (2022, 27)], {2021: ["ev_empire_2021_customer"], 2022: ["ev_empire_2022_loss"]})),
        CompanyTrajectory(company_id="cmp_liberty", display_name="Liberty Wrap Systems (synthetic)", status="high_performer", comparability_score=0.91, trajectory=_trajectory([(2016, 50), (2017, 57), (2018, 63), (2019, 70), (2020, 72), (2021, 76), (2022, 79), (2023, 81), (2024, 88), (2025, 91)], {2019: ["ev_liberty_2019_supplier"], 2024: ["ev_liberty_2024_automation"]})),
        CompanyTrajectory(company_id="cmp_atlas", display_name="Atlas Fiber Pack (synthetic)", status="distressed", comparability_score=0.82, trajectory=_trajectory([(2016, 61), (2017, 60), (2018, 58), (2019, 56), (2020, 54), (2021, 49), (2022, 46), (2023, 43), (2024, 40), (2025, 37)], {})),
    ]

    findings = [
        Finding(finding_id="finding_asset_timing", title="Validate utilization before adding fixed assets", summary="The synthetic cohort shows weaker modeled performance when expansion precedes validated utilization, and recovery after asset-light restructuring.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_hudson_2020_expansion", "ev_hudson_2022_restructure"], impact="negative"),
        Finding(finding_id="finding_concentration", title="Concentration can turn one commercial loss into a survival event", summary="The failed synthetic company had elevated customer concentration before the modeled loss of its largest contract.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_empire_2021_customer", "ev_empire_2022_loss"], impact="negative"),
        Finding(finding_id="finding_staged_investment", title="Stage investment after demand is demonstrated", summary="The strongest fixture trajectories pair supplier resilience and delayed capital deployment with sustained utilization.", confidence=ConfidenceClass.ANALYTICAL_INFERENCE, evidence_ids=["ev_liberty_2019_supplier", "ev_liberty_2024_automation", "ev_northstar_2021_margin"], impact="positive"),
        Finding(finding_id="finding_product_mix", title="Product mix can matter more than category labels", summary="A higher-margin synthetic product mix is associated with a strong modeled trajectory, illustrating why Analytica must explain sub-category shifts rather than only industry averages.", confidence=ConfidenceClass.CORRELATION, evidence_ids=["ev_northstar_2023_mix"], impact="positive"),
    ]

    lessons = [
        Lesson(priority=1, title="Lease before buying when demand is not validated", action="Keep the first capacity decision reversible until utilization is demonstrated.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_hudson_2020_expansion", "ev_hudson_2022_restructure"]),
        Lesson(priority=2, title="Avoid customer concentration", action="Set concentration limits and create a diversification plan before one account can determine survival.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_empire_2021_customer", "ev_empire_2022_loss"]),
        Lesson(priority=3, title="Diversify critical suppliers", action="Qualify alternatives for high-volatility inputs before a price shock occurs.", confidence=ConfidenceClass.VERIFIED_OBSERVATION, evidence_ids=["ev_liberty_2019_supplier"]),
        Lesson(priority=4, title="Stage automation after utilization", action="Tie automation investment to sustained utilization thresholds rather than optimistic forecasts.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_liberty_2024_automation"]),
        Lesson(priority=5, title="Track product-mix quality", action="Measure margin and durability by sub-product rather than judging the whole packaging category as one market.", confidence=ConfidenceClass.CORRELATION, evidence_ids=["ev_northstar_2023_mix"]),
        Lesson(priority=6, title="Protect liquidity during input-cost shocks", action="Delay discretionary fixed-asset purchases when input costs compress operating flexibility.", confidence=ConfidenceClass.ANALYTICAL_INFERENCE, evidence_ids=["ev_northstar_2021_margin"]),
        Lesson(priority=7, title="Treat expansion and demand as one decision", action="Require demand evidence, cash runway, and utilization thresholds before opening additional capacity.", confidence=ConfidenceClass.EVIDENCE_SUPPORTED_EXPLANATION, evidence_ids=["ev_hudson_2020_expansion"]),
        Lesson(priority=8, title="Use failure cases as first-class evidence", action="Review failed peers explicitly instead of benchmarking only surviving companies.", confidence=ConfidenceClass.VERIFIED_OBSERVATION, evidence_ids=["ev_empire_2022_loss"]),
        Lesson(priority=9, title="Prefer reversible early-stage commitments", action="Choose leases, pilots, and staged contracts where uncertainty is still high.", confidence=ConfidenceClass.ANALYTICAL_INFERENCE, evidence_ids=["ev_hudson_2022_restructure", "ev_liberty_2024_automation"]),
        Lesson(priority=10, title="Demand evidence for every recommendation", action="Do not act on an Analytica lesson unless its evidence and confidence level are visible and acceptable.", confidence=ConfidenceClass.VERIFIED_OBSERVATION, evidence_ids=["ev_northstar_2021_margin", "ev_empire_2022_loss"]),
    ]

    return AnalysisReport(
        analysis_id="demo_packaging_ny_v1",
        business_activity="Packaging manufacturing",
        geography="New York",
        market_scope="United States — R&D fixture",
        status=AnalysisStatus.COMPLETED,
        readiness_label="R&D vertical slice — synthetic evidence only",
        disclaimer="All companies and evidence in this demonstrator are synthetic. No real-company conclusion is being asserted.",
        cohort=CohortSummary(target_size=100, fixture_company_count=len(companies), active_count=1, distressed_count=1, failed_count=1, high_performer_count=2, note="Production target is up to 100 comparable companies; this fixture intentionally uses five synthetic entities to validate product behavior."),
        companies=companies,
        evidence=evidence,
        findings=findings,
        lessons=lessons,
    )
