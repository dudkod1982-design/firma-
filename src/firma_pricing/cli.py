"""Command line interface for the HLZ line box pricing calculator."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Dict

from .calculator import PricingCalculator, PricingInput
from .domain import ComplexityLevel


def parse_args(argv: Any = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculate prices for HLZ line boxes")
    parser.add_argument("material", help="Material key to use")
    parser.add_argument("length", type=float, help="External length in millimeters")
    parser.add_argument("width", type=float, help="External width in millimeters")
    parser.add_argument("height", type=float, help="External height in millimeters")
    parser.add_argument("wall", type=float, help="Wall thickness in millimeters")
    parser.add_argument("quantity", type=int, help="Number of boxes required")
    parser.add_argument(
        "--complexity",
        choices=[level.value for level in ComplexityLevel],
        default=ComplexityLevel.STANDARD.value,
        help="Fabrication complexity",
    )
    parser.add_argument("--cable-management", action="store_true", help="Include cable trays")
    parser.add_argument("--emc-shielding", action="store_true", help="Add EMC shielding")
    parser.add_argument("--ip-sealing", action="store_true", help="Include IP rated sealing")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the calculation as JSON rather than a table",
    )
    return parser.parse_args(argv)


def _format_currency(value: float) -> str:
    return f"{value:,.2f} €"


def _format_table(result_dict: Dict[str, Any]) -> str:
    sections = [
        ("Material", result_dict["material_cost"]),
        ("Finishing", result_dict["finishing_cost"]),
        ("Engineering", result_dict["engineering_cost"]),
        ("Assembly", result_dict["assembly_cost"]),
        ("Extras", result_dict["extras_cost"]),
        ("Discount", -result_dict["discount"]),
        ("Total", result_dict["total_cost"]),
        ("Unit price", result_dict["unit_price"]),
    ]
    lines = ["Breakdown:"]
    for label, value in sections:
        lines.append(f"  {label:<12} {_format_currency(value)}")
    return "\n".join(lines)


def main(argv: Any = None) -> int:
    args = parse_args(argv)
    calculator = PricingCalculator()
    order = PricingInput(
        length_mm=args.length,
        width_mm=args.width,
        height_mm=args.height,
        wall_thickness_mm=args.wall,
        material_key=args.material,
        quantity=args.quantity,
        complexity=ComplexityLevel(args.complexity),
        requires_cable_management=args.cable_management,
        requires_emc_shielding=args.emc_shielding,
        requires_ip_sealing=args.ip_sealing,
    )
    result = calculator.calculate(order)
    result_dict = asdict(result)

    if args.json:
        print(json.dumps(result_dict, indent=2))
    else:
        print(_format_table(result_dict))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
