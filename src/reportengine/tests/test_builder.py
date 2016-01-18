# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""

import unittest

from reportengine.resourcebuilder import ResourceBuilder

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
        targets = [{'english_breakfast': {'time': "10AM"}}, 'spam',
                   'restaurant']
        namespace = {'restaurant': "La Patata"}
        
        
        provider = Provider()
        builder = ResourceBuilder(targets=targets, providers=provider, 
                                  namespace=namespace)
        builder.build_graph()

        builder.execute_sequential()
        breakfast_key = builder.target_keys[0]
        self.assertEqual(namespace[breakfast_key],
             "At La Patata. Preparing breakfast with: spam,ham,eggs at 10AM.")

        rest_key = builder.target_keys[2]
        self.assertEqual(namespace[rest_key], "La Patata")



if __name__ =='__main__':
    unittest.main()
