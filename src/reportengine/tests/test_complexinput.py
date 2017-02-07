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
       'fits': ['NLO', 'NNLO'],

       'description': {'from_': 'fit'},

       'maps': [
          {'fit': 'A',
           'pdfsets': ['X', {'from_': 'fit'}],
          },
          {'fit': 'B',
           'pdfsets': ['X', {'from_': 'fit'}],
          },
          {'fit': 'C',
           'pdfsets': ['X', {'from_': 'fit'}],
          },

       ],
       }

class Fit:
    def __init__(self, description):
        self.description = description

    def as_input(self):
        return {'description': self.description, 'pdf': self.description}

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

    def parse_template(self, template, rel_path):
        return template

    @configparser.element_of('fits')
    def parse_fit(self, description):
        return Fit(description)

class Providers:
    def report(self, template):
        return template

    def plot_a_pdf(pdf):
        return "PLOT OF " + str(pdf)



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

    def test_gets_dependencies(self):
        inp = {
         'template': 'template',
         'mapping': {'template': 'othertemplate'},
         #'rel_path': 'cochambres'
        }
        c = Config(inp)
        targets =  [
                    FuzzyTarget('report', (), (), ()),
                    FuzzyTarget('report', ('mapping',), (), ())
                   ]
        builder = resourcebuilder.ResourceBuilder(c, Providers(), targets)
        builder.rootns.update({'rel_path':'examples'})
        builder.resolve_fuzzytargets()
        builder.execute_sequential()
        assert namespaces.resolve(builder.rootns, ('mapping',))['report'] == 'othertemplate'

    def test_iter_from(self):
        c = Config(inp)
        targets = [FuzzyTarget('description', ('fits',), (), ())]
        builder = resourcebuilder.ResourceBuilder(c, Providers(), targets)
        builder.resolve_fuzzytargets()
        builder.execute_sequential()
        s1 = [('fits', 0)]
        s2 = [('fits', 1)]
        assert namespaces.resolve(builder.rootns, s1)['description'] == 'NLO'
        assert namespaces.resolve(builder.rootns, s2)['description'] == 'NNLO'
        assert 'description' not in builder.rootns

    def test_nested_from(self):
        c = Config(inp)
        targets = [FuzzyTarget('plot_a_pdf', ('maps','pdfsets'), (), ())]
        builder = resourcebuilder.ResourceBuilder(c, Providers(), targets)
        builder.resolve_fuzzytargets()
        builder.execute_sequential()
        s0 = (('maps', 0), )
        s1 = (('maps', 1), )
        s2 = (('maps', 2), )

        assert namespaces.resolve(builder.rootns, s0)['pdfsets'] == ['PDF: X', 'PDF: A']
        assert namespaces.resolve(builder.rootns, s1)['pdfsets'] == ['PDF: X', 'PDF: B']
        assert namespaces.resolve(builder.rootns, s2)['pdfsets'] == ['PDF: X', 'PDF: C']





if __name__ == '__main__':
    unittest.main()
