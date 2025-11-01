from firma_pricing.calculator import PricingCalculator, PricingInput
from firma_pricing.domain import ComplexityLevel


def test_pricing_calculation_round_trip():
    calculator = PricingCalculator()
    order = PricingInput(
        length_mm=800,
        width_mm=400,
        height_mm=350,
        wall_thickness_mm=4,
        material_key="galvanised_steel",
        quantity=25,
        complexity=ComplexityLevel.STANDARD,
        requires_cable_management=True,
        requires_emc_shielding=True,
        requires_ip_sealing=False,
    )
    result = calculator.calculate(order)

    assert result.total_cost > 0
    assert result.unit_price == round(result.total_cost / order.quantity, 2)
    assert result.discount > 0


def test_invalid_material_raises():
    calculator = PricingCalculator()
    order = PricingInput(
        length_mm=500,
        width_mm=300,
        height_mm=200,
        wall_thickness_mm=3,
        material_key="unknown",
        quantity=5,
    )
    try:
        calculator.calculate(order)
    except KeyError as exc:
        assert "Material 'unknown'" in str(exc)
    else:  # pragma: no cover - guard against regression
        raise AssertionError("Expected KeyError for missing material")


def test_discount_thresholds():
    calculator = PricingCalculator()
    base_order_kwargs = dict(
        length_mm=400,
        width_mm=350,
        height_mm=250,
        wall_thickness_mm=3,
        material_key="aluminium",
    )

    for qty, expected_discount in [(5, 0.0), (10, 0.03), (30, 0.06), (80, 0.1), (200, 0.14)]:
        order = PricingInput(quantity=qty, **base_order_kwargs)
        result = calculator.calculate(order)
        assert result.discount > 0 or expected_discount == 0.0
        per_unit = result.unit_price
        subtotal = result.total_cost + result.discount
        applied_discount = 1 - (result.total_cost / subtotal)
        assert round(applied_discount, 2) == expected_discount
        assert per_unit == round(result.total_cost / qty, 2)
