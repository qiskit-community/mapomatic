# -*- coding: utf-8 -*-
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Mapomatic

Mapomatic automates mapping of compiled circuits to low-noise sub-graphs
"""

import os
import sys
import subprocess
import setuptools


MAJOR = 0
MINOR = 3
MICRO = 0

ISRELEASED = True
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

REQUIREMENTS = []
with open("requirements.txt") as f:
    for line in f:
        req = line.split('#')[0]
        if req:
            REQUIREMENTS.append(req)

PACKAGES = setuptools.find_namespace_packages()
PACKAGE_DATA = {
}

DOCLINES = __doc__.split('\n')
DESCRIPTION = DOCLINES[0]
LONG_DESCRIPTION = "\n".join(DOCLINES[2:])


def git_short_hash():
    try:
        git_str = "+" + os.popen('git log -1 --format="%h"').read().strip()
    except:  # pylint: disable=bare-except
        git_str = ""
    else:
        if git_str == '+': #fixes setuptools PEP issues with versioning
            git_str = ''
    return git_str

FULLVERSION = VERSION
if not ISRELEASED:
    FULLVERSION += '.dev'+str(MICRO)+git_short_hash()

def write_version_py(filename='mapomatic/version.py'):
    cnt = """\
# THIS FILE IS GENERATED FROM MAPOMATIC SETUP.PY
# pylint: disable=invalid-name, missing-module-docstring
short_version = '%(version)s'
version = '%(fullversion)s'
release = %(isrelease)s
"""
    a = open(filename, 'w')
    try:
        a.write(cnt % {'version': VERSION, 'fullversion':
                       FULLVERSION, 'isrelease': str(ISRELEASED)})
    finally:
        a.close()

local_path = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(local_path)
sys.path.insert(0, local_path)
sys.path.insert(0, os.path.join(local_path, 'mapomatic'))  # to retrive _version

# always rewrite _version
if os.path.exists('mapomatic/version.py'):
    os.remove('mapomatic/version.py')

write_version_py()


# Add command for running pylint from setup.py
class PylintCommand(setuptools.Command):
    """Run Pylint on all Mapomatic Python source files."""
    description = 'Run Pylint on Mapomatic Python source files'
    user_options = [
        # The format is (long option, short option, description).
        ('pylint-rcfile=', None, 'path to Pylint config file')]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.pylint_rcfile = ''  # pylint: disable=attribute-defined-outside-init

    def finalize_options(self):
        """Post-process options."""
        if self.pylint_rcfile:
            assert os.path.exists(self.pylint_rcfile), (
                'Pylint config file %s does not exist.' % self.pylint_rcfile)

    def run(self):
        """Run command."""
        command = ['pylint']
        if self.pylint_rcfile:
            command.append('--rcfile=%s' % self.pylint_rcfile)
        command.append(os.getcwd()+"/mapomatic")
        subprocess.run(command, stderr=subprocess.STDOUT, check=False)


# Add command for running PEP8 tests from setup.py
class StyleCommand(setuptools.Command):
    """Run pep8 from setup."""
    description = 'Run style from setup'
    user_options = [
        # The format is (long option, short option, description).
        ('abc', None, 'abc')]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run command."""
        command = 'pycodestyle --max-line-length=100 mapomatic'
        subprocess.run(command, shell=True, check=False, stderr=subprocess.STDOUT)


setuptools.setup(
    name='mapomatic',
    version=VERSION,
    packages=PACKAGES,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url="",
    author="Paul Nation",
    author_email="paul.nation@ibm.com",
    license="Apache 2.0",
    classifiers=[
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering",
    ],
    cmdclass={'lint': PylintCommand, 'style': StyleCommand},
    install_requires=REQUIREMENTS,
    package_data=PACKAGE_DATA,
    include_package_data=True,
    zip_safe=False
)
