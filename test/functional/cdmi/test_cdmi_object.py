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
import base64


class TestCDMIObject(unittest.TestCase):
    """ Test CDMI ContainerController """
    def setUp(self):
        self.conf = get_config()['func_test']
        if self.conf.get('auth_ssl', 'no') == 'yes':
            auth_method = 'https://'
        else:
            auth_method = 'http://'
        auth_host = (self.conf.get('auth_host') + ':' +
                     self.conf.get('auth_port'))
        auth_url = (auth_method + auth_host +
                    self.conf.get('auth_prefix') + 'v1.0')
        try:
            rets = get_auth(auth_url, (self.conf.get('account') + ':' +
                                       self.conf.get('username')),
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
            self.top_container = 'cdmi_test_top_container_' + suffix
            self.child_container = 'cdmi_test_child_container_' + suffix
            self.object_create = 'cdmi_test_object_create_' + suffix
            self.object_copy = 'cdmi_test_object_copy_' + suffix
            self.object_test = 'cdmi_test_object_' + suffix

            #Create test containers
            self.__create_test_container(self.top_container)
            self.__create_test_container(self.top_container + '/' +
                                         self.child_container)
            self.__create_test_container(self.top_container + '/a/b/c/d/e/f')
            self.__create_test_container(self.top_container + '/a/b/c/d')
            self.__create_test_object(self.top_container + '/' +
                                      self.child_container + '/' +
                                      self.object_test)
            self.__create_test_object(self.top_container + '/a/b/cc')

        except Exception as login_error:
            raise login_error

    def tearDown(self):
        """ Tear down for testing CDMIContainerController """
        self.__delete_test_entity(self.top_container + '/' +
                                  self.child_container + '/' +
                                  self.object_test)
        self.__delete_test_entity(self.top_container + '/' +
                                  self.child_container + '/' +
                                  self.object_create)
        self.__delete_test_entity(self.top_container + '/' +
                                  self.child_container + '/' +
                                  self.object_copy)
        self.__delete_test_entity(self.top_container + '/' +
                                  self.child_container)
        self.__delete_test_entity(self.top_container + '/a/b/c/real_object')
        self.__delete_test_entity(self.top_container + '/a/b/c/d')
        self.__delete_test_entity(self.top_container + '/a/b/c/d/e/f')
        self.__delete_test_entity(self.top_container + '/a/b/c')
        self.__delete_test_entity(self.top_container + '/a/b/cc')
        self.__delete_test_entity(self.top_container)

    def __create_test_container(self, container_path):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'content-type': 'application/directory',
                   'content-length': '0'}
        conn.request('PUT', (self.os_access_root + '/' +
                             container_path), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Test Container creation failed')

    def __create_test_object(self, object_path):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('PUT', self.os_access_root + '/' + object_path,
                     'test object body', headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Test Object creation failed')

    def __delete_test_entity(self, entity_path):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', self.os_access_root + '/' + entity_path,
                     None, headers)
        res = conn.getresponse()

    def test_create_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['value'] = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object creation failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_copy_object_same_dir(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['copy'] = '/'.join(['', self.top_container, self.child_container,
                                self.object_test])
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_copy),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object copy failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_copy_object_different_dir(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['copy'] = '/'.join(['', self.top_container, 'a/b/cc'])

        print body['copy']
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_copy),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object copy failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_copy_object_non_exist(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['copy'] = '/'.join(['', self.top_container, 'a/b/non_exist'])

        print body['copy']
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_copy),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Non exist object copy should have failed')

    def test_handle_base64_object(self):
        # create a new object using base64 encoded data
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['valuetransferencoding'] = 'base64'
        original_value = base64.encodestring('value of the object')
        body['value'] = original_value
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201,
                         'Base64 encoded value object creation failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')
        conn.close()

        # read the object just created.
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200,
                         'Base64 encoded value object read failed')
        data = res.read()
        try:
            body = json.loads(data)
            encoding = body['valuetransferencoding']
            value = body['value']
        except Exception as parsing_error:
            raise parsing_error

        self.assertEquals(encoding, 'base64', 'Encoding is not base64')
        self.assertEquals(value, original_value,
                      'encoded value does not match original')
        conn.close()

    def test_create_object_with_empty_body(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object creation failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_create_object_without_body(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object creation failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_create_object_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['value'] = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/c/real_object'),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Object creation failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_create_object_in_virtual_container_with_conflict_name(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['value'] = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/c/d'), json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409,
                         'Object creation should have failed')

    def test_create_object_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        body = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create), body, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 201, 'Non-CDMI Object creation failed')

    def test_create_object_invalid_body(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = '{value": "wrong", "mimetype": "text/plain"}'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_create), body, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 400, 'Object creation should have failed')

    def test_create_object_no_parent(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['value'] = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             'cdmi_test_not_exist_' +
                             format(time.time(), '.6f') + '/' +
                             self.object_create),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Object creation should have failed')

    def test_create_object_exists_as_parent(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value1', 'key2': 'value2'}
        body['mimetype'] = 'text/plain'
        body['value'] = 'value of the object'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409, 'Object creation should have failed')

    def test_read_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Object read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_read_object_with_header_with_trailing_slash(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_test + '/'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 409, 'Object read should have failed')

    def test_read_object_without_accept_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Object read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_read_object_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/a/b/cc'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Object read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        self.assertIsNotNone(body['parentURI'],
                             'Not parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'Not objectName found which is required.')
        self.assertIsNotNone(body['objectType'],
                             'Not objectType found which is required.')

    def test_read_object_with_wrong_version(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '4.x.x1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container +
                             '/' + self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 400, 'Object read should have failed')
        conn.close()

    def test_read_non_exist_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container + '/' +
                             'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, 'Object read should have failed')

    def test_read_non_exist_object_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/a/b/c/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, 'Object read should have failed')

    def test_update_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value111', 'key2': 'value222'}
        body['value'] = 'New Test body value'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container +
                             '/' + self.object_test),
                     json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertIn(res.status, [201, 202, 204], 'Object update failed')

    def test_update_object_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-object',
                   'Content-Type': 'application/cdmi-object'}
        body = {}
        body['metadata'] = {'key1': 'value111', 'key2': 'value222'}
        body['value'] = 'New Test body value'
        conn.request('PUT', (self.access_root + '/' + self.top_container +
                             '/a/b/cc'), json.dumps(body, indent=2), headers)
        res = conn.getresponse()
        self.assertIn(res.status, [201, 202, 204], 'Object update failed')

    def test_delete_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container +
                                '/' + self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'object deletion failed')

    def test_delete_object_in_virtual_container(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/a/b/cc'), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'object deletion failed')

    def test_delete_object_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container +
                                '/' + self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 204, 'object deletion failed')

    def test_delete_non_exist_object(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container +
                                '/' + 'cdmi_test_not_exist_' +
                                format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, 'object deletion should have failed')

    def test_delete_non_exist_object_non_cdmi(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token}
        conn.request('DELETE', (self.access_root + '/' + self.top_container +
                                '/' + self.child_container +
                                '/' + 'cdmi_test_not_exist_' +
                                format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404, 'object deletion should have failed')

    def test_object_capability_with_header_no_prefix(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container +
                             '/' + self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Object capability read failed')
        data = res.read()
        try:
            body = json.loads(data)
        except Exception as parsing_error:
            raise parsing_error
        conn.close()
        self.assertIsNotNone(body['capabilities'], 'No capabilities found')
        self.assertIsNotNone(body['parentURI'],
                             'No parentURI found which is required.')
        self.assertIsNotNone(body['objectName'],
                             'No objectName found which is required.')
        self.assertIsNot(body['objectType'],
                         'application/cdmi-capability',
                         'objectType should be application/cdmi-capability.')

    def test_object_capability_with_prefix_no_header(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.cdmi_capability_root +
                             '/' + self.top_container +
                             '/' + self.child_container +
                             '/' + self.object_test), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200, 'Object capability read failed')
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

    def test_non_exist_object_capability(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1',
                   'Accept': 'application/cdmi-capability'}
        conn.request('GET', (self.access_root + '/' + self.top_container +
                             '/' + self.child_container +
                             '/' + 'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Object capability read should have failed')

    def test_non_exist_object_capability_with_prefix(self):
        conn = httplib.HTTPConnection(self.conf.get('auth_host'),
                                      self.conf.get('auth_port'))
        headers = {'X-Auth-Token': self.auth_token,
                   'X-CDMI-Specification-Version': '1.0.1'}
        conn.request('GET', (self.cdmi_capability_root + '/' +
                             self.top_container + '/' +
                             self.child_container + '/' +
                             'cdmi_test_not_exist_' +
                             format(time.time(), '.6f')), None, headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 404,
                         'Object capability read should have failed')

#if __name__ == '__main__':
#    unittest.main()
suite = unittest.TestLoader().loadTestsFromTestCase(TestCDMIObject)
unittest.TextTestRunner(verbosity=2).run(suite)
