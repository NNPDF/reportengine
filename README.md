[![DOI](https://zenodo.org/badge/42721933.svg)](https://zenodo.org/badge/latestdoi/42721933)

Reportengine
============

Reportengine is a framework to develop scientific applications. It is
focused on supporting declarative input (YAML), enforcing
initialization time ("*compile time*") constraints, and enabling
iteration within the declarative input.

It includes support for figures, tables (pandas) and HTML
reports.

The documentation of the NNPDF specific implementation can be found
here:

https://data.nnpdf.science/validphys-docs/guide.html


An example application can be found in the `example` directory.


Install
-------

It is recommended to work with the package using
[conda](https://docs.conda.io/en/latest/miniconda.html).

For linux or Mac, you can install a precompiled package by running

````
conda install reportengine -c https://packages.nnpdf.science/conda

````

Alternatively the package can be installed from `pip`:


```
pip install reportengine
```

Note that it will additionally require `pandoc` to work.


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
pytest
````
