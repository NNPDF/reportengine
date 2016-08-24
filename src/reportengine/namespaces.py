# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 15:02:20 2016

@author: Zahari Kassabov
"""
from collections import UserList, UserDict, Sequence, Mapping

from reportengine.utils import ChainMap, ordinal

__all__ = ('AsNamespace', 'NSList', 'NSItemsDict', 'push_nslevel',
           'expand_fuzzyspec_partial', 'resolve',
           'value_from_spcec_ele')




class AsNamespace:
    def __init__(self, *args, nskey=None, **kwargs):
        self.nskey = nskey
        super().__init__(*args, **kwargs)

    def as_namespace(self):
        return self

    def nsitem(self, item):
        return self[item]

class NSList(AsNamespace, UserList):

    def as_namespace(self):
        return [{self.nskey: item} for item in self]

class NSItemsDict(AsNamespace, UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._nsdicts = {}

    def nsitem(self, item):
        return {self.nskey: self[item]}



class _namespaces: pass

def expand_fuzzyspec_partial(fuzzyspec, ns, currspec=None):
    if not isinstance(ns, ChainMap):
        ns = ChainMap(ns)

    if currspec is None:
        currspec = ()
    if not fuzzyspec:
        return (currspec,)

    ns = resolve(ns, currspec)

    results = []
    #ns = ChainMap(d)
    key, remainder = fuzzyspec[0], fuzzyspec[1:]
    if not key in ns:
        yield key, currspec, ns
    val = ns[key]
    if isinstance(val, Mapping):

        cs_ = (*currspec, key)

        ret = yield from expand_fuzzyspec_partial(remainder, ns, cs_)
        results += [r for r in ret]
    elif isinstance(val, Sequence):
        for i,val_ in enumerate(val):
            if not isinstance(val_, Mapping) and not hasattr(val, 'as_namespace'):
                raise TypeError("Cannot expand non-dict "
                                "list item '%s' (the %s item) of list %s." %
                                (val_, ordinal(i+1), val))
            cs_ = (*currspec, (key, i))

            ret = yield from expand_fuzzyspec_partial(remainder, ns, cs_)
            results += [r for r in ret]
    else:
        raise TypeError("In spec %s, namespace specification '%s' must resolve "
        "to a dict or a list of dicts, not %r." % (currspec,
                                                   key, type(val).__name__))
    return results


def push_nslevel(d, name, value=None):
    if value is None:
        value = {}

    d[name] = value


class ElementNotFound(KeyError): pass

def extract_nsval(ns, ele):

    #Whether the element comes from a shared dictionary that has to be updated
    old = False
    if isinstance(ele, tuple):
        name, index = ele
    else:
        name, index = ele, None

    try:
        if hasattr(ns, 'nsitem'):
            val = ns.nsitem(name)
        else:
            val = ns[name]
            old = True
    except KeyError as e:
        raise ElementNotFound(*e.args   ) from e
    if hasattr(val, 'as_namespace'):
        val = val.as_namespace()
        old = False
    if isinstance(val, Mapping):
        if index is not None:
            raise TypeError("Value %s is a dict, but a "
                "list index was specified" % name)
    elif isinstance(val, Sequence):
        if index is None:
            raise TypeError("Value %s is a list, but no "
            "list index was specified." % name)
        val = val[index]
        if not isinstance(val, Mapping):
            raise TypeError("Value %s in list %s must "
                "be a dictionary, not %s" % (val, ele, type(val)))
    else:
        raise TypeError("Value %s of type %s in %s is not expandable "
                            "as namespace" % (val, type(val), ns))
    if old:
        val = ChainMap({}, val)
    return val



def resolve_partial(ns, spec):
    if not isinstance(ns, ChainMap):
        ns = ChainMap(ns)
    if _namespaces not in ns:
        ns.maps[-1][_namespaces] = {}

    remainder = ()
    if not spec:
        return (), ns
    nsmap = ns[_namespaces]

    if spec in nsmap:
        return tuple(), nsmap[spec]


    for i  in range(len(spec)):

        currspec = spec[:i+1]
        if currspec in nsmap:
            ns = nsmap[currspec]
            continue
        ele = currspec[-1]
        try:
            val = extract_nsval(ns, ele)
        except ElementNotFound:
            #currspec and remainder overlap in one element
            remainder = spec[i:]
            break
        ns = ns.new_child(val)
        nsmap[currspec] = ns

    return remainder, ns


def resolve(d, spec):
    spec = tuple(spec)
    rem, ns = resolve_partial(d, spec)
    if rem:
        raise KeyError("The following parts cannot be expanded %s" % list(rem))
    assert(len(ns.maps) == len(spec) + 1)
    return ns

def value_from_spcec_ele(ns, ele):
    if isinstance(ele, tuple):
        name, index = ele
        return ns[name][index]
    else:
        return ns[ele]
