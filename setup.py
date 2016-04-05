#!/usr/bin/env python
# -*- mode:python; sh-basic-offset:4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim:set tabstop=4 softtabstop=4 expandtab shiftwidth=4 fileencoding=utf-8:
#

import os
import setuptools
import shotfirst
import sys


readme = os.path.join(os.path.dirname(sys.argv[0]), 'README.rst')
install_requires = [
    'pyinotify',  # To monitor directories
    'pdfrw',  # For PDF
    'Pillow',  # For EXIF metadata
    'enzyme',  # For Videos
]

setuptools.setup(
    name='shotfirst',
    version=shotfirst.__version__,
    author='Jorge Gallegos',
    author_email='kad@blegh.net',
    url='https://github.com/thekad/shotfirst',
    description=shotfirst.__doc__,
    long_description=open(readme).read(),
    keywords=[
        'inotify',
        'backup',
    ],
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'shotfirst=shotfirst.program:main',
        ],
    },
    license='BSD',
    install_requires=install_requires,
    zip_safe=False,
)
