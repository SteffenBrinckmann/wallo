#!/usr/bin/env python
""" setup to generate version number"""
from __future__ import annotations

from setuptools import find_packages, setup

if __name__ == '__main__':
  setup(name='wallo', version='0.2.0', packages=find_packages(),
        package_data={'wallo.services.claude': ['README.md']})
