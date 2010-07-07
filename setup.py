#!/usr/bin/env python

import os
from distutils.core import setup

version = '0.3'

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Programming Language :: Python",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Environment :: Web Environment",
    "Framework :: Django",
]

root_dir = os.path.dirname(__file__)
if not root_dir:
    root_dir = '.'
long_desc = open(root_dir + '/README.rst').read()

setup(
    name='django-scaffold',
    version=version,
    url='http://github.com/mazelife/django-scaffold/',
    author='James Stevenson',
    author_email='james.m.stevenson at gmail dot com',
    license='BSD License',
    packages=['scaffold'],
    package_dir={'scaffold': 'scaffold'},
    package_data={'treebeard': ['templates/admin/*.html']},
    description=(
        'Reusable application for a generic section/subsection hierarchy'
        ' in Django 1.0+'
    ),
    classifiers=classifiers,
    long_description=long_desc,
    install_requires=['django>=1.0','django-treebeard>=1.60']
)
