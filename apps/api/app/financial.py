from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FinancialModelInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    capex: float = Field(gt=0)
    monthly_capacity_revenue: float = Field(gt=0)
    utilization: float = Field(gt=0, le=1)
    gross_margin: float = Field(gt=0, le=1)
    monthly_fixed_cost: float = Field(ge=0)
    available_cash: float = Field(ge=0)


class ReconciliationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed: bool
    equation: str
    variance: float


class FinancialResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_version: str
    name: str
    monthly_revenue: float
    gross_profit: float
    monthly_fixed_cost: float
    operating_profit: float
    break_even_utilization: float
    payback_months: float
    runway_months: float | None
    reconciliation: ReconciliationResult


class SensitivityResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    driver: str
    profit_swing: float
    low_operating_profit: float
    high_operating_profit: float


class QuantisFinancialPort:
    """Small deterministic boundary compatible with the future extracted Quantis kernel."""

    def __init__(self, model_version: str):
        self.model_version = model_version

    def _calculate(self, inputs: FinancialModelInput, name: str) -> FinancialResult:
        revenue = round(inputs.monthly_capacity_revenue * inputs.utilization, 2)
        gross_profit = round(revenue * inputs.gross_margin, 2)
        operating_profit = round(gross_profit - inputs.monthly_fixed_cost, 2)
        break_even_utilization = round(inputs.monthly_fixed_cost / (inputs.monthly_capacity_revenue * inputs.gross_margin), 4)
        payback = round(inputs.capex / operating_profit, 1) if operating_profit > 0 else 999.0
        runway = round(inputs.available_cash / abs(operating_profit), 1) if operating_profit < 0 else None
        variance = round(gross_profit - inputs.monthly_fixed_cost - operating_profit, 8)
        return FinancialResult(
            model_version=self.model_version, name=name, monthly_revenue=revenue, gross_profit=gross_profit,
            monthly_fixed_cost=inputs.monthly_fixed_cost, operating_profit=operating_profit,
            break_even_utilization=break_even_utilization, payback_months=payback, runway_months=runway,
            reconciliation=ReconciliationResult(
                passed=abs(variance) < 0.01, equation="gross_profit - fixed_cost = operating_profit", variance=variance,
            ),
        )

    def calculate_baseline(self, inputs: FinancialModelInput) -> FinancialResult:
        return self._calculate(inputs, "BASE")

    def run_scenarios(self, inputs: FinancialModelInput) -> list[FinancialResult]:
        downside = inputs.model_copy(update={
            "utilization": max(0.01, inputs.utilization - 0.17),
            "gross_margin": max(0.01, inputs.gross_margin - 0.04),
            "monthly_fixed_cost": inputs.monthly_fixed_cost * 1.08,
        })
        upside = inputs.model_copy(update={
            "utilization": min(1.0, inputs.utilization + 0.09),
            "gross_margin": min(1.0, inputs.gross_margin + 0.03),
            "monthly_fixed_cost": inputs.monthly_fixed_cost * 1.04,
        })
        return [self._calculate(downside, "DOWNSIDE"), self._calculate(inputs, "BASE"), self._calculate(upside, "UPSIDE")]

    def run_sensitivity(self, inputs: FinancialModelInput) -> list[SensitivityResult]:
        variants = [
            ("utilization", {"utilization": max(0.01, inputs.utilization * 0.9)}, {"utilization": min(1.0, inputs.utilization * 1.1)}),
            ("gross_margin", {"gross_margin": max(0.01, inputs.gross_margin * 0.9)}, {"gross_margin": min(1.0, inputs.gross_margin * 1.1)}),
            ("fixed_cost", {"monthly_fixed_cost": inputs.monthly_fixed_cost * 1.1}, {"monthly_fixed_cost": inputs.monthly_fixed_cost * 0.9}),
        ]
        results = []
        for driver, low_change, high_change in variants:
            low = self._calculate(inputs.model_copy(update=low_change), "LOW")
            high = self._calculate(inputs.model_copy(update=high_change), "HIGH")
            results.append(SensitivityResult(
                driver=driver, profit_swing=round(high.operating_profit - low.operating_profit, 2),
                low_operating_profit=low.operating_profit, high_operating_profit=high.operating_profit,
            ))
        return sorted(results, key=lambda item: item.profit_swing, reverse=True)
