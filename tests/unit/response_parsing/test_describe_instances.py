#!/usr/bin/env python
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

data = {'reservationSet': [{'ownerId': '419278470775', 'groupSet': [{'groupName': 'default', 'groupId': 'sg-2c9e7544'}], 'reservationId': 'r-765eaa10', 'instancesSet': [{'productCodes': [], 'instanceId': 'i-5578ec28', 'imageId': 'ami-e565ba8c', 'clientToken': '', 'amiLaunchIndex': 0, 'instanceType': 'm1.small', 'groupSet': [{'groupName': 'default', 'groupId': 'sg-2c9e7544'}], 'monitoring': {'state': 'disabled'}, 'dnsName': 'ec2-107-21-77-162.compute-1.amazonaws.com', 'kernelId': 'aki-88aa75e1', 'privateIpAddress': '10.208.45.119', 'virtualizationType': 'paravirtual', 'privateDnsName': 'domU-12-31-39-06-2A-8D.compute-1.internal', 'reason': '', 'blockDeviceMapping': [{'deviceName': '/dev/sda1', 'ebs': {'status': 'attached', 'deleteOnTermination': True, 'volumeId': 'vol-c94909b3', 'attachTime': '2012-10-04T15:32:54.000Z'}}], 'placement': {'groupName': '', 'tenancy': 'default', 'availabilityZone': 'us-east-1d'}, 'instanceState': {'code': 16, 'name': 'running'}, 'launchTime': '2012-10-04T15:32:50.000Z', 'architecture': 'x86_64', 'hypervisor': 'xen', 'rootDeviceType': 'ebs', 'ipAddress': '107.21.77.162', 'rootDeviceName': '/dev/sda1'}]}], 'requestId': '931a86ce-1415-4105-a851-79520622d582'}

class TestDescribeInstances(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('ec2', 'aws')

    def test_describe_instances(self):
        op = self.service.get_operation('DescribeInstances')
        r = botocore.response.Response(op)
        r.parse(six.b(xml))
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
