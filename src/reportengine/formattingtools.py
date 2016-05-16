# -*- coding: utf-8 -*-
"""
Nice formatting strings from namespace elements, to be used as path names.

Created on Mon May 16 12:48:20 2016

@author: Zahari Kassabov
"""
import re
import logging

from reportengine import namespaces

log = logging.getLogger(__name__)

def normalize_name(name):
    """Remove characters that don't go well in a filename.
    That is, everything non alphanumerical, except from '_' and '-'."""
    return re.sub(r'[^\w_-]', '', str(name))


def get_nice_name(ns, nsspec, suffix=None):
    """Get a name by quering the parts of a namespace specification.
    ``ns`` should be a namespace ChainMap and ``nsspec`` a
    tuple with a valid specification
    (see the ``namespaces`` documentation for more details)"""
    parts = []
    currspec = []
    currns = ns
    for ele in nsspec:
        currspec.append(ele)
        val = namespaces.value_from_spcec_ele(currns, ele)
        try:
            val = str(val)
        except Exception as e:
            log.debug("Could not convert a value (%r) to string: %s" %
                      (val, e))
            val = str(ele)

        #kind of ugly, but we don't want to dumpt compound types, and too long
        #filenames
        if isinstance(val, (list, dict,set,tuple,frozenset)) or len(val) > 25:
            val = str(ele)

        parts.append(normalize_name(val))

        currns = namespaces.resolve(ns, currspec)

    if suffix:
        parts.append(suffix)

    return '_'.join(parts)

