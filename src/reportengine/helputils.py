# -*- coding: utf-8 -*-
"""
Utils for printing documentation and formatting it properly.

Created on Fri Jul  1 11:40:46 2016

@author: Zahari Kassabov
"""
import textwrap
import inspect

from reportengine.utils import get_providers
from reportengine.colors import t

def sane_dedent(txt):
    """Leave the first line alone and dedent the rest"""
    first_line = txt.find('\n')
    if first_line == -1:
        return txt
    else:
        return txt[:first_line+1] + textwrap.dedent(txt[first_line+1:])

def get_parser_type(f):
    """Get a string corresponding to the valid type of a parser function"""
    sig = inspect.signature(f)

    types = {str: 'string', float:'float', bool:'boolean', list:'list',
             int:'int',
             dict:'mapping', type(None): 'none'}
    try:
        param_tp = list(sig.parameters.values())[1].annotation
    except IndexError:
        return ''
    if param_tp is sig.empty:
        return ''

    if isinstance(param_tp, tuple):
        s = " or ".join(str(types.get(k,k)) for k in param_tp)
    else:
        s = types.get(param_tp, param_tp)
    return '(%s)' % s



def format_config(config_class):
    all_parsers = config_class.get_all_parse_functions()
    lines = []
    garbage_len = len(t.bold(''))
    wrap = textwrap.TextWrapper(width=70+garbage_len, initial_indent='    ',
                                subsequent_indent='  ')
    for val, function in all_parsers.items():

        #Get the docs
        doc = function.__doc__
        if doc is None:
            doc = ''

        #Get the recognized type
        tp = get_parser_type(function)



        line = "%s%s: %s"%(t.bold(val), tp, sane_dedent(doc))
        lines.append(wrap.fill(line))


    return '\n\n'.join(lines)

def format_provider(provider):
    moddoc = provider.__doc__
    if moddoc is None:
        moddoc = ''

    functions = get_providers(provider)
    lines = []
    garbage_len = len(t.bold(''))
    wrap = textwrap.TextWrapper(width=70+garbage_len, initial_indent='    ',
                                subsequent_indent='  ')

    for val, function in functions.items():

        #Get the docs
        doc = function.__doc__
        if doc is None:
            doc = ''

        #Get the recognized type
        tp = get_parser_type(function)



        line = "%s%s: %s"%(t.bold(val), tp, sane_dedent(doc))
        lines.append(wrap.fill(line))


    lines = '\n\n'.join(lines)



    s = ("{moddoc}\n"
        "The following providers are defined in this module:\n\n"
        "{lines}".format(moddoc = moddoc, lines=lines))
    return s
