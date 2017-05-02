"""
resourcebuilder.py

Generate an execute a call graph based on Python function signatures.
"""

from collections import namedtuple
import logging

log = logging.getLogger(__name__)

#These represent the final actions we are interested in executiong.
Target = namedtuple('Target', ('name', 'nsspec'))
FuzzyTarget = namedtuple('FuzzyTarget', ('name', 'fuzzyspec', 'rootspec'))



def compiletime(f):
    f.compiletime = True
    return f

class CompileTime():
    pass

class Function():
    pass

class Collect():
    pass

def get_processor(obj, key):
    if hasattr(obj, 'get_processor'):
        return  obj.get_processor(key)
    if hasattr(obj, key):
        res = getattr(obj, key)
        if callable(res):
            if hasattr(res, 'compiletime'):
                return CompileTime(res)
            return Function(res)
    raise InputNotFound(key)

class ResourceBuilder:
    def __init__(self, providers):
        self.providers = providers

