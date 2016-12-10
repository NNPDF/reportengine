 # -*- coding: utf-8 -*-
"""
Save generated figures in the correct path. Use::

    @figure
    def provider(arg):
       return plt.figure(...)

to have the figure be automatically saved in the correct path, once it is
constructed. Similarly use::

    @figuregen
    def provider(arg):
       for ...:
           yield plt.figure(...)

to have the action applied to each element of a generator.

The figures will be automatically closed.

Created on Thu Mar 10 00:59:31 2016

@author: Zahari Kassabov
"""
import logging

import matplotlib.pyplot as plt

from reportengine.formattingtools import  spec_to_nice_name
from reportengine.utils import add_highlight, normalize_name

__all__ = ['figure', 'figuregen']

log = logging.getLogger(__name__)

def prepare_paths(*,spec, namespace, environment ,**kwargs):
    paths = environment.get_figure_paths(spec_to_nice_name(namespace, spec))
    #list is important here. The generator gives a hard to trace bug when
    #running in parallel
    return {'paths':list(paths)}

def savefig(fig, *, paths, suffix=''):
    """Final action to save figures, with a nice filename"""
    for path in paths:
        if suffix:
            suffix = normalize_name(suffix)
            path = path.with_name('_'.join((path.stem, suffix)) + path.suffix)
        log.debug("Writing figure file %s" % path)
        fig.savefig(str(path), bbox_inches='tight')
    plt.close(fig)

def savefiglist(figures, paths):
    """Final action to save lists of figures. It adds a numerical index as
    a suffix, for each figure in the generator."""

    for i, fig in enumerate(figures):
        #Support tuples with (suffix, figure)
        if isinstance(fig, tuple):
            fig, suffix = fig
        else:
            suffix = str(i)
        savefig(fig, paths=paths, suffix=suffix)

@add_highlight
def figure(f):
    f.prepare = prepare_paths
    f.final_action = savefig
    return f

@add_highlight
def figuregen(f):
    f.prepare = prepare_paths
    f.final_action = savefiglist
    return f