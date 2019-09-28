#!/usr/bin/env python

import os
import io
import re
import glob
import sys

from setuptools import setup, find_packages

with io.open('./ancilla/__init__.py', encoding='utf8') as version_file:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")


with io.open('README.md', encoding='utf8') as readme:
    long_description = readme.read()

data_files = []

# start_point = os.path.join('ancilla', 'ui')
for root, dirs, files in os.walk('ancilla'):
    root_files = [os.path.join(root, i) for i in files]
    data_files.append((root, root_files))




setup(
    name='ancilla',
    version=version,
    description='3D printer utilities',
    long_description=long_description,
    author='LayerKeep',
    author_email='hi@layerkeep.com',
    license='Other',
    packages=find_packages(
        exclude=[
            'docs', 'tests',
            'windows', 'macOS', 'linux',
            'iOS', 'android',
            'django'
        ]
    ),
    data_files=data_files,
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: Other',
    ],
    install_requires= [r for r in map(str.strip, open("requirements.txt").readlines())],
    python_requires='>3.7',
    options={
        'app': {
            'formal_name': 'Ancilla',
            'bundle': 'com.layerkeep'
        },

        # Desktop/laptop deployments
        'macos': {
            'icon': 'tmp_ico',
            'app_requires': [
            ]
        },
        'linux': {
            'app_requires': [
            ]
        },
        'windows': {
            'app_requires': [
            ]
        },
    }
)
