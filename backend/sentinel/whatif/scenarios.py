from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class CountryDisruptionScenario:
    type: str = "country_disruption"
    country: str = ""
    severity: str = "total_loss"
    tariff_pct: float | None = None


@dataclass
class SupplierFailureScenario:
    type: str = "supplier_failure"
    manufacturer: str = ""
    failure_mode: str = "bankruptcy"


@dataclass
class ObsolescenceWaveScenario:
    type: str = "obsolescence_wave"
    target_statuses: list[str] = field(default_factory=lambda: ["NRFND"])
    time_horizon_months: int = 12


@dataclass
class ComponentRemovalScenario:
    type: str = "component_removal"
    mpns: list[str] = field(default_factory=list)
    reason: str = "obsolete"


@dataclass
class DemandSpikeScenario:
    type: str = "demand_spike"
    multiplier: float = 2.0
    affected_bom_ids: list[UUID] | None = None


SCENARIO_TEMPLATES = [
    {
        "name": "Taiwan Semiconductor Disruption",
        "description": "Model loss of Taiwan-manufactured semiconductors",
        "scenario_type": "country_disruption",
        "parameters": {"country": "Taiwan", "severity": "total_loss"},
    },
    {
        "name": "China Supply Chain Disruption",
        "description": "Model loss of components manufactured in China",
        "scenario_type": "country_disruption",
        "parameters": {"country": "China", "severity": "total_loss"},
    },
    {
        "name": "Key Supplier Bankruptcy",
        "description": "Model a key manufacturer going bankrupt",
        "scenario_type": "supplier_failure",
        "parameters": {"manufacturer": "", "failure_mode": "bankruptcy"},
    },
    {
        "name": "NRFND Accelerated Obsolescence",
        "description": "Model all NRFND parts going obsolete within 12 months",
        "scenario_type": "obsolescence_wave",
        "parameters": {"target_statuses": ["NRFND"], "time_horizon_months": 12},
    },
    {
        "name": "Demand Surge (2x)",
        "description": "Model doubling of demand across all programs",
        "scenario_type": "demand_spike",
        "parameters": {"multiplier": 2.0},
    },
]
