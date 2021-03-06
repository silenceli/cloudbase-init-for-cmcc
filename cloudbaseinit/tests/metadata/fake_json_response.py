# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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


def get_fake_metadata_json(version):
    if version == '2013-04-04':
        return {"random_seed":
                "Wn51FGjZa3vlZtTxJuPr96oCf+X8jqbA9U2XR5wNdnApy1fz"
                "/2NNssUwPoNzG6etw9RBn+XiZ0zKWnFzMsTopaN7WwYjWTnIsVw3cpIk"
                "Td579wQgoEr1ANqhfO3qTvkOVNMhzTAw1ps+wqRmkLxH+1qYJnX06Gcd"
                "KRRGkWTaOSlTkieA0LO2oTGFlbFDWcOW2vT5BvSBmqP7vNLzbLDMTc7M"
                "IWRBzwmtcVPC17QL6EhZJTUcZ0mTz7l0R0DocLmFwHEXFEEr+q4WaJjt"
                "1ejOOxVM3tiT7D8YpRZnnGNPfvEhq1yVMUoi8yv9pFmMmXicNBhm6zDK"
                "VjcWk0gfbvaQcMnnOLrrE1VxAAzyNyPIXBI/H7AAHz2ECz7dgd2/4ocv"
                "3bmTRY3hhcUKtNuat2IOvSGgMBUGdWnLorQGFz8t0/bcYhE0Dve35U6H"
                "mtj78ydV/wmQWG0iq49NX6hk+VUmZtSZztlkbsaa7ajNjZ+Md9oZtlhX"
                "Z5vJuhRXnHiCm7dRNO8Xo6HffEBH5A4smQ1T2Kda+1c18DZrY7+iQJRi"
                "fa6witPCw0tXkQ6nlCLqL2weJD1XMiTZLSM/XsZFGGSkKCKvKLEqQrI/"
                "XFUq/TA6B4aLGFlmmhOO/vMJcht06O8qVU/xtd5Mv/MRFzYaSG568Z/m"
                "hk4vYLYdQYAA+pXRW9A=",
                "uuid": "4b32ddf7-7941-4c36-a854-a1f5ac45b318",
                "availability_zone": "nova",
                "hostname": "windows.novalocal",
                "launch_index": 0,
                "public_keys": {"key": "ssh-rsa "
                                       "AAAAB3NzaC1yc2EAAAADAQABAAABA"
                                "QDf7kQHq7zvBod3yIZs0tB/AOOZz5pab7qt/h"
                                "78VF7yi6qTsFdUnQxRue43R/75wa9EEyokgYR"
                                "LKIN+Jq2A5tXNMcK+rNOCzLJFtioAwEl+S6VL"
                                "G9jfkbUv++7zoSMOsanNmEDvG0B79MpyECFCl"
                                "th2DsdE4MQypify35U5ri5Qi7E6PEYAsU65LF"
                                "MG2boeCIB29BEooE6AgPr2DuJeJ+2uw+YScF9"
                                "FV3og4Wyz5zipPVh8YpVev6dlg0tRWUrCtZF9"
                                "IODpCTrT3vsPRG3xz7CppR+vGi/1gLXHtJCRj"
                                "frHwkY6cXyhypNmkU99K/wMqSv30vsDwdnsQ1"
                                "q3YhLarMHB Generated by Nova\n",
                                0: "windows"},
                "network_config": {"content_path": "network",
                                   'debian_config': 'iface eth0 inet static'
                                                    'address 10.11.12.13'
                                                    'broadcast 0.0.0.0'
                                                    'netmask 255.255.255.255'
                                                    'gateway 1.2.3.4'
                                                    'dns-nameserver 8.8.8.8'}}
