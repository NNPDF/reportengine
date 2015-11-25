# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 21:18:06 2015

@author: zah
"""

from collections import namedtuple
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import asyncio
import logging
import inspect

import dag

RESOURCE = "resource"
PROVIDER = "provider"

CallSpec = namedtuple("CallSpec", "function kwargs resultname".split())

def print_callspec(spec):
    callargs = ', '.join("%s=%s"% (kw, kw) for kw in spec.kwargs)
    try:
        f = spec.function.__qualname__

    #functools.partial annoyingly doesn't wrap
    except AttributeError:
        f = spec.function.func.__qualname__
        callargs += ", " + ", ".join("%s=%s" % (kw,val) for
                                     kw,val in spec.function.keywords.items())

    return "{res} = {f}({callargs})".format(res=spec.resultname,
                                        f=f,
                                        callargs=callargs)

CallSpec.__str__ = print_callspec


class ResourceExecutor():

    def __init__(self, graph, namespace):
        self.graph = graph
        self.namespace = namespace


    def execute_sequential(self):
        for node in self.graph:
            function, kwargs, resultname = node.value
            kwdict = {kw: self.namespace[kw] for kw in kwargs}
            self.namespace[resultname] = function(**kwdict)

    async def submit_next_specs(self, loop, executor, next_specs, deps):

        futures = []
        for spec in next_specs:
            kwdict = {kw: self.namespace[kw] for kw in spec.kwargs}
            clause = partial(spec.function, **kwdict)
            future = loop.run_in_executor(executor, clause)
            callback = partial(self._spec_done,
                               loop=loop, executor=executor,
                               spec=spec, deps=deps)
            future.add_done_callback(callback)

            futures.append(future)
        for future in futures:
            await future

    def _spec_done(self, future, loop, executor, spec, deps):
        self.namespace[spec.resultname] = future.result()
        try:
            next_specs = deps.send(spec)
        except StopIteration:
            loop.stop()
        else:
            loop.create_task(self.submit_next_specs(loop, executor,
                                                    next_specs, deps))

    def execute_parallel(self, executor=None, loop=None):

        if executor is None:
            executor = ProcessPoolExecutor()
        if loop is None:
            loop = asyncio.get_event_loop()

        deps = self.graph.dependency_resolver()
        next_specs = deps.send(None)

        with executor:
            loop.create_task(self.submit_next_specs(loop, executor,
                                                    next_specs, deps))
            loop.run_forever()

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
                logging.warn("Provider %s is being overwritten by value %s." %
                             (res_name, self.namespace[res_name]))

            return (RESOURCE, self.namespace[res_name])

        try:
            func = getattr(self.providers, res_name)
        except AttributeError:
            raise ResourceNotFound(res_name, required_by)

        return (PROVIDER, (func, res_params))


    def process_requirement(self, requirement, required_by=None):

        requirement = self.find_resource_or_provider(requirement, required_by)
        req_type, req_val = requirement

        if req_type == RESOURCE:
            return

        func,res_params = req_val
        try:
            signature = inspect.signature(func)
        except TypeError:
            raise ResourceNotUnderstood("%s must be callable." % func)

        name = func.__name__

        if res_params is not None:
            try:
                param_spec = signature.bind_partial(**res_params)
            except TypeError:
                raise ResourceNotUnderstood("Unexpected parameters "
                "for provider %s: %s" % func.__qualname__, res_params)
            func = partial(func, *param_spec.args, **param_spec.kwargs)
            #This is the easiest way to recreate the signature
            signature = inspect.signature(func)


        spec_params = []

        for param_name, param in signature.parameters.items():
            if (param.kind ==  inspect.Parameter.POSITIONAL_OR_KEYWORD and
                param.default is inspect.Parameter.empty):

                spec_params.append(param_name)

        callspec = CallSpec(func, tuple(spec_params), name)
        if required_by is None:
            outputs = {}
        else:
            outputs = {required_by}
        self.graph.add_or_update_node(callspec, outputs=outputs)
        for param in spec_params:
            self.process_requirement(param, required_by=callspec)



    def build_graph(self):
        self.graph = dag.DAG()
        for target in self.targets:
            self.process_requirement(target)
