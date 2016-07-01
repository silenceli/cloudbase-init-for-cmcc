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

import os

from oslo.config import cfg

from cloudbaseinit.plugins import base
from cloudbaseinit.plugins.windows import fileexecutils

opts = [
    cfg.StrOpt('local_scripts_path', default=None,
               help='Path location containing scripts to be executed when '
                    'the plugin runs'),
]

CONF = cfg.CONF
CONF.register_opts(opts)


class LocalScriptsPlugin(base.BasePlugin):

    def _get_files_in_dir(self, path):
        return sorted([os.path.join(path, f) for f in os.listdir(path)
                       if os.path.isfile(os.path.join(path, f))])

    def execute(self, service, shared_data):
        if CONF.local_scripts_path:
            for file_path in self._get_files_in_dir(CONF.local_scripts_path):
                fileexecutils.exec_file(file_path)

        return (base.PLUGIN_EXECUTION_DONE, False)
