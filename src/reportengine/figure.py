 # -*- coding: utf-8 -*-
"""
Save generated figures in the correct path. Use::

    @figure
    def provider(arg):
       return matplotlib.figure.Figure(...)

to have the figure be automatically saved in the correct path, once it is
constructed. Similarly use::

    @figuregen
    def provider(arg):
       for ...:
           yield matplotlib.figure.Figure(...)

to have the action applied to each element of a generator.

The figures will be automatically closed.

Created on Thu Mar 10 00:59:31 2016

@author: Zahari Kassabov
"""
import functools
import logging

import numpy as np

from reportengine.formattingtools import spec_to_nice_name
from reportengine.utils import add_highlight, normalize_name

__all__ = ['figure', 'figuregen']

log = logging.getLogger(__name__)

def _generate_markdown_link(path, caption=None):
    if caption is None:
        caption = path.suffix
    return f"[{caption}]({path})"


class Figure():
    def __init__(self, paths):
        self.paths = paths

    @property
    def as_markdown(self):
        # Prepare the anchor
        anchor_link_target = f'#{self.paths[0].stem}'
        # Prepare the link to the actual figures
        links = ' '.join(_generate_markdown_link(path) for path in self.paths) + ' '
        links += _generate_markdown_link(anchor_link_target, "#")
        retmd = f'![{links}]({self.paths[0]}){{{anchor_link_target}}} \n'
        return retmd

class InteractiveFigure():
    def __init__(self, paths, graph_obj):
        self.paths = paths
        self.graph_obj = graph_obj

    @property
    def as_markdown(self):
        # Prepare the anchor
        anchor_link_target = f'#{self.paths[0].stem}'
        # Prepare the link to the actual figures
        plot = self.graph_obj.to_html(include_plotlyjs='cdn', full_html=False)
        plot = ' '.join(plot.split())
        links = ' '.join(_generate_markdown_link(path) for path in self.paths) + ' '
        links += _generate_markdown_link(anchor_link_target, "#")
        # https://stackoverflow.com/questions/14051715/markdown-native-text-alignment#comment60291976_19938870
        retmd = f'{plot}\n <p style="text-align: center;">{links}</p>\n'
        return retmd

def saveinteractivefig(fig, *, paths, output, suffix=''):
    """Save a plotly figure as html for interactive plots
    """
    outpaths = []
    for path in paths:
        if suffix:
            suffix = normalize_name(suffix)
            path = path.with_name('_'.join((path.stem, suffix)) + path.suffix)
        fig.write_html(path, include_plotlyjs='cdn')
        outpaths.append(path.relative_to(output))
    return InteractiveFigure(outpaths, fig)


def prepare_interactive_paths(*, spec, namespace, environment, **kwargs):
    paths = environment.get_interactive_figure_paths(spec_to_nice_name(namespace, spec))
    return {'paths': list(paths), 'output': environment.output_path}


def prepare_paths(*,spec, namespace, environment ,**kwargs):
    paths = environment.get_figure_paths(spec_to_nice_name(namespace, spec))
    #list is important here. The generator gives a hard to trace bug when
    #running in parallel
    return {'paths':list(paths), 'output':environment.output_path}



def savefig(fig, *, paths, output ,suffix=''):
    """Final action to save figures, with a nice filename"""

    outpaths = []
    for path in paths:
        if suffix:
            suffix = normalize_name(suffix)
            path = path.with_name('_'.join((path.stem, suffix)) + path.suffix)
        log.debug("Writing figure file %s" % path)

        #Numpy can produce a lot of warnings while working on producing figures
        with np.errstate(invalid='ignore'):
            fig.savefig(str(path), bbox_inches='tight')
        outpaths.append(path.relative_to(output))

    return Figure(outpaths)

def savefiglist(figures, paths, output):
    """Final action to save lists of figures. It adds a numerical index as
    a suffix, for each figure in the generator."""

    res = []
    res.append('<div class="figiterwrapper">')

    for i, fig in enumerate(figures):
        #Support tuples with (suffix, figure)
        if isinstance(fig, tuple):
            fig, suffix = fig
        else:
            suffix = str(i)
        suffix = normalize_name(suffix)
        p_base = [paths[i].relative_to(output) for i in range(len(paths))]
        p_full = [
            str(p.with_name('_'.join((p.stem, suffix)) + p.suffix)) for p in p_base
        ]
        ref = savefig(fig, paths=paths, output=output, suffix=suffix)
        html = (
            f'\n<div>'
            f'{ref.as_markdown}'
            '</div>\n'
        )
        res.append(html)
    res.append("</div>")
    return res

@add_highlight
def interactive_figure(f):
    f.prepare = prepare_interactive_paths
    f.final_action = saveinteractivefig
    return f

# note: @add_highlight makes figure and figuregen be decorators

@add_highlight
def figure(func):
    """
    Decorator that enables the mechanism for writing to disk figures from
    functions returning a matplotlib ``Figure``.

    It adds special  ``prepare`` and `final_action` attributes to decorated
    functions.
    """
    func.prepare = prepare_paths
    func.final_action = savefig
    return func

@add_highlight
def figuregen(func):
    """
    Decorator that enables the mechanism for writing to disk figures from
    generators yielding matplotlib ``Figure`` instances.

    It adds special  ``prepare`` and `final_action` attributes to decorated
    functions.
    """
    func.prepare = prepare_paths
    func.final_action = savefiglist

    # TODO: Ideally this would only apply if reportengine is executing the
    # function.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return list(func(*args, **kwargs))

    return wrapper
