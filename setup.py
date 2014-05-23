#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup
from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import sys
import py2exe

# To run "setup.py register" change name to "NAME+VERSION_NAME"
# because pychess from another author already exist in pypi.
NAME = "RCFast"
VERSION = "0.1"

DESC = "A tool for searching the minimal crashing file."

LONG_DESC = """This is supposed to be used after a crash was found using a trivial bitflipping 
fuzzing session. It expects a normal not crashing control file and a mutated same sized crashing 
file. It will try to reduce the mutations on the crashing file checking that the resultant file 
still crashes on the configured application.

"""

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Programming Language :: Python',
    'Natural Language :: English',
]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

DATA_FILES = ['rcfast.ui']
DATA_FILES += [("pixmaps", glob('pixmaps/*.png'))]
DATA_FILES += [("sounds", glob('sounds/*.wav'))]

PACKAGES = [ ]

# Setup
setup (
    name             = NAME,
    version          = VERSION,
    author           = 'Joshep J. Cortez Sanchez & Felipe Andres Manzano',
    author_email     = 'felipe.andres.manzano@gmail.com',
    maintainer       = 'Felipe Andres Manzano',
    classifiers      = CLASSIFIERS,
    keywords         = 'python gtk security crash tester fuzzer',
    description      = DESC,
    long_description = LONG_DESC,
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['rcfast.py'],
    console	     = ['rcfast.py'],
    requires	     = ['distorm3', 'pygtk', 'pywin32', 'cairo'],
    options          = {'py2exe' : { 'includes': ['cairo', 'gio', 'pango', 'pangocairo', 'atk'],
				   }
		       },
)
