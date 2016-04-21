# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""

import unittest

from reportengine.configparser import Config
from reportengine.resourcebuilder import ResourceBuilder, Target, ResourceError
from reportengine.checks import require_one

class Provider():

    def spam(self):
        return "spam"

    def ham(self):
        return "ham"

    def eggs(self, spam):
        return "eggs"

    def juice(self, oranges):
        return 'juice'

    @require_one('apple', 'orange')
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

if __name__ =='__main__':
    unittest.main()
