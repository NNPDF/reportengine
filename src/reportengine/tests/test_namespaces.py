# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 17:02:38 2016

@author: Zahari Kassabov
"""
from __future__ import generator_stop
import unittest
import copy
import itertools

from reportengine import namespaces

ChainMap = namespaces.ChainMap

c = [{'l1':8, 'l2':[{'nested': True}]}, {'l1':9, 'l2':[{'nested':True}]}]
b = {1:2}
a = {4:5, 6:7, 'b': b}
d = {1:2, 'a':a, 'c': c}

class TestNamespaces(unittest.TestCase):

    def setUp(self):
        self.d = copy.deepcopy(d)

    def test_resolve(self):

        rem, ns = namespaces.resolve_partial(d, ('a',))
        self.assertFalse(rem)
        self.assertEqual(ns, ChainMap(a,d))

        rem, ns = namespaces.resolve_partial(d, (('c',1),))
        self.assertFalse(rem)
        self.assertEqual(ns, ChainMap(c[1],d))

        spec =  ('a','b', ('c',1))
        rem, ns = namespaces.resolve_partial(d, spec)
        self.assertFalse(rem)
        self.assertEqual(ns, ChainMap(c[1],b,a,d))
        self.assertEqual(ns, namespaces.resolve(d,spec))

        rem, ns = namespaces.resolve_partial(d, ('x','a', 'b'))
        self.assertEqual(list(rem), ['x', 'a', 'b'])
        self.assertEqual(len(ns.maps), 1)

        spec = ('a', 'b', ('x', 0))
        rem, ns = namespaces.resolve_partial(d, spec)
        self.assertEqual(list(rem), [('x', 0)])
        self.assertEqual(len(ns.maps), 3)
        with self.assertRaises(KeyError):
            namespaces.resolve(d, spec)

    def test_expand(self):
        fuzzy = ('a', 'c')
        ns = ChainMap(self.d)
        gen = namespaces.expand_fuzzyspec_partial(fuzzy, ns)
        #self.assertFalse(list(gen))
        while True:
            try:
                next(gen)
            except StopIteration as e:
                self.assertEqual(e.value, [('a', ('c', 0)), ('a', ('c', 1))])
                break
            else:
                self.fail()

        fuzzy = ('a', 'x', 'c')
        ns = ChainMap(self.d)
        gen = namespaces.expand_fuzzyspec_partial(fuzzy, ns)
        #self.assertFalse(list(gen))
        var, spec, cns = next(gen)
        cns[var] = 'not ok'
        with self.assertRaises(TypeError):
            next(gen)

        fuzzy = ('a', 'xx', 'c')
        ns = ChainMap(self.d)
        gen = namespaces.expand_fuzzyspec_partial(fuzzy, ns)
        #self.assertFalse(list(gen))
        var, spec, cns = next(gen)
        cns[var] = [{'ok': True}, {'ok':'yes'}, {'ok':1}]
        with self.assertRaises(StopIteration) as ec:
            next(gen)
        specs = ec.exception.value
        self.assertEqual(set(specs),
             set(itertools.product('a', [('xx', 0), ('xx', 1,), ('xx', 2)],
                                         [('c', 0), ('c', 1)]))
        )

    def test_nested_expand(self):
        d = self.d
        d['c'][0]['l3'] = [{'x':1},{'x':2}]
        d['c'][1]['l3'] = [{'x':1},]
        ns = ChainMap(d)
        fuzzy = ('c', 'l3')
        gen = namespaces.expand_fuzzyspec_partial(fuzzy, ns)
        with self.assertRaises(StopIteration) as ec:
            next(gen)
        self.assertEqual(ec.exception.value,
         [(('c', 0), ('l3', 0)), (('c', 0), ('l3', 1)), (('c', 1), ('l3', 0))]
        )

    def test_identities(self):
        a = {1:'a'}
        alta = {1:'aa'}
        b = {2:'b'}
        d = {'a':a, 'alta':alta, 'b':b}
        m1 = namespaces.resolve(d, ('a','b'))
        m2 = namespaces.resolve(d, ('a','b'))
        m3 = namespaces.resolve(d, ('alta','b'))

        self.assertIs(m1.maps[0], m2.maps[0])
        self.assertFalse(m3.maps[0] is m2.maps[0])



if __name__ == '__main__':
    unittest.main()
