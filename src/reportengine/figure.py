# -*- coding: utf-8 -*-
"""
Created on Thu Mar 10 00:59:31 2016

@author: Zahari Kassabov
"""
import functools
import inspect

import matplotlib.pyplot as plt

#TODO: This is to be heavily extended and changed. We want better
#names for the output files, and
#also to do nothing by default, outside of the reportengine loop. For that
#we need a sensible provider protocol.

i = 0

def savefig(fig, environment):
    global i
    i += 1
    for path in environment.get_figure_paths(str(i)):
        fig.savefig(str(path), bbox_inches='tight')
    plt.close(fig)



def figure(f):
    s = inspect.signature(f)
    @functools.wraps(f)
    def f_(*args, environment, **kwargs):
        fig = f(*args, **kwargs)
        savefig(fig, environment)

    params = (*s.parameters.values(), inspect.Parameter('environment',
                                            inspect.Parameter.KEYWORD_ONLY))

    f_.__signature__ = inspect.Signature(parameters=params)
    return f_

def figuregen(f):
    s = inspect.signature(f)
    @functools.wraps(f)
    def f_(*args, environment, **kwargs):
        figures = f(*args, **kwargs)
        for fig in figures:
            savefig(fig, environment)

    params = (*s.parameters.values(), inspect.Parameter('environment',
                                            inspect.Parameter.KEYWORD_ONLY))

    f_.__signature__ = inspect.Signature(parameters=params)
    return f_