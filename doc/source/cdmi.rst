=================================
CDMI REST Implementation On Swift
=================================

----------------
Design decisions
----------------

The CDMI implementation on OpenStack Swift was designed to be a filter so that
the implementation can be easily configured to run like any other modules in
Swift pipeline. It can also take advantages of Swift authentication filter so
that the CDMI implementation modules can be completely independent from other
modules. When not needed, changing the Swift configuration to disable it.

Among many concepts in CDMI specification, container and data object are
certainly two most important concepts. This CDMI implementation chose to only
support container, data object and capability specification. CDMI
specification also allows container being nested, that is, a container can
have other containers inside. CDMI containers and data objects make a tree like
structure. OpenStack containers and data object form a tree but the depth of
the tree is only two, that means, a container can not have another container
inside, container can only have data object as its children. Because of the
OpenStack container, data object model, this implementation will only a user
to create a container at the top level, once a container is created, it can not
have containers inside, a container can only hold data objects. However,
OpenStack Swift does provide some tricks to allow a feel-like tree structure by
using files with special metadata such as content-type. For more information,
please check with Swift documents.

The implementation includes total of 8 modules. Six modules are the
implementations and two modules are test cases. The first module is named
cdmi.py which serves as a bootstrap or SWGI server. This module should be
placed in swift/common/middleware directory. This module also defines the
filter_factory method which is to make the entire module an OpenStack filter.
It also inspect each request and dispatch the request to container or data
object controllers in other two modules. Other than the first module, other
implementation modules can be found in swift/common/middleware/cdmiapp
directory.  Module cdmicommoncontroller.py is created to handle common
operations among container and data object such as read, delete,
and capabilities. Module cdmicontrollers.py and noncdmicontrollers.py are
created to handle cdmi content and non-cdmi content request operations such
as container creation and update.

Since CDMI specification defines capability against each container and data
object, so a client can send a request against a container or data object
capability URL to look up capabilities that entity supports, this
implementation naturally uses the cdmicommoncontroller.py module to response
to the capability (a GET request) request for both container and data object.

In cdmiapp directory, there are two small modules named cdmibase.py and
cdmiutils.py which are used to define a base controller class so that other
controllers can inherit from and few utility methods so the entire
implementation can be a little cleaner.

Test case modules are organized into a folder called cdmi which are placed in
siwft/test/functional/cdmi. These two modules are named test_cdmi_container.py
and test_cdmi_object.py which are to test container and data object requests
with capability functions. There are total of 70 test cases created to verify
various use cases.

CDMI specification allows an entity to have an objectID attribute which can be
used to access that object with a short and uniformed URL. But supporting of
the objectID is an optional requirement by CDMI specification. This
implementation choose not to support the CDMI objectID.

CDMI specification allows a container exists in another container, that is,
containers can be nested. This is a significant difference between OpenStack
and CDMI. This implementation uses OpenStack "application/directory" metadata
of an object to represent a container when it is not a top level container.

-----------------------------------------------
Install onto an existing OpenStack Swift server
-----------------------------------------------

Please follow the following steps to configure CDMI filter on an Swift
installation.

    1. In /etc/swift/proxy-server.conf, add cdmi filter before proxy-server

       [pipeline:main]
       pipeline = healthcheck cache tempauth *cdmi* proxy-server

       [filter:cdmi]
       use = egg:swift#cdmi

    2. In <swiftroot>/swift.egg-info/entry-points.txt, add the following line
       at the end of the section [paste.filter_factory]

       cdmi = swift.common.middleware.cdmi:filter_factory

    3. Once the above two steps are done, restart swift.

---------------------------------------------
Optional Configuration of this implementation
---------------------------------------------

Optionally, this implementation can be configured to use different access root.
By default, the access root looks like "http://hostname:port/cdmi", you can
configure the implementation to use different root like the following

    http://hostname:port/another/root

Simply change /etc/swift/proxy-server.conf file by adding the following line
in the [default] section:

    cdmi_root = another/root

cdmi capability prefix can also be configured by adding the following line.

    cdmi_capabilities = cap.

When it is configured this way, the cdmi capability URL may look like this
http://host:port/cdmi/cap/some/thing/else

You can also configure the supported version of CDMI by adding the following
line in the [default] section:

    cdmi_version_supported = 1.0.1, 2.0.1

The current implementation only support CDMI specification 1.0.1 so this
parameter should be set either to 1.0.1 or completely removed so it will
default to 1.0.1. This parameter was added in the implementation for future
use when more CDMI versions are supported.

------------------------------
How to use this implementation
------------------------------

The following steps assume that you are using Swift All In One configuration.
Your environment may be different from the Swift All In One configuration,
in that case, the user id and password used in the following steps should be
replaced with your configurations.

Once it is installed and optionally configured, a client can use the CDMI API
by following the steps below.

    1. Use http://hostname:port/cdmi to login, the host name and port should
       be the same host name and port number Swift uses, normally it should be
       8080 in a Swift All In One environment. The login should be a GET
       request with header like the following:

        X-Storage-User: test:tester
        X-Storage-Pass: testing

    2. Once you logged in, you should get something like the following in the
       response header.

        X-Auth-Token: AUTH_tk629536dff4ca4915b55227ab88363370
        X-Storage-Token: AUTH_tk629536dff4ca4915b55227ab88363370
        X-Storage-Url: http://192.168.1.63:8080/cdmi/AUTH_test

    3. Use the X-Auth-Token and the X-Storage-Url to retrieve all containers of
       an account.  Use the storage url in the login response header to send a
       GET request with the auth token, you should receive the following.

        if using None-CDMI api:

            HTTP/1.1 200 OK
            X-Account-Object-Count: 7
            X-Account-Bytes-Used: 130
            X-Account-Container-Count: 3
            Accept-Ranges: bytes
            Content-Length: 69
            Content-Type: text/plain; charset=utf-8
            Date: Tue, 24 Jan 2012 14:21:46 GMT

            cdmi_test_container_11327335466
            cdmi_test_container_11327335467
            pics

        if using CDMI api:

            HTTP/1.1 200 OK
            X-Account-Object-Count: 7
            X-Account-Bytes-Used: 130
            X-Account-Container-Count: 3
            Accept-Ranges: bytes
            Content-Type: application/json; charset=utf-8
            Content-Length: 340
            Date: Tue, 24 Jan 2012 14:19:51 GMT

            {
              "mimetype": "application/cdmi-container",
              "objectID": "41608b843cd98c2f598648fd2bd72c1fae0119be",
              "objectName": "AUTH_test",
              "parentURI": "/cdmi/",
              "objectType": "application/cdmi-container",
              "children": [
                "cdmi_test_container_11327335466",
                "cdmi_test_container_11327335467",
                "pics"
              ],
              "metadata": {}
            }

    4. Use CDMI spec specified URLs to manipulate containers, objects and
       capabilities of container and object.

    5. To query an entity capability, use the capability URL returned from
       the response coming back for the entity read GET request. a GET
       request will return capabilities defined allowed by this implementation.

--------------
Run Test Cases
--------------

CDMI test cases were developed as functional tests, it will access a running
Swift system with CDMI filter enabled. Before you run the test cases, make
sure CDMI filter configuration is correct by checking the proxy-server.conf
file of your installation.

Once OpenStack Swift is up running, switch to the following directory

    <SwiftInstallRoot>/test/functional/cdmi directory

Run the following two commands to test container and objects operations.

    To test container behaviors, issue "python test_cdmi_container.py" command
    To test object behaviors, issue "python test_cdmi_object.py" command