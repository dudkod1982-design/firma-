"""Pricing calculator for HLZ line boxes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .domain import ComplexityLevel, DEFAULT_MATERIALS, MaterialProperties


@dataclass(frozen=True)
class PricingInput:
    """Input parameters describing a box order."""

    length_mm: float
    width_mm: float
    height_mm: float
    wall_thickness_mm: float
    material_key: str
    quantity: int
    complexity: ComplexityLevel = ComplexityLevel.STANDARD
    requires_cable_management: bool = False
    requires_emc_shielding: bool = False
    requires_ip_sealing: bool = False

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if min(self.length_mm, self.width_mm, self.height_mm, self.wall_thickness_mm) <= 0:
            raise ValueError("All dimensions must be positive")


@dataclass(frozen=True)
class PricingResult:
    """Detailed breakdown produced by the calculator."""

    material_cost: float
    finishing_cost: float
    engineering_cost: float
    assembly_cost: float
    extras_cost: float
    discount: float
    total_cost: float
    unit_price: float

    def per_unit_breakdown(self) -> Dict[str, float]:
        """Returns each component apportioned to a single unit."""

        return {
            "material": self.material_cost,
            "finishing": self.finishing_cost,
            "engineering": self.engineering_cost,
            "assembly": self.assembly_cost,
            "extras": self.extras_cost,
            "discount": self.discount,
        }


class PricingCalculator:
    """Encapsulates the rules required to price HLZ line boxes."""

    def __init__(
        self,
        materials: Optional[Dict[str, MaterialProperties]] = None,
        base_engineering_rate_per_hour: float = 48.0,
        base_assembly_rate_per_hour: float = 32.0,
        handling_fee: float = 180.0,
    ) -> None:
        self._materials = materials or DEFAULT_MATERIALS
        self.base_engineering_rate_per_hour = base_engineering_rate_per_hour
        self.base_assembly_rate_per_hour = base_assembly_rate_per_hour
        self.handling_fee = handling_fee

    def available_materials(self) -> Iterable[str]:
        return self._materials.keys()

    def _material(self, key: str) -> MaterialProperties:
        try:
            return self._materials[key]
        except KeyError as exc:
            raise KeyError(
                f"Material '{key}' is not defined. Available materials: {', '.join(self._materials)}"
            ) from exc

    def calculate(self, order: PricingInput) -> PricingResult:
        material = self._material(order.material_key)
        volume_m3 = self._calculate_volume(order)
        surface_area_m2 = self._calculate_surface_area(order)

        material_cost = volume_m3 * material.price_per_cubic_meter
        finishing_cost = surface_area_m2 * material.finishing_price_per_square_meter

        engineering_hours = order.complexity.engineering_hours
        engineering_cost = engineering_hours * self.base_engineering_rate_per_hour

        assembly_hours = self._calculate_assembly_hours(order)
        assembly_cost = assembly_hours * self.base_assembly_rate_per_hour

        extras_cost = self._calculate_extras(order, material)

        subtotal = (
            material_cost
            + finishing_cost
            + engineering_cost
            + assembly_cost
            + extras_cost
            + self.handling_fee
        )

        subtotal *= order.complexity.multiplier
        discount = subtotal * self._quantity_discount(order.quantity)
        total_cost = subtotal - discount
        unit_price = total_cost / order.quantity

        return PricingResult(
            material_cost=round(material_cost, 2),
            finishing_cost=round(finishing_cost, 2),
            engineering_cost=round(engineering_cost, 2),
            assembly_cost=round(assembly_cost, 2),
            extras_cost=round(extras_cost, 2),
            discount=round(discount, 2),
            total_cost=round(total_cost, 2),
            unit_price=round(unit_price, 2),
        )

    @staticmethod
    def _calculate_volume(order: PricingInput) -> float:
        external_volume_mm3 = order.length_mm * order.width_mm * order.height_mm
        internal_length = max(order.length_mm - 2 * order.wall_thickness_mm, 0)
        internal_width = max(order.width_mm - 2 * order.wall_thickness_mm, 0)
        internal_height = max(order.height_mm - 2 * order.wall_thickness_mm, 0)
        internal_volume_mm3 = internal_length * internal_width * internal_height
        used_material_volume_mm3 = external_volume_mm3 - internal_volume_mm3
        return used_material_volume_mm3 / 1_000_000_000

    @staticmethod
    def _calculate_surface_area(order: PricingInput) -> float:
        lw = order.length_mm * order.width_mm
        lh = order.length_mm * order.height_mm
        wh = order.width_mm * order.height_mm
        surface_area_mm2 = 2 * (lw + lh + wh)
        return surface_area_mm2 / 1_000_000

    @staticmethod
    def _calculate_assembly_hours(order: PricingInput) -> float:
        base_hours = 1.8
        scale_factor = (order.length_mm + order.width_mm + order.height_mm) / 1500
        thickness_factor = 1 + (order.wall_thickness_mm / 5)
        quantity_factor = max(0.6, 1.4 - order.quantity / 120)
        return base_hours * scale_factor * thickness_factor * quantity_factor

    def _calculate_extras(self, order: PricingInput, material: MaterialProperties) -> float:
        extras = 0.0
        if order.requires_cable_management:
            extras += 140.0 + 6.5 * order.height_mm / 100
        if order.requires_emc_shielding:
            extras += 220.0 * material.conductivity_modifier
        if order.requires_ip_sealing:
            perimeter_m = 2 * (order.length_mm + order.width_mm) / 1000
            extras += 35.0 + 24.0 * perimeter_m
        return extras

    @staticmethod
    def _quantity_discount(quantity: int) -> float:
        if quantity >= 150:
            return 0.14
        if quantity >= 80:
            return 0.1
        if quantity >= 30:
            return 0.06
        if quantity >= 10:
            return 0.03
        return 0.0
