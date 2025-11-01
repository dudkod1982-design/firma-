"""Domain models used by the pricing calculator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class ComplexityLevel(Enum):
    """Represents how involved the fabrication of the box is."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"

    @property
    def multiplier(self) -> float:
        return {
            ComplexityLevel.SIMPLE: 1.0,
            ComplexityLevel.STANDARD: 1.15,
            ComplexityLevel.COMPLEX: 1.35,
        }[self]

    @property
    def engineering_hours(self) -> float:
        return {
            ComplexityLevel.SIMPLE: 2.0,
            ComplexityLevel.STANDARD: 4.0,
            ComplexityLevel.COMPLEX: 6.5,
        }[self]


@dataclass(frozen=True)
class MaterialProperties:
    """Describes how a material influences pricing."""

    price_per_cubic_meter: float
    finishing_price_per_square_meter: float
    conductivity_modifier: float = 1.0


DEFAULT_MATERIALS: Dict[str, MaterialProperties] = {
    "galvanised_steel": MaterialProperties(
        price_per_cubic_meter=4600.0,
        finishing_price_per_square_meter=48.0,
        conductivity_modifier=1.0,
    ),
    "stainless_steel": MaterialProperties(
        price_per_cubic_meter=6900.0,
        finishing_price_per_square_meter=68.0,
        conductivity_modifier=1.1,
    ),
    "aluminium": MaterialProperties(
        price_per_cubic_meter=5200.0,
        finishing_price_per_square_meter=58.0,
        conductivity_modifier=0.95,
    ),
}
"""Built in material catalogue."""
