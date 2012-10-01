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
    (get_pair_from_header, get_err_response, check_resource, send_manifest)
from webob import Request, Response
from swift.common.utils import get_logger
from urlparse import parse_qs
import json
import base64
import email
import mimetypes


class CDMIBaseController(Controller):
    """
    Handles container request.
    This is the base class for other controllers. In the constructor,
    it sets up new path for handing the request to OS and also set up
    the parent_name, metadata_prefix according to OS structure. This base
    class defines few more utility methods to process metadata and check
    parent status according to the request path.
    """
    def __init__(self, env, conf, app, logger, account_name, container_name,
                 parent_name, object_name, **kwargs):
        Controller.__init__(self, conf, app, logger)
        self.account_name = account_name
        self.container_name = container_name
        self.object_name = object_name
        self.parent_name = parent_name
        if self.object_name:
            self.metadata_prefix = Consts.META_OBJECT_ID
        else:
            self.metadata_prefix = Consts.META_CONTAINER_ID
        env['PATH_INFO'] = '/v1/' + concat_parts(self.account_name,
                                                 self.container_name,
                                                 self.parent_name,
                                                 self.object_name)

    def _process_metadata(self, headers):
        """ Get CDMI metadata from the header and add to the body """
        metadata = {}
        for header, value in headers.iteritems():
            key = header.lower()
            if key.startswith(self.metadata_prefix):
                key, value = get_pair_from_header(value)
                if key != '' and value != '':
                    metadata[key] = value

        return metadata

    def _check_parent(self, env, start_response):
        """
        This method checks if the parent really represents a directory.
        Returns error if parent does not exist or the parent actually points
        to a non directory. Returns None means that the parent points to a
        valid container (top container or virtual container)
        """
        if self.parent_name:
            # Try to hit the resource url and see if it exists
            path = '/' + concat_parts('v1', self.account_name,
                                      self.container_name, self.parent_name)
            exists, headers, dummy = check_resource(env, 'GET',
                                                    path, self.logger)
            if exists:
                content_type = str(headers.get('content-type', ''))
                if content_type.find('application/directory') < 0:
                    return get_err_response('InvalidContainerName')
                else:
                    return None
            else:
                # Check if there is anything below that parent, if it is,
                # then this is actually a virtual container.
                path = '/' + concat_parts('v1', self.account_name,
                                          self.container_name)
                query_string = 'delimiter=/&prefix=' + self.parent_name + '/'
                parent_exists, dummy, body = check_resource(env, 'GET', path,
                                                            self.logger, True,
                                                            query_string)
                if parent_exists:
                    try:
                        children = json.loads(body)
                        if len(children) <= 0:
                            # No children under, no resource exist
                            return get_err_response('NoParentContainer')
                        else:
                            return None
                    except ValueError:
                        return get_err_response('InconsistantState')
                # The root container does not event exist, this is an error
                else:
                    return get_err_response('NoParentContainer')

        return None

    def _check_resource_attribute(self, env, start_response):
        """
        This method checks if a given url points to either a container, or
        an object or does not exist. It will also check if a resource is a
        virtual container in CDMI term. If a resource exists, the headers
        will also be return in following sequence.
        res - The response which containers errors, None means there is no
        error
        is_container - if it is a container, it is True, otherwise, it is
        False
        headers - if the resource exists, this holds the headers
        children - if it is a container, return container's child list
        """
        path = env['PATH_INFO']
        res, is_container, headers, children = None, False, {}, None
        exists, headers, dummy = check_resource(env, 'GET', path, self.logger)
        # If exists, we need to check if the resource is a container
        if exists:
            content_type = (headers.get('content-type') or '').lower()
            if (content_type.find('application/directory') < 0 and
                self.object_name):
                is_container = False
            else:
                is_container = True
        # None self.object_name means that we are dealing with a real OS
        # container, return resource not found error
        elif not self.object_name:
            res = get_err_response('NoSuchKey')

        if res is None and (not exists or is_container):
            # Now we will try to get the children of the container and also
            # do more checks to see if there is any virtual resources.
            path = '/' + concat_parts('v1', self.account_name,
                                      self.container_name)
            query_string = 'delimiter=/'
            if self.object_name:
                query_string += ('&prefix=' +
                                 concat_parts(self.parent_name,
                                              self.object_name) +
                                 '/')

            container_exists, dummy, body = check_resource(env, 'GET', path,
                                                           self.logger, True,
                                                           query_string)
            if container_exists:
                try:
                    children = json.loads(body)
                    no_of_children = len(children)
                    # The entity could be a virtual container since it
                    # does not exist
                    if not exists:
                        # There is no children under also not exists,
                        # it is not virtual container.
                        if no_of_children <= 0:
                            res = get_err_response('NoSuchKey')
                        # There are children under and not exist, it is
                        # a virtual container
                        elif no_of_children > 0 and not exists:
                            is_container = True
                except ValueError:
                    res = get_err_response('InconsistantState')
            else:
                res = get_err_response('NoSuchKey')

        return res, is_container, headers, children

    def _handle_body(self, env, is_cdmi_type=False):
        '''
        this method will parse the multipart message and return one object
           body = {'value': 'some value', 'mimetype': content_type}
        if the request body is not multipart, then for cdmi content request
        this method will parse the body as json. for non cdmi content request
        this method will simply make a body object with the value being
        the request body and the mimetype being the content type
        '''
        body = {}
        req = Request(env)
        content_type = (req.headers['Content-Type'] or '').lower()
        # multipart
        if content_type.find('multipart/mixed') >= 0:
            try:
                message = email.message_from_file(req.body_file)
                for i, part in enumerate(message.walk()):
                    if i > 0:
                        content_type = part.get_content_type() or ''
                        if (content_type.find('cdmi-object') > 0 and
                            is_cdmi_type):
                            payload = part.get_payload(decode=True)
                            body.update(json.loads(payload))
                        else:
                            body['value'] = part.get_payload(decode=True)
                            body['mimetype'] = content_type
            except Exception as ex:
                raise ex
        # not multipart
        elif is_cdmi_type:
            body = json.loads(req.body)
            body['mimetype'] = body.get('mimetype', content_type)
        else:
            body['value'] = req.body
            body['mimetype'] = content_type

        return body

    def _handle_part(self, env):
        '''
        This method will inspect if the request is part of a series of
        a large data object upload. inspect the headers such as
        X-Object-UploadID, X-CDMI-Partial, Content-Range
        '''

        try:
            upload_id = env.get('HTTP_X_CDMI_UPLOADID')
            cdmi_partial = (env.get('HTTP_X_CDMI_PARTIAL') or '').lower()
            content_range = (env.get('HTTP_CONTENT_RANGE') or '').lower()
            if upload_id and cdmi_partial:
                start, end = self._get_range(content_range)
                if start:
                    new_name = self.object_name + '_segments/'
                    new_name += upload_id + '/' + start
                    new_name += '-' + end if end else ''
                    env['PATH_INFO'] = \
                        '/v1/' + concat_parts(self.account_name,
                                              self.container_name,
                                              self.parent_name, new_name)

                if cdmi_partial.find('false') >= 0:
                    new_name = self.object_name + '_segments/' + upload_id
                    new_name += '/'
                    env['HTTP_X_OBJECT_MANIFEST'] = \
                        concat_parts(self.container_name,
                                     self.parent_name, new_name)
                    #only when there is a content and cdmi_partial is false
                    #two requests are needed
                    if start:
                        env['HTTP_X_USE_EXTRA_REQUEST'] = 'true'

        except Exception as ex:
            raise ex

    def _put_manifest(self, env):
        '''
        This method will send the manifest request
        '''
        if env.get('HTTP_X_OBJECT_MANIFEST'):
            path = '/v1/' + concat_parts(self.account_name,
                                        self.container_name,
                                        self.parent_name,
                                        self.object_name)
            extra_header = {}
            extra_header['X-OBJECT-MANIFEST'] = \
                env.get('HTTP_X_OBJECT_MANIFEST')
            return send_manifest(env, 'PUT', path, self.logger, extra_header)

    def _get_range(self, header_value, valid_units=('bytes', 'none')):
        """Parses the value of an HTTP Range: header.
        The value of the header as a string should be passed in; without
        the header name itself.
        Returns a range object.
        """
        if header_value and len(header_value.strip()) > 0:
            parts = header_value.split('=')
            if parts[0] != 'bytes' or len(parts) != 2:
                raise Exception('InvalidRange')
            # further split and get the range
            parts = parts[1].split('-')
            if len(parts) < 1 or len(parts) > 2:
                raise Excetpion('InvalidRange')
            start = '%020d' % int(parts[0])
            if len(parts) == 2:
                end = '%020d' % int(parts[1])
            else:
                end = None
            return start, end
        else:
            return None, None


class CDMICommonController(CDMIBaseController):
    """
    the base controller which handles entity read and delete
    extended the controllers will handle other operations.
    """

    def _read_object(self, env, start_response, headers):

        query_string = env.get('QUERY_STRING', '').lower()
        if len(query_string) > 0:
            params = parse_qs(query_string, True, False)
            new_qs = ''
            for key, value in params.items():
                if 'value:bytes' == key:
                    env['HTTP_RANGE'] = 'bytes=' + ''.join(value)
                else:
                    new_qs += key + '=' + ''.join(value) + '&'
            env['QUERY_STRING'] = new_qs

        req = Request(env)
        os_res = req.get_response(self.app)

        cdmi_version = env.get('HTTP_X_CDMI_SPECIFICATION_VERSION', False)
        # If this is not a CDMI content request, simply return the response
        if not cdmi_version:
            return os_res

        # For CDMI content request, more work need to be done.
        res = Response()
        # Set up CDMI required headers
        res.headers[Consts.CDMI_VERSION] = Consts.CDMI_VERSION_VALUE
        res.headers['Content-Type'] = Consts.CDMI_APP_OBJECT

        object_body = os_res.body
        # Build the response message body according to CDMI specification
        body = {}

        # Setup required attributes for response body
        body['objectType'] = Consts.CDMI_APP_OBJECT
        body['objectName'] = self.object_name

        if self.parent_name != '':
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          self.container_name,
                                          self.parent_name, ''])
        else:
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          self.container_name, ''])

        body['capabilitiesURI'] = '/'.join(['', self.cdmi_root,
                                            self.account_name,
                                            self.cdmi_capability_id,
                                            'dataobject/'])

        body['completionStatus'] = 'Complete'
        body['metadata'] = {}

        # Handling CDMI metadata
        body['metadata'] = self._process_metadata(headers)
        body['mimetype'] = headers.get('content-type', '')
        encoding = headers.get(Consts.VALUE_ENCODING, 'utf-8')
        body['valuetransferencoding'] = encoding
        if (encoding.lower() == Consts.ENCODING_BASE64 or
            'text/' not in body['mimetype']):
            body['valuetransferencoding'] = Consts.ENCODING_BASE64
            body['value'] = base64.encodestring(object_body)
        else:
            body['value'] = object_body
        body['valuerange'] = '0-' + str(len(object_body))
        res.body = json.dumps(body, indent=2)
        res.status_int = os_res.status_int

        return res

    def _read_container(self, env, start_response, headers, children):

        # Build the response message body according to CDMI specification
        res = Response()
        res.headers['content-type'] = 'application/json; charset=UTF-8'

        body = {}

        # Setup required attributes for response body
        body['objectType'] = Consts.CDMI_APP_CONTAINER
        if self.object_name:
            body['objectName'] = self.object_name + '/'
            if self.parent_name != '':
                body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          self.container_name,
                                          self.parent_name, ''])
            else:
                body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name,
                                          self.container_name, ''])
        else:
            body['objectName'] = self.container_name + '/'
            body['parentURI'] = '/'.join(['', self.cdmi_root,
                                          self.account_name, ''])

        body['capabilitiesURI'] = '/'.join(['', self.cdmi_root,
                                            self.account_name,
                                            self.cdmi_capability_id,
                                            'container/'])
        body['completionStatus'] = 'Complete'
        body['metadata'] = {}

        #Get CDMI metadata from the header and add to the body
        for header, value in headers.iteritems():
            key = header.lower()
            if key.startswith(self.metadata_prefix):
                key, value = get_pair_from_header(value)
                if key != '' and value != '':
                    body['metadata'][key] = value

        body['children'] = []
        if children:
            string_to_cut = concat_parts(self.parent_name, self.object_name)
            size = len(string_to_cut)
            if size > 0:
                size += 1
            tracking_device = {}
            for child in children:
                if child.get('name', False):
                    child_name = child.get('name')
                else:
                    child_name = child.get('subdir', False)
                if child_name:
                    child_name = child_name[size:]
                    if not child_name.endswith('/'):
                        content_type = child.get('content_type', '')
                        if content_type.find('directory') >= 0:
                            child_name += '/'
                    if tracking_device.get(child_name) is None:
                        tracking_device[child_name] = child_name
                        body['children'].append(child_name)
        body['childrenRange'] = '0-' + str(len(body['children']))
        res.body = json.dumps(body, indent=2)
        res.status_int = 200

        return res

    def _read_entity(self, env, start_response):
        res, is_container, headers, children = \
            self._check_resource_attribute(env, start_response)

        if res is None:
            if ((is_container and not env.get('X-WANTS-CONTAINER')) or
                (not is_container and env.get('X-WANTS-CONTAINER'))):
                return get_err_response('Conflict')

            if is_container:
                return self._read_container(env, start_response,
                                            headers, children)
            else:
                return self._read_object(env, start_response, headers)
        else:
            return res

    # Use GET to handle all container read related operations.
    # TODO: filtering resources
    def GET(self, env, start_response):
        """
        Handle GET Container (List Objects) request
        """
        return self._read_entity(env, start_response)

    def DELETE(self, env, start_response):
        """
        Handle DELETE both container and data object removal.
        """

        path = '/v1/' + self.account_name + '/' + self.container_name
        query_string = 'delimiter=/'
        if self.object_name:
            query_string += '&prefix=' + concat_parts(self.parent_name,
                                                      self.object_name) + '/'
        exists, dummy, body = check_resource(env, 'GET', path, self.logger,
                                             True, query_string)
        # Not even the top container exist, so there is no such resource.
        if not exists:
            return get_err_response('NoSuchKey')
        # Top container exists, check if there is anything under.
        else:
            try:
                children = json.loads(body)
                #there are some children under
                if len(children) > 0:
                    return get_err_response('ContainerNotEmpty')
            except ValueError:
                return get_err_response('InconsistantState')

        # Create a new WebOb Request object according to the current request
        req = Request(env)
        # Now send the request over.
        return req.get_response(self.app)
