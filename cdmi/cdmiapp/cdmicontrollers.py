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

from cdmibase import \
    (Consts, Controller, concat_parts)
from cdmiutils import \
    (get_err_response, check_resource)
from cdmicommoncontroller import \
    (CDMIBaseController)
from urllib import unquote, quote
from webob import Request, Response
from swift.common.utils import get_logger
from swift.common.utils import split_path
from swift.common.bufferedhttp import http_connect_raw
import json
import base64


class ContainerController(CDMIBaseController):
    """
    Handles container request.
    This controller handles create and update for container
    """

    # Use PUT to handle container update and create
    def PUT(self, env, start_response):
        """
        Handle Container update and create request
        """

        # First check if the resource exists and if it is a directory
        path = '/' + concat_parts('v1', self.account_name, self.container_name,
                                  self.parent_name, self.object_name)
        exists, headers, dummy = check_resource(env, 'GET', path,
                                                self.logger, False)
        if exists:
            content_type = headers.get('content-type', '')
            content_type = content_type.lower() if content_type else ''
            if (content_type.find('application/directory') < 0 and
                self.object_name):
                return get_err_response('Conflict')
        # Not a top container, so it has to be virtual container
        else:
            res = self._check_parent(env, start_response)
            if res:
                return res

        # Create a new WebOb Request object according to the current request
        req = Request(env)

        # We are creating a container, set the content-type to be
        # application/directory
        req.headers['content-type'] = 'application/directory'

        metadata = {}
        if req.body:
            try:
                body = json.loads(req.body)
            except ValueError:
                return get_err_response('InvalidContent')

            metadata = body.get('metadata')
            if metadata:
                for key in metadata:
                    if metadata[key] == '':
                        req.headers[self.metadata_prefix + key] = ''
                    else:
                        req.headers[self.metadata_prefix + key] = \
                            key + ":" + str(metadata[key])
            else:
                metadata = {}

        # Now set the body to be empty and content-length to 0
        req.body = ''
        req.headers['Content-Length'] = 0

        res = req.get_response(self.app)

        # Deal with the response now.
        # Build the response message body according to CDMI specification
        # if the response status is 201, then we know we have successfully
        # created the container. According to CDMI spec, only send response
        # body when creating new container
        if res.status_int == 201:
            body = {}
            body['objectType'] = Consts.CDMI_APP_CONTAINER
            body['objectName'] = (self.object_name + '/') if self.object_name \
                else (self.container_name + '/')
            if self.object_name:
                body['parentURI'] = '/'.join(['', self.cdmi_root,
                                              self.account_name,
                                              self.container_name,
                                              self.parent_name, ''])
            else:
                body['parentURI'] = '/'.join(['', self.cdmi_root,
                                              self.account_name, ''])

            body['capabilitiesURI'] = '/'.join(['', self.cdmi_root,
                                                self.account_name,
                                                self.cdmi_capability_id,
                                                'container/'])
            body['completionStatus'] = 'Complete'
            body['metadata'] = metadata
            res.body = json.dumps(body, indent=2)
        # Otherwise, no body should be returned.
        else:
            res.body = ''

        return res


class ObjectController(CDMIBaseController):
    """
    Handles requests for create and update of objects
    """

    # Use PUT to handle object update and create
    def PUT(self, env, start_response):
        """
        Handle Container update and create request
        """
        # First check if the resource exists and if it is a directory
        path = '/' + concat_parts('v1', self.account_name, self.container_name,
                                  self.parent_name, self.object_name)
        exists, headers, body = check_resource(env, 'GET', path, self.logger,
                                               False, None)
        if exists:
            content_type = headers.get('content-type', '')
            content_type = content_type.lower() if content_type else ''
            if content_type.find('application/directory') >= 0:
                return get_err_response('Conflict')
        else:
            path = '/' + concat_parts('v1', self.account_name,
                                      self.container_name)
            query_string = 'delimiter=/&prefix=' + \
                concat_parts(self.parent_name, self.object_name) + '/'
            parent_exists, dummy, body = check_resource(env, 'GET', path,
                                                        self.logger, True,
                                                        query_string)
            if parent_exists:
                try:
                    children = json.loads(body)
                    if len(children) > 0:
                        # No children under, no resource exist
                        return get_err_response('Conflict')
                except ValueError:
                    return get_err_response('InconsistantState')
            else:
                return get_err_response('NoParentContainer')

        # Check if the parent is OK. it should be either a real directory or
        # a virtual directory
        res = self._check_parent(env, start_response)
        if res:
            return res

        # Create a new WebOb Request object according to the current request
        #if we found X-Object-UploadID in the header, we need know that
        #the request is uploading a piece of a large object, the piece
        #will need to go to the segments folder

        try:
            self._handle_part(env)
        except Exception as ex:
            return get_err_response(ex.message)

        req = Request(env)

        metadata = {}
        if req.body:
            try:
                body = self._handle_body(env, True)
            except Exception:
                return get_err_response('InvalidBody')

            # headling copy object
            if body.get('copy'):
                # add the copy-from header to indicate a copy operation
                # for swift
                req.headers['X-Copy-From'] = body.get('copy')
                req.body = ''
            else:
                if body.get('metadata'):
                    metadata = body['metadata']
                    for key in metadata:
                        if metadata[key] == '':
                            req.headers[Consts.META_OBJECT_ID + key] = ''
                        else:
                            req.headers[Consts.META_OBJECT_ID + key] = \
                                key + ":" + str(metadata[key])
                else:
                    metadata = {}

                try:
                    req.body = str(body.get('value', ''))
                    req.headers['content-type'] = body.get('mimetype',
                        'text/plain').lower()
                    encoding = body.get('valuetransferencoding', 'utf-8')
                    req.headers[Consts.VALUE_ENCODING] = encoding
                    # if the value is encoded using base64, then
                    # we need to decode it and save as binary
                    if encoding == Consts.ENCODING_BASE64:
                        req.body = base64.decodestring(req.body)
                except KeyError:
                    return get_err_response('InvalidContent')
        else:
            req.headers['content-length'] = '0'

        res = req.get_response(self.app)

        # Deal with the response now.
        # Build the response message body according to CDMI specification
        # If the response status is 201, then we know we have successfully
        # created the object. According to CDMI spec, only send response body
        # when creating new object.
        if res.status_int == 201:
            body = {}
            body['objectType'] = Consts.CDMI_APP_OBJECT
            body['objectName'] = self.object_name
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          self.container_name,
                                          self.parent_name, ''])

            body['capabilitiesURI'] = '/'.join(['', self.cdmi_root,
                                               self.account_name,
                                               self.cdmi_capability_id,
                                               'dataobject/'])

            if env.get('HTTP_X_USE_EXTRA_REQUEST'):
                extra_res = self._put_manifest(env)
                res.status_int = extra_res.status

            body['metadata'] = metadata
            res.body = json.dumps(body, indent=2)
        # Otherwise, no response body should be returned.
        else:
            res.body = ''

        return res
