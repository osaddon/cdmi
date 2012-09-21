# Copyright (c) 2011 IBM
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

from webob import Request, Response
from swift.common.bufferedhttp import http_connect_raw
import json


def concat_parts(*args):
    path = ''
    if args and len(args) > 0:
        for index, item in enumerate(args):
            path += '/' + str(item) if item and item != '' else ''
    return path.lstrip('/')


# Define a constant class which only hold all the strings
class Consts(object):
    CDMI_VERSION = 'X-CDMI-Specification-Version'
    AUTH_TOKEN = 'X-Auth-Token'
    CDMI_APP_CONTAINER = 'application/cdmi-container'
    CDMI_APP_OBJECT = 'application/cdmi-object'
    CDMI_APP_CAPABILITY = 'application/cdmi-capability'
    APP_JSON = 'application/json'
    CDMI_VERSION_VALUE = '1.0.1'
    CONTAINER_ID = 'X-Container-Meta-Cdmi-Objectid'
    OBJECT_ID = 'X-Object-Meta-Cdmi-Objectid'
    META_CONTAINER_ID = 'x-container-meta-cdmi-'
    META_OBJECT_ID = 'x-object-meta-cdmi-'
    VALUE_ENCODING = 'x-object-meta-valuetransferencoding'
    ENCODING_BASE64 = 'base64'
    MULTIPART_TYPE = 'multipart/mixed'


class Controller(object):
    def __init__(self, conf, app, logger):
        self.app = app
        self.conf = conf
        self.response_args = []
        self.logger = logger
        self.cdmi_root = conf.get('cdmi_root')
        self.cdmi_version_supported = conf.get('cdmi_version_supported')
        self.cdmi_capability_id = conf.get('cdmi_capability_id')

    def do_start_response(self, *args):
        self.response_args.extend(args)


class ErrorController(Controller):
    """
    Error controller, handles cdmi path error requests
    """
    def __init__(self, env, conf, app, logger, account_name, **kwargs):
        Controller.__init__(self, conf, app, logger)


class CapabilityController(Controller):
    """
    Capability controller to handles cdmi capability request
    """
    def __init__(self, env, conf, app, logger, account_name, container_name,
                 parent_name, object_name, **kwargs):
        Controller.__init__(self, conf, app, logger)
        self.account_name = account_name
        self.container_name = container_name
        self.object_name = object_name
        self.parent_name = parent_name
        self.logger.info('tongli')
        self.logger.info(self.container_name)

    # Use GET to handle all cdmi log in attempt and respond with X-Storage-Url
    def GET(self, env, start_response):
        """
        Handle for GET method
        """
        res = Response()

        # System wide capability request
        if self.container_name is None or self.container_name == '':
            #this is a system capability request.
            res.status = 200
            res.headers['Content-Type'] = Consts.CDMI_APP_CAPABILITY
            res.headers[Consts.CDMI_VERSION] = Consts.CDMI_VERSION_VALUE

            body = {}
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name, ''])
            body['objectName'] = 'cdmi_capabilities/'
            body['objectType'] = Consts.CDMI_APP_CAPABILITY
            body['capabilities'] = {}
            body['capabilities']['cdmi_dataobjects'] = 'true'
            body['capabilities']['cdmi_object_copy_from_local'] = 'true'
            body['capabilities']['cdmi_multipart_mime'] = 'true'
            body['capabilities']['cdmi_metadata_maxitems'] = 90
            body['capabilities']['cdmi_metadata_maxtotalsize'] = 4096 * 90
            body['childrenRange'] = '0-2'
            body['children'] = ['rootcontainer/', 'container/',
                                'dataobject/']
            body['completionStatus'] = 'Complete'
        elif self.container_name == 'rootcontainer':
            res.status = 200
            res.headers['Content-Type'] = Consts.CDMI_APP_CAPABILITY
            res.headers[Consts.CDMI_VERSION] = Consts.CDMI_VERSION_VALUE

            body = {}
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          'cdmi_capabilities/'])
            body['objectName'] = 'rootcontainer/'
            body['objectType'] = Consts.CDMI_APP_CAPABILITY
            body['capabilities'] = {}
            body['capabilities']['cdmi_list_children'] = True
            body['capabilities']['cdmi_create_container'] = True
            body['childrenRange'] = '0-0'
            body['children'] = {}
            body['completionStatus'] = 'Complete'
        elif self.container_name == 'container':
            res.status = 200
            res.headers['Content-Type'] = Consts.CDMI_APP_CAPABILITY
            res.headers[Consts.CDMI_VERSION] = Consts.CDMI_VERSION_VALUE

            body = {}
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          'cdmi_capabilities/'])
            body['objectName'] = 'container/'
            body['objectType'] = Consts.CDMI_APP_CAPABILITY
            body['capabilities'] = {}
            body['capabilities']['cdmi_list_children'] = 'true'
            body['capabilities']['cdmi_read_metadata'] = 'true'
            body['capabilities']['cdmi_modify_metadata'] = 'true'
            body['capabilities']['cdmi_create_dataobject'] = 'true'
            body['capabilities']['cdmi_delete_container'] = 'true'
            body['capabilities']['cdmi_create_container'] = 'true'
            body['capabilities']['cdmi_copy_dataobject'] = 'true'
            body['childrenRange'] = '0-0'
            body['children'] = {}
            body['completionStatus'] = 'Complete'
        elif self.container_name == 'dataobject':
            res.status = 200
            res.headers['Content-Type'] = Consts.CDMI_APP_CAPABILITY
            res.headers[Consts.CDMI_VERSION] = Consts.CDMI_VERSION_VALUE

            body = {}
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          'cdmi_capabilities/'])
            body['objectName'] = 'dataobject/'
            body['objectType'] = Consts.CDMI_APP_CAPABILITY
            body['capabilities'] = {}
            body['capabilities']['cdmi_read_value'] = 'true'
            body['capabilities']['cdmi_read_metadata'] = 'true'
            body['capabilities']['cdmi_modify_value'] = 'true'
            body['capabilities']['cdmi_modify_metadata'] = 'true'
            body['capabilities']['cdmi_delete_dataobject'] = 'true'
            body['childrenRange'] = '0-0'
            body['children'] = {}
            body['completionStatus'] = 'Complete'
        else:
            res.status = 404
            body = {}

        res.body = json.dumps(body, indent=2)
        return res


class LoginController(Controller):
    """
    Login controller, handles cdmi login request
    """
    def __init__(self, env, conf, app, logger, account_name, **kwargs):
        Controller.__init__(self, conf, app, logger)
        env['PATH_INFO'] = '/auth/v1.0'

    # Use GET to handle all cdmi log in attempt and respond with X-Storage-Url
    def GET(self, env, start_response):
        """
        Handle GET Data Object request
        """
        # Create a new WebOb Request object according to the current request
        req = Request(env)
        ssl = True if req.scheme.lower() == 'https' else False

        conn = http_connect_raw(req.server_name, req.server_port, 'GET',
                                '/auth/v1.0', req.headers, None, ssl)
        res = conn.getresponse()

        # Create a new response
        resp = Response()
        if res.status == 200:
            storage_url = res.getheader('X-Storage-Url')
            resp.headers['X-Auth-Token'] = res.getheader('X-Auth-Token')
            resp.headers['X-Storage-Token'] = res.getheader('X-Storage-Token')
            subs = storage_url.partition('/v1/')
            resp.headers['X-Storage-Url'] = (req.host_url + '/' +
                                             self.cdmi_root + '/' + subs[2])
            return resp
        else:
            resp.status = res.status
            return resp


class AccountController(Controller):
    """
    Account controller, handles requests related to user account
    """
    def __init__(self, env, conf, app, logger, account_name, **kwargs):
        Controller.__init__(self, conf, app, logger)
        self.account_name = account_name
        env['PATH_INFO'] = '/v1/%s' % (account_name)

    def _read_root(self, env, start_response):

        req = Request(env)
        req.headers['Accept'] = Consts.APP_JSON
        res = req.get_response(self.app)

        body = {}

        # Setup required attributes for response body
        body['objectType'] = Consts.CDMI_APP_CONTAINER
        body['objectName'] = self.account_name + '/'
        body['parentURI'] = '/'.join(['', self.cdmi_root, ''])
        body['capabilitiesURI'] = '/'.join(['', self.cdmi_root,
                                            self.account_name,
                                            self.cdmi_capability_id,
                                           'rootcontainer/'])
        body['metadata'] = {}

        body['children'] = []

        if res.status_int == 200:
            children = json.loads(res.body)
            for child in children:
                body['children'].append(child['name'] + '/')
        body['childrenRange'] = '0-' + str(len(body['children']))
        res.body = json.dumps(body, indent=2)

        return res

    # Use GET to retrieve all cdmi containers for a given user
    def GET(self, env, start_response):
        """
        Handle request for container listing of an account
        """
        # Create a new WebOb Request object according to the current request
        req = Request(env)
        # if cdmi content, then we return response in cdmi format
        if req.headers.get(Consts.CDMI_VERSION, False):
            return self._read_root(env, start_response)
        else:
            res = req.get_response(self.app)
            return res
