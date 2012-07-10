#
# Copyright (c) 2012, Intel Performance Learning Solutions Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Setupstools script which defines an entry point which can be used for CDMI
app later.
"""

from setuptools import setup


setup(
    name='cdmiapi',
    version='1.0',
    description='CDMI interface for Openstack Swift.',
    long_description='''
         This provides a python egg which can be deployed in OpenStack.
      ''',
    classifiers=[
        'Programming Language :: Python'
        'Development Status :: 5 - Production/Stable',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
        ],
    keywords='',
    include_package_data=True,
    packages=['cdmi','cdmi.cdmiapp'],
    zip_safe=False,
    install_requires=[
        'setuptools',
        ],
    entry_points='''
      [paste.filter_factory]
      cdmiapp = cdmi:filter_factory
      ''',
)
