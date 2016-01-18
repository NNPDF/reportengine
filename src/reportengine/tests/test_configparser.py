# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 11:09:28 2016

@author: Zahari Kassabov
"""

import unittest

from reportengine.configparser import Config ,BadInputType

class ExampleConfig(Config):
    
    @staticmethod
    def parse_three(number:int):
        return number
    
    

class TestConfig(unittest.TestCase):
    
    def test_simple_input(self):
        inp = {'one':1, 'two':2}
        c = ExampleConfig(inp)
        self.assertEqual(c.params, inp)
    
    def test_types(self):
        inp = {'three': 'spam'}
        with self.assertRaises(BadInputType):
            c = ExampleConfig(inp)
        inp = {'three' : 3}
        c = ExampleConfig(inp)
        self.assertEqual(c.params, inp)
    
    def test_interface(self):
        inp = {'one':1, 'two':2, 'three': 3}
        c = ExampleConfig(inp)
        self.assertTrue('one' in c)
        self.assertEqual(c['three'], 3)
        self.assertEqual(len(c), 3)

if __name__ =='__main__':
    unittest.main()