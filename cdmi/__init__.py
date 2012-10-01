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

from swift.common.utils import get_logger
from cdmi import CdmiMiddleware


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""

    conf = global_conf.copy()
    conf.update(local_conf)

    logger = get_logger(conf, log_route='cdmi')
    logger.info('CDMI implementation')

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
