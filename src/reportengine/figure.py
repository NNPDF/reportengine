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

__all__ = ['figure', 'figuregen']

#TODO: This is to be heavily extended and changed. We want better
#names for the output files, and
#also to do nothing by default, outside of the reportengine loop. For that
#we need a sensible provider protocol.

i = 0

def savefig(fig, spec ,environment):
    global i
    i += 1
    for path in environment.get_figure_paths(str(i)):
        fig.savefig(str(path), bbox_inches='tight')
    plt.close(fig)

def savefiglist(figures, spec, environment):
    for fig in figures:
        savefig(fig, spec ,environment)


def figure(f):
    f.final_action = savefig
    return f




def figuregen(f):
    f.final_action = savefiglist
    return f