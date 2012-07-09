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
