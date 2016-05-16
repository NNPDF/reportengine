# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 21:18:06 2015

@author: zah
"""

from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
import asyncio
import logging
import inspect
import enum
import functools

from reportengine import dag
from reportengine import namespaces
from reportengine.configparser import ConfigError
from reportengine.checks import CheckError
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

class ResourceExecutor():

    def __init__(self, graph, rootns, environment=None):
        self.graph = graph
        self.rootns = rootns
        self.environment = environment

    def resolve_kwargs(self, nsspec, kwargs):
        namespace = namespaces.resolve(self.rootns, nsspec)
        kwdict = {}
        put_index = len(namespace.maps) - 1
        for kw in kwargs:
            index, kwdict[kw] =  namespace.get_where(kw)
            #We ignore the indeternal default namespace for the function
            if index > 0 and index < put_index:
                put_index = index
        kwdict = {kw: namespace[kw] for kw in kwargs}
        return kwdict, put_index



    def execute_sequential(self):
        for node in self.graph:
            function, kwargs, resultname, mode, nsspec = spec = node.value
            kwdict, put_index = self.resolve_kwargs(nsspec, kwargs)
            result = self.get_result(function, **kwdict)
            self.set_result(result, spec, put_index)

    #This needs to be a staticmethod, because otherwise we have to serialize
    #the whole self object when passing to multiprocessing.
    @staticmethod
    def get_result(function, **kwdict):
        return function(**kwdict)

    def set_result(self, result, spec, put_index):
        function, kwargs, resultname, execmode, nsspec = spec
        namespace = namespaces.resolve(self.rootns, nsspec)
        put_map = namespace.maps[put_index]
        log.debug("put index: %s, spec: %s" % (put_index, nsspec))
        if not execmode in ExecModes:
            raise TypeError("Callspecmode must be an ExecMode")

        if execmode == ExecModes.SET_UNIQUE:
            if resultname in put_map:
                raise ValueError("Resource already set: %s" % resultname)
            put_map[resultname] = result

        elif execmode == ExecModes.SET_OR_UPDATE:
            put_map[resultname] = result

        elif execmode == ExecModes.APPEND_UNORDERED:
            if not resultname in namespace:
                put_map[resultname] = []
            put_map[resultname].append(result)

        else:
            raise NotImplementedError(execmode)

        if hasattr(function, 'final_action'):
            function.final_action(result,
                                  self.environment,
                                  spec, self.rootns, self.graph)

    async def submit_next_specs(self, loop, executor, next_specs, deps):
        tasks = []
        for spec in next_specs:
            kwdict, put_index = self.resolve_kwargs(spec.nsspec, spec.kwargs)
            clause = comparepartial(self.get_result, spec.function, **kwdict)
            future = loop.run_in_executor(executor, clause)


            spec_done = self._spec_done(future=future,
                               loop=loop, executor=executor,
                               spec=spec, deps=deps, put_index=put_index)

            task = loop.create_task(spec_done)
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def _spec_done(self, future, loop, executor, spec, deps, put_index):
        result = await future
        self.set_result(result, spec, put_index)
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


class ResourceError(Exception):
    def __init__(self, name, message, parents):
        self.name = name
        self.message = message
        if not parents:
            parents = ('Target specification',)
        self.parents = parents

    def __str__(self):
        return "Could not process the resource %s, required by:\n%s\n%s"%(
                self.name, '\n'.join(' - ' + p for p in self.parents),
                self.message)

class ResourceNotUnderstood(ResourceError, TypeError): pass

Target = namedtuple('Target', ('name', 'nsspec', 'extraargs'))

EMPTY = inspect.Signature.empty

class ResourceBuilder(ResourceExecutor):

    def __init__(self, input_parser, providers, targets, environment=None):

        self.input_parser = input_parser
        self.providers = providers
        self.targets = targets

        self.rootns = ChainMap()
        self.graph = dag.DAG()

        self.environment = environment

    def resolve_targets(self):
        for target in self.targets:
            self.resolve_target(target)

    def resolve_target(self, target):
        name, fuzzy, extra_args = target
        try:
            specs = self.input_parser.process_fuzzyspec(fuzzy,
                                                self.rootns, parents=[name])
        except ConfigError as e:
            raise
        except Exception as e:
            raise ResourceError(target, e, None)
        for spec in specs:
            self.process_requirement(name, spec, extra_args)

    def process_requirement(self, name, nsspec, extraargs=None, required_by=None,
                            default=EMPTY, back=False):

        ns = namespaces.resolve(self.rootns, nsspec)
        if extraargs is None:
            extraargs = ()
        try:
            self.input_parser.resolve_key(name, ns, parents=[required_by])
        except KeyError as e:
            if hasattr(self.providers, name):

                defaults_label = '_' + name + '_defaults'

                if back:
                    nsspec = (*nsspec[:-1], defaults_label)
                    ns = ns.parents

                else:
                    nsspec = (*nsspec, defaults_label)

                namespaces.push_nslevel(ns, defaults_label)
                ns = namespaces.resolve(self.rootns, nsspec)


                f = getattr(self.providers, name)
                s = inspect.signature(f)
                if(extraargs):
                    ns.update(dict(extraargs))
                cs = CallSpec(f, tuple(s.parameters.keys()), name,
                              ExecModes.SET_UNIQUE,
                              nsspec)
                self.graph.add_or_update_node(cs)
                for param_name, param in s.parameters.items():
                    self.process_requirement(param_name, nsspec, None,
                                             required_by=cs,
                                             default=param.default, back=True)
                if required_by is None:
                    outputs = set()
                else:
                    outputs = set([required_by])
                self.graph.add_or_update_node(cs, outputs=outputs)

                if hasattr(f, 'checks'):
                    for check in f.checks:
                        try:
                            check(cs, ns, self.graph)
                        except CheckError as e:
                            raise ResourceError(name, e, [req.resultname
                                                       for req in outputs])
            else:
                if default is EMPTY:
                    raise e
                else:
                    ns[name] = default


        else:
            if extraargs:
                raise ResourceNotUnderstood(name, "The resource %s name is "
                "already present in the input, but some arguments were "
                "passed to compute it: %s" % (name, extraargs), required_by)
