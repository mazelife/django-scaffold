#!/usr/bin/env python

import os
from distutils.core import setup

version = '1.1.3'

classifiers = [
    "Development Status :: 5 - Production/Stable",
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

package_data = [
    '*.html',
    '*.gif',
    '*.png',
    '*.jpg',
    '*.js',
    '*.css'
]

setup(
    name='django-scaffold',
    version=version,
    url='http://github.com/mazelife/django-scaffold/',
    author='James Stevenson',
    author_email='james.m.stevenson at gmail dot com',
    license='BSD License',
    packages=['scaffold', 'scaffold.templatetags'],
    package_dir={'scaffold': 'scaffold'},
    package_data={'scaffold': [
        'templates/scaffold/*.html',
        'templates/scaffold/admin/*.html',
        'templates/scaffold/admin/includes/*.html',
        'static/scaffold/images/jstree/*.*',
        'static/scaffold/images/jstree/*.*',
        'static/scaffold/images/jstree/file_icons/*.*',
        'static/scaffold/images/jstree/jquery/*.*',
        'static/scaffold/images/jstree/plugins/*.*',
        'static/scaffold/scripts/*.js',
        'static/scaffold/scripts/jstree/*.js',
        'static/scaffold/scripts/jstree/_lib/*.js',
        'static/scaffold/scripts/jstree/themes/django/*.*',
        'static/scaffold/styles/*.css',
        'static/scaffold/styles/jquery.ui.start/*.css',
        'static/scaffold/styles/jquery.ui.start/images/*.png',
    ]},
    description=(
        'Reusable application for a generic section/subsection hierarchy'
        ' in Django 1.4.x'
    ),
    classifiers=classifiers,
    long_description=long_desc,
    install_requires=['django>=1.4','django-treebeard>=1.61']
)
