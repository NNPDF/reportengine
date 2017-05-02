from string import printable, ascii_letters

from hypothesis import given
from hypothesis.strategies import (recursive, none, booleans, floats, text,
    lists, dictionaries)

from reportengine import inputcache


json = recursive(none() | booleans() | floats() | text(printable),
    lambda children: lists(children) | dictionaries(text(printable), children))

args = dictionaries(text(printable), json)

c = inputcache.Cache()

@given(text(ascii_letters), args, floats(allow_nan=False))
def test_register(key, args, value):
    c[key, args] = value
    assert (key, args) in c
    assert c[key, args] == value
