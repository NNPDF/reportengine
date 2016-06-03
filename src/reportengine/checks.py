# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 11:40:20 2016

@author: Zahari Kassabov
"""
import functools

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