import decimal

from hypothesis import given
from hypothesis.strategies import floats

from reportengine.floatformatting import format_number, significant_digits

@given(floats(allow_nan=False))
def test_format_rountrip(x):
    assert (significant_digits(x, 4) == decimal.Decimal(format_number(x, 4)))

def test_nan_roundtrip():
    assert decimal.Decimal(format_number(float('nan'))).is_nan()


