# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 15:01:14 2015

@author: zah
"""
import os
from collections.abc import Mapping
from typing import Any, Optional
import unittest
import unittest.mock as mock

from reportengine.configparser import Config, BadInputType, explicit_node
from reportengine.resourcebuilder import (ResourceBuilder, FuzzyTarget,
                                          ResourceError, collect)
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
    english_taster = collect(english_breakfast, ('restaurants',))
    restaurant_collect = collect('restaurant', ('restaurants',))

    def score(self, restaurants, english_taster):
        print(english_taster)
        print(restaurants)
        for r, t in zip(restaurants, english_taster):
            assert t.startswith("At " + r['restaurant'])
        return -1


class TestBuilder(unittest.TestCase):

    def test_builder(self):

        extra_args = ( ('time', '10AM') ,)

        fuzzytargets = [
            FuzzyTarget('english_breakfast', (), tuple(), extra_args),
            FuzzyTarget('spam', tuple(), (), ()),
            FuzzyTarget('restaurant', tuple(), (), ())

        ]
        c = Config({'restaurant': "La Patata"})

        provider = Provider()
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        builder.resolve_fuzzytargets()

        builder.execute_sequential()


        namespace = builder.rootns
        breakfast_key = builder.fuzzytargets[0].name
        self.assertEqual(namespace[breakfast_key],
             "At La Patata. Preparing breakfast with: spam,ham,eggs at 10AM.")

        rest_key = builder.fuzzytargets[2].name
        self.assertEqual(namespace[rest_key], "La Patata")

    def test_require_one(self):
        fuzzytargets = [FuzzyTarget('fruit', (), (), ())]
        c = Config({})
        provider = Provider()
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        with self.assertRaises(ResourceError):
            builder.resolve_fuzzytargets()




        c = Config({'apple': True})
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        builder.resolve_fuzzytargets()
        builder.execute_sequential()
        self.assertEqual(builder.rootns['fruit'], (True, None))


    def test_remove_outer(self):
        fuzzytargets = [FuzzyTarget('fruit', (['inner']), (), ())]
        c = Config({'apple': True, 'inner':{'orange':False}})

        provider = Provider()
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        builder.resolve_fuzzytargets()
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
        fuzzytargets = [
                    FuzzyTarget('sweet_breakfast', tuple('a'), (), ()),
                    FuzzyTarget('sweet_breakfast', tuple('b'), (), ())
                  ]
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        builder.resolve_fuzzytargets()

        builder.execute_sequential()


    @mock.patch.dict(os.environ,{'MAX_WORKER_PROCESSES':'2'})
    def test_collect(self):
        inp = {
        'Spain': {'restaurants': [{'restaurant': x} for x in ["La patata", "La boñata"]]},
        'UK': {'restaurants': [{'restaurant':x} for x in ["Whetherspoon","Kings arms"]]},
        'lists': [
                  {'restaurants': [{'restaurant': x} for x in "ABC"]},
                  {'restaurants': [{'restaurant': x} for x in "123"]},
                  {'restaurants': [{'restaurant': x} for x in "xyz"]},

                 ],
        'apple': "Golden",
        }
        provider = Provider()
        c = Config(inp)
        fuzzytargets = [
                    FuzzyTarget('score', ('Spain',), (), ()),
                    FuzzyTarget('score', ('UK',), (), ()),
                    FuzzyTarget('score', ('lists',), (), ()),
                    FuzzyTarget('restaurant_collect', ('lists',), (), ()),
                  ]
        builder = ResourceBuilder(fuzzytargets=fuzzytargets, providers=provider,
                                  input_parser=c)
        builder.resolve_fuzzytargets()
        d = namespaces.resolve(builder.rootns,  [('lists',1)])
        assert d['restaurant_collect'] == list("123")
        client = builder.execute_parallel()
        # since it is using dask it returns a future
        assert namespaces.resolve(builder.rootns, ('UK',))['score'].result() == -1
        # close the client
        client.close()

    def test_collect_raises(self):
        with self.assertRaises(TypeError):
            collect(1, ['a', 'b', 'c'])
        provider = Provider()
        with self.assertRaises(TypeError):
            collect(provider.english_taster,['a', 'b', 'c'])




class Price():
    def __init__(self, value):
        self.value = value


def _compute_price(menu):
    return Price(len(menu))


class TypedConfig(Config):
    @explicit_node
    def produce_price(self):
        return _compute_price


class TypedProvider():

    def bill(self, menu: Mapping[str, Any], price: Optional[Price] = None):
        return price.value

    def receipt(self, menu: dict[str, int], price: Price | None):
        return price.value

    def tip(self, menu: list[int]):
        return 0


class TestCheckTypes(unittest.TestCase):

    def _build(self, target, inp):
        builder = ResourceBuilder(
            fuzzytargets=[FuzzyTarget(target, (), (), ())],
            providers=TypedProvider(),
            input_parser=TypedConfig(inp),
        )
        builder.resolve_fuzzytargets()
        return builder

    def test_explicit_node_and_generics(self):
        """Generic annotations are checked against their origin, and a
        resource produced by an explicit node is not checked before it is
        computed."""
        for target in ('bill', 'receipt'):
            builder = self._build(target, {'menu': {'spam': 1, 'eggs': 2}})
            builder.execute_sequential()
            self.assertEqual(builder.rootns[target], 2)

    def test_generic_origin_mismatch(self):
        with self.assertRaises(ResourceError) as cm:
            self._build('tip', {'menu': {'spam': 1}})
        self.assertIsInstance(cm.exception.__cause__, BadInputType)
        self.assertIn('list[int]', str(cm.exception))


if __name__ =='__main__':
    unittest.main()
