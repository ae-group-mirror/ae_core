<!--
# THIS FILE IS EXCLUSIVELY MAINTAINED IN THE AE ROOT PACKAGE. ANY CHANGES SHOULD BE DONE THERE.
# All changes will be deployed automatically to all the portions of this namespace package.
-->
# core Portion Of ae Namespace Package

The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes for to develop
full-featured applications with Python.


## Installation

For to only use this module in your code type in your command shell:
 
```shell script
pip install ae-core
```

If you instead want to contribute to this portion then first fork this repository,
then pull it to your machine and execute in the root folder of this repository:

```shell script
pip install -e .[dev]
```

The last command will install this portion into your virtual environment, along with
the tools you need to develop and run tests or for to extend the portion documentation.
For to contribute only to the unit tests or the documentation of this portion replace
the setup extras key `dev` in the above command with `tests` or `docs` respectively.


## Namespace Portion Documentation

More info on the features and usage of this portion are available at
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/ae.core.html#module-ae.core
"ae_core documentation").

<!-- Common files version 0.0.16 deployed to the ae_core module version 0.0.14.
-->