# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 10:00:19 2016

@author: Zahari Kassabov
"""
import pytest

from reportengine import app
from reportengine.tests.utils import tmp

runcard =\
"""
a: 1
b: 2

template_text: |
    % A test
    {@a@} + {@b@}

actions_:
    - report
"""

bad_runcard =\
"""
a: 1
b: 2


actions_:
    - bad_provider
"""


class TypoException(Exception):
    pass

class Typo:
    @staticmethod
    def bad_provider(a):
        raise TypoException(a)

def test_app_runs(tmp):
    runcardfile = tmp/'runcard.yaml'
    with open(runcardfile, 'w') as f:
        f.write(runcard)
    args = [str(runcardfile), '-o', str(tmp/'output')]
    a = app.App('test', ['reportengine.report'])
    a.main(cmdline=args)

    helpargs = ['--help', 'report']
    try:
        a.main(cmdline=helpargs)
    except SystemExit as e:
        assert e.args == (0,)

    badruncardfile = tmp/'bad.yaml'
    with open(badruncardfile, 'w') as f:
        f.write(bad_runcard)
    bad_app = app.App('othertest', [Typo()])
    badargs = [str(badruncardfile), '--debug' , '-o', str(tmp/'output')]
    with pytest.raises(TypoException):
        bad_app.main(badargs)


