# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 15:31:29 2015

@author: Zahari Kassabov
"""
import inspect
import logging
import functools
import collections

import yaml

from reportengine import namespaces
from reportengine.utils import ChainMap
from reportengine.baseexceptions import ErrorWithAlternatives, AsInputError

log = logging.getLogger(__name__)

_config_token = 'parse_'

def trim_token(s):
    return s[len(_config_token):]


class ConfigError(ErrorWithAlternatives):
    pass


class BadInputType(ConfigError, TypeError):
    """Exception that happens when the user enters the wrong input type in the
    config"""
    def __init__(self, param, val, input_type):
        if isinstance(input_type, tuple):
            names = tuple(tp.__name__ for tp in input_type)
        else:
            names = input_type.__name__
        valtype = type(val).__name__
        msg = ("Bad input type for parameter '{param}': Value '{val}' "
               "is not of type {names}, but of type '{valtype}'.").format(**locals())
        super().__init__(msg)

class InputNotFoundError(ConfigError, KeyError):
    """Error when the input is not found in the config,"""
    alternatives_header = "Maybe you mistyped %s in one of the following keys?"

def element_of(paramname, elementname=None):
    """Append an elementname and a parentname attribute that will be used
    to generate parsers for lists and mappings of this function."""
    def inner(f):
        nonlocal elementname
        if elementname is None:
            if f.__name__.startswith(_config_token):
                elementname = trim_token(f.__name__)

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
            d = {k: self.trap_or_f(f,  v, f._elementname , **kwargs)
                 for k,v in param.items()}
            return namespaces.NSItemsDict(d, nskey=f._elementname)

        parse_func.__doc__ = "A mapping of %s objects." % f._elementname
    else:
        def parse_func(self, param:list, **kwargs):
            l = [self.trap_or_f(f, elem, f._elementname, **kwargs)
                 for elem in param]
            return namespaces.NSList(l, nskey=f._elementname)
        parse_func.__doc__ = "A list of %s objects." % f._elementname

    #We replicate the same signature for the kwarg parameters, so that we can
    #use that to build the graph.
    list_params = list(inspect.signature(parse_func).parameters.values())[0:2]
    kwarg_params = list(inspect.signature(f).parameters.values())[2:]
    params = [*list_params, *kwarg_params]
    parse_func.__signature__ = inspect.Signature(parameters=params)
    return parse_func

class ExplicitNode():
    def __init__(self, value):
        self.value = value

def explicit_node(f):
    @functools.wraps(f)
    def f_(*args, **kwargs):
        return ExplicitNode(f(*args,**kwargs))
    return f_


def _parse_func(f):
    """Check that the function has at least one argument, and check that the
    argument corresponds the type declared in the annotation if any."""

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
        newattrs = collections.OrderedDict()
        _list_keys = collections.OrderedDict()
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

        #We want to make respect the fact that attrs is an ordered dict
        #attrs = {**newattrs, **attrs}
        for k in newattrs:
            attrs[k] = newattrs[k]
        return super().__new__(cls, name, bases, attrs)

class AutoTypeCheck(type):
    """Apply automatically the _parse_func decorator
    to every parsing method fouds in the class."""
    def __new__(cls, name, bases, attrs):
        for k,v in attrs.items():
            if k.startswith(_config_token):
                attrs[k] = _parse_func(v)
        return super().__new__(cls, name, bases, attrs)

#Copied from python docs https://docs.python.org/3/reference/datamodel.html
class OrderedClass(type):
    @classmethod
    def __prepare__(metacls, name, bases, **kwds):
        return collections.OrderedDict()

    def __new__(cls, name, bases, namespace, **kwds):
        result = super().__new__(cls, name, bases, dict(namespace))
        if hasattr(result, 'members'):
            result.members = tuple(namespace) + result.members
        else:
            result.members = tuple(namespace)
        return result

class ConfigMetaClass(ElementOfResolver, AutoTypeCheck, OrderedClass):
    pass

class Config(metaclass=ConfigMetaClass):

    _traps = ['from_']

    def __init__(self, input_params, environment=None):
        if not isinstance(input_params, collections.Mapping):
            raise ConfigError("Failed to process the configuration. Expected "
            "the whole file to resolve to a mapping, but "
            "instead it is %s" % type(input_params))
        self.environment = environment
        self.input_params = input_params

        #self.params = self.process_params(input_params)

    @classmethod
    def get_all_parse_functions(cls):
        """Return all defined parse functions, as a dictionary:
        {parsed_element:function}"""
        return collections.OrderedDict((trim_token(k),getattr(cls,k))
                                       for k in cls.members
                                       if k.startswith(_config_token))



    def get_parse_func(self, param):
        """Return the function that is defined to parse `param` if it exists.
        Otherwise, return None."""
        func_name = _config_token + param
        try:
            return getattr(self, func_name)
        except AttributeError:
            return None

    def get_trap_func(self, input_val):
        """If the value has a special meaning that is trapped, return the
        function that handles it. Otherwise, return None"""
        if isinstance(input_val, dict) and len(input_val) == 1:
            k = next(iter(input_val))
            if k in self._traps:
                f = self.get_parse_func(k)
                return functools.partial(f, input_val[k])
        return None

    def explain_param(self, param_name):
        func = self.get_parse_func(param_name)

        if func is None:
            #TODO: Why not an exception instead of this?
            return None
        result = [func]

        sig = inspect.signature(func)
        for pname, param in list(sig.parameters.items())[1:]:
            if self.get_parse_func(pname):
                result.append(('config', pname, self.explain_param(pname)))
            else:
                result.append('unknown', param)
        return result



    def trap_or_f(self, f, value, elemname, **kwargs):
        """If the value is a trap, process it, based on the elementname.
        Otherwise just return the result of f(self, value, **kwargs)"""
        tf = self.get_trap_func(value)
        if tf:
            res = tf(elemname, write=False)
            return res[1]
        else:
            return f(self, value, **kwargs)


    def resolve_key(self, key, ns, input_params=None, parents=None,
                    max_index=None, write=True):
        """Get one key from the input params and put it in the namespace.
        It will be added to the outermost namespace that satisfies all the
        dependencies, but no more levels than `max_index`, if it's given.
        Parents controls the chain of resources that requested this parameter
        (mostly to display errors).
        `write` controls whether the resulting key is to be written to the
        namespace. It only applies to the requested parameter. All dependencies
        will be written to the namespace anyway.
        """


        if parents is None:
            parents = []
        if input_params is None:
            input_params = self.input_params

        #Sometimes we just need state, just let's try to not abuse it
        self._curr_key = key
        self._curr_ns = ns
        self._curr_input = input_params
        self._curr_parents = parents

        if max_index is None:
            max_index = len(ns.maps) -1


        nsindex = nsval = None
        finindex = finval = None
        if key in ns:
            ind, val = ns.get_where(key)
            if ind <= max_index:
                nsindex, nsval = ind, val
            finindex, finval = ind, val



        if not key in input_params:
            if finindex is not None:
                return finindex, finval
            msg = "A parameter is required: {key}.".format(key=key)
            if parents:
                msg += "\nThis is needed to process:\n"
                msg += '\ntrough:\n'.join(' - ' + str(p) for
                                          p in reversed(parents))
            #alternatives_text = "Note: The following similarly spelled "
            #                     "params exist in the input:"

            raise InputNotFoundError(msg, key, alternatives=input_params.keys())

        put_index = max_index
        input_val = input_params[key]

        trap_func = self.get_trap_func(input_val)
        if trap_func:
            #TODO: Think about this interface
            return trap_func(key)


        f = self.get_parse_func(key)
        if f:

            sig = inspect.signature(f)
            kwargs = {}
            for pname, param in list(sig.parameters.items())[1:]:
                try:
                    index, pval = self.resolve_key(pname,
                                                   ns,
                                                   input_params= input_params,
                                                   max_index=max_index,
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

            if nsindex is not None and nsindex <= put_index:
                return nsindex, nsval
            val = f(input_val, **kwargs)
        elif nsindex is not None:
            return nsindex, nsval
        else:
            #Recursively parse dicts
            if isinstance(input_val, dict):
                val = {}
                res_ns = ns.new_child(val)
                inputs = ChainMap(input_val, input_params)
                for k in input_val.keys():
                    self.resolve_key(k, res_ns, inputs,
                                     parents=[*parents, key],
                                     max_index = 0
                                    )
            #Recursively parse lists of dicts
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
        if write:
            #TODO: Need to fix this better
            if isinstance(val, ExplicitNode):
                ns[key]=val
            else:
                ns.maps[put_index][key] = val
        return put_index, val

    def process_fuzzyspec(self, fuzzy, ns, parents=None, initial_spec=None):
        if parents is None:
            parents = []
        gen = namespaces.expand_fuzzyspec_partial(ns, fuzzy, currspec=initial_spec)
        while True:
            try:
                key, currspec, currns = next(gen)
            except StopIteration as e:
                return e.value
            except TypeError as e:
                raise ConfigError("Error when processing namespace "
                "specification %s: %s" % (fuzzy, e))
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
                        "a mapping if present: %s" % k)
                    yield k, currspec, () ,tuple(args.items())
                elif isinstance(v, str):
                    yield v, currspec, (), ()
                else:
                    raise ConfigError("Unrecognized format for actions. "
                    "Must be a string or mapping, not '%s'" %v)
        else:
            raise ConfigError("Unrecognized format for actions")

    def parse_actions_(self, actions:list):
        """A list of action specifications. See documentation and examples for details."""
        allacts = [list(self._parse_actions_gen(act)) for act in actions]
        #Flatten
        return [act for acts in allacts for act in acts]



    #TODO: This interface is absolutely horrible, but we need to do a few
    #more examples (like 'zip_') to see how it generalizes.
    def parse_from_(self, value:str, element, write=True):
        """Take the key from the referenced element,
        which should be another input resource  and resolve as a dict."""

        ns = self._curr_ns
        input_params = self._curr_input
        parents = self._curr_parents
        if parents is None:
            parents = []
        parents = [*parents, element]



        nokey_message = ("Could retrieve element %s from namespace. "
                          "No such key" %
                              (element,))

        #Make sure key is loaded
        self.resolve_key(value, ns, input_params=input_params, parents=parents,)

        tip = ns[value]

        if hasattr(tip, 'as_input'):
            try:
                d = tip.as_input()
            except AsInputError as e:
                raise ConfigError("Could not process '%s' as input: %s" % (value, e)) from e
            try:
                ele_input = d[element]
            except KeyError as e:
                raise ConfigError(nokey_message) from e

            return self.resolve_key(element, ns,
                input_params=ChainMap({element:ele_input},input_params),
                parents=parents, write=write)
        elif isinstance(tip, dict):
            d = tip
            try:
                res  = d[element]
            except KeyError as e:
                raise ConfigError(nokey_message) from e
            if write:
                ns[element] = res
            return 0, res
        else:
            bad_message = ("Unrecognized value for from_: "
            "The value must resolve to a mapping or an object implementing "
            "as_input")
            raise ConfigError(bad_message)

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
