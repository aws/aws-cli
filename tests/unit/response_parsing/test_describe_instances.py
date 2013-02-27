#!/usr/bin/env python
# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest
import six
import botocore.session
import botocore.response

xml = """<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2011-07-15/">
    <requestId>931a86ce-1415-4105-a851-79520622d582</requestId>
    <reservationSet>
        <item>
            <reservationId>r-765eaa10</reservationId>
            <ownerId>419278470775</ownerId>
            <groupSet>
                <item>
                    <groupId>sg-2c9e7544</groupId>
                    <groupName>default</groupName>
                </item>
            </groupSet>
            <instancesSet>
                <item>
                    <instanceId>i-5578ec28</instanceId>
                    <imageId>ami-e565ba8c</imageId>
                    <instanceState>
                        <code>16</code>
                        <name>running</name>
                    </instanceState>
                    <privateDnsName>domU-12-31-39-06-2A-8D.compute-1.internal</privateDnsName>
                    <dnsName>ec2-107-21-77-162.compute-1.amazonaws.com</dnsName>
                    <reason/>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>m1.small</instanceType>
                    <launchTime>2012-10-04T15:32:50.000Z</launchTime>
                    <placement>
                        <availabilityZone>us-east-1d</availabilityZone>
                        <groupName/>
                        <tenancy>default</tenancy>
                    </placement>
                    <kernelId>aki-88aa75e1</kernelId>
                    <monitoring>
                        <state>disabled</state>
                    </monitoring>
                    <privateIpAddress>10.208.45.119</privateIpAddress>
                    <ipAddress>107.21.77.162</ipAddress>
                    <groupSet>
                        <item>
                            <groupId>sg-2c9e7544</groupId>
                            <groupName>default</groupName>
                        </item>
                    </groupSet>
                    <architecture>x86_64</architecture>
                    <rootDeviceType>ebs</rootDeviceType>
                    <rootDeviceName>/dev/sda1</rootDeviceName>
                    <blockDeviceMapping>
                        <item>
                            <deviceName>/dev/sda1</deviceName>
                            <ebs>
                                <volumeId>vol-c94909b3</volumeId>
                                <status>attached</status>
                                <attachTime>2012-10-04T15:32:54.000Z</attachTime>
                                <deleteOnTermination>true</deleteOnTermination>
                            </ebs>
                        </item>
                    </blockDeviceMapping>
                    <virtualizationType>paravirtual</virtualizationType>
                    <clientToken/>
                    <hypervisor>xen</hypervisor>
                </item>
            </instancesSet>
        </item>
    </reservationSet>
</DescribeInstancesResponse>"""

data = {'Reservations': [{'OwnerId': '419278470775', 'ReservationId':
                          'r-765eaa10', 'Groups': [{'GroupName': 'default',
                                                    'GroupId': 'sg-2c9e7544'}],
                          'Instances': [{'Monitoring': {'State': 'disabled'},
                                         'PublicDnsName':
                                         'ec2-107-21-77-162.compute-1.amazonaws.com',
                                         'RootDeviceType': 'ebs', 'State':
                                         {'Code': 16, 'Name': 'running'},
                                         'LaunchTime':
                                         '2012-10-04T15:32:50.000Z',
                                         'PublicIpAddress': '107.21.77.162',
                                         'PrivateIpAddress': '10.208.45.119',
                                         'ProductCodes': [],
                                         'StateTransitionReason': '',
                                         'InstanceId': 'i-5578ec28', 'ImageId':
                                         'ami-e565ba8c', 'PrivateDnsName':
                                         'domU-12-31-39-06-2A-8D.compute-1.internal',
                                         'SecurityGroups': [{'GroupName': 'default',
                                                     'GroupId':
                                                     'sg-2c9e7544'}],
                                         'ClientToken': '', 'InstanceType':
                                         'm1.small', 'Placement': {'Tenancy':
                                                                   'default',
                                                                   'GroupName':
                                                                   '',
                                                                   'AvailabilityZone':
                                                                   'us-east-1d'},
                                         'Hypervisor': 'xen',
                                         'BlockDeviceMappings': [{'DeviceName':
                                                                  '/dev/sda1',
                                                                  'Ebs':
                                                                  {'Status':
                                                                   'attached',
                                                                   'DeleteOnTermination':
                                                                   True,
                                                                   'VolumeId':
                                                                   'vol-c94909b3',
                                                                   'AttachTime':
                                                                   '2012-10-04T15:32:54.000Z'}}],
                                         'Architecture': 'x86_64', 'KernelId':
                                         'aki-88aa75e1', 'RootDeviceName':
                                         '/dev/sda1', 'VirtualizationType':
                                         'paravirtual', 'AmiLaunchIndex':
                                         0}]}], 'requestId':
        '931a86ce-1415-4105-a851-79520622d582'}


class TestDescribeInstances(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('ec2', 'aws')

    def test_describe_instances(self):
        op = self.service.get_operation('DescribeInstances')
        r = botocore.response.XmlResponse(op)
        r.parse(six.b(xml))
        self.maxDiff = None
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
