import pytest
from app.models import Product
from app.services.pricing import validate_quantity, calculate_total, PricingError

def test_stars_minimum_and_integer_validation():
    p = Product(name='Stars', category='استارز تلگرام', price_toman=120, pricing_type='per_unit')
    assert validate_quantity(p, 50, 50) == 50
    with pytest.raises(PricingError): validate_quantity(p, 49, 50)
    with pytest.raises(PricingError): validate_quantity(p, '50', 50)
    with pytest.raises(PricingError): validate_quantity(p, 50.0, 50)

def test_per_unit_and_fixed_pricing_are_integer_toman():
    unit = Product(name='Views', category='views', price_toman=17, pricing_type='per_unit')
    fixed = Product(name='Premium', category='premium', price_toman=100_001, pricing_type='fixed')
    assert calculate_total(unit, 51) == 867
    assert calculate_total(fixed, 5) == 100_001
