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

"""
The cdmi middleware implements CDMI specification REST api on top of swift.

The following opperations are currently supported:

    * Login and Get Auth-Token
    * GET Account list children of the account
    * PUT Container and object for creating new and updating existings.
    * DELETE Container and object
    * GET Container and object

To add this middleware to your configuration, add the cdmi middleware
in front of the proxy-server middleware.
"""

from cdmiapp.cdmibase import \
    (Consts, concat_parts, ErrorController, LoginController, AccountController)
from cdmiapp.cdmicontrollers import \
    (ContainerController, ObjectController)
from cdmiapp.cdmicommoncontroller import \
    CDMICommonController
from cdmiapp.noncdmicontrollers import \
    (NonCDMIContainerController, NonCDMIObjectController)
from cdmiapp.cdmiutils import get_err_response
from webob import Request, Response
from urllib import unquote
from swift.common.utils import get_logger
from swift.common.utils import split_path


class CdmiMiddleware(object):
    """CDMI compatibility midleware"""

    def __init__(self, app, conf, *args, **kwargs):
        self.app = app
        self.conf = conf
        self.cdmi_root = conf.get('cdmi_root')
        self.cdmi_version_supported = conf.get('cdmi_version_supported')
        self.cdmi_root_length = conf.get('cdmi_root_length')
        self.cdmi_capability_id = conf.get('cdmi_capability_id')
        self.logger = get_logger(conf, log_route='cdmi')

    def get_container_controller_by_version(self, version):
        if version == '1.0.1':
            return ContainerController
        # Can add other statements here to support different versions with
        # different controller
        return None

    def get_object_controller_by_version(self, version):
        if version == '1.0.1':
            return ObjectController
        # Can add other statements here to support different versions with
        # different controller
        return None

    def get_controller(self, env, path, cdmi_version, method):
        if path.startswith('/' + self.cdmi_root):
            content_type = (env.get('CONTENT_TYPE') or '').lower()
            accept = (env.get('HTTP_ACCEPT') or '').lower()

            content_is_container = \
                content_type.find('application/cdmi-container') >= 0 or False

            content_is_object = (content_type.find('multipart/') >= 0 or
                content_type.find('application/cdmi-object') >= 0 or False)

            accept_is_container = \
                accept.find('application/cdmi-container') >= 0 or False

            accept_is_object = \
                accept.find('application/cdmi-object') >= 0 or False

            content_length = int(env.get('CONTENT_LENGTH') or '0')

            subs = path.lstrip('/ ').rstrip('/ ').split('/')

            # We first get rid of the cdmi_root which is no important
            # for rest of the work
            subs = subs[self.cdmi_root_length:]
            subs[len(subs):] = [None, None, None, None]
            if subs[0] == self.cdmi_capability_id:
                is_capability_request = True
                subs = subs[1:]
            else:
                is_capability_request = False

            account_name = subs[0]
            container_name = subs[1]
            parent_name = concat_parts(*subs[2:])
            if parent_name == '':
                parent_name = None
                object_name = None
            else:
                newsubs = parent_name.split('/')
                object_name = newsubs[-1]
                parent_name = '/'.join(newsubs[0:-1])

            if method in ['GET']:
                if account_name is None:
                    controller = LoginController
                elif container_name is None:
                    controller = AccountController
                    if is_capability_request:
                        env['HTTP_ACCEPT'] = 'application/cdmi-capability'
                else:
                    controller = CDMICommonController
                    if is_capability_request:
                        env['HTTP_ACCEPT'] = 'application/cdmi-capability'
                    # To setup a flag so that we know what the request wants
                    if (content_is_container or accept_is_container or
                        path.endswith('/')):
                        env['X-WANTS-CONTAINER'] = 'True'
                d = dict(container_name=container_name,
                         parent_name=parent_name,
                         object_name=object_name)
                return account_name, controller, d
            elif method in ['PUT']:
                if account_name:
                    if cdmi_version:
                        # Ensure that accept headers indicate what the client
                        # want to do, header overwrite trailing slash
                        # Only when no headers, the trailing slash plays
                        # an important role.
                        if (accept_is_container or
                            (path.endswith('/') and not accept_is_object)):
                            controller = ContainerController
                        elif (accept_is_object or not path.endswith('/')):
                            controller = ObjectController
                        else:
                            controller = ErrorController
                    else:
                        if path.endswith('/'):
                            controller = NonCDMIContainerController
                        else:
                            controller = NonCDMIObjectController
                else:
                    controller = ErrorController
                d = dict(container_name=container_name,
                         parent_name=parent_name,
                         object_name=object_name)
                return account_name, controller, d
            elif method in ['DELETE']:
                if account_name is None:
                    controller = ErrorController
                else:
                    controller = CDMICommonController
                d = dict(container_name=container_name,
                         parent_name=parent_name,
                         object_name=object_name)
                return account_name, controller, d
            else:
                controller = ErrorController
                d = dict(container_name=container_name,
                         parent_name=parent_name,
                         object_name=object_name)
                return account_name, controller, d
        else:
            d = dict(container_name=None, object_name=None)
            return None, None, d

    def __call__(self, env, start_response):

        path = unquote(env.get('PATH_INFO', ''))
        cdmi_version = env.get('HTTP_X_CDMI_SPECIFICATION_VERSION', False)
        method = env.get('REQUEST_METHOD').upper()
        # All CDMI requests have to have header with
        # the X-CDMI-Specification-Version
        if cdmi_version and self.cdmi_version_supported.find(cdmi_version) < 0:
            return get_err_response('VersionNotSupported')(env, start_response)

        # All non-CDMI request should not have the header
        # We use this header as the identifier to identify CDMI request.
        try:
            account, controller, path_parts = \
                self.get_controller(env, path, cdmi_version, method)
        except ValueError:
            return get_err_response('InvalidURI')(env, start_response)

        if controller is not None:
            controller = controller(env, self.conf, self.app,
                                    self.logger, account, **path_parts)
            if hasattr(controller, method) and not method.startswith('_'):
                res = getattr(controller, method)(env, start_response)
                return res(env, start_response)
            else:
                return get_err_response('BadRequest')(env, start_response)
        # Not CDMI request, move on
        else:
            return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""

    conf = global_conf.copy()
    conf.update(local_conf)

    # Process the cdmi root and strip off leading or trailing space and slashes
    cdmi_root = conf.setdefault('cdmi_root', 'cdmi')
    cdmi_root = cdmi_root.lstrip('/ ').rstrip('/ ')
    conf['cdmi_root'] = cdmi_root
    conf['cdmi_root_length'] = len(cdmi_root.split('/'))
    conf.setdefault('cdmi_version_supported', '1.0.1')
    conf.setdefault('cdmi_capability_id', 'cdmi_capabilities')

    def cdmi_filter(app):
        return CdmiMiddleware(app, conf)

    return cdmi_filter
