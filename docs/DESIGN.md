Report Engine
=============

The main components are:

 - A Report object. 
 - An interface to construct a report from a given configuration:
	 `DAGResolver` (Better name?).
 - A convention for the layout of the code that actually produces the
	 report, based on `DAGResolver` plus some helper tools to enforce
	 that convention (`repottools`?).

The main interface should be coded in Python 3.5.

Report
------

The Report object should be as simple as possible and easy to extend.

The report class should only understand a set of basic objects and
know how to compile them to Markdown. External tools are then used to
convert Markdown to other formats. The set of objects could be:

 - Title
 - Section
 - Figure
 - Table
 - Raw

The containers (ie Report and Section) can be accessed as
a simple python object (ie a List of other report pieces).

Default helpers and styles exist to produce the final content (i.e.
PDF or html files) but are largely a concern of the clients.

A layout configuration file can be used to specify the structure of
the report. A data file, which is processed by a `DAGResolver` is used
to supply the data.

DAGResolver
-----------

This class takes a configuration file which contains *input resources*
and figures out the processing that needs to be done to obtain *output
resources* (which are specified in the report layout in this case). 

While it is made with reports in mind, it is way more general.

In addition to tools for running the configuration, there are tools to
validate the inputs and analyze the requirements.

While in the most simple case, the outputs are directly functions of
the inputs, there is also the possibility of intermediate steps, so
that the required operations can be represented as a *Direct Acyclic
Graph (DAG)*.

The class also takes a python module which contains the functions
needed to actually carry out the computations (as well as doing
specific validations). These are called *providers*.

###Example

Imagine we have one *input resource*, *fit*. And we need to produce
two *output resources*: *arclength plots* and *arclength affinty*.

Both of these require a rather expensive computation called
*arclength.

`DagResolver` would be called with these parameters, as well as
a module `validphys` containing the following functions:

```python

#provides the *resource* arclength
def arclength(fit):
    ...

def arclength_affinity(arclength):
    ...

def plot_arclength(arclength):
    ...

```

The job of `DAGResolver` is then figure out that these functions need
to be called in the appropriate order. 


###Documentation

The docstrings of the provider functions (plus some additions) are
automatically made available as documentation in the various
interfaces. For example:

```python

#provides the *resource* arclength
def arclength(fit):
    """Computes the arclength for all replicas in ``fit``. It uses
	``nndiff`` to calculate the analytical expression of the
	derivative of the neural network.
    ...

def plot_arclength(arclength):
    """Plot distribution of arclengths."""
    ...
```

Would cause the docs to be automatically available to various parts in
the code and possibly the report itself (tooltips of figures?).


###Namespaces

It would be useful that different variables can be specified as the
same arguments for the scripts. For example, imagine a function:

```python
def plot_compare_pdfs(pdf, base_pdf):
    ...
```

It might be useful to call that function with `base_pdf` pointing at
the previous fit or at the closure test prior in different parts of
the report. This should be supported, so all resources should be
resolved within *namespaces* which can be specified by the user in (the
report layout). 

There is also the global namespace, which will be used by default. If
a resource is not found in the current namespace, it is searched in
the global one.

In principle, an independent DAG will be constructed for each
namespace and all the functions necessary to construct them will be
executed (even if the inputs are the same). Any caching behaviour is
responsibility of the client.

###Interactive interfaces

Using a `DAGResources` should be trivial to determine what needs to be
recomputed when some *input resource* is changed by the user. This
sets the stage for building a more interactive representation such as
a web interface.

###Checks

As much as possible failures due to incorrect user input must be
checked **before** any computation takes place. `DAGResolver` should
implement the basic checks (i.e. that the graph can actually be
constructed). Additionally the Python 3.5 [`typing
module`](https://docs.python.org/3/library/typing.html) could be used
to check for the types of the resources.

There is also support for domain-specific checks implemented as
a `check` decorator. It takes a function as a parameter which in turn
is called with the decorated function, the namespace and the instance
of `DAGResolver`. The decorated function  For example:

```python
def pdfs_installed(resource, namespace, resolver):
   """Check if the relevant pdfs are installed in LHAPDF"""
   ...

@check(pdfs_installed)
def plot_compare_pdfs(pdf:PDF, base_pdf:PDF) -> reportengine.Figure:
    ...
```

The fact that the arguments are in fact PDFs would be checked by
`DAGResolver` (which will know the return types of all producers),
while the function `pdfs_installed` would be called before actually
building the report.

The checks are called in the same order as the functions would.

###SMPDF correspondence

Many of these ideas are directly taken from
[SMPDF](https://github.com/scarrazza/smpdf). In particular the
[`actions`](https://github.com/scarrazza/smpdf/blob/master/src/smpdflib/actions.py)
module is a primitive implementation of `DAGResolver`, though much of
the work is done manually.

A rough correspondence in terminology would be:

action -> provider

actiongroup -> namespace

Configuration -> DAGResolver

Eventually that part of SMPDF would be reworked to use this framework.
