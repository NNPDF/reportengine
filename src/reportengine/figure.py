# -*- coding: utf-8 -*-
"""
Created on Thu Mar 10 00:59:31 2016

@author: Zahari Kassabov
"""
import functools
import inspect

import matplotlib.pyplot as plt

i = 0

def figure(f):
    s = inspect.signature(f)
    @functools.wraps(f)
    def f_(*args, environment, **kwargs):
        global i
        fig = f(*args, **kwargs)
        i += 1
        for path in environment.get_figure_paths(str(i)):
            fig.savefig(str(path), bbox_inches='tight')
        plt.close(fig)

    params = (*s.parameters.values(), inspect.Parameter('environment',
                                            inspect.Parameter.KEYWORD_ONLY))

    f_.__signature__ = inspect.Signature(parameters=params)
    return f_
