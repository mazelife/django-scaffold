#!/usr/bin/env python

import os
from distutils.core import setup

version = '0.2'

classifiers = [
    "Development Status :: 3 - Alpha",
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
long_desc = open(root_dir + '/README').read()

setup(
    name='django-scaffold',
    version=version,
    url='http://github.com/mazelife/django-scaffold/',
    author='James Stevenson',
    author_email='james.m.stevenson@gmail.com',
    license='BSD License',
    packages=['scaffold'],
    package_dir={'scaffold': 'scaffold'},
    package_data={'treebeard': ['templates/admin/*.html']},
    description=(
        'Reusable application for a generic section/subsection hierarchy'
        ' in Django 1.0+'
    )
    classifiers=classifiers,
    keyworkers=(
        'django', 
        'webapps', 
        'taxonomy', 
        'information architechture', 
        'sections'
    ),
    long_description=long_desc,
    requires=['django (=1.1.1)','django-treebeard (>=1.60)']
)
