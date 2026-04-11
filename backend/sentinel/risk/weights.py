from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskWeightProfile:
    name: str
    lifecycle: float
    supply: float
    geographic: float
    supplier: float
    regulatory: float

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "lifecycle": self.lifecycle,
            "supply": self.supply,
            "geographic": self.geographic,
            "supplier": self.supplier,
            "regulatory": self.regulatory,
        }


DEFAULT_PROFILE = RiskWeightProfile(
    name="default",
    lifecycle=0.30,
    supply=0.25,
    geographic=0.20,
    supplier=0.15,
    regulatory=0.10,
)

SUPPLY_CHAIN_PROFILE = RiskWeightProfile(
    name="supply_chain_focus",
    lifecycle=0.15,
    supply=0.30,
    geographic=0.30,
    supplier=0.20,
    regulatory=0.05,
)

PROFILES: dict[str, RiskWeightProfile] = {
    DEFAULT_PROFILE.name: DEFAULT_PROFILE,
    SUPPLY_CHAIN_PROFILE.name: SUPPLY_CHAIN_PROFILE,
}
