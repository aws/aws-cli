# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.compat import compat_open
from awscli.testutils import BaseAWSCommandParamsTest, temporary_file


class TestRunInstances(BaseAWSCommandParamsTest):
    prefix = 'ec2 run-instances'

    def assert_run_instances_call(self, args, result):
        if not isinstance(args, list):
            args_list = (self.prefix + args).split()
        else:
            args_list = self.prefix.split() + args
        self.assert_params_for_cmd(
            args_list, result, ignore_params=['ClientToken']
        )

    def test_no_count(self):
        args = ' --image-id ami-foobar'
        result = {'ImageId': 'ami-foobar', 'MaxCount': 1, 'MinCount': 1}
        self.assert_run_instances_call(args, result)

    def test_count_scalar(self):
        args = ' --image-id ami-foobar --count 2'
        result = {'ImageId': 'ami-foobar', 'MaxCount': 2, 'MinCount': 2}
        self.assert_run_instances_call(args, result)

    def test_user_data(self):
        data = '\u0039'
        with temporary_file('r+') as tmp:
            with compat_open(tmp.name, 'w') as f:
                f.write(data)
                f.flush()
                args = ' --image-id foo --user-data file://%s' % f.name
                result = {
                    'ImageId': 'foo',
                    'MaxCount': 1,
                    'MinCount': 1,
                    # base64 encoded content of utf-8 encoding of data.
                    'UserData': 'OQ==',
                }
            self.assert_run_instances_call(args, result)

    def test_count_range(self):
        args = ' --image-id ami-foobar --count 5:10'
        result = {'ImageId': 'ami-foobar', 'MaxCount': 10, 'MinCount': 5}
        self.assert_run_instances_call(args, result)

    def test_count_in_json_only(self):
        input_json = '{"ImageId":"ami-xxxx","MaxCount":9,"MinCount":5}'
        args = ' --cli-input-json ' + input_json
        result = {'ImageId': 'ami-xxxx', 'MaxCount': 9, 'MinCount': 5}
        self.assert_run_instances_call(args, result)

    def test_count_in_cli_and_in_json(self):
        input_json = '{"ImageId":"ami-xxxx","MaxCount":9,"MinCount":5}'
        args = ' --count 3 --cli-input-json ' + input_json
        result = {'ImageId': 'ami-xxxx', 'MaxCount': 3, 'MinCount': 3}
        self.assert_run_instances_call(args, result)

    def test_block_device_mapping(self):
        args_list = ' --image-id ami-foobar --count 1'.split()
        # We're switching to list form because we need to test
        # when there's leading spaces.  This is the CLI equivalent
        # of --block-dev-mapping ' [{"device_name" ...'
        # (note the space between ``'`` and ``[``)
        args_list.append('--block-device-mapping')
        args_list.append(
            ' [{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20}}]'
        )
        result = {
            'BlockDeviceMappings': [
                {'DeviceName': '/dev/sda1', 'Ebs': {'VolumeSize': 20}},
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args_list, result)

    def test_secondary_ip_address(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--secondary-private-ip-addresses 10.0.2.106'
        args_list = (self.prefix + args).split()
        result = {
            'ImageId': 'ami-foobar',
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'PrivateIpAddresses': [
                        {'Primary': False, 'PrivateIpAddress': '10.0.2.106'}
                    ],
                }
            ],
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_secondary_ip_address_with_subnet(self):
        args = ' --image-id ami-foobar --count 1 --subnet subnet-12345678 '
        args += '--secondary-private-ip-addresses 10.0.2.106'
        result = {
            'ImageId': 'ami-foobar',
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'SubnetId': 'subnet-12345678',
                    'PrivateIpAddresses': [
                        {'Primary': False, 'PrivateIpAddress': '10.0.2.106'}
                    ],
                }
            ],
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_secondary_ip_addresses(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--secondary-private-ip-addresses 10.0.2.106 10.0.2.107'
        result = {
            'ImageId': 'ami-foobar',
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'PrivateIpAddresses': [
                        {'Primary': False, 'PrivateIpAddress': '10.0.2.106'},
                        {'Primary': False, 'PrivateIpAddress': '10.0.2.107'},
                    ],
                }
            ],
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_secondary_ip_address_count(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--secondary-private-ip-address-count 4'
        result = {
            'NetworkInterfaces': [
                {'DeviceIndex': 0, 'SecondaryPrivateIpAddressCount': 4}
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_secondary_ip_address_count_with_subnet(self):
        args = ' --image-id ami-foobar --count 1 --subnet subnet-12345678 '
        args += '--secondary-private-ip-address-count 4'
        result = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'SubnetId': 'subnet-12345678',
                    'SecondaryPrivateIpAddressCount': 4,
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_associate_public_ip_address(self):
        args = ' --image-id ami-foobar --count 1 --subnet-id subnet-12345678 '
        args += '--associate-public-ip-address'
        result = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'SubnetId': 'subnet-12345678',
                },
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_associate_public_ip_address_switch_order(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--associate-public-ip-address --subnet-id subnet-12345678'
        result = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'SubnetId': 'subnet-12345678',
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_no_associate_public_ip_address(self):
        args = ' --image-id ami-foobar --count 1  --subnet-id subnet-12345678 '
        args += '--no-associate-public-ip-address'
        result = {
            'ImageId': 'ami-foobar',
            'NetworkInterfaces': [
                {
                    'AssociatePublicIpAddress': False,
                    'DeviceIndex': 0,
                    'SubnetId': 'subnet-12345678',
                }
            ],
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_subnet_alone(self):
        args = ' --image-id ami-foobar --count 1 --subnet-id subnet-12345678'
        result = {
            'SubnetId': 'subnet-12345678',
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_associate_public_ip_address_and_group_id(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--security-group-id sg-12345678 '
        args += '--associate-public-ip-address --subnet-id subnet-12345678'
        result = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'SubnetId': 'subnet-12345678',
                    'Groups': ['sg-12345678'],
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_group_id_alone(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--security-group-id sg-12345678'
        result = {
            'SecurityGroupIds': ['sg-12345678'],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_associate_public_ip_address_and_private_ip_address(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--private-ip-address 10.0.0.200 '
        args += '--associate-public-ip-address --subnet-id subnet-12345678'
        result = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'SubnetId': 'subnet-12345678',
                    'PrivateIpAddresses': [
                        {'PrivateIpAddress': '10.0.0.200', 'Primary': True}
                    ],
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_private_ip_address_alone(self):
        args = ' --image-id ami-foobar --count 1 '
        args += '--private-ip-address 10.0.0.200'
        result = {
            'PrivateIpAddress': '10.0.0.200',
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, result)

    def test_ipv6_address_count_and_associate_public_ip_address(self):
        args = ' --associate-public-ip-address'
        args += ' --ipv6-address-count 5 --image-id ami-foobar --count 1'
        expected = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Ipv6AddressCount': 5,
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, expected)

    def test_ipv6_addresses_and_associate_public_ip_address(self):
        args = ' --associate-public-ip-address --count 1'
        args += ' --ipv6-addresses Ipv6Address=::1 --image-id ami-foobar '
        expected = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Ipv6Addresses': [{'Ipv6Address': '::1'}],
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, expected)

    def test_enable_primary_ipv6_and_associate_public_ip_address(self):
        args = ' --associate-public-ip-address'
        args += ' --enable-primary-ipv6 --image-id ami-foobar --count 1'
        expected = {
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'PrimaryIpv6': True,
                }
            ],
            'ImageId': 'ami-foobar',
            'MaxCount': 1,
            'MinCount': 1,
        }
        self.assert_run_instances_call(args, expected)
