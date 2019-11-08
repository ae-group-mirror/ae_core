""" common setup for root and portions (modules or sub-packages) of the ae namespace package.

# THIS FILE IS EXCLUSIVELY MAINTAINED IN THE NAMESPACE ROOT PACKAGE. CHANGES HAVE TO BE DONE THERE.
# All changes will be deployed automatically to all the portions of this namespace package.

This file get run by each portion of this namespace package for builds (sdist/bdist_wheel)
and installation (install); also gets imported by the root package (for the globals defined
here) for documentation builds (docs/conf.py), common file deploys and commit preparations.
"""
import glob
import os
import pprint
import re
import setuptools
from typing import Dict, List


PT_PKG: str = 'sub-package'         #: sub-package portion type
PT_MOD: str = 'module'              #: module portion type
PY_EXT = '.py'

REQ_FILE_NAME = 'requirements.txt'
REQ_TEST_FILE_NAME = 'test_requirements.txt'

version_patch_parser = re.compile(r"(^__version__ = ['\"]\d*[.]\d*[.])(\d+)([a-z]*['\"])", re.MULTILINE)


def bump_code_file_patch_number(file_name: str) -> str:
    """ read code file version and then increment the patch number by one and write the code file back. """
    if not os.path.exists(file_name):
        return f"Not existing file {file_name}"
    content = file_content(file_name)
    if not content:
        return f"Empty file {file_name}"
    content, replaced = version_patch_parser.subn(lambda m: m.group(1) + str(int(m.group(2)) + 1) + m.group(3), content)
    if replaced != 1:
        return f"Variable __version__ found {replaced} times in {file_name}"
    with open(file_name, 'w') as fp:
        fp.write(content)
    return ""


def code_file_version(file_name: str) -> str:
    """ read version of Python code file - from __version__ module variable initialization. """
    content = file_content(file_name)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
    if not version_match:
        raise FileNotFoundError(f"Unable to find version string within {file_name}")
    return version_match.group(1)


def determine_package_vars(portion_root_path: str, portion_type: str = PT_MOD, portion_end: str = PY_EXT
                           ) -> Dict[str, str]:
    """ determine vars of a ae namespace package portion (and if it is either a module or a sub-package). """
    if os.path.exists(portion_root_path):                   # run/imported by portion repository
        search_module = portion_type == PT_MOD
        files = [fn for fn in glob.glob(os.path.join(portion_root_path, '*' + portion_end)) if '__' not in fn]
        if len(files) > 1:
            raise RuntimeError(f"More than one {portion_type} found: {files}")
        if len(files) == 0:
            if not search_module:
                raise RuntimeError(f"Neither module nor sub-package found in package path {portion_root_path}")
            return determine_package_vars(portion_root_path, PT_PKG, os.path.sep)
        portion_name = os.path.split(files[0][:-len(portion_end)])[1]
    else:                                                   # imported by namespace root repo
        portion_type = ''
        portion_name = "{portion-name}"

    p_vars = dict()
    p_vars['namespace_name'] = namespace_name
    p_vars['portion_type'] = portion_type
    p_vars['portion_name'] = portion_name
    p_vars['portion_file_name'] = portion_name + (os.path.sep + '__init__.py' if portion_type == PT_PKG else PY_EXT)
    p_vars['portion_file_path'] = os.path.abspath(os.path.join(portion_root_path, p_vars['portion_file_name']))
    p_vars['package_name'] = f"{namespace_name}_{portion_name}"
    p_vars['pip_name'] = f"{namespace_name}-{portion_name}"
    p_vars['import_name'] = f"{namespace_name}.{portion_name}"
    p_vars['package_version'] = code_file_version(p_vars['portion_file_path']) if portion_type else 'x.y.z'
    p_vars['root_version'] = 'un.kno.wn' if portion_type else code_file_version(os.path.join(setup_path, 'setup.py'))
    p_vars['repo_root'] = f"https://gitlab.com/{namespace_name}-group"
    p_vars['repo_pages'] = "https://ae-group.gitlab.io"
    p_vars['pypi_root'] = "https://pypi.org/project"

    return p_vars


def determine_setup_path() -> str:
    """ check if setup.py got called from portion root or from docs/RTD root. """
    cwd = os.getcwd()
    if os.path.exists('setup.py'):      # local build
        return cwd
    if os.path.exists('conf.py'):       # RTD build
        return os.path.abspath('..')
    raise RuntimeError(f"Neither setup.py nor conf.py found in current working directory {cwd}")


def file_content(file_name: str) -> str:
    """ returning content of the file specified by file_name arg as string. """
    with open(file_name) as fp:
        return fp.read()


def patch_templates(patch_vars: Dict[str, str], exclude_folder: str = '') -> List[str]:
    """ convert ae namespace package templates found in the cwd or underneath (except excluded) to the final files. """
    patched = list()
    for fn in glob.glob('**/*.*' + template_extension, recursive=True):
        if not exclude_folder or not fn.startswith(exclude_folder + os.path.sep):
            content = file_content(fn).format(**patch_vars)
            with open(fn[:-len(template_extension)], 'w') as fp:
                fp.write(content)
            patched.append(fn)
    return patched


namespace_name = 'ae'
portions_common_root_path = 'portions_common_root'
template_extension = '.tpl'
setup_path = determine_setup_path()
portion_path = os.path.join(setup_path, namespace_name)
package_vars = determine_package_vars(portion_path)
package_name = package_vars['package_name']
repo_root = package_vars['repo_root']

dev_require = list()
requirements_file = os.path.join(setup_path, REQ_FILE_NAME)
if os.path.exists(requirements_file):
    dev_require.extend(_ for _ in file_content(requirements_file).strip().split('\n') if not _.startswith('#'))
docs_require = [_ for _ in dev_require if _.startswith('sphinx_')]
install_require = [_ for _ in dev_require if not _.startswith('sphinx_')]
portions_package_names = [_ for _ in dev_require if _.startswith('ae_')]

tests_require = list()
requirements_file = os.path.join(setup_path, REQ_TEST_FILE_NAME)
if os.path.exists(requirements_file):
    tests_require.extend(_ for _ in file_content(requirements_file).strip().split('\n') if not _.startswith('#'))

# provide additional package info for root package templates
package_vars['portions_common_root_path'] = portions_common_root_path
package_vars['portions_pypi_refs_md'] = "\n".join(
    f'* [{_}]({package_vars["pypi_root"]}/{_} "ae namespace portion {_}")'
    for _ in portions_package_names)                        # used in ./README.md.tpl
namespace_len = len(namespace_name)
package_vars['portions_import_names'] = ("\n" + " " * 4).join(
    _[:namespace_len] + '.' + _[namespace_len + 1:]
    for _ in portions_package_names)                        # used in docs/index.rst.tpl


if __name__ == "__main__":
    setup_kwargs = dict(
        name=package_name,              # pip install name (not the import package name)
        version=package_vars['package_version'],
        author="Andi Ecker",
        author_email="aecker2@gmail.com",
        description=package_name + " portion of python application environment namespace package",
        long_description=file_content("README.md"),
        long_description_content_type="text/markdown",
        url=f"{repo_root}/{package_name}",
        # don't needed for native/implicit namespace packages: namespace_packages=['ae'],
        # packages=setuptools.find_packages(),
        packages=setuptools.find_namespace_packages(include=[namespace_name]),  # find ae namespace portions
        python_requires=">=3.6",
        install_requires=install_require,
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
    print("#  EXECUTING SETUPTOOLS SETUP #################################")
    print(pprint.pformat(setup_kwargs, indent=3, width=75, compact=True))
    setuptools.setup(**setup_kwargs)
    print("#  FINISHED SETUPTOOLS SETUP  #################################")
