""" common setup for root and portions (modules or sub-packages) of the ae namespace package.

# THIS FILE IS EXCLUSIVELY MAINTAINED IN THE AE ROOT PACKAGE. ANY CHANGES SHOULD BE DONE THERE.
# All changes will be deployed automatically to all the portions of this namespace package.

This file get used by each portion of this namespace package for builds (sdist/bdist_wheels)
and installation (install); also gets imported by the root package (for the globals defined
here) for documentation build (docs/conf.py), common file deploys and commit preparation.
"""
import glob
import os
import re
import setuptools
import sys
from typing import List, Tuple


def file_content(file_name: str) -> str:
    """ returning content of the file specified by file_name arg as string. """
    with open(file_name) as fh:
        content = fh.read()
    return content


def patch_templates() -> List[str]:
    """ convert all ae namespace package templates found in the cwd or underneath to the final files. """
    patched = list()
    for fn in glob.glob('**/*.*' + template_extension, recursive=True):
        content = file_content(fn).format(**globals())
        with open(fn[:-len(template_extension)], 'w') as fp:
            fp.write(content)
        patched.append(fn)
    return patched


def determine_setup_path() -> str:
    """ check if setup.py got called from portion root or from docs/RTD root. """
    cwd = os.getcwd()
    if os.path.exists('setup.py'):      # local build
        return cwd
    if os.path.exists('conf.py'):       # RTD build
        return os.path.abspath('..')
    raise RuntimeError(f"Neither setup.py nor conf.py found in current working directory {cwd}")


def read_package_version() -> str:
    """ read version of portion directly from the module or from the __init__.py of the sub-package. """
    file_name = portion_name + ('.py' if is_module else os.path.sep + '__init__.py')
    file_name = os.path.join(package_path, file_name)
    content = file_content(file_name)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
    if not version_match:
        raise RuntimeError(f"Unable to find version string of package {package_name} within {file_name}")
    return version_match.group(1)


def determine_portion(portion_type='module', portion_end='.py') -> Tuple[str, bool]:
    """ determine ae namespace package portion (and if it is either a module or a sub-package). """
    search_module = portion_type == 'module'
    files = [fn for fn in glob.glob(os.path.join(package_path, '*' + portion_end)) if '__' not in fn]
    if len(files) > 1:
        raise RuntimeError(f"More than one {portion_type} found: {files}")
    if len(files) == 0:
        if not search_module:
            raise RuntimeError(f"Neither module nor sub-package found in package path {package_path}")
        return determine_portion('sub-package', os.path.sep)
    return os.path.split(files[0][:-len(portion_end)])[1], search_module


namespace_root = 'ae'
root_len = len(namespace_root)
template_extension = '.tpl'
setup_path = determine_setup_path()
package_path = os.path.join(setup_path, namespace_root)
if os.path.exists(package_path):
    portion_name, is_module = determine_portion()   # running from portion repository
    package_version = read_package_version()
else:
    portion_name = '<portion-name>'                 # running from namespace root repo
    package_version = 'x.y.z'
package_name = namespace_root + '_' + portion_name  # results in package name e.g. 'ae_core'
pip_name = namespace_root + '-' + portion_name                              # e.g. 'ae-core'
import_name = namespace_root + '.' + portion_name                           # e.g. 'ae.core'

requirements_file = os.path.join(setup_path, 'requirements.txt')
if os.path.exists(requirements_file):
    dev_require = [_ for _ in file_content(requirements_file).strip().split('\n')
                   if not _.startswith('#')]
else:
    dev_require = ['pytest', 'pytest-cov']
docs_require = [_ for _ in dev_require if _.startswith('sphinx_')]
tests_require = [_ for _ in dev_require if _.startswith('pytest')]
portions = [_ for _ in dev_require if _.startswith('ae_')]
portions_import_names = ("\n" + " " * 4).join([_[:root_len] + '.' + _[root_len+1:] for _ in portions])  # -> index.rst
portions_pypi_refs_md = "\n".join(f'* [{_}](https://pypi.org/project/{_} "ae namespace portion {_}")' for _ in portions)


if __name__ == "__main__":
    patch_templates()

    setuptools.setup(
        name=package_name,              # pip install name (not the import package name)
        version=package_version,
        author="Andi Ecker",
        author_email="aecker2@gmail.com",
        description=package_name + " portion of python application environment namespace package",
        long_description=file_content("README.md"),
        long_description_content_type="text/markdown",
        url="https://gitlab.com/ae-group/" + package_name,
        # don't needed for native/implicit namespace packages: namespace_packages=['ae'],
        # packages=setuptools.find_packages(),
        packages=setuptools.find_namespace_packages(include=[namespace_root]),  # find ae namespace portions
        python_requires=">=3.6",
        extras_require={
            'docs': docs_require,
            'tests': tests_require,
            'dev': docs_require + tests_require,
        },
        classifiers=[
            "Development Status :: 1 - Planning",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Libraries :: Application Frameworks",
        ],
        keywords=[
            'productivity',
            'application',
            'environment',
            'configuration',
            'development',
        ]
    )
