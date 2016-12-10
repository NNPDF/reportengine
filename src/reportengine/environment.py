# -*- coding: utf-8 -*-
"""
Created on Thu Mar 10 00:09:52 2016

@author: Zahari Kassabov
"""
import pathlib
import logging
from collections import Sequence

log = logging.getLogger(__name__)

class EnvironmentError_(Exception): pass

available_figure_formats = {
 'eps': 'Encapsulated Postscript',
 'jpeg': 'Joint Photographic Experts Group',
 'jpg': 'Joint Photographic Experts Group',
 'pdf': 'Portable Document Format',
 'pgf': 'PGF code for LaTeX',
 'png': 'Portable Network Graphics',
 'ps': 'Postscript',
 'raw': 'Raw RGBA bitmap',
 'rgba': 'Raw RGBA bitmap',
 'svg': 'Scalable Vector Graphics',
 'svgz': 'Scalable Vector Graphics',
 'tif': 'Tagged Image File Format',
 'tiff': 'Tagged Image File Format'
}

class Environment:
    def __init__(self, *, output, formats=('pdf',),
                 default_figure_format=None, loglevel=logging.DEBUG, **kwargs):
        self.output_path = pathlib.Path(output).absolute()
        self.figure_formats = formats
        self._default_figure_format = default_figure_format
        self.loglevel = loglevel
        self.extra_args = kwargs

    @property
    def figure_formats(self):
        return self._figure_formats

    @property
    def default_figure_format(self):
        if self._default_figure_format is None:
            return self.figure_formats[0]
        else:
            return self._default_figure_format

    @default_figure_format.setter
    def default_figure_format(self, fmt):
        self._default_figure_format = fmt

    @figure_formats.setter
    def figure_formats(self, figure_formats):
        if isinstance(figure_formats, str):
            figure_formats = (figure_formats,)
        if not isinstance(figure_formats, Sequence):
            raise EnvironmentError_("Bad figure format specification: %s. "
                                    "Must be a string or a list." % figure_formats)

        bad_formats = set(figure_formats) - set(available_figure_formats)
        if bad_formats:
            raise EnvironmentError_("The following are not valid figure"
                    "formats %s: It must be one of %s" % (bad_formats,
                                                     available_figure_formats))
        self._figure_formats = figure_formats

    def init_output(self):
        if self.output_path.exists():
            log.warn("Output folder exists: %s Overwritting contents" %
                     self.output_path)
        else:
            self.output_path.mkdir()
        #TODO: Decide if we want to create these always or not
        self.figure_folder = (self.output_path/'figures')
        self.figure_folder.mkdir(exist_ok=True)

        self.table_folder = (self.output_path/'tables')
        self.table_folder.mkdir(exist_ok=True)

    def get_figure_paths(self, handle):
        for fmt in self.figure_formats:
            yield self.figure_folder / (handle + '.' + fmt)