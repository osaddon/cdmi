# Copyright (c) 2010-2011 IBM.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from test import get_config
from swiftclient.client import get_auth
import httplib
import time
import json


class TestCDMIContainer(unittest.TestCase):
    """ Test CDMI ContainerController """
    def setUp(self):
        self.conf = get_config()['func_test']
        if self.conf.get('auth_ssl', 'no') == 'yes':
            auth_method = 'https://'
        else:
            auth_method = 'http://'
        auth_host = (self.conf.get('auth_host') + ':' +
                    self.conf.get('auth_port'))
                     self.conf.get('auth_port'))
        auth_url = (auth_method + auth_host +
                    self.conf.get('auth_prefix') + 'v1.0')
        try:
            rets = get_auth(auth_url, (self.conf.get('account') +
                                       ':' + self.conf.get('username')),
                            self.conf.get('password'))
            self.auth_token = rets[1]
            #Parse the storage root and get the access root for CDMI
            pieces = rets[0].partition('/v1/')
            self.os_access_root = '/v1/' + pieces[2]
            self.access_root = ('/' + self.conf.get('cdmi_root', 'cdmi') +
                                '/' + pieces[2])
            self.cdmi_capability_root = ('/' +
                                         self.conf.get('cdmi_root', 'cdmi') +
                                         '/' +
                                         self.conf.get('cdmi_capability_id',
                                                       'cdmi_capabilities') +
                                         '/' + pieces[2])
            #Setup two container names
            suffix = format(time.time(), '.6f')
            self.child_container = "cdmi_test_child_container_" + suffix
            self.top_container = "cdmi_test_top_container_" + suffix
            self.child_container_to_create = \
                ("cdmi_test_child_container_create_" + suffix)
            self.top_container_to_create = ("cdmi_test_top_container_create_" +
                                            suffix)
            self.top_container_to_delete = ("cdmi_test_top_container_delete_" +
                                            suffix)
            #Create test containers
            self.__create_test_container(self.top_container)
            self.__create_test_container(self.top_container + '/' +
                                         self.child_container)
            self.__create_test_container(self.top_container_to_delete)
            self.__create_test_container(self.top_container + "/a/b/c/d/e/f")
        except Exception as login_error:
            raise login_error

    def tearDown(self):
        """ Tear down for testing CDMIContainerController """
        self.__delete_test_container(self.top_container + '/' +
                                     self.child_container_to_create)
        self.__delete_test_container(self.top_container + '/' +
                                     self.child_container)
        self.__delete_test_container(self.top_container_to_create)
        self.__delete_test_container(self.top_container_to_delete)
        self.__delete_test_container(self.top_container + "/a/b/c/d/e/f")
        self.__delete_test_container(self.top_container +
                                     "/a/b/c/real_container")
        self.__delete_test_container(self.top_container + "/a/b/c")
        self.__delete_test_container(self.top_container)

    def __concat_parts__(self, *args):
        path = ''
        if args and len(args) > 0:
            for index, item in enumerate(args):
                path += '/' + str(item) if item and item != '' else ''
        return path.lstrip('/')

    def __create_test_container(self, container_name):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'content-type': 'application/directory',
                   'content-length': '0'}
        conn.request('PUT', self.os_access_root + '/' + container_name,
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Test Container creation failed")

    def __delete_test_container(self, container_name):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', self.os_access_root + '/' + container_name,
                     None, headers)
        res = conn.getresponse()

    def test_create_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {"key1": "value1", "key2": "value2"}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container_to_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()

    def test_create_child_container_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {"key1": "value1", "key2": "value2"}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/c/real_container'),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()

    def test_create_child_container_no_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        body = {}
        body['metadata'] = {"key1": "value1", "key2": "value2"}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container_to_create + '/'),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201,
                         "Child container without header but with trailing \
                         slash should create container and not fail")
        conn.close()

    def test_create_child_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token, 'content-length': '0'}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container_to_create + '/'),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        conn.close()

    def test_create_child_container_in_virtual_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/c/real_container/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        conn.close()

    def test_create_grandchild_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token, 'content-length': '0'}
        non_exist_child_container = \
            "cdmi_test_non_exist_child_container_" + format(time.time(), '.6f')
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + non_exist_child_container + '/grandchild/'),
                    None, headers)
        res = conn.getresponse()
        #We expect 404 error since the parent container does not exist
        self.assertEqual(res.status, 404, "Container creation failed")
        conn.close()

    def test_create_top_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {"key1": "value1", "key2": "value2"}
        conn.request('PUT', (self.access_root + '/' +
                             self.top_container_to_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         "objectType must be application/cdmi-container")

    def test_create_top_container_with_empty_body(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        conn.request('PUT', (self.access_root + '/' +
                             self.top_container_to_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         "objectType must be application/cdmi-container")

    def test_create_top_container_without_body(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        conn.request('PUT', (self.access_root + '/' +
                             self.top_container_to_create),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         "objectType must be application/cdmi-container")

    def test_create_top_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token, 'content-length': '0'}
        conn.request('PUT', (self.access_root + '/' +
                             self.top_container_to_create + '/'),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, "Container creation failed")
        conn.close()

    def test_read_top_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' +
                             self.top_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         'objectType must be application/cdmi-container')

    def test_read_top_account_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', self.access_root + '/', None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, "Account read failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilitiesURI'],
                             'No capabilitiesURI found which is required.')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         'objectType must be application/cdmi-container')

    def test_read_top_account_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', self.access_root + '/', None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, "Account read failed")
        conn.close()

    def test_read_top_non_exist_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, "Container read should have failed")
        conn.close()

    def test_read_top_container_with_wrong_version(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '4.x.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 400, "Container read should have failed")
        conn.close()

    def test_read_top_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()

    def test_read_top_non_exist_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', (self.access_root + '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f') + '/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, "Container read should have failed")
        conn.close()

    def test_read_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         'objectType must be application/cdmi-container')

    def test_read_virtual_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/a/b/c'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         'objectType must be application/cdmi-container')

    def test_read_virtual_child_container_without_header_trailing_slash(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/a/b'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409, 'Container read should have failed')

    def test_read_virtual_child_container_wo_header_w_trailing_slash(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/a/b/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         "objectType must be application/cdmi-container")

    def test_read_non_exist_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, "Container read should have failed")
        conn.close()

    def test_read_child_container_no_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409,
                         "The read operation should have failed")

    def test_read_child_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNotNone(body['metadata'],
                             'No metadata found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-container',
                         "objectType must be application/cdmi-container")

    def test_read_child_container_non_cdmi_without_trailing_slash(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409, 'Container read should have failed')

    def test_read_non_exist_child_container_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f') + '/'),
                             None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, 'Container read should have failed')
        conn.close()

    def test_child_container_capability_with_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container capability read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'],
                             'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_child_container_capability_with_prefix(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container + '/' + self.child_container),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, "Container capability read failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'],
                             'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_child_virtual_container_capability(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container + '/a/b'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, "Container capability read failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'],
                             'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_non_exist_child_container_capability(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container + '/' +
                             'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Container capability read should have failed')
        conn.close()

    def test_top_container_capability_with_header_prefix(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, "Container capability read failed")
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'],
                             'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_top_container_capability_with_prefix_without_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Container capability read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'],
                             'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_non_exist_top_container_capability(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Container capability read should have failed')

    def test_update_top_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {'key1': 'value111', 'key2': 'value222'}
        conn.request('PUT', self.access_root + '/' + self.top_container,
                           json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertIn(res.status, [201, 202, 204], 'Container update failed')
        conn.close()

    def test_update_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {'key1': 'value111', 'key2': 'value222'}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertIn(res.status, [201, 202, 204], 'Container update failed')
        conn.close()

    def test_update_virtual_child_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-container',
                   'Content-Type': 'application/cdmi-container'}
        body = {}
        body['metadata'] = {'key1': 'updated', 'key2': 'updated'}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/c'), json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertIn(res.status, [201, 202, 204], 'Container update failed')
        conn.close()

    def test_delete_child_container(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'Container deletion failed')
        conn.close()

    def test_delete_virtual_child_container(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/a/b'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409,
                         'Container deletion should have failed')
        conn.close()

    def test_delete_child_container_non_cdmi(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container + '/'),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'Container deletion failed')
        conn.close()

    def test_delete_top_container(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' +
                                self.top_container_to_delete), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'Container deletion failed')
        conn.close()

    def test_delete_top_non_exist_container(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' +
                                'cdmi_test_not_exist_' +
                                format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Container deletion should have failed')
        conn.close()

    def test_delete_top_container_non_cdmi(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', (self.access_root + '/' +
                                self.top_container_to_delete + '/'),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'Container deletion failed')
        conn.close()

    def test_delete_top_non_exist_container_non_cdmi(self):
        #Delete the child container first
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', (self.access_root + '/' +
                                'cdmi_test_not_exist_' +
                                format(time.time(), '.6f') + '/'),
                     None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Container deletion should have failed')
        conn.close()

#if __name__ == '__main__':
#    unittest.main()
suite = unittest.TestLoader().loadTestsFromTestCase(TestCDMIContainer)
unittest.TextTestRunner(verbosity=2).run(suite)
