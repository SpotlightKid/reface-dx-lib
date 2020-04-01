#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py
#
"""A patch librarian for the Yamaha Reface DX synthesizer."""

from io import open
from os.path import join
from setuptools import setup


def read(*paths):
    with open(join(*paths), encoding='utf-8') as fp:
        return fp.read()


exec(read('refacedx', 'version.py'))


setup(
    name='reface-dx-lib',
    version=__version__,  # noqa
    description=__doc__.splitlines()[0],
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    author="Christopher Arndt",
    author_email="info@chrisarndt.de",
    url="https://github.com/SpotlightKid/reface-dx-lib",
    packages=["refacedx"],
    install_requires=[
        'PyQt5',
        'python-rtmidi>=1.1.1',
        'python-dateutil',
        'sqlalchemy>=1.2.0',
        'sqlalchemy-filters'
    ],
    entry_points={
        "console_scripts": [
            "reface-dx-lib = refacedx.app:main",
            "reface-request-patch = refacedx.tools.request_patch:main"
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: MIDI',
        'Topic :: Utilities',
    ]
)
