# Copyright (c) 2014 Mirantis Inc.
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

import json
import requests

import murano.common.config as config
import murano.dsl.murano_class as murano_class
import murano.dsl.murano_object as murano_object
import murano.openstack.common.log as logging

LOG = logging.getLogger(__name__)


@murano_class.classname('io.murano.contrib.zabbix.Api')
class ZabbixApi(murano_object.MuranoObject):
    def initialize(self, _context):
        self.zb_conf = config.CONF.zabbix

        self.session = requests.Session()
        # Default headers for all requests
        self.session.headers.update({
            'Content-Type': 'application/json-rpc',
            'User-Agent': 'python/pyzabbix'
        })

        self.req_id = 0
        self.auth_token = 0
        self.url = 'http://%s/zabbix/api_jsonrpc.php' % self.zb_conf.hostname

        self.authenticate()

    def authenticate(self):
        params = {
            'user': self.zb_conf.username,
            'password': self.zb_conf.password
        }
        self.auth_token = self.doRequest('user.login', params=params)['result']

    # noinspection PyPep8Naming
    def doRequest(self, method, params=None):
        request_json = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params or {},
            'id': self.req_id,
        }

        if self.auth_token:
            request_json['auth'] = self.auth_token

        response = self.session.post(
            self.url,
            data=json.dumps(request_json),
            timeout=30
        )
        response.raise_for_status()

        if not len(response.text):
            raise Exception("Received empty response")

        try:
            response_json = json.loads(response.text)
        except ValueError:
            raise Exception(
                "Unable to parse json: %s" % response.text
            )

        self.req_id += 1

        return response_json

    # noinspection PyPep8Naming
    def createGroup(self, name):
        response = self.doRequest('hostgroup.create', params={'name': name})
        return response['result']['groupids'][0]

    # noinspection PyPep8Naming
    def createHost(self, groupId, instanceIp, name):
        params = {
            'host': name,
            'ip': instanceIp,
            'port': 80,
            'useip': 1,
            "groups": [{
                "groupid": groupId,
            }]
        }
        response = self.doRequest('host.create', params=params)
        return response['result']['hostids'][0]

    # noinspection PyPep8Naming
    def createItem(self, hostId, key):
        params = {
            'description': 'check host',
            'type': 3,
            'delay': 5,
            'key_': key,
            'hostid': hostId
        }
        response = self.doRequest('item.create', params=params)
        return response

    # noinspection PyPep8Naming
    def addProbe(self, probeType, instanceIp, name):
        http_key, ping_key = 'http', 'icmpping'

        groupId = self.createGroup('%s-group' % name)
        hostId = self.createHost(groupId, instanceIp, name)

        key = http_key if probeType == 'HTTP' else ping_key
        self.createItem(hostId, key)
