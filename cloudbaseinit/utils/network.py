# Copyright 2012 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from six.moves.urllib import parse
from six.moves.urllib import request

from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
import time


LOG = logging.getLogger(__name__)

MAX_URL_CHECK_RETRIES = 120


def check_url(url, retries_count=MAX_URL_CHECK_RETRIES):
    for i in range(0, MAX_URL_CHECK_RETRIES):
        try:
            LOG.debug("Testing url: %s" % url)
            request.urlopen(url)
            return True
        except Exception:
            time.sleep(1)
    return False


def check_metadata_ip_route(metadata_url):
    #Workaround for: https://bugs.launchpad.net/quantum/+bug/1174657
    osutils = osutils_factory.get_os_utils()

    if sys.platform == 'win32' and osutils.check_os_version(6, 0):
        # 169.254.x.x addresses are not getting routed starting from
        # Windows Vista / 2008
        metadata_netloc = parse.urlparse(metadata_url).netloc
        metadata_host = metadata_netloc.split(':')[0]

        if metadata_host.startswith("169.254."):
            if (not osutils.check_static_route_exists(metadata_host) and
                    not check_url(metadata_url)):
                (interface_index, gateway) = osutils.get_default_gateway()
                if gateway:
                    try:
                        LOG.debug('Setting gateway for host: %s',
                                  metadata_host)
                        osutils.add_static_route(metadata_host,
                                                 "255.255.255.255",
                                                 gateway,
                                                 interface_index,
                                                 10)
                    except Exception as ex:
                        # Ignore it
                        LOG.exception(ex)
