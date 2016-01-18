from __future__ import print_function
import sys
from setuptools import setup, find_packages
import subprocess
import platform

if sys.version_info < (3,5):
    print("SMPDF requires Python 3.5 or later", file=sys.stderr)
    sys.exit(1)

with open("README.md") as f:
    long_desc = f.read()


setup (name = 'reportengine',
       version = '0.1',
       description = "Report Generator",
       author = 'Zahari Kassabov',
       author_email = 'kassabov@to.infn.it',
       url = 'https://github.com/NNPDF/reportengine',
       long_description =  long_desc,
    
       package_dir = {'': 'src'},
       packages = find_packages('src'),
       package_data = {
            '':['*.template', '*.mplstyle']
       },
       zip_safe = False,
       classifiers=[
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Physics',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            ],
       )
