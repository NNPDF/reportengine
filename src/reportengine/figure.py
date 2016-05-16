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

import matplotlib.pyplot as plt

from reportengine.formattingtools import  get_nice_name

__all__ = ['figure', 'figuregen']




def savefig(fig, environment, spec, namespace, graph, *, suffix=''):

    #Remove the internal default namespace

    suffix = str(spec.function.__name__) + '_' + suffix
    name = get_nice_name(namespace, spec.nsspec[:-1], suffix)

    for path in environment.get_figure_paths(name):
        fig.savefig(str(path), bbox_inches='tight')
    plt.close(fig)

def savefiglist(figures, environment, spec, namespace, graph):
    print(spec.nsspec)
    for i, fig in enumerate(figures):
        savefig(fig, environment, spec, namespace, graph, suffix=str(i))


def figure(f):
    f.final_action = savefig
    return f




def figuregen(f):
    f.final_action = savefiglist
    return f