"""
inputcache.py

Saves and retrieves parsed data for providers.
"""

import pickle

from attr import attributes, attr

@attributes(hash=False)
class Frozen:
    value = attr()
    def __hash__(self):
        return hash(pickle.dumps(self.value))

def freeze(ele):
    try:
        hash(ele)
    except TypeError:
        return Frozen(ele)
    else:
        return ele

def unfreeze(ele):
    if isinstance(ele, Frozen):
        return ele.value
    return ele

class Cache:
    def __init__(self):
        self._d = {}

    def _freezeargs(self, args):
        return tuple((k,freeze(v)) for k,v in args.items())

    def _unfreeze_args(self, args):
        return {k : unfreeze(v) for k,v in args.items()}

    def register(self, key, args, value):
        self._d[(key, self._freezeargs(args))] = value

    def retrieve(self, key, args):
        return self._d[(key, self._freezeargs(args))]

    def __contains__(self, item):
        key, args = item
        return (key, self._freezeargs(args)) in self._d

    def __getitem__(self, item):
        key,args = item
        return self.retrieve(key,args)

    def __setitem__(self, item, value):
        key,args = item
        self.register(key,args,value)
