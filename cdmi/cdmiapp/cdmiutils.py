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

# This module defines utility methods used by both cdmi controllers and
# none-cdmi controllers

from cdmibase import Consts
from swift.common.bufferedhttp import http_connect_raw, BufferedHTTPConnection
from webob import Request, Response

from eventlet.green.httplib import HTTPConnection


def get_err_response(code):
    """
    Given an HTTP response code, create a properly formatted error response

    :param code: error code
    :returns: webob.response object
    """

    error_table = {
        'AccessDenied':
            (403, 'Access denied'),
        'ContainerAlreadyExists':
            (409, 'The requested Container alredy exists'),
        'ContainerNotEmpty':
            (409, 'The container you tried to delete is not empty'),
        'InvalidArgument':
            (400, 'Invalid Argument'),
        'InvalidContainerName':
            (400, 'The specified container is not valid'),
        'InvalidURI':
            (400, 'Required header or the URI formation is not correct.'),
        'InvalidHeader':
            (400, 'CDMI required headers are not present in the request'),
        'InvalidContent':
            (400, 'CDMI request body is not in a correct format'),
        'BadRequest':
            (400, 'Bad request'),
        'NotContainer':
            (400, 'Requested resource is not a CDMI container'),
        'BadRequestPath':
            (400, 'Request url does not confirm with CDMI specification'),
        'InconsistantState':
            (400, 'The storage state is inconsistant.'),
        'VersionNotSupported':
            (400, 'Requested cdmi version is not supported.'),
        'InvalidRange':
            (400, 'Requested Range is not valid.'),
        'InvalidBody':
            (400, 'MIME message or the request body can not be parsed.'),
        'NoSuchContainer':
            (404, 'The specified container does not exist'),
        'ResourceIsNotObject':
            (404, 'The specified resource is not data object'),
        'NoParentContainer':
            (404, 'The parent container does not exist'),
        'NoSuchKey':
            (404, 'The resource you requested does not exist'),
        'Conflict':
            (409, 'The requested name already exists as a different type')}

    resp = Response()
    if error_table.get(code):
        resp.status = error_table[code][0]
        resp.body = error_table[code][1]
    else:
        resp.status = 400
        resp.body = 'Unknown Error'
    return resp


def get_pair_from_header(whole_value):
    """
    Parse the value of a metadata saved as OpenStack metadata.
    The separator between key and value is colon.
    """
    key, sep, value = whole_value.partition(':')
    return key, value


def check_resource(env, method, path, logger, get_body=False,
                   query_string=None):
    """
    Use this method to check if a resource already exist.
    If the resource exists, then it should return True with headers.
    If the resource does not exist, then it should return False with None
    headers
    If the get_body is set to True, the response body will also be returned
    """

    # Create a new Request
    req = Request(env)
    ssl = True if req.scheme.lower() == 'https' else False

    # Fixup the auth token, for some reason, the auth token padded the user
    # account at the front with a comma. We need to get rid of it, otherwise,
    # the auth token will be considered invalid.
    key, sep, value = req.headers[Consts.AUTH_TOKEN].partition(',')
    headers = {}
    headers[Consts.AUTH_TOKEN] = value if value != '' else key
    headers['Accept'] = 'application/json'
    method = 'GET' if not method else method
    path = req.path if not path else path
    path = path.rstrip('/')

    conn = http_connect_raw(req.server_name, req.server_port, method, path,
                            headers, query_string, ssl)
    res = conn.getresponse()

    if res.status == 404:
        conn.close()
        return False, {}, None
    elif res.status == 200 or res.status == 204:
        values = {}
        header_list = res.getheaders()
        for header in header_list:
            values[header[0]] = header[1]
        if get_body:
            length = res.getheader('content-length')
            if length:
                body = res.read(int(length))
            else:
                body = res.read()
        else:
            body = ""
        conn.close()
        return True, values, body
    else:
        values = {}
        header_list = res.getheaders()
        for header in header_list:
            values[header[0]] = header[1]
        conn.close()
        return True, values, None


def send_manifest(env, method, path, logger, extra_header, get_body=False,
                   query_string=None):
    """
    Use this method to send header against a resource already exist.
    """

    # Create a new Request
    req = Request(env)
    ssl = True if req.scheme.lower() == 'https' else False

    # Fixup the auth token, for some reason, the auth token padded the user
    # account at the front with a comma. We need to get rid of it, otherwise,
    # the auth token will be considered invalid.
    key, sep, value = req.headers[Consts.AUTH_TOKEN].partition(',')
    headers = {}
    headers[Consts.AUTH_TOKEN] = value if value != '' else key
    headers['Content-Length'] = '0'
    extra_header.update(headers)
    path = path.rstrip('/')

    if ssl:
        conn = HTTPSConnection('%s:%s' % (req.server_name,
                                          req.server_portport))
    else:
        conn = BufferedHTTPConnection('%s:%s' % (req.server_name,
                                                 req.server_port))

    conn.request('PUT', path, '', extra_header)

    res = conn.getresponse()

    return res
