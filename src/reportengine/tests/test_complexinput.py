# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 21:09:40 2016

@author: Zahari Kassabov
"""
import unittest

from reportengine import namespaces, configparser, utils, resourcebuilder
from reportengine.resourcebuilder import FuzzyTarget

inp = {'pdfsets': ['a', 'b'],
       'theories': [1,2],
       'datasets': ['d1', 'd2'],
       'use_cuts': False,
       'cuts': {'use_cuts':True},
       'nocuts': {'use_cuts':False},
       }

class Config(configparser.Config):
    @configparser.element_of('pdfsets')
    def parse_pdf(self, pdf):
        return 'PDF: ' + pdf

    @configparser.element_of('theories')
    def parse_theory(self, theory):
        return 'th ' + str(theory)


    @configparser.element_of('datasets')
    def parse_dataset(self, ds,  theory, use_cuts):
        return 'ds: {ds} (theory: {theory}, cuts: {use_cuts})'.format(**locals())


class TestSpec(unittest.TestCase):
    def test_nsexpand(self):
        spec = ('pdfsets', 'theories', 'datasets')
        c = Config(inp)
        ns = utils.ChainMap()
        specs = c.process_fuzzyspec(spec, ns=ns)
        self.assertEqual(len(specs), 8)
        datasets = [
              'ds: d1 (theory: th 1, cuts: False)',
              'ds: d2 (theory: th 1, cuts: False)',
              'ds: d1 (theory: th 2, cuts: False)',
              'ds: d2 (theory: th 2, cuts: False)',
              'ds: d1 (theory: th 1, cuts: False)',
              'ds: d2 (theory: th 1, cuts: False)',
              'ds: d1 (theory: th 2, cuts: False)',
              'ds: d2 (theory: th 2, cuts: False)']
        for spec, ds in zip(specs, datasets):
            self.assertEqual(namespaces.resolve(ns, spec)['dataset'], ds)

    def test_nsspec(self):
        c = Config(inp)
        spec = ('pdfsets', 'theories', 'datasets')
        targets = [
                   FuzzyTarget('dataset', spec+(), (), ()),
                   FuzzyTarget('dataset', ('cuts',)+spec, (), ()),
                   FuzzyTarget('dataset', ('nocuts',)+spec, (), ()),
                  ]
        builder = resourcebuilder.ResourceBuilder(c, (), targets)
        builder.resolve_fuzzytargets()
        ns = namespaces.resolve(builder.rootns,
                  ('cuts', ('pdfsets',0), ('theories', 0), ('datasets', 0),))

        assert(ns['use_cuts']==True)
        assert(ns['dataset']=="ds: d1 (theory: th 1, cuts: True)" )
        ns = namespaces.resolve(builder.rootns,
                  ('nocuts', ('pdfsets',0), ('theories', 0), ('datasets', 0),))

        assert(ns['use_cuts']==False)
        assert(ns['dataset']=="ds: d1 (theory: th 1, cuts: False)" )
        ns = namespaces.resolve(builder.rootns,
                  (('pdfsets',0), ('theories', 0), ('datasets', 0),))

        assert(ns['use_cuts']==False)
        assert(ns['dataset']=="ds: d1 (theory: th 1, cuts: False)" )


if __name__ == '__main__':
    unittest.main()
