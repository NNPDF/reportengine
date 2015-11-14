# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 22:51:32 2015

@author: zah
"""

import unittest
import time

from dag import DAG
from resourcebuilder import ResourceExecutor, CallSpec

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

class TestResourceExecutor(unittest.TestCase, ResourceExecutor):
    def setUp(self):
        self.namespace = {'param':4}
        self.graph = DAG()
        fcall = CallSpec(f, ('param',), 'fresult')
        gcall = CallSpec(g, ('fresult',), 'gresult')
        hcall = CallSpec(h, ('fresult',), 'hresult')
        mcall = CallSpec(m, ('gresult','hresult','param'), 'mresult')
        
        self.graph.add_node(fcall)
        self.graph.add_node(gcall, inputs={fcall})
        self.graph.add_node(hcall, inputs={fcall})
        self.graph.add_node(mcall, inputs={gcall, hcall})
    
    def test_seq_execute(self):
        self.execute_sequential()
        self.assertEqual(self.namespace['mresult'], 'fresult: 4'*10)
    
    def test_parallel_execute(self):
        self.execute_parallel()
        self.assertEqual(self.namespace['mresult'], 'fresult: 4'*10)

if __name__ =='__main__':
    unittest.main()