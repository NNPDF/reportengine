import jinja2
import os

class Report():

    def __init__(self, template):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
        self._template = env.get_template(template)
    
    def build_report(self, resources):
        return self._template.render(**resources)


r = Report('test.md')

resources = {
    'resource': (1,2,3,4),
    'provider': lambda param: param*2, 
    
}

print(r.build_report(resources))