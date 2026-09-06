import tempfile
import unittest
from pathlib import Path

from apps.api.app.cost_ledger import (
    CaseCostLedger, CaseCostLedgerRepository, CostMeasurement, CostMetric, MeasurementStatus,
)


class CaseCostLedgerTests(unittest.TestCase):
    """Costs must remain attributable and never turn unknown inputs into a price."""

    def test_aggregates_measured_and_estimated_operating_costs_without_selecting_a_price(self):
        ledger = CaseCostLedger.open("case_cost_001")
        ledger = ledger.record(CostMeasurement.money(CostMetric.PROVIDER_COST, 2.00, MeasurementStatus.MEASURED, provider_id="predicta"))
        ledger = ledger.record(CostMeasurement.measured_quantity(CostMetric.SEARCH_COUNT, 10, "searches", MeasurementStatus.MEASURED, unit_cost_usd=0.10))
        ledger = ledger.record(CostMeasurement.money(CostMetric.MODEL_COST, 3.00, MeasurementStatus.MEASURED, provider_id="model_alpha"))
        ledger = ledger.record(CostMeasurement.measured_quantity(CostMetric.COMPUTE_TIME_SECONDS, 10, "seconds", MeasurementStatus.MEASURED, unit_cost_usd=0.20))
        ledger = ledger.record(CostMeasurement.measured_quantity(CostMetric.STORAGE_GB_MONTHS, 1, "GB-months", MeasurementStatus.ESTIMATED, unit_cost_usd=0.10))
        ledger = ledger.record(CostMeasurement.measured_quantity(CostMetric.HUMAN_QA_MINUTES, 30, "minutes", MeasurementStatus.ESTIMATED, unit_cost_usd=0.50))
        ledger = ledger.record(CostMeasurement.money(CostMetric.CASE_REVENUE, 100.00, MeasurementStatus.MEASURED))

        report = ledger.report()

        self.assertEqual(report.research_cost.known_amount_usd, 3.00)
        self.assertEqual(report.ai_cost.known_amount_usd, 3.00)
        self.assertEqual(report.human_review_cost.known_amount_usd, 15.00)
        self.assertEqual(report.direct_variable_cost.known_amount_usd, 23.10)
        self.assertEqual(report.direct_variable_cost.status, MeasurementStatus.ESTIMATED)
        self.assertEqual(report.gross_contribution.known_amount_usd, 76.90)
        self.assertEqual([item.target_contribution_margin for item in report.break_even_prices], [0.5, 0.7, 0.8])
        self.assertEqual([item.lower_bound_price_usd for item in report.break_even_prices], [46.2, 77.0, 115.5])
        self.assertTrue(all(item.selected_price is None for item in report.break_even_prices))

    def test_unknown_human_review_cost_produces_only_a_known_cost_floor(self):
        ledger = CaseCostLedger.open("case_cost_002")
        ledger = ledger.record(CostMeasurement.money(CostMetric.PROVIDER_COST, 10.00, MeasurementStatus.MEASURED, provider_id="predicta"))
        ledger = ledger.record(CostMeasurement.unknown(CostMetric.HUMAN_QA_MINUTES, "minutes", "reviewer time not entered"))

        report = ledger.report()

        self.assertEqual(report.direct_variable_cost.known_amount_usd, 10.00)
        self.assertEqual(report.direct_variable_cost.status, MeasurementStatus.UNKNOWN)
        self.assertIn(CostMetric.HUMAN_QA_MINUTES, report.direct_variable_cost.unknown_metrics)
        fifty_percent = report.break_even_prices[0]
        self.assertEqual(fifty_percent.lower_bound_price_usd, 20.00)
        self.assertIsNone(fifty_percent.upper_bound_price_usd)
        self.assertEqual(fifty_percent.status, MeasurementStatus.UNKNOWN)
        self.assertIsNone(report.gross_contribution.known_amount_usd)

    def test_repository_keeps_an_audit_event_when_a_measurement_is_corrected(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = CaseCostLedgerRepository(Path(directory) / "costs.db")
            repository.open_case("case_cost_003")
            repository.record("case_cost_003", CostMeasurement.measured_quantity(CostMetric.HUMAN_QA_MINUTES, 40, "minutes", MeasurementStatus.ESTIMATED, unit_cost_usd=0.50))
            repository.record("case_cost_003", CostMeasurement.measured_quantity(CostMetric.HUMAN_QA_MINUTES, 35, "minutes", MeasurementStatus.MEASURED, unit_cost_usd=0.50))

            report = repository.report("case_cost_003")
            events = repository.events("case_cost_003")

            self.assertEqual(report.human_review_cost.known_amount_usd, 17.50)
            self.assertEqual(report.human_review_cost.status, MeasurementStatus.MEASURED)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[-1].measurement.status, MeasurementStatus.MEASURED)


if __name__ == "__main__":
    unittest.main()
