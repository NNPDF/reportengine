# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 11:40:20 2016

@author: Zahari Kassabov
"""
import functools

from reportengine.utils import saturate
from reportengine.baseexceptions import ErrorWithAlternatives

class CheckError(ErrorWithAlternatives):pass

def add_check(f, check):
    if not hasattr(f, 'checks'):
        f.checks = [check]
    else:
        f.checks.append(check)


def require_one(*args):
    """Ensure that at least one argument is not None."""
    @make_check
    def check(callspec, ns, graph, **kwargs):
        s = set(args)
        in_input_specs = {node.value.resultname for node in graph[callspec].inputs}
        in_ns = {k for k in s if ns.get(k, None) is not None}


        if not (s & (in_ns | in_input_specs)):
            raise CheckError("You need to supply at least one of: %s" % (args,))

    return check

def remove_outer(*args):
    """Set to None all but the innermost values for *args that are not None"""
    @make_check
    def check(ns,**kwargs):
        min_index = len(ns.maps)
        indexes = []
        for arg in args:
            index, val = ns.get_where(arg)
            if val is not None and index < min_index:
                min_index = index
            indexes.append(index)
        for i,arg in zip(indexes, args):
            if i > min_index:
                ns[arg] = None

    return check

def check_positive(var):
    """Ensure that `var` is positive"""
    @make_check
    def check(ns, **kwargs):
        val = ns[var]
        if not val>0:
            raise CheckError(f"'{var}' must be positive, but it is {val!r}.")
    return check


def check_not_empty(var):
    """Ensure that the string ``var`` corresponds to a non empty value in
    the namespace"""
    @make_check
    def check(callspec, ns, graph, **kwargs):
        val = ns[var]
        #Don't just "if val" because we don't know if it's some crazy collection
        if len(val) == 0:
            raise CheckError("'%s' cannot be empty." % var)

    return check

def make_check(check_func):
    @functools.wraps(check_func)
    def decorator(f):
        add_check(f, check_func)
        return f

    return decorator

def make_argcheck(check_func):
    @functools.wraps(check_func)
    @make_check
    def check(ns, *args, **kwargs):
        res = saturate(check_func, ns)
        if res is not None:
            ns.update(res)

    return check