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
#from test import get_config
from swift.common.utils import readconf

import httplib
import time
import json
import base64
import os


def get_config(section_name=None, defaults=None):
    """
    Attempt to get a test config dictionary.

    :param section_name: the section to read (all sections if not defined)
    :param defaults: an optional dictionary namespace of defaults
    """
    config_file = os.environ.get('SWIFT_TEST_CONFIG_FILE',
                                 '/etc/swift/test.conf')
    config = {}
    if defaults is not None:
        config.update(defaults)

    try:
        config = readconf(config_file, section_name)
    except SystemExit:
        if not os.path.exists(config_file):
            print >>sys.stderr, \
                'Unable to read test config %s - file not found' \
                % config_file
        elif not os.access(config_file, os.R_OK):
            print >>sys.stderr, \
                'Unable to read test config %s - permission denied' \
                % config_file
        else:
            print >>sys.stderr, \
                'Unable to read test config %s - section %s not found' \
                % (config_file, section_name)
    return config


def get_auth(auth_host, auth_port, auth_url, user_name, user_key, tenant_name):
    """Authenticate"""
    if auth_url.find('tokens') >= 0:
        """ v2.0 authentication"""
        conn = httplib.HTTPConnection(auth_host, auth_port)
        
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        body = {}
        body['auth'] = {
            "passwordCredentials": {
                "username": user_name,
                "password": user_key,
            },
            "tenantName": tenant_name
        }
        conn.request('POST', auth_url,
                     json.dumps(body, indent=2), headers)

        res = conn.getresponse()
        if res.status != 200:
            raise Exception('The authentication has failed')

        data = res.read()
        body = json.loads(data)
        token = body.get('access').get('token').get('id')
        endpoints = body.get('access').get('serviceCatalog')
        for endpoint in endpoints:
            if 'object-store' == endpoint.get('type'):
                public_url = endpoint.get('endpoints')[0].get('publicURL')
                parts = public_url.split('/')
                account_id = parts[-1]
                return token, account_id
    else:
        """ try the old way"""
        print 'basic auth'
