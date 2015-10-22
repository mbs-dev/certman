#!/usr/bin/env python

from setuptools import setup

setup(name='certman',
      version='1.0a',
      description='Certman Storage Utility',
      author='Vladimir Ignatev',
      author_email='ya.na.pochte@gmail.com',
      url='https://www.python.org/',
      packages=['certman'],
      scripts=['certman/bin/certman', 'certman/bin/certman-config'],
      install_requires=['terminaltables==1.1.1', 'PyYAML==3.11']
     )
