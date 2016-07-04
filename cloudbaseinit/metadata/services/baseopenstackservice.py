# Copyright 2014 Cloudbase Solutions Srl
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

import json
import posixpath

from oslo.config import cfg

from cloudbaseinit.metadata.services import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.utils import x509constants
import yaml

opts = [
    cfg.StrOpt('metadata_base_url', default='http://169.254.169.254/',
               help='The base URL where the service looks for metadata'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class BaseOpenStackService(base.BaseMetadataService):

    def get_content(self, name):
        path = posixpath.normpath(
            posixpath.join('openstack', 'content', name))
        return self._get_cache_data(path)

    def get_user_data(self):
        path = posixpath.normpath(
            posixpath.join('openstack', 'latest', 'user_data'))
        return self._get_cache_data(path)

    def _get_meta_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join('openstack', version, 'meta_data.json'))
        data = self._get_cache_data(path)
        return json.loads(data.decode('utf8'))

    def get_instance_id(self):
        return self._get_meta_data().get('uuid')

    def get_host_name(self):
        return self._get_meta_data().get('hostname')

    def get_public_keys(self):
        public_keys = self._get_meta_data().get('public_keys')
        if public_keys:
            return public_keys.values()

    def get_network_config(self):
        return self._get_meta_data().get('network_config')

    def get_admin_password(self):
        user_data = self.get_user_data()
        if user_data == None:
            LOG.debug('user_data is None')
            return None
        elif user_data == '':
            LOG.debug('user_data is NULL')
            return None
        LOG.info('get user_data OK')
        #pos_line_1 is list, contain the position of any #cloud-config
        pos_line_1 = []
        pos = user_data.find("#cloud-config")
        if pos == -1:
            LOG.warn("user-data contain no #cloud-config, password will be setted to default pw.")
            return None
        #get all #cloud-config position into pos_line_1
        while pos != -1:
            pos_line_1.append(pos)
            pos = user_data.find("#cloud-config", pos + len("#cloud-config"))
        
        i = 0
        #1. we get password from first #cloud-config, if not have, we get from second #cloud-config
        #and so on
        #next_pos is the next position of #cloud-config in user_data
        while i < len(pos_line_1):
            if len(pos_line_1) <= (i + 1):
                next_pos = -1
            else:
                next_pos = pos_line_1[i+1]
            pos_2 = user_data.find("disable_root:", pos_line_1[i]+1)
            if pos_2 == -1:
                LOG.warn("user-data contain no disable_root:, password will be setted to default pw.")
                return None
            elif pos_2 >= next_pos and next_pos != -1:
                i = i + 1
                continue
            pos_3 = user_data.find("password:", pos_2+1)
            if pos_3 == -1:
                LOG.warn("user-data contain no password:, password will be setted to default pw.")
                return None
            elif pos_3 >= next_pos and next_pos != -1:
                i = i + 1
                continue
            pos_4 = user_data.find("chpasswd:", pos_3+1)
            if pos_4 == -1:
                LOG.warn("user-data contain no chpasswd:, password will be setted to default pw.")
                return None
            elif pos_4 >= next_pos and next_pos != -1:
                i = i + 1
                continue
            password = user_data[pos_3 + len("password:"):pos_4]
            LOG.info("we got password from user-data")
            return password.lstrip()
        LOG.warn("Should not come here, password will be setted to default pw.")
        return None


    def get_client_auth_certs(self):
        cert_data = None

        meta_data = self._get_meta_data()
        meta = meta_data.get('meta')

        if meta:
            i = 0
            while True:
                # Chunking is necessary as metadata items can be
                # max. 255 chars long
                cert_chunk = meta.get('admin_cert%d' % i)
                if not cert_chunk:
                    break
                if not cert_data:
                    cert_data = cert_chunk
                else:
                    cert_data += cert_chunk
                i += 1

        if not cert_data:
            # Look if the user_data contains a PEM certificate
            try:
                user_data = self.get_user_data()
                if user_data.startswith(x509constants.PEM_HEADER):
                    cert_data = user_data
            except base.NotExistingMetadataException:
                LOG.debug("user_data metadata not present")

        if cert_data:
            return [cert_data]
