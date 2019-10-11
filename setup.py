""" common setup for the portions (modules or sub-packages) of the ae namespace package.

# THIS FILE IS EXCLUSIVELY MAINTAINED IN THE AE ROOT PACKAGE. ANY CHANGES SHOULD BE DONE THERE.
# All changes will be deployed automatically to all the portions of this namespace package.

This file get exclusively used by each portion of this namespace package for builds (sdist/bdist_wheels)
and installation (install); also gets imported by docs/conf.py (package need to be installed via `pip install -e .`).

"""
import glob
import os
import re
import setuptools
import sys


def file_content(file_name):
    """ returning content of the file specified by file_name arg as string. """
    with open(file_name) as fh:
        content = fh.read()
    return content


def read_package_version():
    """ read version of portion directly from the module or from the __init__.py of the sub-package. """
    file_name = portion_name + ('.py' if is_module else os.path.sep + '__init__.py')
    file_name = os.path.join(package_path, file_name)
    content = file_content(file_name)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
    if not version_match:
        raise RuntimeError(f"Unable to find version string of package {package_name} within {file_name}")
    return version_match.group(1)


def patch_install_templates():
    """ create final files from all found install ae namespace package templates. """
    for fn in glob.glob('**/*.*' + template_extension, recursive=True):
        content = file_content(fn).format(**globals())
        with open(fn[:-len(template_extension)], 'w') as fh:
            fh.write(content)


def determine_setup_path():
    """ check if setup.py got called from portion root or from docs/RTD root. """
    cwd = os.getcwd()
    if os.path.exists('setup.py'):      # local build
        return cwd
    if os.path.exists('conf.py'):       # RTD build
        return os.path.abspath('..')
    raise RuntimeError(f"Neither setup.py nor conf.py found in current working directory {cwd}")


def determine_portion(portion_type='module', portion_end='.py'):
    """ determine the ae namespace package portion (either a module or a sub-package). """
    search_module = portion_type == 'module'
    portions = [fn for fn in glob.glob(os.path.join(package_path, '*' + portion_end)) if '__' not in fn]
    if len(portions) > 1:
        raise RuntimeError(f"More than one {portion_type} found: {portions}")
    if len(portions) == 0:
        if not search_module:
            raise RuntimeError(f"Neither module nor sub-package found in package path {package_path}")
        return determine_portion('sub-package', os.path.sep)
    return os.path.split(portions[0][:-len(portion_end)])[1], search_module


namespace_root = 'ae'
template_extension = '.tpl'
setup_path = determine_setup_path()
package_path = os.path.join(setup_path, namespace_root)
if not os.path.exists(package_path):
    raise RuntimeError(f"Package path {package_path} not found")
portion_name, is_module = determine_portion()
package_name = namespace_root + '_' + portion_name  # results in package name e.g. 'ae_core'
pip_name = namespace_root + '-' + portion_name                              # e.g. 'ae-core'
import_name = namespace_root + '.' + portion_name                           # e.g. 'ae.core'
package_version = read_package_version()

requirements_file = os.path.join(setup_path, 'requirements.txt')
if os.path.exists(requirements_file):
    dev_require = [_ for _ in file_content(requirements_file).strip().split('\n')
                   if not _.startswith('#')]
else:
    dev_require = ['pytest', 'pytest-cov']
docs_require = [_ for _ in dev_require if _.startswith('sphinx_')]
tests_require = [_ for _ in dev_require if _.startswith('pytest')]


if __name__ == "__main__":
    if 'install' in sys.argv or 'sdist' in sys.argv:
        patch_install_templates()

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
