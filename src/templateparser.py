# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 14:58:12 2015

@author: zah
"""
import functools
import contextlib

import jinja2
import jinja2.runtime
from jinja2.exceptions import TemplateError

from resourcebuilder import ResourceError


class TemplateRecordError(ResourceError, TemplateError): pass

@functools.total_ordering
class TargetRecord:
    def __init__(self, recorder, name, args=None, kwargs=None):
        self.name = name
        self.recorder = recorder
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        for val in (*args, *kwargs.values()):
            if isinstance(val, TargetRecord):
                raise TemplateRecordError("Cannot determine the value of "
                                          "parameter inside a top"
                                          "level template: %s" % val.name)
        return type(self)(recorder=self.recorder, name=self.name,
                          args=args, kwargs=kwargs)

    def __iter__(self):
        raise TemplateRecordError("Cannot iterate a resource inside a top "
                                  "level template: %s" % self.name)

    def __eq__(self, other):
        raise TemplateRecordError("Cannot compare resources inside a top "
                                  "level template: %s" % self.name)

    def __lt__(self, other):
        raise TemplateRecordError("Cannot compare resources inside a top "
                                  "level template: %s" % self.name)

    def __bool__(self):
        raise TemplateRecordError("Cannot determine boolean value of a "
                                  "resource inside a top "
                                  "level template: %s" % self.name)

    def __str__(self):
        """Do not call this!"""
        #This is dangerous as it will produce wrong results if called
        #outside the the template. Maybe it would be better to use some other
        #name, and overwrite buitins.str in the template code context.
        if self.args is not None and self.kwargs is not None:
            if self.args:
                msg = ("Error at {0.name}. Positional arguments like {0.args} "
                       "are not aloowed inside a top-level template. "
                       "Use keyword arguments, such as "
                       "{0.name}(argname={0.args[0]},...)").format(self)
                raise TemplateRecordError(msg)
            target = {self.name: self.kwargs}
        else:
            target = self.name

        env_targets = self.recorder.environment.targets
        env_targets.append(target)

        return "<Provider {} args={} kwargs={}>".format(self.name, self.args,
                                                        self.kwargs)

class TargetSubs(TargetRecord):
    def __str__(self):
        return str(next(self.recorder.environment.results))

class TargetRecorder(jinja2.runtime.Context):

    record_class = TargetRecord

    def resolve(self, item):
        return self[item]

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        #TODO: Make sure we are not overwritting this
        if item in self.environment.globals:
            return self.environment.globals[item]
        record = self.record_class(self, item)
        return record

class TargetSubstituter(TargetRecorder):
    record_class = TargetSubs

class Environment(jinja2.Environment):
    """This class is the same as `jinja2.Environment` except that is adds a
    `fetch_mode` context manager, where the rendered templates register the
    variables and functions (with parameters) that will be called to
    render the template. This  is used to extract the target resources and
    perform the corresponding checks. Also it imposes some restrictions on
    what the template can do, which is OK because we don't want a lot of
    logic in the user templates (we can always use another environment to
    render complex objects like figures)."""

    @contextlib.contextmanager
    def _change_context(self, context_class):
        past_context = self.context_class
        self.context_class = context_class
        try:
            yield
        finally:
            self.context_class = past_context

    @contextlib.contextmanager
    def fetch_mode(self):
        self.targets = []
        with self._change_context(TargetRecorder):
            yield

    @contextlib.contextmanager
    def subs_mode(self, results):
        self.results = iter(results)
        with self._change_context(TargetSubstituter):
            yield

    def render_with_targets(self, template):
        with self.fetch_mode():
            template.render()
            results = yield self.targets
        with self.subs_mode(results):
            yield template.render()
