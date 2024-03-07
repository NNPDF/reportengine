# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 22:51:32 2015

Demonstrates a simple usage of the reportengine module for building 
and executing a Directed Acyclic Graph (DAG) of functions.
DAG is executed in parallel and in sequence.

@author: zah
"""

import unittest
import time

from reportengine.dag import DAG
from reportengine.utils import ChainMap
from reportengine import namespaces
from reportengine.resourcebuilder import ResourceExecutor, CallSpec

"""
Define some simple functions that will be used as nodes in the DAG.
"""


def node_1(param):
    print("Executing node_1")
    time.sleep(0.1)
    return "node_1_result: %s" % param


def node_2_1(node_1_result):
    print("Executing node_2_1")
    time.sleep(0.2)
    return node_1_result * 2


def node_2_2(node_1_result):
    print("Executing node_2_2")
    time.sleep(0.2)
    return node_1_result * 3


def node_3(node_2_1_result, node_2_2_result, param=None):
    print("Executing node_3")
    return (node_2_1_result + node_2_2_result) * (param // 2)


class TestResourceExecutor(unittest.TestCase, ResourceExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ResourceExecutor.__init__(self, None, None)

    def setUp(self):
        """
        Creates a simple DAG of functions with diamond shape.

                       node_1 
                        /  \
                node_2_1    node_2_2
                        \  /
                        node_3

        """
        self.rootns = ChainMap({"param": 4, "inner": {}})

        def nsspec(x, beginning=()):
            ns = namespaces.resolve(self.rootns, beginning)
            default_label = "_default" + str(x)
            namespaces.push_nslevel(ns, default_label)
            return beginning + (default_label,)

        self.graph = DAG()

        node_1_call = CallSpec(node_1, ("param",), "node_1_result", nsspec(node_1))

        node_2_1_call = CallSpec(
            node_2_1, ("node_1_result",), "node_2_1_result", nsspec(node_2_1)
        )

        node_2_2_call = CallSpec(
            node_2_2, ("node_1_result",), "node_2_2_result", nsspec(node_2_2)
        )

        node_3_call = CallSpec(
            node_3,
            ("node_2_1_result", "node_2_2_result", "param"),
            "node_3_result",
            nsspec(node_3),
        )

        self.graph.add_node(node_1_call)
        self.graph.add_node(node_2_1_call, inputs={node_1_call})
        self.graph.add_node(node_2_2_call, inputs={node_1_call})
        self.graph.add_node(node_3_call, inputs={node_2_1_call, node_2_2_call})

    def _test_ns(self, promise=False):
        """
        Asserts that the namespace contains the expected results.
        """
        node_3_result = "node_1_result: 4" * 10
        namespace = self.rootns
        if promise:
            self.assertEqual(namespace["node_3_result"].result(), node_3_result)
        else:
            self.assertEqual(namespace["node_3_result"], node_3_result)

    def test_seq_execute(self):
        """
        This test will execute the DAG in sequence.
        """
        self.execute_sequential()
        self._test_ns()

    def test_parallel_execute(self):
        """
        This test will execute the DAG in parallel, using
        dask distributed scheduler.
        """
        client = self.execute_parallel()
        self._test_ns(promise=True)
        client.close()


if __name__ == "__main__":
    unittest.main()
