#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools for generating reports. The basic job of this module is to extract
actions from templates and process them in order to obtaint the report.

The actions are extracted from special tags in the template file:

{@act@} will extract the action 'act'. For example

{@plot_pdfs@}

would search for the necessary inputs in the configuration
(i.e. 'pdfs' and 'Q'), execute the action
(after checking for correctness) with
those parameters and finally, substitute the special text with valid
markdown that results in the images appearing on the report.


{@namspace::othernamespace act@} Generate an action threading over each
of the values in the namespace. For example, if the special text is

{@theoryids::pdfs experiment_chi2table@}

the result will be a table for each theoryid and each pdf.

{@namespace act(param=val, otherparam=othervalue)@} This way one can
specify parameters for the action.


"""
from __future__ import generator_stop

from os.path import exists, getmtime
import logging
import subprocess
import shutil

import jinja2
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader
from jinja2 import BaseLoader, TemplateNotFound, Environment


from . import configparser
from . resourcebuilder import target_map, Target
from . import templateparser
from . formattingtools import spec_to_nice_name
from . checks import make_check, CheckError

log = logging.getLogger(__name__)

__all__ = ('report', 'Config')


class AbsLoader(BaseLoader):
    def get_source(self, environment, template):
        path = template
        if not exists(path):
            raise TemplateNotFound(template)
        mtime = getmtime(path)
        with open(path) as f:
            source = f.read()
        return source, path, lambda: mtime == getmtime(path)


class JinjaEnv(jinja2.Environment):
    def preprocess(self, source, name=None, filename=None):
        targets = []
        it = templateparser.get_targets_and_replace(source.splitlines(True))
        while True:
            try:
                targets.append(next(it))
            except StopIteration as e:
                rval = e.value
                break
        self._targets = targets
        return rval

def prepare_path(*,spec, namespace, environment ,**kwargs):
    path = environment.output_path/(spec_to_nice_name(namespace, spec) + '.md')
    #list is important here. The generator gives a hard to trace bug when
    #running in parallel
    return {'path':path}

@make_check
def _check_pandoc(*args, **kwargs):
    if not shutil.which('pandoc'):
        raise CheckError("Could not find pandoc. Please make sure it's installed.")



#TODO: Should/could this do anything?
def report(template):
    """Generate a report from a template. Parse the template, process
    the actions, produce the final report with jinja and call pandoc to
    generate the final output."""
    return template

def savereport(res, *, path):
    log.debug("Writing report file %s" % path)
    with path.open('w') as f:
        f.write(res)

    pandoc_path = path.with_name(path.stem + '.html')
    try:
        subprocess.check_output(['pandoc', str(path), '-o', str(pandoc_path), '-S' ,'--toc'],
                                universal_newlines=True)
    except Exception as e:
        log.error("Could not run pandoc to process the report: %s" % e)
    else:
        import webbrowser
        webbrowser.open(str(pandoc_path))

    return path

report.prepare = prepare_path
report.final_action = savereport
report.highlight = 'report'



#TODO: The stucture of this is suboptimal. Decide if we want several claseses.

class Config(configparser.Config):
    @configparser.explicit_node
    def parse_template(self, template:str):
        """Filename specifying a template for a report."""

        loader = ChoiceLoader([AbsLoader(), PackageLoader('reportengine')])
        env = JinjaEnv(loader=loader)
        try:
            temp = env.get_template(template)
        except TemplateNotFound as e:
            raise configparser.ConfigError(e)
        return report_generator(env._targets, temp)


def prepare_save(*,spec, namespace, environment ,**kwargs):
    return {'environment': environment}


def as_markdown(obj):
    if isinstance(obj, list):
        return '\n'.join(as_markdown(elem) for elem in obj)
    if hasattr(obj, 'as_markdown'):
        return obj.as_markdown
    return str(obj)


class report_generator(target_map):
    def __init__(self, targets, template):
        self.template = template
        super().__init__(targets)

    def __call__(self, ns):
        def resolve_target_vals(target):
            return self.resolve_target_vals(ns, target)
        return self.template.render(Target=Target, resolve_target_vals=resolve_target_vals)


    def resolve_target_vals(self, ns ,target_spec):
        l = ns[target_map.targetlenskey][target_spec]

        results = [ns[target_map.resultkey][(target_spec,i)] for i in range(l)]
        return '\n'.join(as_markdown(obj) for obj in results)



