# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 21:18:06 2015

@author: zah
"""

from collections import namedtuple
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import asyncio

CallSpec = namedtuple("CallSpec", "function kwargs resultname".split())

def print_callspec(spec):
    callargs = ', '.join("%s=%s"% (kw, kw) for kw in spec.kwargs)
    return "{res} = {f}({callargs})".format(res=spec.resultname,
                                        f=spec.function.__qualname__,
                                        callargs=callargs)


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
