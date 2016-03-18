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