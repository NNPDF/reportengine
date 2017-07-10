"""
floatformatting.py

Tools to format floating point number properly. This is more difficult than
it looks like.
"""

import decimal

def significant_digits(value, digits):
    """Return a `Decimal` object with all the digits less signingicant than
    `digits` trimmed (that is, with floor rounding)."""
    cv = decimal.getcontext().copy()
    cv.prec = digits
    fval =  cv.create_decimal(value)
    return fval

def remove_exponent(d):
    return d.quantize(1) if d == d.to_integral() else d.normalize()

def write_in_adequate_representation(n, minexp = -4, maxexp = None):
    """Return a decimal string representatin of `n` if its most signigicative
    power of 10 is between ``minexp`` and ``maxexp``. Otherwise return a
    scientific reporesentation.
    Values of ``None``
    for either minexp or maxexp signifies that the value is unbounded"""
    dec = decimal.Decimal(n)
    if not dec.is_finite():
        return str(dec)
    nexp = dec.adjusted()
    if nexp < minexp or (maxexp is not None and nexp > maxexp):
        tp = dec.as_tuple()
        digits = tp.digits

        #print nexp, digits
        mantissa =  ''.join(str(d) for d in digits[1:])
        signstr = '-' if tp.sign == 1 else ''
        digit_string = f'{signstr}{digits[0]}.{mantissa}'
        return "%sE%d"%(digit_string, nexp)
    return str(remove_exponent(dec))

def format_number(n, digits=4):
    """Return a string representation of n with at most ``digits`` significative
    figures"""
    sig = significant_digits(n, digits)
    return write_in_adequate_representation(sig, -digits, digits)