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
import importlib

from reportengine.resourcebuilder import ResourceBuilder, ResourceError
from reportengine.configparser import ConfigError, Config
from reportengine.environment import Environment
from reportengine import colors
from reportengine import helputils


log = logging.getLogger(__name__)
root_log = logging.getLogger()

class ArgumentHelpAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 config_class = None,
                 help=None):

        self.config_class = config_class
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs='?',
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            parser.print_help()
        elif values=='config':
            txt = "The following keys of the config file have a special meaning:\n"
            print(txt)
            print(helputils.format_config(self.config_class))

        parser.exit()

class ArgparserWithProviderDescription(argparse.ArgumentParser):

    def __init__(self, providers, *args, **kwargs):
        self.__providers = providers
        self.__text_description = ''
        super().__init__(*args, **kwargs)

    @property
    def description(self):

        modules = '\n'.join(' - %s' % provider for provider in self.__providers)

        provider_description = (
"""The installed provider modules are:

{modules}

Use {t.bold}{prog} --help{t.normal} {t.blue}<provider module>{t.normal} to get specific information about actions
in the module.

Use {t.bold}{prog} --help{t.normal} {t.blue}<action>{t.normal} to get specific information about the action.

Use {t.bold}{prog} --help config{t.normal} to get information on the parseable resources in the config
file.
"""
        ).format(modules=modules, t=colors.t, prog=self.prog)
        return self.__text_description + provider_description

    @description.setter
    def description(self, txt):
        if txt:
            self.__text_description = txt
        else:
            self.__text_description = ''

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
        parser = ArgparserWithProviderDescription(self.default_providers,
                      epilog="A reportengine application",
                      formatter_class=argparse.RawDescriptionHelpFormatter,
                      add_help=False
                      )

        parser.add_argument('config_yml',
                        help = "path to the configuration file")

        parser.add_argument('-o','--output', help="output folder where to "
                                         "store resulting plots and tables",
                        default='output')

        loglevel = parser.add_mutually_exclusive_group()

        loglevel.add_argument('-q','--quiet', help="supress INFO messages",
                        action='store_true')

        loglevel.add_argument('-d', '--debug', help = "show debug info",
                          action='store_true')

        parser.add_argument('--style',
                        help='matplotlib style file to override the built-in one.',
                        default=None)

        parser.add_argument('--formats', nargs='+', help="formats of the output figures",
                        default=('pdf',))

        parser.add_argument('-x', '--extra-providers', nargs='+',
                            help="additional providers from which to "
                            "load actions. Must be an importable specifiaction.")

        parallel = parser.add_mutually_exclusive_group()
        parallel.add_argument('--parallel', action='store_true',
                              help="execute actions in parallel")
        parallel.add_argument('--no-parrallel', dest='parallel',
                              action='store_false')

        parser.add_argument('-h', '--help', action=ArgumentHelpAction,
                            config_class=self.config_class)

        return parser

    def init_providers(self, args):
        extra_providers = args['extra_providers']
        if extra_providers is None:
            extra_providers = []
        maybe_names = reversed(self.default_providers + extra_providers)
        providers = []
        for mod in maybe_names:
            if isinstance(mod, str):
                try:
                    mod = importlib.import_module(mod)
                except ImportError:
                    log.error("Could not import module %s", mod)
                    sys.exit(1)
            providers.append(mod)
        self.providers = providers


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
        self.init_providers(args)
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

        providers = self.providers

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

        try:
            if parallel:
                rb.execute_parallel()
            else:
                rb.execute_sequential()
        except KeyboardInterrupt:
            print(colors.t.bold_red("Interrupted by user. Exiting."), file=sys.stderr)
            exit(1)

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