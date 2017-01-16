#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 10:19:59 2017

@author: zah
"""

from reportengine.resourcebuilder import ResourceBuilder
from reportengine.report import Config
from reportengine.environment import Environment
from reportengine import namespaces
import reportengine.report

expected_parsed = (
"""This is a test with title My report
===================================

ñ


### Another title, inside l: First
Yet world stays the same:
ñ

But can get repeated:
ñ
ñ

Can nest even more:

####Nested
See?

####Nested
See?


This was the previous title: First


### Another title, inside l: Second
Yet world stays the same:
ñ

But can get repeated:
ñ
ñ

Can nest even more:

####Nested
See?

####Nested
See?


This was the previous title: Second



And this the original title My report.

Done."""
                   )

def test_processing(tmpdir):
    inp = {'template': 'test_new.md', 'config_rel_path':'.',
           'report_title':{
                'title': "My report",
            },
            'title': "Bad title",

           'world': "ñ",
           'l': [{'title': "First"}, {'title': "Second"}],
           'nested': {'title': "Nested"},

           }

    spec = ('report_title',)
    rb = ResourceBuilder(Config(inp), reportengine.report,
                         fuzzytargets=[('template', spec, (), ())],
                         environment=Environment(output=str(tmpdir)))
    rb.resolve_fuzzytargets()
    rb.execute_sequential()


    res = namespaces.resolve(rb.rootns, spec)['template']
    assert res== expected_parsed