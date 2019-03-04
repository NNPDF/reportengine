"""
API for resource engine
"""

import logging
import importlib

from reportengine.resourcebuilder import ResourceBuilder
from reportengine.resourcebuilder import FuzzyTarget
from reportengine.configparser import Config
from reportengine.environment import Environment

log = logging.getLogger(__name__)

class API:
    """The API class"""
    config_class = Config
    environment_class = Environment

    def __init__(self, providers, **kwargs):
        #TODO: need to add providers here
        prov_list = []
        for prov in providers:
            try:
                mod = importlib.import_module(prov)
            except ImportError:
                #TODO: the code this is copying is wrong and should be changed to have prov here
                log.error("Could not import module %s", prov)
                raise
            prov_list.append(mod)
        self.provider_loaded = prov_list
        self.loadedenv = self.environment_class(**kwargs)

    def __call__(self, actions: str, **kwargs):
        fuzzytarg = [FuzzyTarget(actions, (), (), ())]
        c = self.config_class(kwargs, environment=self.loadedenv)
        builder = ResourceBuilder(c, self.provider_loaded, fuzzytarg)
        builder.resolve_fuzzytargets()
        builder.execute_sequential(perform_final=False)
        res = builder.rootns[actions]
        return res

    def __getattr__(self, name):
        print(type(name))
        def closure(**kwargs):
            return self.__call__(name, **kwargs)
        return closure
