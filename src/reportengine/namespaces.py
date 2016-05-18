# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 15:02:20 2016

@author: Zahari Kassabov
"""
from collections import deque, UserList, UserDict

from reportengine.utils import ChainMap

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

def extract_nsval(ns, item):
    if hasattr(ns, 'nsitem'):
        val = ns.nsitem(item)
    else:
        val = ns[item]
    if hasattr(val, 'as_namespace'):
        if '_namespaces' not in ns.maps[0]:
            ns['_namespaces'] = {}
        if item not in ns['_namespaces']:
            ns['_namespaces'][item] = val.as_namespace()
        val = ns['_namespaces'][item]
    return val

def push_nslevel(ns, name, value=None):
    """Append one namespace level"""
    if value is None:
        value = {}
    if '_namespaces' not in ns.maps[0]:
        ns['_namespaces'] = {}
    ns['_namespaces'][name] = value



def expand_fuzzyspec_partial(fuzzyspec, ns, currspec=None):
    if currspec is None:
        currspec = ()
    if not fuzzyspec:
        return (currspec,)

    results = []
    #ns = ChainMap(d)
    key, remainder = fuzzyspec[0], fuzzyspec[1:]
    if not key in ns:
        yield key, currspec, ns
    val = extract_nsval(ns, key)
    if isinstance(val, dict):
        ns = ns.new_child(val)
        cs_ = (*currspec, key)
        ret = yield from expand_fuzzyspec_partial(remainder, ns, cs_)
        results += [r for r in ret]
    elif isinstance(val, list):
        for i,val_ in enumerate(val):
            if not isinstance(val_, dict):
                raise TypeError("Cannot expand non-dict "
                                "list %s item of list %s" % (val_, val))
            cs_ = (*currspec, (key, i))
            ns_ = ns.new_child(val_)
            ret = yield from expand_fuzzyspec_partial(remainder, ns_, cs_)
            results += [r for r in ret]
    else:
        raise TypeError("In spec %s, namespace specification '%s' must resolve "
        "to a dict or a list of dicts, not %r." % (currspec,
                                                   key, type(val).__name__))
    return results


def resolve_partial(d, spec):
    remainder = deque(spec)

    #parts = deque([d])
    res = ChainMap(d)


    while remainder:
        ele = remainder[0]
        if isinstance(ele, tuple):
            name, index = ele
        else:
            name, index = ele, None

        if '_namespaces' in d:
            d = ChainMap(d['_namespaces'], d)

        if name in d:
            val = extract_nsval(d, name)
            if isinstance(val, dict):
                if index is not None:
                    raise TypeError("Value %s is a dict, but a "
                    "list index was specified" % name)
                res = res.new_child(val)
                remainder.popleft()
            elif isinstance(val, list):
                if index is None:
                    raise TypeError("Value %s is a list, but no "
                    "list index was specified." % name)
                val = val[index]
                if hasattr(val, 'as_namespace'):
                    if '_namespaces' in d:
                        d['_namespaces'] = {}
                    if not name in d['_namespaces']:
                        d['_namespcaces']['name'] = val.as_namespace()
                    val = d['_namespcaces']['name']
                if isinstance(val, dict):
                    res = res.new_child(val)
                    remainder.popleft()
                else:
                    raise TypeError("Value %s in list %s must "
                    "be a dictionary, not %s" % (val, ele, type(val)))
            else:
                raise TypeError("Value %s in %s is not expandable "
                                "as namespace" % (val, d))
            d = res
        else:
            break
    return(remainder, res)

def resolve(d, spec):
    rem, ns = resolve_partial(d, spec)
    if rem:
        raise KeyError("The following parts cannot be expanded %s" % list(rem))
    return ns

def value_from_spcec_ele(ns, ele):
    if isinstance(ele, tuple):
        name, index = ele
        return ns[name][index]
    else:
        return ns[ele]
