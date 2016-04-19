Report Engine
============

General purpose report generator.

Install
-------

For linux, you can install a precompiled package by running

````
conda install reportengine -c https://zigzah.com/static/conda-pkgs

````

At the moment, the dependencies are:

 - matplotlib
 - pyyaml
 - jinja2

You can install all the dependencies, and then:


````
pip install .
````

Alternatively, you can satisfy all the dependencies automatically by
running:

````
conda build conda-recipe
````

and then installing the resulting package.


Development
-----------

Install in development mode:

````
pip install -e .
````

Running the tests
-----------------

Easiest way is:

````
nosetests
````
