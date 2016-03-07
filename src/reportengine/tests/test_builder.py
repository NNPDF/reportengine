# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""

import unittest

from reportengine.configparser import Config
from reportengine.resourcebuilder import ResourceBuilderX as ResourceBuilder, Target
    
class Provider():

    def spam(self):
        return "spam"

    def ham(self):
        return "ham"

    def eggs(self, spam):
        return "eggs"

    def english_breakfast(self, restaurant ,spam, ham, eggs, time="8AM"):
        return "At %s. Preparing breakfast with: %s at %s." % (restaurant,
                                                               ','.join([spam,
                                                                        ham,
                                                                        eggs]),
                                                               time)

class TestBuilder(unittest.TestCase):

    def test_builder(self):
    
        extra_args = ( ('time', '10AM') ,)
        
        targets = [
            Target('english_breakfast', tuple(), extra_args),
            Target('spam', tuple(), ()),
            Target('restaurant', tuple(), ())
        
        ]        
        c = Config({'restaurant': "La Patata"})

        provider = Provider()
        builder = ResourceBuilder(targets=targets, providers=provider,
                                  input_parser=c)
        builder.resolve_targets()

        builder.execute_sequential()
        namespace = builder.rootns
        breakfast_key = builder.targets[0].name
        self.assertEqual(namespace[breakfast_key],
             "At La Patata. Preparing breakfast with: spam,ham,eggs at 10AM.")

        rest_key = builder.targets[2].name
        self.assertEqual(namespace[rest_key], "La Patata")

#==============================================================================
# class TestNSResolver(unittest.TestCase):
#     d = {1: [
#               {'a': 1},
#               {'a': 2, 'other': 3},
#             ],
# 
#          2: {'key': 'value'},
# 
#          3: {'deep': [
#                       {'nested': {'x':{0:1, 'd': {'a':0}}, 'y':2, 'w':0},
#                        'other':{'':''}},
#                       {'nested': {'x':{1000:1}, 'z':2, 'w':1}},
#                       {'nested': {'x':{0:1}, 'y':2, 'w':2}},
#                       {'nested': {'x':{122:1}, 'y':2, 'w':3}},
# 
#                      ]
#             }
#         }
#     def setUp(self):
#         self.res = NSResolver(self.d.copy())
# 
#     def test_span(self):
#         res = self.res
#         with self.assertRaises(TypeError):
#             res.span_specs((1,'a'))
# 
#         spec = res.span_specs((1,))
#         self.assertEqual(list(spec), [((1, 0),), ((1, 1),)])
# 
#         spec = res.span_specs((2,))
#         self.assertEqual(list(spec), [(2,)])
# 
#         spec = res.span_specs((3, 'deep', 'nested'))
#         self.assertEqual(list(spec), [(3, ('deep', 0), 'nested'),
#                          (3, ('deep', 1), 'nested'),
#                          (3, ('deep', 2), 'nested'),
#                          (3, ('deep', 3), 'nested')])
# 
#         with self.assertRaises(TypeError):
#             spec = res.span_specs((3, 'deep', 'nested', 'x', 0))
# 
#         #TODO: Make this fail
# #==============================================================================
# #         spec = res.span_specs((3, 'deep', 'nested', 'x', 'd'))
# #
# #==============================================================================
#         with self.assertRaises(KeyError):
#             spec = res.span_specs((3, 'deep', 'other'))
# 
#     def test_resolve(self):
#         res = self.res
#         spec = ( (1,1) ),
#         ns = res.resolve(spec)
#         self.assertEqual(ns['other'], 3)
# 
#         spec = (3, ('deep', 2), 'nested')
#         ns = res.resolve(spec)
#         self.assertTrue(3 in ns)
# 
# 
# 
#     def test_both(self):
#         res = self.res
#         specs = res.span_specs((3, 'deep', 'nested'))
#         for w, spec in enumerate(specs):
#             ns = res.resolve(spec)
#             self.assertEqual(w, ns['w'])
#             if w == 0:
#                 self.assertFalse('z' in ns)
#                 self.assertTrue('other' in ns)
#             else:
#                 self.assertFalse('other' in ns)
#         specs = res.span_specs((3, 'deep', 'nested', 'x', 'd'))
#         with self.assertRaises(KeyError):
#             for spec in specs:
#                 ns = res.resolve(spec)
#==============================================================================



if __name__ =='__main__':
    unittest.main()
