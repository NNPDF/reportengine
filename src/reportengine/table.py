# -*- coding: utf-8 -*-
"""
Save generated tables.

Apply the decorators to functions returning a dataframe
and they will be saved in the correct path. If the providers return instead a
tuple (handle, df), the hanndle will be appended at the end of the file name
(but before the extension).

The tables are saved tab separated (i.e. the only reasonable way to write csv).

Otherwise, this works the same as figure.py.

Created on Mon May 16 11:36:13 2016

@author: Zahari Kassabov
"""
from reportengine.formattingtools import spec_to_nice_name
from reportengine.utils import add_highlight

__all__ = ('table', 'tablegen')


def savetable(df, environment, spec, namespace, graph, *, suffix=''):
    """Final action to save figures, with a nice filename"""

    name = spec_to_nice_name(namespace, spec, suffix)
    path = environment.table_folder / (name + '.csv')
    df.to_csv(str(path), sep='\t', na_rep='nan')

def savetablelist(figures, environment, spec, namespace, graph):
    """Final action to save lists of figures. It adds a numerical index as
    a suffix, for each figure in the generator."""

    for i, fig in enumerate(figures):
        savetable(fig, environment, spec, namespace, graph, suffix=str(i))

@add_highlight
def table(f):
    """Save the resulting table as a tab separated csv file after
    it is generated"""
    f.final_action = savetable
    return f
@add_highlight
def tablegen(f):
    """Save each table of the generator. See ``table``."""
    f.final_action = savetablelist
    return f
