import unittest

from apps.api.app.financial import FinancialModelInput, QuantisFinancialPort


class QuantisFinancialPortTests(unittest.TestCase):
    def setUp(self):
        self.port = QuantisFinancialPort(model_version="quantis-compatible.demo.v1")
        self.inputs = FinancialModelInput(
            capex=350000,
            monthly_capacity_revenue=420000,
            utilization=0.71,
            gross_margin=0.31,
            monthly_fixed_cost=69000,
            available_cash=510000,
        )

    def test_same_inputs_produce_identical_reconciled_results(self):
        first = self.port.calculate_baseline(self.inputs)
        second = self.port.calculate_baseline(self.inputs)
        self.assertEqual(first, second)
        self.assertTrue(first.reconciliation.passed)
        self.assertAlmostEqual(first.gross_profit - first.monthly_fixed_cost, first.operating_profit)

    def test_downside_is_financially_worse_than_base_and_upside(self):
        scenarios = self.port.run_scenarios(self.inputs)
        by_name = {scenario.name: scenario for scenario in scenarios}
        self.assertLess(by_name["DOWNSIDE"].operating_profit, by_name["BASE"].operating_profit)
        self.assertLess(by_name["BASE"].operating_profit, by_name["UPSIDE"].operating_profit)
        self.assertGreater(by_name["DOWNSIDE"].payback_months, by_name["BASE"].payback_months)

    def test_sensitivity_ranks_the_driver_with_largest_profit_effect_first(self):
        sensitivity = self.port.run_sensitivity(self.inputs)
        self.assertEqual(sensitivity[0].driver, "utilization")
        self.assertGreaterEqual(sensitivity[0].profit_swing, sensitivity[-1].profit_swing)


if __name__ == "__main__":
    unittest.main()
