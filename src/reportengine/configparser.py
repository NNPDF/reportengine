# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 15:31:29 2015

@author: zah
"""
import inspect


class ConfigError(Exception): pass

class BadInputType(ConfigError, TypeError):
    def __init__(self, param, val, input_type):
        msg = ("Bad input type for parameter {param}: Value {val} "
               "is not of type {input_type}.").format(**locals())

class Config:
    def __init__(self, input_params):
        self.input_params = input_params
        self.process_params(input_params)
        

    def process_params(self, input_params):
        self.params = {}
        for param in self.input_params:
            val = self.parse_param(param, input_params[param])
            self.params[param] = val
    
    def parse_param(self, param, val):
        func_name = "parse_" + param
        try:
            parse_func = getattr(self, func_name)
        except AttributeError:
            return val
        
        sig = inspect.signature(parse_func)
        try:
            first_param = next(iter(sig.parameters.values()))
        except StopIteration:
            raise TypeError("Parser functiom must have one parameter: %s"
                            % parse_func.__qualname__)
        
        input_type = first_param.annotation        
        if input_type is not sig.empty:
            if not isinstance(val, input_type):
                raise BadInputType(param, val, input_type)
        
        result = parse_func(val)
        return result
    
    def __getitem__(self, item):
        return self.params[item]
    
    def __iter__(self):
        return iter(self.params)
    
    def __len__(self):
        return len(self.params)
    
    def __contains__(self, item):
        return item in self.params
        
        
                   
    
    