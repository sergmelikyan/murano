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

import base64
import urlparse

import json
import requests

import murano.common.config as config
import murano.dsl.murano_class as murano_class
import murano.dsl.murano_object as murano_object
import murano.openstack.common.log as logging

LOG = logging.getLogger(__name__)


@murano_class.classname('io.murano.contrib.vyatta.Api')
class VyattaApi(murano_object.MuranoObject):
    def initialize(self, _context):
        self.vy_conf = config.CONF.vyatta

        auth = base64.b64encode('{username}:{password}'.format(
            username=self.vy_conf.username,
            password=self.vy_conf.password,
        ))

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Vyatta-Specification-Version': '0.1',
            'Authorization': 'Basic %s' % auth
        })

        self.base_url = 'http://%s' % self.vy_conf.hostname

    def configure(self):
        response = self.session.post(
            urlparse.urljoin(self.base_url, '/rest/conf/')
        )
        response.raise_for_status()
        url = response.headers['Location'] + '/'
        self.base_url = urlparse.urljoin(self.base_url, url)

    def save(self):
        r = self.session.post(
            urlparse.urljoin(self.base_url, 'commit')
        )
        r.raise_for_status()
        r = self.session.post(
            urlparse.urljoin(self.base_url, 'save')
        )
        r.raise_for_status()
        self.base_url = 'http://%s' % self.vy_conf.hostname

    # noinspection PyPep8Naming
    def openPort(self, instanceName, instanceIp, port):
        self.configure()
        base = 'set/firewall/name/%s/rule/10/' % instanceName

        # set action
        call = base + 'action/accept'
        r = self.session.put(
            urlparse.urljoin(self.base_url, call)
        )
        r.raise_for_status()
        # set protocol
        call = base + 'protocol/tcp'
        r = self.session.put(
            urlparse.urljoin(self.base_url, call)
        )
        r.raise_for_status()
        # set address
        call = base + 'destination/address/{0}%2F24'.format(instanceIp)
        r = self.session.put(
            urlparse.urljoin(self.base_url, call)
        )
        r.raise_for_status()
        # set port
        call = base + 'destination/port/{0}'.format(port)
        r = self.session.put(
            urlparse.urljoin(self.base_url, call)
        )
        r.raise_for_status()

        self.save()
