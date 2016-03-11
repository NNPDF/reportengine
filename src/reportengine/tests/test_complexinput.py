# -*- coding: utf-8 -*-
"""
Created on Fri Mar  4 21:09:40 2016

@author: Zahari Kassabov
"""
import unittest

from reportengine import namespaces, configparser, utils

inp = {'pdfsets': ['a', 'b'], 'theories': [1,2], 'datasets': ['d1', 'd2']}

class Config(configparser.Config):
    @configparser.element_of('pdfsets')
    def parse_pdf(self, pdf):
        return 'PDF: ' + pdf

    @configparser.element_of('theories')
    def parse_theory(self, theory):
        return 'th ' + str(theory)

    @configparser.element_of('datasets')
    def parse_dataset(self, ds,  theory):
        return 'ds: {ds} (theory: {theory})'.format(**locals())


class TestSpec(unittest.TestCase):
    def test_nsexpand(self):
        spec = ('pdfsets', 'theories', 'datasets')
        c = Config(inp)
        ns = utils.ChainMap()
        specs = c.process_fuzzyspec(spec, ns=ns)
        self.assertEqual(len(specs), 8)
        datasets = [
              'ds: d1 (theory: th 1)',
              'ds: d2 (theory: th 1)',
              'ds: d1 (theory: th 2)',
              'ds: d2 (theory: th 2)',
              'ds: d1 (theory: th 1)',
              'ds: d2 (theory: th 1)',
              'ds: d1 (theory: th 2)',
              'ds: d2 (theory: th 2)']
        for spec, ds in zip(specs, datasets):
            self.assertEqual(namespaces.resolve(ns, spec)['dataset'], ds)


if __name__ == '__main__':
    unittest.main()
