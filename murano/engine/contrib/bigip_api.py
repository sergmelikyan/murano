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

import bigsuds

import murano.common.config as config
import murano.dsl.helpers as helpers
import murano.dsl.murano_class as murano_class
import murano.dsl.murano_object as murano_object
import murano.openstack.common.log as logging

LOG = logging.getLogger(__name__)


@murano_class.classname('io.murano.contrib.bigIp.Api')
class BigIpApi(murano_object.MuranoObject):
    def initialize(self, _context):
        bigip_settings = config.CONF.bigip
        environment = helpers.get_environment(_context)
        self.partition_name = 'uuid_%s' % environment.tenant_id

        self.bigip = bigsuds.BIGIP(
            hostname=bigip_settings.hostname,
            username=bigip_settings.username,
            password=bigip_settings.password
        )

    # noinspection PyPep8Naming
    def createPool(self, name, port, balancingMethod):
        self.bigip.LocalLB.Pool.create_v2(
            pool_names=['/Common/%s' % name],
            lb_methods=[balancingMethod],
            members=[{}]
        )
        self.bigip.LocalLB.VirtualServer.create(
            definitions=[{
                'name': '/Common/%s_vip' % name,
                'address': '1.1.1.1',
                'port': port,
                'protocol': 'PROTOCOL_TCP'
            }],
            wildmasks=['255.255.255.255'],
            resources=[{
                'type': 'RESOURCE_TYPE_POOL',
                'default_pool_name': '/Common/%s' % name
            }],
            profiles=[[{
                'profile_context': 'PROFILE_CONTEXT_TYPE_ALL',
                'profile_name': '/Common/tcp'
            }]]
        )
        return '1.1.1.1'

    # noinspection PyPep8Naming
    def addMember(self, name, port, address):
        pool_name = '/{partition}/{pool_name}'.format(
            partition=self.partition_name,
            pool_name=name
        )
        self.bigip.LocalLB.Pool.add_member_v2(
            pool_names=[pool_name],
            members=[[{
                'port': port,
                'address': address}]]
        )

    # noinspection PyPep8Naming
    def setBalancingMethod(self, name, balancingMethod):
        pool_name = '/{partition}/{pool_name}'.format(
            partition=self.partition_name,
            pool_name=name
        )
        self.bigip.LocalLB.Pool.set_lb_method(
            pool_names=[pool_name],
            lb_methods=[balancingMethod]
        )

    # noinspection PyPep8Naming
    def addRule(self, name, definition):
        self.bigip.LocalLB.Rule.create(
            rules=[{'rule_name': name, 'rule_definition': definition}]
        )

    # noinspection PyPep8Naming
    def assignRule(self, name, virtual_server):
        virtual_server_name = '/{partition}/{virtual_server_name}'.format(
            partition=self.partition_name,
            virtual_server_name=virtual_server
        )
        self.bigip.LocalLB.VirtualServer.add_profile(
            virtual_servers=[virtual_server_name],
            profiles=[[{
                'profile_context': 'PROFILE_CONTEXT_TYPE_ALL',
                'profile_name': 'http'
            }]]
        )
        self.bigip.LocalLB.VirtualServer.add_rule(
            virtual_servers=[virtual_server_name],
            rules=[[{'rule_name': name, 'priority': 0}]]
        )

