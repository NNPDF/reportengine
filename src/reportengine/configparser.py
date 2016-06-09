# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 15:31:29 2015

@author: Zahari Kassabov
"""
import inspect
import logging
import functools

import yaml

from reportengine import namespaces
from reportengine.utils import ChainMap
from reportengine.baseexceptions import ErrorWithAlternatives

log = logging.getLogger(__name__)

_config_token = 'parse_'


class ConfigError(ErrorWithAlternatives):
    pass


class BadInputType(ConfigError, TypeError):
    def __init__(self, param, val, input_type):
        msg = ("Bad input type for parameter '{param}': Value '{val}' "
               "is not of type {input_type}.").format(**locals())
        super().__init__(msg)

class InputNotFoundError(ConfigError, KeyError):
    alternatives_header = "Maybe you mistyped %s in one of the following keys?"

def element_of(paramname, elementname=None):
    def inner(f):
        nonlocal elementname
        if elementname is None:
            if f.__name__.startswith(_config_token):
                elementname = f.__name__[len(_config_token):]

        f._element_of = paramname
        f._elementname = elementname
        return f
    return inner

def named_element_of(paramname, elementname=None):
    def inner(f):
        element_of(paramname, elementname)(f)
        f._named = True
        return f
    return inner

def _make_element_of(f):
    if getattr(f, '_named', False):
        def parse_func(self, param:dict, **kwargs):
            d = {k: f(self,  v , **kwargs) for k,v in param.items()}
            return namespaces.NSItemsDict(d, nskey=f._elementname)

        parse_func.__doc__ = "A list of %s objects." % f._elementname
    else:
        def parse_func(self, param:list, **kwargs):
            l = [f(self, elem, **kwargs) for elem in param]
            return namespaces.NSList(l, nskey=f._elementname)
        parse_func.__doc__ = "A mapping of %s objects" % f._elementname

    #We replicate the same signature for the kwarg parameters, so that we can
    #use that to build the graph.
    list_params = list(inspect.signature(parse_func).parameters.values())[0:2]
    kwarg_params = list(inspect.signature(f).parameters.values())[2:]
    params = [*list_params, *kwarg_params]
    parse_func.__signature__ = inspect.Signature(parameters=params)
    return parse_func


def _parse_func(f):
    """Check that the function has at least one argument, and check that the
    argument corresponds the type declared in the annotation id any."""

    sig = inspect.signature(f)

    try:
        first_param = list(sig.parameters.values())[1]
    except IndexError:
        raise TypeError(("Parser functiom must have at least one "
                        "parameter: %s")
                        % f.__qualname__)

    input_type = first_param.annotation

    @functools.wraps(f)
    def f_(self, val, *args, **kwargs):

        if input_type is not sig.empty:
            if not isinstance(val, input_type):
                raise BadInputType(f.__name__, val, input_type)


        return f(self, val, *args, **kwargs)

    return f_

class ElementOfResolver(type):
    """Generate a parsing function for collections of each 'atomic' parsing
    function found in the class, and marked with the relevant decorator."""
    def __new__(cls, name, bases, attrs):
        newattrs = {}
        _list_keys = {}
        for attr, f in attrs.items():
            if hasattr(f, '_element_of'):
                newattr = _config_token + f._element_of
                if newattr in attrs:
                    raise ValueError("Cannot construct {newattr} from "
                                     "'_element_of' {attr} because it is "
                                     "already declared.")

                #We have to apply parse func in here as well.
                newattrs[newattr] = _make_element_of(_parse_func(f))
                _list_keys[f._element_of] = f._elementname

        newattrs['_list_keys'] = _list_keys

        attrs = {**newattrs, **attrs}
        return super().__new__(cls, name, bases, attrs)

class AutoTypeCheck(type):
    """Apply automatically the _parse_func decorator
    to every parsing method fouds in the class."""
    def __new__(cls, name, bases, attrs):
        for k,v in attrs.items():
            if k.startswith(_config_token):
                attrs[k] = _parse_func(v)
        return super().__new__(cls, name, bases, attrs)

class ConfigMetaClass(ElementOfResolver, AutoTypeCheck):
    pass

class Config(metaclass=ConfigMetaClass):

    def __init__(self, input_params, environment=None):
        self.environment = environment
        self.input_params = input_params

        #self.params = self.process_params(input_params)


    def get_parse_func(self, param):
        func_name = _config_token + param
        try:
            return getattr(self, func_name)
        except AttributeError:
            return None

    def resolve_key(self, key, ns, input_params=None, parents=None,
                    max_index=None):
        if key in ns:
            return ns.get_where(key)
        if parents is None:
            parents = []
        if input_params is None:
            input_params = self.input_params
        if not key in input_params:
            msg = "A parameter is required: {key}.".format(key=key)
            if parents:
                msg += "\nThis is needed to process:\n"
                msg += '\ntrough:\n'.join(' - ' + str(p) for
                                          p in reversed(parents))
            #alternatives_text = "Note: The following similarly spelled "
            #                     "params exist in the input:"
            raise InputNotFoundError(msg, key, alternatives=input_params.keys())
        if max_index is None:
            max_index = len(ns.maps) -1
        put_index = max_index
        input_val = input_params[key]
        f = self.get_parse_func(key)
        if f:

            sig = inspect.signature(f)
            kwargs = {}
            for pname, param in list(sig.parameters.items())[1:]:
                if pname in ns:
                    index, pval = ns.get_where(pname)
                else:
                    try:
                        index, pval = self.resolve_key(pname,
                                                       ns,
                                                       parents=[*parents, key])
                    except KeyError:
                        if param.default is not sig.empty:
                            pval = param.default
                            index = max_index
                        else:
                            raise

                if index < put_index:
                    put_index = index

                kwargs[pname] = pval

            val = f(input_val, **kwargs)
        else:
            if isinstance(input_val, dict):
                val = {}
                res_ns = ns.new_child(val)
                inputs = ChainMap(input_val, input_params)
                for k in input_val.keys():
                    self.resolve_key(k, res_ns, inputs,
                                     parents=[*parents, key],
                                     max_index = 0
                                    )
            elif (isinstance(input_val, list) and
                 all(isinstance(x, dict) for x in input_val)):
                val = []
                for linp in input_val:
                    lval = {}
                    res_ns = ns.new_child(lval)
                    inputs = ChainMap(linp, input_params)
                    for k in linp.keys():
                        self.resolve_key(k, res_ns, inputs,
                                         parents=[*parents, key],
                                         max_index = 0
                                        )
                    val.append(lval)


            else:
                val = input_val

        ns.maps[put_index][key] = val
        return put_index, val

    def process_fuzzyspec(self, fuzzy, ns, parents=None):
        if not parents:
            parents = []
        gen = namespaces.expand_fuzzyspec_partial(fuzzy, ns)
        while True:
            try:
                key, currspec, currns = next(gen)
            except StopIteration as e:
                return e.value
            else:
                self.resolve_key(key, currns, parents=[*parents, currspec])

    def process_all_params(self, input_params=None, *,ns=None):
        """Simple shortcut to process all paams in a simple namespace, if
        possible."""
        if input_params is None:
            input_params = self.input_params

        if ns is None:
            ns = ChainMap()
        for param in input_params:
            if param not in ns:
                self.resolve_key(param, ns, input_params=input_params)
        return ns

    def _parse_actions_gen(self, actions, currspec=()):
        if isinstance(actions, dict):
            for k,v in actions.items():
                yield from self._parse_actions_gen(v, (*currspec, k))
        elif isinstance(actions, list):
            for v in actions:
                if isinstance(v, dict):
                    if len(v) != 1:
                        raise ConfigError(("Invalid action specification %s. "
                        "Must be a scalar or a mapping with exactly one key") % v)
                    k = next(iter(v.keys()))
                    args = v[k]
                    if not isinstance(args, dict):
                        raise ConfigError("Action arguments must be "
                        "a mapping if present" % k)
                    yield k, currspec, tuple(args.items())
                elif isinstance(v, str):
                    yield v, currspec, ()
                else:
                    raise ConfigError("Unrecognized format for actions. "
                    "Must be a string or mapping, not '%s'" %v)
        else:
            raise ConfigError("Unrecognized format for actions")

    def parse_actions_(self, actions:list):
        allacts = [list(self._parse_actions_gen(act)) for act in actions]
        #Flatten
        return [act for acts in allacts for act in acts]





    def __getitem__(self, item):
        return self.input_params[item]

    def __iter__(self):
        return iter(self.input_params)

    def __len__(self):
        return len(self.input_params)

    def __contains__(self, item):
        return item in self.input_params

    @classmethod
    def from_yaml(cls, o, *args, **kwargs):
        try:
            return cls(yaml.load(o), *args, **kwargs)
        except yaml.error.YAMLError as e:
            raise ConfigError("Failed to parse yaml file: %s" % e)
