""" generic setup.py used for all modules and sub-packages of the ae namespace package. """
import glob
import os
import re
import setuptools


namespace_root = 'ae'
docs_folder = 'docs'

docs_require = [
    'sphinx',
    'sphinx-autodoc-typehints',
    'sphinx_rtd_theme',     # since Sphinx 1.4 no longer integrated (like alabaster)
    'sphinx_paramlinks',
    # typehints extension does that already so no need to also include 'sphinx-autodoc-annotation',
]

tests_require = [
    'pytest',
    'pytest-cov',
]


def replace_placeholders(file_content):
    """ replace placeholders within the passed file content """
    return file_content \
        .replace('{{setup_path}}', setup_path) \
        .replace('{{package_name}}', package_name) \
        .replace('{{pip_name}}', pip_name) \
        .replace('{{import_name}}', import_name) \
        .replace('{{package_path}}', package_path) \
        .replace('{{package_version}}', package_version)


def read_package_version():
    """ read version of module/sub-package directly from the module or from the __init__.py of the sub-package.

    also used by docs/conf.py (package need to be installed via pip install -e .)
    """
    file_name = sub_name + ('.py' if is_module else os.path.sep + '__init__.py')
    file_name = os.path.join(package_path, file_name)
    with open(file_name) as fh:
        file_content = fh.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", file_content, re.M)
    if not version_match:
        raise RuntimeError(f"Unable to find version string of package {package_name} within {file_name}")
    return version_match.group(1)


def patch_read_me():
    """ create final README.md from the ae namespace package template. """
    with open("AE_PACKAGES_README.md") as fh:
        file_content = fh.read()
    file_content = replace_placeholders(file_content)
    with open("README.md", 'w') as fh:
        fh.write(file_content)
    return file_content


cwd = os.getcwd()
if os.path.exists('setup.py'):      # local build
    setup_path = cwd
elif os.path.exists('conf.py'):     # RTD build
    setup_path = os.path.abspath('..')
else:
    raise RuntimeError(f"Neither setup.py nor conf.py found in current working directory {cwd}")
package_path = os.path.join(setup_path, namespace_root)
if not os.path.exists(package_path):
    raise RuntimeError(f"Package path {package_path} not found")
modules = glob.glob(os.path.join(package_path, '*.py'))
if len(modules) > 1:
    raise RuntimeError(f"More than one module found: {modules}")
elif len(modules) == 0:
    sub_packages = [_ for _ in glob.glob(os.path.join(package_path, '*' + os.path.sep)) if '__pycache__' not in _]
    if len(sub_packages) > 1:
        raise RuntimeError(f"More than one sub-package found: {sub_packages}")
    elif len(sub_packages) == 0:
        raise RuntimeError(f"Neither module nor sub-package found in package path {package_path}")
    is_module = False
    sub_name = os.path.split(sub_packages[0][:-1])[1]
else:
    is_module = True
    sub_name = os.path.split(os.path.splitext(modules[0])[0])[1]
package_name = namespace_root + '_' + sub_name  # results in package name e.g. 'ae_core'
pip_name = namespace_root + '-' + sub_name                              # e.g. 'ae-core'
import_name = namespace_root + '.' + sub_name                           # e.g. 'ae.core'
package_version = read_package_version()


if __name__ == "__main__":
    long_description = patch_read_me()

    setuptools.setup(
        name=package_name,              # pip install name (not the import package name)
        version=package_version,
        author="Andi Ecker",
        author_email="aecker2@gmail.com",
        description=package_name + " sub-package/portion of python application environment namespace package",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://gitlab.com/ae-group/" + package_name,
        # don't needed for native/implicit namespace packages: namespace_packages=['ae'],
        # packages=setuptools.find_packages(),
        packages=setuptools.find_namespace_packages(include=[namespace_root]),  # find ae namespace module/sub-package
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
