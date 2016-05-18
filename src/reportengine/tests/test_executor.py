# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 22:51:32 2015

@author: zah
"""

import unittest
import time

from reportengine.dag import DAG
from reportengine.utils import ChainMap
from reportengine import namespaces
from reportengine.resourcebuilder import (ResourceExecutor, CallSpec,
                                          ExecModes)

def f(param):
    print("Executing f")
    time.sleep(1)
    return "fresult: %s" % param

def g(fresult):
    print("Executing g")
    time.sleep(2)
    return fresult*2

def h(fresult):
    print("Executing h")
    time.sleep(2)
    return fresult*3

def m(gresult, hresult, param=None):
    print("executing m")
    return (gresult+hresult)*(param//2)

def n(mresult):
    return mresult

def o(mresult):
    return mresult*2

def p(mresult):
    return mresult*3

class TestResourceExecutor( unittest.TestCase, ResourceExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.rootns = ChainMap({'param':4, 'inner': {}})
        def nsspec(x, beginning=()):
            ns = namespaces.resolve(self.rootns, beginning)
            default_label =  '_default' + str(x)
            namespaces.push_nslevel(ns, default_label)
            return beginning + (default_label,)

        self.graph = DAG()

        fcall = CallSpec(f, ('param',), 'fresult', ExecModes.SET_UNIQUE,
                         nsspec(f))

        gcall = CallSpec(g, ('fresult',), 'gresult', ExecModes.SET_UNIQUE,
                         nsspec(g))

        hcall = CallSpec(h, ('fresult',), 'hresult', ExecModes.SET_UNIQUE,
                         nsspec(h))

        mcall = CallSpec(m, ('gresult','hresult','param'), 'mresult',
                         ExecModes.SET_UNIQUE, nsspec(m))

        ncall = CallSpec(n, ('mresult',), 'arr', ExecModes.APPEND_UNORDERED,
                         nsspec(n))

        ocall = CallSpec(o, ('mresult',), 'arr', ExecModes.APPEND_UNORDERED,
                         nsspec(o))

        pcall = CallSpec(p, ('mresult',), 'arr', ExecModes.APPEND_UNORDERED,
                         nsspec(p))

        self.graph.add_node(fcall)
        self.graph.add_node(gcall, inputs={fcall})
        self.graph.add_node(hcall, inputs={fcall})
        self.graph.add_node(mcall, inputs={gcall, hcall})
        self.graph.add_node(ncall, inputs={mcall})

        self.graph.add_node(ocall, inputs={mcall})
        self.graph.add_node(pcall, inputs={mcall})

    def _test_ns(self):
        mresult = 'fresult: 4'*10
        namespace = self.rootns
        self.assertEqual(namespace['mresult'], mresult)
        self.assertEqual(set(namespace['arr']),  {mresult, mresult*2,
                         mresult*3})

    def test_seq_execute(self):
        self.execute_sequential()
        self._test_ns()

    def test_parallel_execute(self):
        self.execute_parallel()
        self._test_ns()

if __name__ =='__main__':
    unittest.main()