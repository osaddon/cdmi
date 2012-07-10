
CDMI for OpenStack's SWIFT
--------------------------

This is a clone of the repository: https://github.com/litong01/cdmi

It will provide an Python egg which can be used by any existing OpenStack installation.

Setup
=====

1. Install Openstack with Swift
2. Install this python egg
3. Configure Swift:

In `/etc/swift/proxy-server.conf`, add cdmi filter before proxy-server

	[pipeline:main]
	pipeline = healthcheck cache tempauth *cdmi* proxy-server

And add the following section to the file:

	[filter:cdmi]
	use = egg:cdmiapi#cdmiapp

Running tests
=============

First copy a test config file to /etc/swift:

	cp /opt/stack/swift/test/sample.conf /etc/swift/test.conf

Now the test cases in the test directory can be run without problems.

Development with devstack
=========================

Please make sure `swift` is enabled in your devstack environment file `localrc`.
