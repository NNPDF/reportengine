# -*- coding: utf-8 -*-
"""
Created on Thu May 12 16:07:25 2016

@author: Zahari Kassabov

Functions to drive reportengine, and report errors properly.
"""
import sys
import logging
import contextlib
import argparse
import inspect
import pathlib
import tempfile
import traceback
import os

from reportengine.resourcebuilder import ResourceBuilder, ResourceError
from reportengine.configparser import ConfigError, Config
from reportengine.environment import Environment
from reportengine import colors


log = logging.getLogger(__name__)
root_log = logging.getLogger()

class App:
    """Class that processes the config file and drives the entire application.
    It contains various hooks for concrete implementations to use."""

    environment_class = Environment
    config_class = Config

    default_style = None

    critical_message = "A critical error oucurred. It has been logged in %s"


    def __init__(self, name, default_providers):
        self.name = name
        self.default_providers = default_providers

    @property
    def argparser(self):
        parser = argparse.ArgumentParser(epilog="A reportengine application")
        parser.add_argument('config_yml',
                        help = "path to the configuration file")

        parser.add_argument('-o','--output', help="output folder where to "
                                         "store resulting plots and tables",
                        default='output')

        loglevel = parser.add_mutually_exclusive_group()

        loglevel.add_argument('-q','--quiet', help="supress INFO messages and C output",
                        action='store_true')

        loglevel.add_argument('-d', '--debug', help = "show debug info",
                          action='store_true')

        parser.add_argument('--formats', nargs='+', help="formats of the output figures",
                        default=('pdf',))

        parallel = parser.add_mutually_exclusive_group()
        parallel.add_argument('--parallel', action='store_true')
        parallel.add_argument('--no-parrallel', dest='parallel',
                              action='store_false')
        return parser

    def get_commandline_arguments(self):
        args = vars(self.argparser.parse_args())

        if args.get('quiet', False):
            level = logging.WARN
        elif args.get('debug', False):
            level = logging.DEBUG
        else:
            level = logging.INFO

        args['loglevel'] = level
        args['this_folder'] = self.this_folder()
        return args




    @classmethod
    def this_folder(cls):
        try:
            p = inspect.getfile(cls)
        except TypeError: #__main__ module
            return pathlib.Path('.')

        return pathlib.Path(p).parent

    def excepthook(self, etype, evalue, tb):
        print("\n----\n")
        print(colors.color_exception(etype, evalue, tb), file=sys.stderr)
        print("----\n")

        fd,name = tempfile.mkstemp(prefix=self.name + '-crash-', text=True)
        with os.fdopen(fd, 'w') as f:
            traceback.print_exception(etype, evalue, tb, file=f)



        root_log.critical(self.critical_message, colors.t.blue(name))


    def init_logging(self, args):
        root_log.setLevel(args['loglevel'])
        root_log.addHandler(colors.ColorHandler())

    def init_style(self, args):
        #Delay expensive import
        import matplotlib.pyplot as plt
        if args.get('style', False):
            try:
                plt.style.use(args['style'])
            except Exception as e:
                log.error("There was a problem reading the supplied style: %s" %e,
                     )
                sys.exit(1)
        elif self.default_style:
            plt.style.use(self.default_style)


    def init(self):
        args = self.get_commandline_arguments()
        self.init_logging(args)
        sys.excepthook = self.excepthook
        self.environment = self.make_environment(args)
        self.init_style(args)
        self.args = args

    def run(self):

        args = self.args
        environment = self.environment
        parallel = args['parallel']
        config_file = args['config_yml']

        try:
            with open(config_file) as f:
                try:
                    c = self.config_class.from_yaml(f, environment=environment)
                except ConfigError as e:
                    format_rich_error(e)
                    sys.exit(1)
        except OSError as e:
            log.error("Could not open configuration file: %s" % e)
            sys.exit(1)
        self.environment.init_output()

        try:
            actions = c.parse_actions_(c['actions_'])
        except ConfigError as e:
            format_rich_error(e)
            sys.exit(1)
        except KeyError as e:
            log.error("A key 'actions_' is needed in the top level of the config file.")
            sys.exit(1)

        providers = self.default_providers

        rb = ResourceBuilder(c, providers, actions, environment=self.environment)
        try:
            rb.resolve_targets()
        except ConfigError as e:
            format_rich_error(e)
            sys.exit(1)
        except ResourceError as e:
            with contextlib.redirect_stdout(sys.stderr):
                log.error("Cannot process a resource:")
                print(e)
            sys.exit(1)
        if parallel:
            rb.execute_parallel()
        else:
            rb.execute_sequential()

    def make_environment(self, args):
        env = self.environment_class(**args)
        return env



def format_rich_error(e):
    with contextlib.redirect_stdout(sys.stderr):
        log.error("Bad configuration encountered:")
        print(e)

def main():
    a = App()
    a.init()
    a.run()

if __name__ == '__main__':
    main()