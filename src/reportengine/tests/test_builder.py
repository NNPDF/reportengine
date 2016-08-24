# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""

import unittest

from reportengine.configparser import Config
from reportengine.resourcebuilder import ResourceBuilder, Target, ResourceError
from reportengine.checks import require_one, remove_outer
from reportengine import namespaces

class Provider():

    def spam(self):
        return "spam"

    def ham(self):
        return "ham"

    def eggs(self, spam):
        return "eggs"

    def juice(self, oranges):
        return 'juice'

    def sweet_breakfast(self, oranges, fruit):
        return "Breakfast with oranges from %s and %s" % (oranges, fruit)

    @require_one('apple', 'orange')
    @remove_outer('apple', 'orange')
    def fruit(self, apple=None, orange=None):
        return (apple, orange)


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

    def test_require_one(self):
        targets = [Target('fruit', (), ())]
        c = Config({})
        provider = Provider()
        builder = ResourceBuilder(targets=targets, providers=provider,
                                  input_parser=c)
        with self.assertRaises(ResourceError):
            builder.resolve_targets()




        c = Config({'apple': True})
        builder = ResourceBuilder(targets=targets, providers=provider,
                                  input_parser=c)
        builder.resolve_targets()
        builder.execute_sequential()
        self.assertEqual(builder.rootns['fruit'], (True, None))


    def test_remove_outer(self):
        targets = [Target('fruit', (['inner']), ())]
        c = Config({'apple': True, 'inner':{'orange':False}})

        provider = Provider()
        builder = ResourceBuilder(targets=targets, providers=provider,
                                  input_parser=c)
        builder.resolve_targets()
        builder.execute_sequential()
        ns = namespaces.resolve(builder.rootns, ('inner',))
        self.assertEqual(ns['fruit'], (None, False))

    def test_nested_specs(self):
        inp = {
        'a': {'oranges': 'Valencia'},
        'b': {'oranges': 'Ivrea'},
        'apple': "Golden",
        }
        provider = Provider()
        c = Config(inp)
        targets = [
                    Target('sweet_breakfast', tuple('a'), ()),
                    Target('sweet_breakfast', tuple('b'), ())
                  ]
        builder = ResourceBuilder(targets=targets, providers=provider,
                                  input_parser=c)
        builder.resolve_targets()

        builder.execute_sequential()


if __name__ =='__main__':
    unittest.main()
