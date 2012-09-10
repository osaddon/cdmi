CDMI for OpenStack's Swift
--------------------------

A Python egg that adds support for the [CDMI protocol](http://cdmi.sniacloud.org/) to OpenStack Swift.

Setup
=====

1. Install [Openstack with Swift](http://docs.openstack.org/essex/openstack-object-storage/admin/content/)
2. Grab the code from github:
     `git clone http://github.com/osaddon/cdmi`
3. Install this python egg: `sudo python setup.py install`
4. Configure Swift:

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

if you are using keystone configuration for authentication, you will have to
make changes in /etc/swift/test.conf and to make sure that you have all the
information correct as follows:

    auth_host = 127.0.0.1
    auth_port = 5000
    access_port = 8080
    auth_ssl = no
    auth_prefix = /v2.0/tokens

    account = your_tenant_name
    username = your_user_name
    password = your_password

if you have swift all-in-one environment, then make sure the information in
/etc/swift/test.conf is as follows:

Now the test cases in the test directory can be run using `python <name_of_test.py>` in the tests directory.

Development with devstack
=========================

Please make sure `swift` is enabled in your devstack environment file `localrc`.

Some sample curl commands
=========================

Authenticate and get an auth token (Swift All-in-one environment):

    curl -v -H 'X-Storage-User: test:tester' -H 'X-Storage-Pass: testing' http://127.0.0.1:8080/auth/v1.0

Authenticate and get an auth token (DevStack or Keystone 2.0):

    curl -d '{"auth": {"passwordCredentials": {"username": "<<your name>>",
    "password": "<<your password>>"}, "tenantName":"<<your tenant name>>"}}'
    -H "Content-Type: application/json" http://127.0.0.1:5000/v2.0/tokens

Use the Authentication token and URL which is in the response from the last
curl command to perform an *GET* operation:

    curl -v -X GET -H 'X-Auth-Token: AUTH_tk56b01c82710b41328db7c9f953d3933d'
    http://127.0.0.1:8080/v1/AUTH_test

Create a Container: (replace the auth token with the token obtained above,
also replace the root container)

    curl -v -X PUT -H 'X-Auth-Token: <<your token>>'
    -H 'Content-tType: application/directory'-H 'Content-Length: 0'
    http://127.0.0.1:8080/v1/<root container>/<container_name>

Query the capabilites of a Container:

    curl -v -X GET -H 'X-Auth-Token: <<your token>>'
    -H 'X-CDMI-Specification-Version: 1.0.1'
    http://127.0.0.1:8080/cdmi/cdmi_capabilities/<root container>/<container_name>

Add an Object to a Container:

    curl -v -X PUT -H 'X-Auth-Token: <<your token>>'
    -H 'X-CDMI-Specification-Version: 1.0.1'
    -H 'Accept: application/cdmi-object'
    -H 'Content-Type: application/cdmi-object'
    http://127.0.0.1:8080/v1/<root container>/<container_name>/<object_name> -d '<Some JSON>'
