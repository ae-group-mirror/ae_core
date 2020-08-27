<!--
  THIS FILE IS EXCLUSIVELY MAINTAINED IN THE NAMESPACE ROOT PACKAGE. CHANGES HAVE TO BE DONE THERE.
  All changes will be deployed automatically to all the portions of this namespace package.
-->
# core portion of ae namespace package

[![GitLabPipeline](https://img.shields.io/gitlab/pipeline/ae-group/ae_core/master?logo=python)](
    https://gitlab.com/ae-group/ae_core)
[![PyPIVersion](https://img.shields.io/pypi/v/ae_core)](
    https://pypi.org/project/ae-core/#history)

>The portions (modules and sub-packages) of the Application Environment for Python are within
the `ae` namespace and are providing helper methods and classes for to develop
full-featured applications with Python.

[![Coverage](https://ae-group.gitlab.io/ae_core/coverage.svg)](
    https://ae-group.gitlab.io/ae_core/coverage/ae_core_py.html)
[![MyPyPrecision](https://ae-group.gitlab.io/ae_core/mypy.svg)](
    https://ae-group.gitlab.io/ae_core/lineprecision.txt)
[![PyLintScore](https://ae-group.gitlab.io/ae_core/pylint.svg)](
    https://ae-group.gitlab.io/ae_core/pylint.log)

[![PyPIImplementation](https://img.shields.io/pypi/implementation/ae_core)](
    https://pypi.org/project/ae-core/)
[![PyPIPyVersions](https://img.shields.io/pypi/pyversions/ae_core)](
    https://pypi.org/project/ae-core/)
[![PyPIWheel](https://img.shields.io/pypi/wheel/ae_core)](
    https://pypi.org/project/ae-core/)
[![PyPIFormat](https://img.shields.io/pypi/format/ae_core)](
    https://pypi.org/project/ae-core/)
[![PyPIStatus](https://img.shields.io/pypi/status/ae_core)](
    https://libraries.io/pypi/ae-core)
[![PyPIDownloads](https://img.shields.io/pypi/dm/ae_core)](
    https://pypi.org/project/ae-core/#files)


## installation


Execute the following command for to use the ae.core module in your
application. It will install ae.core into your python (virtual) environment:
 
```shell script
pip install ae-core
```

If you instead want to contribute to this portion then first fork
[the ae_core repository at GitLab](https://gitlab.com/ae-group/ae_core "ae.core code repository"),
then pull it to your machine and finally execute the following command in the root folder
of this repository (ae_core):

```shell script
pip install -e .[dev]
```

The last command will install this module portion into your virtual environment, along with
the tools you need to develop and run tests or for to extend the portion documentation.
For to contribute only to the unit tests or the documentation of this portion replace
the setup extras key `dev` in the above command with `tests` or `docs` respectively.


## namespace portion documentation

More info on the features and usage of this portion are available at
[ReadTheDocs](https://ae.readthedocs.io/en/latest/_autosummary/ae.core.html#module-ae.core
"ae_core documentation").

<!-- Common files version 0.0.60 deployed version 0.1.42 (with 0.0.60)
     to https://gitlab.com/ae-group as ae_core module as well as
     to https://ae-group.gitlab.io with CI check results as well as
     to https://pypi.org/project/ae-core as namespace portion ae-core.
-->
