# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 15:31:29 2015

@author: Zahari Kassabov
"""
import inspect
import difflib
import logging
import functools
import collections

import yaml

from reportengine.dag import DAG

log = logging.getLogger(__name__)

_config_token = 'check_'

class AsNamespace:
    def __init__(self, *args, nskey=None, **kwargs):
        self.nskey = nskey
        super().__init__(*args, **kwargs)

    def as_namespace(self):
        return self

    def nsitem(self, item):
        return self[item]

class NSList(AsNamespace, collections.UserList):

    def as_namespace(self):
        return [{self.nskey: item} for item in self]

class NSItemsDict(AsNamespace, collections.UserDict):
    def nsitem(self, item):
        return {self.nskey: self[item]}


class ConfigError(Exception):

    def __init__(self, message, bad_item = None, alternatives = None, *,
                 display_alternatives='best'):
        super().__init__(message)
        self.bad_item = bad_item
        self.alternatives = alternatives
        self.display_alternatives = display_alternatives

    def alternatives_text(self):
        if (self.display_alternatives=='none' or not self.display_alternatives
            or not self.alternatives):
            return ''
        if self.display_alternatives == 'best':
            alternatives = difflib.get_close_matches(self.bad_item,
                                                     self.alternatives)
        elif self.display_alternatives == 'all':
            alternatives = self.alternatives
        else:
            raise ValueError("Unrecognized display_alternatives option. "
            "Must be one of: 'all', 'best' or 'none'.")
        if not alternatives:
            return ''
        head = ("Instead of '%s', did you mean one of the following?\n"
                % (self.bad_item,))
        txts = [' - {}'.format(alt) for alt in alternatives]
        return '\n'.join((head, *txts))


class BadInputType(ConfigError, TypeError):
    def __init__(self, param, val, input_type):
        msg = ("Bad input type for parameter '{param}': Value '{val}' "
               "is not of type {input_type}.").format(**locals())
        super().__init__(msg)

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
            return NSItemsDict(d, nskey=f._elementname)
    else:
        def parse_func(self, param:list, **kwargs):
            l = [f(self, elem, **kwargs) for elem in param]
            return NSList(l, nskey=f._elementname)

    #We replicate the same signature for the kwarg parameters, so that we can
    #use that to build the graph.
    list_params = list(inspect.signature(parse_func).parameters.values())[0:2]
    kwarg_params = list(inspect.signature(f).parameters.values())[2:]
    params = [*list_params, *kwarg_params]
    parse_func.__signature__ = inspect.Signature(parameters=params)
    return parse_func


def _parse_func(f):

    sig = inspect.signature(f)

    try:
        first_param = list(sig.parameters.values())[1]
    except IndexError:
        raise TypeError(("Parser functiom must have at least one "
                        "parameter: %s")
                        % f.__qualname__)

    input_type = first_param.annotation

    @functools.wraps(f)
    def _f(self, val, **kwargs):

        if input_type is not sig.empty:
            if not isinstance(val, input_type):
                raise BadInputType(f.__name__, val, input_type)


        return f(self, val, **kwargs)

    return _f

class ElementOfResolver(type):
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

        self.params = self.process_params(input_params)

    def get_parse_func(self, param):
        func_name = _config_token + param
        try:
            return getattr(self, func_name)
        except AttributeError:
            return lambda x : x

    def make_graph(self, params):
        g = DAG()
        for param in params:
            f = self.get_parse_func(param)
            reqs = set()
            if f:
                sig = inspect.signature(f)
                for p, spec in list(sig.parameters.items())[1:]:
                    reqs.add(p)
                    g.add_or_update_node(p)
            g.add_or_update_node(param, inputs=reqs)
        return g

    def process_params(self, input_params=None):
        if input_params is None:
            input_params = self.input_params
        params = {}
        g = self.make_graph(input_params)
        for node in g.topological_iter():
            param = node.value
            parse_func = self.get_parse_func(param)

            sig = inspect.signature(parse_func)

            kwargs = {}
            for inpnode in node.inputs:
                inp = inpnode.value
                if inp in params:
                    kwargs[inp] = params[inp]
                elif sig.parameters[inp].default is not sig.empty:
                    kwargs[inp] = sig.parameters[inp].default
                else:
                    raise ConfigError("An input is required to "
                    "process resource '%s': '%s'" % (param, inp))

            try:
                inval = input_params[param]
            except KeyError:

                if node.outputs:
                    continue #Raise the exception later on, to see who
                             #required this, and because there migh be defaults
                raise #This should not be reached
            val = parse_func(inval, **kwargs)
            params[param] = val
        return params


    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, item, value):
        self.params[item] = value

    def __iter__(self):
        return iter(self.params)

    def __len__(self):
        return len(self.params)

    def __contains__(self, item):
        return item in self.params

    @classmethod
    def from_yaml(cls, o, environment=None):
        try:
            return cls(yaml.load(o), environment=environment)
        except yaml.error.YAMLError as e:
            raise ConfigError("Failed to parse yaml file: %s" % e)
