from reportengine import configparser
from reportengine import api

FILTER_DEFAULTS = {'highpass': [8, 9, 10], 'lowpass': [1, 2, 3]}


class StubConfig(configparser.Config):
    @configparser.record_from_defaults
    def parse_filter_defaults(self, spec):
        return spec

    def load_default_filter_defaults(self, spec):
        return FILTER_DEFAULTS[spec]

    def produce_actual_filter(
        self, filter_defaults, filter_defaults_recorded_spec_=None
    ):
        if filter_defaults_recorded_spec_ is not None:
            return filter_defaults_recorded_spec_[filter_defaults]
        print(filter_defaults)
        return self.load_default_filter_defaults(filter_defaults)


class Providers:
    def data(self, actual_filter):
        return actual_filter


class Env:
    def ns_dump(self):
        return {}

TestAPI = api.API([Providers()], StubConfig, Env)


def test_defaults():
    assert TestAPI.data(filter_defaults='lowpass') == [1, 2, 3]
    assert TestAPI.data(
        filter_defaults='lowpass',
        filter_defaults_recorded_spec_={'lowpass': [10, 20, 30]},
    ) == [10, 20, 30]
    assert TestAPI.data(
        filter_defaults='lowpass',
        filter_defaults_recorded_spec_={'highpass': [10, 20, 30]},
    ) == [1, 2, 3]
