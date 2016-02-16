# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 15:31:29 2015

@author: Zahari Kassabov
"""
import inspect
import difflib

import yaml

from reportengine.dag import DAG



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

def element_of(paramname):
    def inner(f):
        f._element_of = paramname
        return f
    return inner

def _make_element_of(f):
    def parse_func(self, param:list, **kwargs):
                return [f(self, elem, **kwargs) for elem in param]

    #We replicate the same signature for the kwarg parameters, so that we can
    #use that to build the graph.
    list_params = list(inspect.signature(parse_func).parameters.values())[0:2]
    kwarg_params = list(inspect.signature(f).parameters.values())[2:]
    params = [*list_params, *kwarg_params]
    parse_func.__signature__ = inspect.Signature(parameters=params)
    return parse_func

class ElementOfResolver(type):
    def __new__(cls, name, bases, attrs):
        newattrs = {}
        for attr, f in attrs.items():
            if hasattr(f, '_element_of'):
                newattr = 'check_' + f._element_of
                if newattr in attrs:
                    raise ValueError("Cannot construct {newattr} from "
                                     "'_element_of' {attr} because it is "
                                     "already declared.")

                newattrs[newattr] = _make_element_of(f)

        attrs = {**newattrs, **attrs}
        return super().__new__(cls, name, bases, attrs)


class Config(metaclass=ElementOfResolver):

    def __init__(self, input_params, environment=None):
        self.environment = environment
        self.input_params = input_params

        self.params = self.process_params(input_params)


    def get_parse_func(self, param):
        func_name = "check_" + param
        return getattr(self, func_name, None)

    def make_graph(self):
        g = DAG()
        for param in self.input_params:
            f = self.get_parse_func(param)
            reqs = set()
            if f:
                sig = inspect.signature(f)
                for p, spec in sig.parameters.items():
                    if spec.kind == inspect.Parameter.KEYWORD_ONLY:
                        reqs.add(p)
                        g.add_or_update_node(p)
            g.add_or_update_node(param, inputs=reqs)

        return g



    def process_params(self, input_params):
        params = {}
        g = self.make_graph()
        for node in g.topological_iter():
            param = node.value
            kwargs = {inp.value:params[inp.value] for inp in node.inputs}
            val = self.parse_param(param, input_params[param], **kwargs)
            params[param] = val
        return params

    def parse_param(self, param, val, **kwargs):

        parse_func = self.get_parse_func(param)
        if parse_func is None:
            return val

        sig = inspect.signature(parse_func)
        try:
            first_param = next(iter(sig.parameters.values()))
        except StopIteration:
            raise TypeError("Parser functiom must have one parameter: %s"
                            % parse_func.__qualname__)

        input_type = first_param.annotation
        if input_type is not sig.empty:
            if not isinstance(val, input_type):
                raise BadInputType(param, val, input_type)

        result = parse_func(val, **kwargs)
        return result

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
