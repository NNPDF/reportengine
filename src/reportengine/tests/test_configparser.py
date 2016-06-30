# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 11:09:28 2016

@author: Zahari Kassabov
"""

import unittest

from reportengine.utils import ChainMap
from reportengine import namespaces
from reportengine.configparser import (Config, BadInputType, element_of,
                                       named_element_of, ConfigError)

class BaseConfig(Config):

    @element_of('ys')
    def parse_y(self, number):
        return number


    @element_of("fours")
    def parse_four(self, number:int):
        return 4

    @named_element_of("fives")
    def parse_five(self, number:int):
        return 5

    def parse_three(self, number:int):
        return number

    def parse_sum(self, sum, y, three=3, four=4):
        return three + four + y

class ExampleConfig(BaseConfig):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = self.process_all_params()


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

    def test_graph(self):
        inp = {'sum':None, 'three': 3, 'y': 0}
        c = ExampleConfig(inp)
        self.assertEqual(c.params, {'sum':7, 'three':3, 'y':0})

        inp = {'sum':None, 'three': 3, 'four':10, 'y':0}
        c = ExampleConfig(inp)
        self.assertEqual(c.params, {'sum':7, 'three':3, 'four':4, 'y':0})

        inp = {'sum':None, 'three': 3, 'four':10}
        with self.assertRaises(ConfigError):
            c = ExampleConfig(inp)

        inp = {'sum':None, 'three': 3, 'four':10}

        with self.assertRaises(ConfigError):
            c = ExampleConfig(inp)

    def test_transform(self):

        inp = {'fours': [4,4,4,4,4]}
        p = ExampleConfig(inp).params
        self.assertEqual(p['fours'].as_namespace(), [{'four': 4}, {'four': 4},
                                         {'four': 4}, {'four': 4},
                                         {'four': 4}])
        self.assertEqual(p['fours'], [4]*5)
        inp = {'fours': [4,'x']}
        with self.assertRaises(BadInputType):
            ExampleConfig(inp)

        inp = {'fours': "patata"}
        with self.assertRaises(BadInputType):
            ExampleConfig(inp)

        inp = {'fives': {'f1': 55, 'f2':555}}
        r = ExampleConfig(inp).params['fives']
        self.assertEqual(r, {'f1': 5 ,'f2' : 5})
        d = {k: r.nsitem(k)  for k in r.keys()}
        self.assertEqual(d,
                         {'f1': {'five': 5}, 'f2': {'five': 5}})

    def test_fuzzy(self):
        inp = {'four': 4, 'ys': [-1,-2,-3,-4], 'sum':None}
        c = BaseConfig(inp)
        ns = ChainMap()
        ret = c.process_fuzzyspec(('ys',), ns=ns)
        for spec, s in zip(ret, (6,5,4,3)):
            ns_ = namespaces.resolve(ns, spec)
            c.resolve_key('sum', ns=ns_)
            self.assertEqual(ns_['sum'], s)

        #specs have to be persistent
        self.assertEqual(namespaces.resolve(ns, spec).maps[0],
                         {'sum': 3, 'y': -4})

    def test_from_(self):
        inp = {

            'd': {'y': 1},
            'ys': [4, 5, {'from_':'d'}],
            'inner': {'y': {'from_':'d'}, 'three':33},
            'three': 3,
            'four': 4,
            'sum': None,
            'z': {'from_':'d'},
        }
        c = BaseConfig(inp)
        ns = ChainMap()
        specs = c.process_fuzzyspec(('ys',), ns=ns)
        ns_ = namespaces.resolve(ns, specs[2])
        self.assertEqual(ns_['y'], 1)
        self.assertEqual(c.resolve_key('sum', ns=ns_)[1], 8)

        #ns = ChainMap()

        spec, = c.process_fuzzyspec(('inner',), ns=ns)

        ns_ = namespaces.resolve(ns, spec)

        self.assertEqual(ns_['y'], 1)
        self.assertEqual(c.resolve_key('sum', ns=ns_)[1], 38)

        with self.assertRaises(ConfigError):
            c.resolve_key('z', ns)



if __name__ =='__main__':
    unittest.main()