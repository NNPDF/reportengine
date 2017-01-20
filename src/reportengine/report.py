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

import os.path as osp
import logging
import subprocess
import shutil

import jinja2
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader
from jinja2 import BaseLoader, TemplateNotFound


from . import configparser
from . resourcebuilder import target_map, FuzzyTarget
from . import namespaces
from . import templateparser
from . formattingtools import spec_to_nice_name
from . checks import make_check, CheckError
from . import styles

log = logging.getLogger(__name__)

__all__ = ('report', 'Config')


class AbsLoader(BaseLoader):
    def get_source(self, environment, template):
        path = template
        if not osp.exists(path):
            raise TemplateNotFound(template)
        mtime = osp.getmtime(path)
        with open(path) as f:
            source = f.read()
        return source, path, lambda: mtime == osp.getmtime(path)


class JinjaEnv(jinja2.Environment):

    def preprocess(self, source, name=None, filename=None):
        if filename:
            log.debug("Processing template %s" % osp.abspath(filename))

        root = {}
        d = root
        d['targets'] = {}
        d['withs'] = {}

        parents = []

        lines = source.splitlines(keepends=True)
        it = templateparser.get_targets_and_replace(lines)
        while True:
            try:
                tp, value = next(it)
            except StopIteration as e:
                rval = e.value
                break
            if tp == 'target':
                d['targets'][value] = []

            if tp == 'with':
                parents.append(d)
                if not value in d['withs']:
                    newd = {}
                    newd['targets'] = {}
                    newd['withs'] = {}
                    d['withs'][value] = newd

                d = d['withs'][value]

            if tp=='endwith':
                try:
                    d = parents.pop()
                except IndexError:
                    it.throw(templateparser.BadToken("Found endwith with no matching with."))

        if parents:
            raise templateparser.BadTemplate("Reched the end of the file and "
            "didn't find a closing 'endwith' tag for all the with tags: The "
            "following remain open:\n%s." % '\n'.join(str(tuple(parent['withs'].keys())) for parent in parents))

        self._root = root
        return rval

@make_check
def _check_pandoc(*args, **kwargs):
    if not shutil.which('pandoc'):
        raise CheckError("Could not find pandoc. Please make sure it's installed with e.g.\n\n"
        "conda install pandoc -c conda-forge")

@make_check
def _nice_name(*,callspec, ns, **kwargs):
    if ns['out_filename'] is None:
        ns['out_filename'] = spec_to_nice_name(ns, callspec, 'md')


@_check_pandoc
@_nice_name
def report(template, output_path, out_filename=None):
    """Generate a report from a template. Parse the template, process
    the actions, produce the final report with jinja and call pandoc to
    generate the final output.
    """

    if out_filename is None:
        out_filename = 'report.md'

    path = output_path / out_filename

    log.debug("Writing report file %s" % path)
    with path.open('w') as f:
        f.write(template)

    #TODO: Add options to customize?
    style = 'report.css'

    pandoc_path = path.with_name(path.stem + '.html')

    args = ['pandoc', str(path),
            '-o', str(pandoc_path),
            '-s' ,'-S' ,'--toc',
            #http://stackoverflow.com/questions/39220389/embed-indented-html-in-markdown-with-pandoc
            '-f', 'markdown-markdown_in_html_blocks+raw_html',
            '--to', 'html5',
            '--css', style]
    try:
        subprocess.run(args, check=True, universal_newlines=True)
    except Exception as e:
        log.error("Could not run pandoc to process the report: %s" % e)
        raise

    log.debug("Report written to %s" % pandoc_path.absolute())
    styles.copy_style(style, str(output_path))
    import webbrowser
    webbrowser.open('file://'+ str(pandoc_path))

    return pandoc_path.relative_to(output_path)

report.highlight = 'report'

#TODO: The stucture of this is suboptimal. Decide if we want several claseses.

class Config(configparser.Config):
    @configparser.explicit_node
    def parse_template(self, template:str, config_rel_path):
        """Filename specifying a template for a report."""

        absloader = AbsLoader()
        fsloader = FileSystemLoader(str(config_rel_path))
        pkgloader = PackageLoader('reportengine')

        loader = ChoiceLoader([absloader,
                               fsloader,
                               pkgloader])

        listloader = ChoiceLoader([fsloader, pkgloader])
        env = JinjaEnv(loader=loader)
        try:
            temp = env.get_template(template)
        #Ridiculous error message
        except TemplateNotFound as e:
            raise configparser.ConfigError("Could not find template '%s'" %
                                           template, template,
                                           listloader.list_templates()) from e
        except templateparser.BadTemplate as e:
            raise configparser.ConfigError("Could not process the template %s: %s" % (template, e)) from e
        return report_generator(env._root, temp)

def as_markdown(obj):

    if hasattr(obj, 'as_markdown'):
        return obj.as_markdown

    if isinstance(obj, list):
        return '\n'.join(as_markdown(elem) for elem in obj)

    return str(obj)


class report_generator(target_map):
    def __init__(self, root, template):
        self.template = template
        self.root = root

    def __call__(self, ns, nsspec):


        #Trim the private namespace
        spec = nsspec[:-1]

        def format_collect_fuzzyspec(ns, key, fuzzyspec, currspec=None):
            res = namespaces.collect_fuzzyspec(ns, key, fuzzyspec, currspec)
            return as_markdown(res)

        return self.template.render(ns=ns, spec = spec,
                   collect_fuzzyspec=format_collect_fuzzyspec,
                   expand_fuzzyspec=namespaces.expand_fuzzyspec,
               )
