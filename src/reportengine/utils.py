import functools
import collections
import pickle
import inspect

class comparepartial(functools.partial):
    def __eq__(self, other):
        return (isinstance(other, type(self)) and
                self.func == other.func and self.args == other.args and
                self.keywords == other.keywords
               )

    def __hash__(self):
        return hash(pickle.dumps(self))

class ChainMap(collections.ChainMap):
    def get_where(self, key):
        for i, mapping in enumerate(self.maps):
            try:
                return i, mapping[key]             # can't use 'key in mapping' with defaultdict
            except KeyError:
                pass
        return self.__missing__(key)            # support subclasses that define __missing__

def get_functions(obj):
    """Get the list of members of the object that are functions,
    as an OrderedDict"""
    return collections.OrderedDict(inspect.getmembers(obj, inspect.isfunction))

def get_providers(obj):
    """Return the objects that are likely to make sense as providers.
    This is stricter than what resourceengine uses internally."""
    functions = get_functions(obj)

    def predicate(k,v):
        if hasattr(obj, '__all__'):
            if not k in obj.__all__:
                return False

        return ((not k.startswith('_')) and #hide hidden functions
                inspect.getmodule(v) == obj #require that they are defined in that module
                )

    return collections.OrderedDict((k,v) for k,v in functions.items() if
               predicate(k,v))


def ordinal(n):
    """Return an ordinal string for the integer n"""
    residual = n % 10
    teenth = 10 < n % 100 < 20
    if teenth or not residual or residual > 3:
        suffix = 'th'
    else:
        suffix = ('st', 'nd', 'rd')[residual - 1]
    return '%d%s' % (n,suffix)