# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""

import unittest

from reportengine.configparser import Config
from reportengine.resourcebuilder import ResourceBuilder, Target
    
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

if __name__ =='__main__':
    unittest.main()
