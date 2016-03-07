# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 21:18:06 2015

@author: zah
"""

from collections import namedtuple, deque
from concurrent.futures import ProcessPoolExecutor
import itertools
import asyncio
import logging
import inspect
import enum
import functools
import copy

from reportengine import dag
from reportengine import namespaces
from reportengine.utils import comparepartial, ChainMap

log = logging.getLogger(__name__)

RESOURCE = "resource"
PROVIDER = "provider"

class provider:
    """Decorator intended to be used for the functions that are to
    be exposed as providers, either directly or trough more specialized
    decorators in reportengine."""
    def __init__(self, f):
        functools.update_wrapper(self, f)
        self.f = f

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)



class ExecModes(enum.Enum):
    SET_UNIQUE = 'set_unique'
    SET_OR_UPDATE = "set_or_update"
    APPEND_UNORDERED = 'append_to'

CallSpec = namedtuple('CallSpec', ('function', 'kwargs', 'resultname',
                                  'execmode','nsspec'))
#TODO; Improve namespace spec
def print_callspec(spec, nsname = None):

    if nsname is None:
        res = spec.resultname
    else:
        res = "nsname[{!r}]".format(spec.resultname)
    callargs = ', '.join("%s=%s"% (kw, kw) for kw in spec.kwargs)
    try:
        f = spec.function.__qualname__

    #functools.partial annoyingly doesn't wrap
    except AttributeError:
        f = spec.function.func.__qualname__
        callargs += ", " + ", ".join("%s=%s" % (kw,val) for
                                     kw,val in spec.function.keywords.items())

    if spec.execmode in (ExecModes.SET_OR_UPDATE, ExecModes.SET_UNIQUE):
        return "{res} = {f}({callargs})".format(res=res,
                                        f=f,
                                        callargs=callargs)
    elif spec.execmode == ExecModes.APPEND_UNORDERED:
        return "{res}.append({f}({callargs}))".format(res=res,
                                        f=f,
                                        callargs=callargs)

CallSpec.__str__ = print_callspec

class NSResolver():

    def __init__(self, rootdict):
        self.rootdict = rootdict
    
    @functools.lru_cache()
    def resolve(self, spec, parent=None):
        if parent is None:
            parent = self.rootdict
        nss = deque([parent])
        for elem in spec:
            if isinstance(elem, tuple):
                name, index = elem
                if not name in parent:
                    raise KeyError("Element %s in spec %s is invalid"%(name,
                                                                       spec))
                item = parent[name]
                if not isinstance(item, list):
                    raise TypeError("In spec %s, %s must be a list" % (spec,
                                                                       name))
                item = item[index]
                parent = item
            else:
                name = elem
                if not elem in parent:
                    raise KeyError("Element %s in spec %s is invalid"%(
                                             name,
                                             spec))
                item = parent[elem]

            if not isinstance(item, dict):
                raise TypeError("Element must be a dict")
            nss.appendleft(item)
            parent = item
        return ChainMap(*nss)

    def span_specs(self, levels):
        parent = self.rootdict
        result_parts = []
        for depth, level in enumerate(levels):
            if isinstance(level, tuple):
                name, index = level
                item = parent[name]
                if not isinstance(item, list):
                    raise TypeError("In spec %s, %s must be  list."
                                     %(levels, name))
                item = item[index]
                result_parts.append(level)
            else:
                name = level
                item = parent[name]
                if isinstance(item, list):
                    #Beware of late variable binding
                    def capture_gen(name):
                        return ((name, i) for i in range(len(item)))
                    result_parts.append(capture_gen(name))

                    #Maybe better to just remove this code block
                    #and check in resolve
                    if depth < len(levels) - 1:
                        next_item = levels[depth+1]
                        if isinstance(next_item, tuple):
                            next_name = next_item[0]
                        else:
                            next_name = next_item
                        try:
                            s = set(type(el[next_name]) for el in item)
                        except KeyError:
                            raise KeyError("%s is is required for all "
                            "instances of %s" % (next_name, name))
                        #Treat the len 0 case later
                        if len(s) > 1:
                            raise TypeError("For spec %s all elements of %s "
                            "must be of the same type" % (levels, name))

                    #FIXME: This only checks the first element from now on.
                    item = item[0]
                elif isinstance(item, dict):
                    result_parts.append((name,))
                else:
                    raise TypeError("Spec items %s must be a dict or a list" %
                                    (name,))
            parent = item
        return itertools.product(*result_parts)

class ResourceExecutor():

    def __init__(self, graph, rootns):
        self.graph = graph
        self.rootns = rootns


    def execute_sequential(self):
        for node in self.graph:
            function, kwargs, resultname, mode, nsspec = spec = node.value
            namespace = namespaces.resolve(self.rootns, nsspec)
            kwdict = {kw: namespace[kw] for kw in kwargs}
            result = self.get_result(function, **kwdict)
            self.set_result(result, spec)

    #This needs to be a staticmethod, because otherwise we have to serialize
    #the whole self object when passing to multiprocessing.
    @staticmethod
    def get_result(function, **kwdict):
        return function(**kwdict)

    def set_result(self, result, spec):
        function, kwargs, resultname, execmode, nsspec = spec
        namespace = namespaces.resolve(self.rootns, nsspec)
        if not execmode in ExecModes:
            raise TypeError("Callspecmode must be an ExecMode")
        if execmode == ExecModes.SET_UNIQUE:
            if resultname in namespace:
                raise ValueError("Resource already set: %s" % resultname)
            namespace[resultname] = result
        elif execmode == ExecModes.SET_OR_UPDATE:
            namespace[resultname] = result
        elif execmode == ExecModes.APPEND_UNORDERED:
            if not resultname in namespace:
                namespace[resultname] = []
            namespace[resultname].append(result)
        else:
            raise NotImplementedError(execmode)

    async def submit_next_specs(self, loop, executor, next_specs, deps):
        tasks = []
        for spec in next_specs:
            namespace = namespaces.resolve(self.rootns, spec.nsspec)
            kwdict = {kw: namespace[kw] for kw in spec.kwargs}
            clause = comparepartial(self.get_result, spec.function, **kwdict)
            future = loop.run_in_executor(executor, clause)


            spec_done = self._spec_done(future=future,
                               loop=loop, executor=executor,
                               spec=spec, deps=deps)

            task = loop.create_task(spec_done)
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def _spec_done(self, future, loop, executor, spec, deps):
        result = await future
        self.set_result(result, spec)
        try:
            next_specs = deps.send(spec)
        except StopIteration:
            pass
        else:
             await self.submit_next_specs(loop, executor, next_specs, deps)

    def execute_parallel(self, executor=None, loop=None):

        if executor is None:
            executor = ProcessPoolExecutor()
            shut_executor = True
        else:
            shut_executor = False

        if loop is None:
            loop = asyncio.get_event_loop()

        deps = self.graph.dependency_resolver()
        next_specs = deps.send(None)


        task = loop.create_task(self.submit_next_specs(loop, executor,
                                                    next_specs, deps))
        loop.run_until_complete(task)

        if shut_executor:
            executor.shutdown()

    def __str__(self):
        return "\n".join(print_callspec(node.value) for node in self.graph)



class ResourceError(Exception):pass

class ResourceNotUnderstood(ResourceError, TypeError): pass

class ResourceNotFound(ResourceError):
    def __init__(self, res_name, required_by=None):
        self.res_name = res_name
        self.required_by = required_by
        if required_by is not None:
            msg = ("Resource %s, which is required to compute %s, "
            "cannot be found nor computed from a provider") % (res_name,
                                                               required_by)
        else:
            msg = ("Resource %s cannot be found nor computed from a provider."
                   % res_name)
        super().__init__(msg)


Target = namedtuple('Target', ('name', 'nsspec', 'extraargs'))

EMPTY = inspect.Signature.empty

class ResourceBuilderX(ResourceExecutor):
    
    def __init__(self, input_parser, providers, targets):
        
        self.input_parser = input_parser        
        self.providers = providers
        self.targets = targets
        
        self.rootns = ChainMap()
        self.graph = dag.DAG()
    
    def resolve_targets(self):
        for target in self.targets:
            self.resolve_target(target)
    
    def resolve_target(self, target):
        name, fuzzy, extra_args = target
        specs = self.input_parser.process_fuzzyspec(fuzzy, 
                                                self.rootns, parents=[name])
        print("The specs are %s" % specs)
        for spec in specs:
            self.process_requirement(name, spec, extra_args)
    
    def process_requirement(self, name, nsspec, extraargs=None, required_by=None, 
                            default=EMPTY):
        
        print(nsspec)
        ns = namespaces.resolve(self.rootns, nsspec)
        if extraargs is None:
            extraargs = ()
        try:
            self.input_parser.resolve_key(name, ns, parents=required_by)
        except KeyError as e:
            if hasattr(self.providers, name):
                f = getattr(self.providers, name)
                s = inspect.signature(f)
                if(extraargs):
                    ns.update(dict(extraargs))
                cs = CallSpec(f, tuple(s.parameters.keys()), name, ExecModes.SET_UNIQUE, 
                              nsspec)
                self.graph.add_or_update_node(cs)
                for param_name, param in s.parameters.items():
                    self.process_requirement(param_name, nsspec, None, 
                                             required_by=cs, 
                                             default=param.default)
                print(cs)
                if required_by is None:
                    outputs = set()
                else:
                    outputs = set([required_by])
                self.graph.add_or_update_node(cs, outputs=outputs)
            else:
                if default is EMPTY:
                    raise e
                else:
                    ns[name] = default
        else:
            if extraargs:
                raise ResourceNotUnderstood("The resource %s name is "
                "already present in the input, but some arguments were "
                "passed to compute it: %s" % (name, extraargs))
        
        
            
 

        
    
class ResourceBuilder(ResourceExecutor):

    def __init__(self, providers, targets, nsresolver, resource_parser=None):

        self.providers = providers
        self.targets = targets
        self.nsresolver = nsresolver
        self.resource_parser = resource_parser

    #To be extended
    def find_provider(self, name):
        return getattr(self.providers, name)

    def find_resource_or_provider(self, resource, required_by):

        name, nsspec, extra_args = resource
        namespace = self.nsresolver.resolve(nsspec)


        index = len(namespace.maps) - 1
        if name in namespace:
            index, resource = namespace.get_where(name)

            if hasattr(self.providers, name):
                if extra_args is not None:
                    raise ResourceError("Provider %s "
                                        "is being overwritten by value %s, "
                                        "with")
                log.warn("Provider %s is being overwritten by value %s." %
                             (name, resource))

            #TODO: Less ugly control flow?
            provider = None
            if (self.resource_parser):
                func = self.resource_parser.get_parse_func(name)
                if func:
                    #Make sure whatever we are parsing is unique
                    #(to keep the node hashable)
                    provider = comparepartial(func, copy.deepcopy(resource))

            if not provider:
                return (RESOURCE, resource, index)
        else:
            try:
                provider = self.find_provider(name)
            except AttributeError:
                raise ResourceNotFound(name, required_by=required_by)

        try:
            signature = inspect.signature(provider)
        except TypeError:
            raise ResourceNotUnderstood("%s must be callable." % func)

        if extra_args is not None:
            try:
                param_spec = signature.bind_partial(**extra_args)
            except TypeError:
                raise ResourceNotUnderstood("Unexpected parameters "
                "for provider %s: %s. \nThe parameters of this function are: "
                "%s" %
                (provider.__qualname__, extra_args, signature))
            provider = comparepartial(provider, *param_spec.args,
                                      **param_spec.kwargs)



        return (PROVIDER, provider, index)


    def process_requirement(self, req_spec, required_by=None):

        requirement = self.find_resource_or_provider(req_spec, required_by)
        req_type, req_val = requirement
        if req_type == RESOURCE:
            return
        ...


    def build_graph(self):
        self.graph = dag.DAG()
        for target in self.targets:
            self.process_requirement(target)


class ResourceBuilder(ResourceExecutor):

    def __init__(self, providers, targets, namespace):
        self.namespace = namespace
        self.targets = targets
        self.providers = providers



    def find_resource_or_provider(self, resource, required_by=None):
        """Find a resource in the namespace or else a provider in
        the providers.

        This function does **not** depend on ``required_by``
        except because it's
        used to produce a nice error message."""


        if isinstance(resource, dict):
            if len(resource) != 1:
                raise ResourceNotUnderstood("Resource must have at most "
                                            "one key: %s." % resource)
            res_name = next(iter(resource))
            res_params = resource[res_name]
        elif isinstance(resource, str):
            res_name = resource
            res_params = None
        else:
            raise ResourceNotUnderstood("Resource type not understood: %s" %
                                        resource)
        if res_name in self.namespace:

            #Target already in namespace
            if hasattr(self.providers, res_name):
                if res_params is not None:
                    raise ResourceError("Provider %s "
                                        "is being overwritten by value %s, "
                                        "with")
                log.warn("Provider %s is being overwritten by value %s." %
                             (res_name, self.namespace[res_name]))

            return (RESOURCE, self.namespace[res_name])

        try:
            func = getattr(self.providers, res_name)
        except AttributeError:
            raise ResourceNotFound(res_name, required_by)

        return (PROVIDER, (func, res_params))


    def process_requirement(self, req_spec, required_by=None):

        requirement = self.find_resource_or_provider(req_spec, required_by)
        req_type, req_val = requirement

        if req_type == RESOURCE:
            return req_spec

        func,res_params = req_val
        try:
            signature = inspect.signature(func)
        except TypeError:
            raise ResourceNotUnderstood("%s must be callable." % func)

        if res_params is not None:
            try:
                param_spec = signature.bind_partial(**res_params)
            except TypeError:
                raise ResourceNotUnderstood("Unexpected parameters "
                "for provider %s: %s. \nThe parameters of this function are:" %
                (func.__qualname__, res_params, signature))
            func = comparepartial(func, *param_spec.args, **param_spec.kwargs)
            #This is the easiest way to recreate the signature
            signature = inspect.signature(func)
            name = func
        else:
            name = func.__name__

        mode = ExecModes.SET_UNIQUE
        spec_params = []

        for param_name, param in signature.parameters.items():
            if (param.kind ==  inspect.Parameter.POSITIONAL_OR_KEYWORD and
                param.default is inspect.Parameter.empty):

                spec_params.append(param_name)

        callspec = CallSpec(func, tuple(spec_params), name, mode)

        if required_by is None:
            outputs = {}
        else:
            outputs = {required_by}
        self.graph.add_or_update_node(callspec, outputs=outputs)
        for param in spec_params:
            self.process_requirement(param, required_by=callspec)

        return name


    def build_graph(self):
        self.graph = dag.DAG()
        self.target_keys = []
        for target in self.targets:
            name = self.process_requirement(target)
            self.target_keys.append(name)
