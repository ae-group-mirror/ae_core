<!--
# THIS FILE IS EXCLUSIVELY MAINTAINED IN THE AE ROOT PACKAGE. ANY CHANGES SHOULD BE DONE THERE.
# All changes will be deployed automatically to all the portions of this namespace package.
-->
# Version {package_version} Of {package_name} Portion Of ae Namespace Package

The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes for to develop
full-featured applications with Python.


## Installation

For to only use this portion in your code type in your command shell:
 
```shell script
pip install {pip_name}
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
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/{import_name}.html#module-{import_name}
"{package_name} documentation").
